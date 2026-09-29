# orionis.cache

> Capa de caché asíncrona basada en drivers (memoria, archivo, Redis, Memcached, base de datos) más la caché síncrona de artefactos que usa el arranque del framework.

## Tabla de contenidos

- [Descripción funcional](#descripción-funcional)
  - [Dónde encaja en el framework](#dónde-encaja-en-el-framework)
  - [Cadena de resolución](#cadena-de-resolución)
  - [Mapa de archivos](#mapa-de-archivos)
  - [Decisiones de diseño](#decisiones-de-diseño)
- [Referencia de API](#referencia-de-api)
  - [Fachada `Cache`](#fachada-cache)
  - [`ICacheManager` / `CacheManager`](#icachemanager--cachemanager)
  - [`ICacheRepository` / `CacheRepository`](#icacherepository--cacherepository)
  - [`CacheLock`](#cachelock)
  - [`FileCacheBackend`](#filecachebackend)
  - [`DatabaseCacheBackend`](#databasecachebackend)
  - [Fábricas de backend](#fábricas-de-backend)
  - [`MsgspecSerializer`](#msgspecserializer)
  - [`Serializer`](#serializer)
  - [`IFileBasedCache` / `FileBasedCache`](#ifilebasedcache--filebasedcache)
  - [`CacheProvider`](#cacheprovider)
  - [Excepciones](#excepciones)
  - [Entidades de configuración](#entidades-de-configuración)
- [Ejemplos de uso](#ejemplos-de-uso)
- [Rendimiento y concurrencia](#rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)

## Descripción funcional

`orionis.cache` resuelve dos problemas que no están relacionados entre sí más
allá de compartir la palabra *caché*:

1. **Caché de aplicación**: un almacén clave/valor asíncrono con drivers
   intercambiables (`memory`, `file`, `redis`, `memcached`, `database`), TTL,
   lecturas y escrituras por lotes, helpers de memoización (`remember`) y
   bloqueos distribuidos. Se accede por la fachada `Cache` o inyectando
   `ICacheManager`.
2. **Caché de artefactos**: `FileBasedCache` junto a `Serializer`, una caché
   *síncrona* de un solo archivo con invalidación por cambios en las fuentes,
   usada internamente por `orionis.foundation.application`,
   `orionis.console.core.loader` y `orionis.http.routes.loader` para no volver a
   escanear el proyecto en cada arranque.

### Dónde encaja en el framework

| Consumidor | Qué usa |
|---|---|
| `orionis.foundation.core_providers` | Registra `CacheProvider` como provider del núcleo |
| `orionis.session.stores.cache.CacheSessionStore` | Recibe un `ICacheManager` y llama a `store(name)` |
| `orionis.foundation.application` | Construye un `FileBasedCache` para el estado compilado del bootstrap |
| `orionis.console.core.loader.Loader` | Cachea en un `FileBasedCache` la metadata de los comandos descubiertos |
| `orionis.http.routes.loader` | Cachea en un `FileBasedCache` las rutas compiladas |
| `orionis.orm.resolver.ConnectionResolver` | Aporta el `IConnection` que usa el driver `database` |

### Cadena de resolución

```text
Cache (fachada, orionis.support.facades.cache)
 └── ICacheManager ──singleton──► CacheManager(app)
        │  app.config("cache") → entidad Cache (default, prefix, stores)
        └── store(name) ─────────► CacheRepository(backend, prefix)   [memoizado por nombre]
                                      └── backend
                                          memory     → aiocache.SimpleMemoryCache
                                          redis      → aiocache.backends.redis.RedisCache
                                          memcached  → aiocache.backends.memcached.MemcachedCache
                                          database   → DatabaseCacheBackend(IConnection)
                                          <cualquier otro nombre> → FileCacheBackend(path)
```

`CacheRepository.lock(key, timeout)` devuelve un `CacheLock`, que elige su
implementación según el tipo de backend: `asyncio.Lock` para
`FileCacheBackend`, un bloqueo por fila para `DatabaseCacheBackend` y
`aiocache.lock.RedLock` para el resto.

### Mapa de archivos

| Ruta | Contenido |
|---|---|
| `__init__.py` | Exporta `CacheManager`, `CacheRepository`, `FileBasedCache` |
| `cache_manager.py` | `CacheManager`: resolución de stores y proxy del store por defecto |
| `repository.py` | `CacheRepository`: prefijado y API de alto nivel |
| `exceptions.py` | `CacheException`, `CacheStoreException` |
| `file_based_cache.py` | `FileBasedCache`: caché síncrona de artefactos |
| `serializer.py` | `Serializer`: codificador/decodificador JSON con etiquetas de tipo |
| `provider.py` | `CacheProvider`: bindings del contenedor y pin de la fachada |
| `contracts/` | `ICacheManager`, `ICacheRepository`, `IFileBasedCache` |
| `locks/lock.py` | `CacheLock`: bloqueo como context manager asíncrono |
| `serializers/json.py` | `MsgspecSerializer`: serializador de aiocache sobre msgspec |
| `stores/memory.py` | `build()` → `SimpleMemoryCache` |
| `stores/redis.py` | `build()` → `RedisCache` |
| `stores/memcached.py` | `build()` → `MemcachedCache` |
| `stores/file.py` | `FileCacheBackend`: un archivo JSON por clave |
| `stores/database.py` | `DatabaseCacheBackend` + definiciones de tabla + `build()` |

`locks/__init__.py`, `stores/__init__.py` y `serializers/__init__.py` están
vacíos; hay que importar los módulos concretos directamente.

### Decisiones de diseño

- `CacheManager`, `CacheRepository`, `CacheLock`, `FileCacheBackend` y
  `DatabaseCacheBackend` declaran `__slots__`: las instancias no llevan
  `__dict__`.
- `CacheProvider` hereda de `ServiceProvider` y de `DeferrableProvider`, así que
  el binding (y el pin de la fachada) solo ocurre al resolver `ICacheManager`
  por primera vez. Eso cambia el comportamiento de la fachada; ver
  [Fachada `Cache`](#fachada-cache).
- `CacheManager.store()` memoiza un `CacheRepository` por nombre de store
  resuelto, de modo que un nombre corresponde a exactamente una instancia de
  backend por manager.
- El prefijo de claves lo aplica `CacheRepository._k()`, no los backends: un
  repositorio construido a mano con `prefix=""` escribe claves sin prefijo.
- `remember()` y `pull()` leen usando un centinela privado `_MISSING`, así que
  un `None` almacenado es un acierto, no un fallo de caché.
- `FileCacheBackend` y `DatabaseCacheBackend` exponen métodos en camelCase
  (`multiGet`, `multiSet`) y también en el snake_case de aiocache (`multi_get`,
  `multi_set`); eso es lo que permite que `CacheRepository` hable con los
  backends de aiocache y con los propios usando el mismo código.
- Los tres backends de aiocache se construyen siempre con
  `MsgspecSerializer`, de modo que los valores se codifican en JSON en todos los
  drivers en lugar de guardarse con pickle o en crudo.
- `FileBasedCache` **no** hereda de `IFileBasedCache` ni está registrada en el
  contenedor; los consumidores la instancian directamente.
- Ni `ICacheManager` ni `ICacheRepository` declaran `lock()`, aunque tanto
  `CacheManager` como `CacheRepository` lo implementan.

## Referencia de API

### Fachada `Cache`

`orionis.support.facades.cache.Cache` es una `Facade` cuyo accessor es
`ICacheManager`:

```python
class Cache(Facade):
    @classmethod
    def getFacadeAccessor(cls) -> type: ...
```

Como `CacheProvider` es diferido, la fachada **no** está fijada (pinned) cuando
arranca la aplicación. El comportamiento de cada acceso depende de ese estado:

| Acceso | Fachada sin pin | Fachada con pin |
|---|---|---|
| `await Cache.get("k")` | Funciona (el dispatcher resuelve y hace await) | Funciona |
| `async with Cache.lock("k"):` | Funciona (`_FacadeDispatch.__aenter__`) | Funciona |
| `Cache.store("memory")` | Devuelve un `_FacadeDispatch`, no un repositorio | Devuelve `CacheRepository` |
| `await Cache.store("memory")` | Devuelve `CacheRepository` | `TypeError: 'CacheRepository' object can't be awaited` |

El primer `await` a través de la fachada resuelve `ICacheManager`, lo que
dispara el registro diferido, ejecuta `CacheProvider.boot()` y fija la fachada;
a partir de ahí los métodos síncronos (`store`, `lock`) deben llamarse *sin*
`await`. El código que deba funcionar en ambos estados conviene que inyecte
`ICacheManager` en lugar de usar la fachada.

### `ICacheManager` / `CacheManager`

`ICacheManager` (`contracts/cache_manager.py`) es un `ABC` que declara `store`
más los trece proxies del store por defecto. `CacheManager` lo implementa.

```python
class CacheManager(ICacheManager):
    __slots__ = (
        "_app",
        "_base_path",
        "_config",
        "_default",
        "_prefix",
        "_repositories",
    )

    def __init__(self, app: IApplication) -> None: ...
```

`__init__` lee `app.config("cache")`. Si ese valor es un `dict` lo convierte a
la entidad de configuración `Cache`; en caso contrario lo usa tal cual.
`_default` y `_prefix` se convierten con `str()`, y `_base_path` es
`app.basePath`.

| Método | Firma | Notas |
|---|---|---|
| `store` | `store(self, name: str \| None = None) -> CacheRepository` | Memoizado por nombre; `None` selecciona `config.default` |
| `get` | `async get(self, key: str) -> Any` | Delega en `store().get` |
| `set` | `async set(self, key: str, value: Any, ttl: float \| None = None) -> bool` | |
| `has` | `async has(self, key: str) -> bool` | |
| `delete` | `async delete(self, key: str) -> bool` | |
| `clear` | `async clear(self) -> bool` | |
| `getMany` | `async getMany(self, keys: list[str]) -> dict[str, Any]` | |
| `setMany` | `async setMany(self, values: dict[str, Any], ttl: float \| None = None) -> bool` | |
| `remember` | `async remember(self, key: str, ttl: float \| None, resolver: Callable) -> Any` | |
| `rememberForever` | `async rememberForever(self, key: str, resolver: Callable) -> Any` | |
| `pull` | `async pull(self, key: str) -> Any` | |
| `add` | `async add(self, key: str, value: Any, ttl: float \| None = None) -> bool` | |
| `increment` | `async increment(self, key: str, amount: int = 1) -> int` | |
| `decrement` | `async decrement(self, key: str, amount: int = 1) -> int` | |
| `lock` | `lock(self, key: str, timeout: float \| None = None) -> Any` | No está declarado en `ICacheManager` |

**Resolución de stores** (`_buildBackend`, se ejecuta una vez por nombre):

| `name` | Backend | Lanza |
|---|---|---|
| `"memory"` | `SimpleMemoryCache` | — |
| `"redis"` | `RedisCache` | `CacheStoreException` si `stores.redis` es `None` |
| `"memcached"` | `MemcachedCache` | `CacheStoreException` si `stores.memcached` es `None` |
| `"database"` | `DatabaseCacheBackend` | `CacheStoreException` si `stores.database` es `None` |
| cualquier otro valor | `FileCacheBackend` | — |

La última fila es la rama final de `_buildBackend`: un nombre de store
desconocido produce en silencio un repositorio respaldado por archivos, no un
error. La ruta sale de `stores.file.path` (por defecto
`storage/framework/cache/data`) y, si es relativa, se resuelve contra
`app.basePath`.

La rama `database` obtiene su conexión mediante
`ConnectionResolver.connection(...)`, así que requiere que el gestor de
conexiones del ORM esté instalado; si no, `ConnectionResolver` lanza
`OrmConfigurationException`.

### `ICacheRepository` / `CacheRepository`

`replace(key, value, ttl=None) -> bool` reemplaza atómicamente una entrada vigente
sin crear claves ausentes. Archivos usan stripes de `filelock` entre procesos;
SQL usa UPDATE condicional; backends aiocache usan CAS de OptimisticLock rechazando
claves ausentes. Un cambio concurrente puede devolver False. Repositorios propios
deben implementar este contrato para sesiones de caché seguras.

```python
class CacheRepository(ICacheRepository):
    __slots__ = ("_backend", "_prefix")

    def __init__(self, backend: Any, prefix: str = "") -> None: ...
```

Las claves pasan por `_k(key)`, que devuelve `f"{prefix}:{key}"` cuando hay
prefijo configurado y la clave sin tocar en caso contrario.

| Método | Firma | Comportamiento |
|---|---|---|
| `get` | `async get(self, key: str) -> Any` | `backend.get(_k(key))`; `None` si no existe |
| `set` | `async set(self, key: str, value: Any, ttl: float \| None = None) -> bool` | Resultado convertido con `bool()` |
| `has` | `async has(self, key: str) -> bool` | Usa `backend.exists()`, nunca deserializa |
| `delete` | `async delete(self, key: str) -> bool` | `True` si la clave existía |
| `clear` | `async clear(self) -> bool` | Vacía el backend completo |
| `getMany` | `async getMany(self, keys: list[str]) -> dict[str, Any]` | `backend.multi_get`; se reasocia con `zip(..., strict=True)` a los nombres originales |
| `setMany` | `async setMany(self, values: dict[str, Any], ttl: float \| None = None) -> bool` | `backend.multi_set` con pares ya prefijados |
| `remember` | `async remember(self, key: str, ttl: float \| None, resolver: Callable) -> Any` | Si falla la caché llama a `resolver()`, hace await si es awaitable, guarda y devuelve |
| `rememberForever` | `async rememberForever(self, key: str, resolver: Callable) -> Any` | `remember(key, None, resolver)` |
| `pull` | `async pull(self, key: str) -> Any` | Lee y borra; `None` si no existe |
| `add` | `async add(self, key: str, value: Any, ttl: float \| None = None) -> bool` | Captura el `ValueError` del backend y devuelve `False` |
| `increment` | `async increment(self, key: str, amount: int = 1) -> int` | `backend.increment(_k(key), amount)` |
| `decrement` | `async decrement(self, key: str, amount: int = 1) -> int` | `backend.increment(_k(key), -amount)` |
| `lock` | `lock(self, key: str, timeout: float \| None = None) -> CacheLock` | Síncrono; devuelve un context manager asíncrono. No está declarado en `ICacheRepository` |

`remember` y `pull` llaman a `backend.get(key, default=_MISSING)` con un
centinela privado a nivel de módulo, así que un `None` cacheado se devuelve tal
cual en vez de disparar un recálculo.

### `CacheLock`

```python
class CacheLock:
    __slots__ = ("_backend", "_impl", "_key", "_owner", "_timeout")

    def __init__(
        self,
        backend: Any,
        key: str,
        timeout: float | None = None,
    ) -> None: ...
```

Constantes de módulo: `_DEFAULT_LEASE = 10`, `_POLL_INTERVAL = 0.05` y
`_FILE_LOCKS: dict[str, asyncio.Lock]`.

`__aenter__` decide según el tipo de backend:

| Backend | Implementación | Comportamiento del timeout |
|---|---|---|
| `FileCacheBackend` | `asyncio.Lock` obtenido del dict `_FILE_LOCKS` (ámbito de proceso) | `asyncio.wait_for` → `TimeoutError` |
| `DatabaseCacheBackend` | Sondea `backend.acquireLock(key, owner, lease)` cada `0.05 s`; `owner` es un `uuid4().hex` y `lease` es `timeout or 10` | `TimeoutError` al superar el plazo |
| cualquier otro | `aiocache.lock.RedLock(backend, key, lease=timeout or 10)` | Delegado en `RedLock` |

`__aexit__` libera el `asyncio.Lock`, llama a `backend.releaseLock(key, owner)`
o delega en `RedLock.__aexit__`, según la rama tomada al entrar.

### `FileCacheBackend`

```python
class FileCacheBackend:
    __slots__ = ("_counter_lock", "_path", "_rename_lock")

    def __init__(self, path: Path) -> None: ...
```

Crea el directorio al construirse. Cada clave se hashea con SHA-256 y se guarda
como `<digest>.json`, con el contenido `{"v": <valor>, "e": <vencimiento |
None>}` codificado con `msgspec.json`. El vencimiento es
`time.monotonic() + ttl`.

| Método | Firma | Notas |
|---|---|---|
| `get` | `async get(self, key: str, default: Any = None) -> Any` | Borra el archivo si expiró (desalojo perezoso) |
| `set` | `async set(self, key: str, value: Any, ttl: float \| None = None) -> bool` | Siempre `True` |
| `exists` | `async exists(self, key: str) -> bool` | |
| `delete` | `async delete(self, key: str) -> int` | `1` / `0` |
| `clear` | `async clear(self) -> bool` | Elimina `*.json` y `*.tmp` |
| `multiGet` / `multi_get` | `async multiGet(self, keys: list[str], default: Any = None) -> list[Any]` | Un `get` secuencial por clave |
| `multiSet` / `multi_set` | `async multiSet(self, pairs: list[tuple[str, Any]], ttl: float \| None = None) -> bool` | Un `set` secuencial por par |
| `add` | `async add(self, key: str, value: Any, ttl: float \| None = None) -> bool` | Creación exclusiva; lanza `ValueError` si la clave existe |
| `increment` | `async increment(self, key: str, delta: int = 1) -> int` | Lectura-modificación-escritura serializada que conserva el vencimiento |

Lecturas, escrituras y borrados pasan por `asyncio.to_thread`. Las escrituras se
preparan en un archivo hermano con un infijo aleatorio (`<archivo>.<aleatorio>.tmp`)
y se publican con `Path.replace`; el rename lo serializa un `threading.Lock` por
instancia y se reintenta hasta `_REPLACE_ATTEMPTS = 3` veces con `5 ms` de espera
cuando el sistema operativo reporta una violación de compartición. Una escritura
fallida elimina su propio archivo de preparación antes de propagar el `OSError`.

### `DatabaseCacheBackend`

```python
class DatabaseCacheBackend:
    __slots__ = ("_connection", "_lock_table", "_ready", "_ready_lock", "_table")

    def __init__(
        self,
        connection: IConnection,
        table: str,
        lock_table: str | None = None,
    ) -> None: ...
```

`lock_table` cae por defecto en `_DEFAULT_LOCK_TABLE = "cache_locks"`.
`_ensureSchema()` crea ambas tablas en el primer uso, protegido por un
`asyncio.Lock` y un flag `_ready` (double-checked).

Esquema construido por `_buildEntriesTable(table)` y `_buildLocksTable(table)`:

| Tabla | Columnas |
|---|---|
| entradas | `cache_key` `String(255)` clave primaria, `cache_value` `Text` nullable, `expiration` `Double` nullable |
| locks | `cache_key` `String(255)` clave primaria, `owner` `String(255)` nullable, `expiration` `Double` nullable |

`expiration` es un epoch de reloj de pared (`time.time()`) guardado como número
en coma flotante, lo que conserva TTL y leases por debajo del segundo.

| Método | Firma | Notas |
|---|---|---|
| `get` | `async get(self, key: str, default: Any = None) -> Any` | Borra la fila si expiró |
| `set` | `async set(self, key: str, value: Any, ttl: float \| None = None) -> bool` | `UPDATE` y luego `INSERT` si no hubo filas; un `INSERT` en conflicto reintenta como `UPDATE` |
| `exists` | `async exists(self, key: str) -> bool` | |
| `delete` | `async delete(self, key: str) -> int` | Filas afectadas |
| `clear` | `async clear(self) -> bool` | `DELETE FROM <tabla>` |
| `multiGet` / `multi_get` | `async multiGet(self, keys: list[str], default: Any = None) -> list[Any]` | Secuencial |
| `multiSet` / `multi_set` | `async multiSet(self, pairs: list[tuple[str, Any]], ttl: float \| None = None) -> bool` | Secuencial |
| `add` | `async add(self, key: str, value: Any, ttl: float \| None = None) -> bool` | Borra la fila ya expirada y hace `INSERT`; lanza `ValueError` si la clave está tomada y vuelve a lanzar `QueryException` en cualquier otro caso |
| `increment` | `async increment(self, key: str, delta: int = 1) -> int` | Bucle compare-and-swap, `_INCREMENT_ATTEMPTS = 25`; lanza `QueryException` al agotarlo |
| `acquireLock` | `async acquireLock(self, key: str, owner: str, lease: float) -> bool` | Un solo intento: `INSERT`, o `UPDATE` condicional si la fila expiró o es propia |
| `releaseLock` | `async releaseLock(self, key: str, owner: str) -> None` | `DELETE ... WHERE cache_key = :k AND owner = :o` |

Los valores se codifican con `msgspec.json`; un payload que no se pueda
decodificar se lee como `None`.

### Fábricas de backend

Cada módulo de store expone una función `build()` a nivel de módulo;
`CacheManager` las importa con alias (`_build_memory`, `_build_redis`, …).

```python
# orionis/cache/stores/memory.py
def build() -> SimpleMemoryCache: ...

# orionis/cache/stores/redis.py
def build(
    endpoint: str = "127.0.0.1",
    port: int = 6379,
    db: int = 0,
    password: str | None = None,
) -> RedisCache: ...

# orionis/cache/stores/memcached.py
def build(endpoint: str = "127.0.0.1", port: int = 11211) -> MemcachedCache: ...

# orionis/cache/stores/database.py
def build(
    connection: IConnection,
    table: str,
    lock_table: str | None = None,
) -> DatabaseCacheBackend: ...
```

Los tres backends de aiocache se construyen siempre con
`serializer=MsgspecSerializer()`.

### `MsgspecSerializer`

```python
class MsgspecSerializer(BaseSerializer):
    DEFAULT_ENCODING = None

    def dumps(self, value: Any) -> bytes: ...
    def loads(self, data: bytes | str | float | None) -> Any: ...
```

Subclase de `aiocache.serializers.BaseSerializer`. `DEFAULT_ENCODING = None`
mantiene los payloads del backend como bytes crudos. `loads` devuelve `None`
cuando la entrada es `None`, codifica la entrada si llega como `str` y devuelve
sin tocar cualquier otro payload que no sea de bytes; eso es lo que mantiene
legible un contador escrito con el `increment()` del driver de memoria, que
aiocache guarda como un `int` nativo.

### `Serializer`

Utilidad estática usada por `FileBasedCache` (no tiene relación con el
serializador de aiocache anterior).

```python
class Serializer:
    @staticmethod
    def dumps(data: Any, indent: int | None = None) -> str: ...
    @staticmethod
    def loads(raw: str | bytes) -> Any: ...
    @staticmethod
    def dumpToFile(data: Any, file_path: Path) -> None: ...
    @staticmethod
    def loadFromFile(file_path: Path) -> Any: ...
```

Los valores que JSON no puede expresar de forma nativa se envuelven en un
mapeo con etiqueta de tipo `{"__type__": ..., "__value__": ...}`. Etiquetas
soportadas: `path`, `bytes`, `datetime`, `date`, `time`, `timedelta`,
`decimal`, `uuid`, `complex`, `tuple`, `set`, `frozenset`, `type`, `enum` y
`missing` (el centinela `MISSING` de `orionis.support.types.sentinel`). `dict`
y `list` se codifican recursivamente; `str`, `int`, `float`, `bool` y `None`
pasan sin cambios.

- `dumps` usa `msgspec.json` cuando `indent` es `None`, y el módulo `json` de la
  biblioteca estándar cuando se indica una indentación.
- Codificar un tipo no soportado lanza `TypeError`; decodificar un `__type__`
  desconocido lanza `ValueError`.
- `dumpToFile` prepara el payload en un archivo hermano con un infijo aleatorio
  (`<archivo>.<aleatorio>.tmp`), lo publica con `Path.replace` y elimina su
  propio archivo de preparación antes de propagar un `OSError`.
- `loadFromFile` devuelve `None` si el archivo no existe (cualquier `OSError`) o
  está vacío.
- Los payloads `type` y `enum` se resuelven importando la ruta punteada
  registrada, así que decodificar ejecuta un import cuando el módulo no está ya
  cargado.

### `IFileBasedCache` / `FileBasedCache`

```python
class FileBasedCache:
    __slots__ = (
        "__file",
        "__file_resolved",
        "__hashInterval",
        "__lasthashcheck",
        "__monitored_dirs",
        "__monitored_files",
        "__path",
        "__sourceshashcache",
    )

    CACHE_VERSION = 1

    def __init__(
        self,
        path: Path,
        filename: str,
        monitored_dirs: list[Path] | None = None,
        monitored_files: list[Path] | None = None,
    ) -> None: ...
```

`__init__` lanza `TypeError` si `path` no es un `Path` y crea el directorio con
`mkdir(parents=True, exist_ok=True)`.

| Método | Firma | Comportamiento |
|---|---|---|
| `get` | `get(self) -> dict \| None` | Devuelve `__data__` solo si el payload existe, `__meta__.version` coincide con `CACHE_VERSION` y `__meta__.sourcesHash` sigue casando |
| `save` | `save(self, data: dict) -> tuple[int, str]` | Lanza `TypeError` si `data` no es `dict`; omite la escritura si versión, hash y datos no cambiaron; devuelve `(CACHE_VERSION, sources_hash)` |
| `clear` | `clear(self) -> bool` | `True` si se eliminó el archivo, `False` si no existía |

El payload almacenado es
`{"__meta__": {"version", "generatedAt", "sourcesHash"}, "__data__": data}`.
`sourcesHash` es un SHA-1 (construido con `usedforsecurity=False`) sobre el
conjunto ordenado y sin duplicados de archivos monitoreados: todos los `*.py`
que `rglob` encuentra en `monitored_dirs` más las entradas existentes de
`monitored_files`, excluyendo el propio archivo de caché. Por cada archivo el
hash absorbe los bytes de la ruta POSIX y
`struct.pack(">QQ", st_mtime_ns, st_size)`. El resultado se memoiza durante
`0.5 s` (`time.monotonic()`), de modo que las llamadas consecutivas dentro de
esa ventana lo reutilizan.

`IFileBasedCache` (`contracts/file_based_cache.py`) declara los mismos tres
métodos, pero `FileBasedCache` no hereda de él; el contrato se usa como
anotación de tipo en `orionis.console.core.loader` y
`orionis.http.routes.loader`.

### `CacheProvider`

```python
class CacheProvider(ServiceProvider, DeferrableProvider):
    @classmethod
    def provides(cls) -> list[type]: ...
    def register(self) -> None: ...
    async def boot(self) -> None: ...
```

- `provides()` devuelve `[ICacheManager]`.
- `register()` ejecuta `self.app.singleton(ICacheManager, CacheManager)`.
- `boot()` hace `await Cache.pin()`.
- Aparece en `orionis.foundation.core_providers.CORE_PROVIDERS`; al ser
  diferido, el registro y el boot los dispara la primera resolución de
  `ICacheManager`.

### Excepciones

```python
class CacheException(Exception): ...
class CacheStoreException(CacheException): ...
```

`CacheStoreException` la lanzan `CacheManager._buildBackend` y
`_buildDatabaseBackend` con los mensajes `"Redis store is not configured."`,
`"Memcached store is not configured."` y `"Database store is not
configured."`. Ningún otro punto del módulo lanza `CacheException`
directamente.

### Entidades de configuración

La configuración vive en `orionis.foundation.config.cache` y la materializa la
aplicación en `config/cache.py` (`BootstrapCache`).

| Entidad | Campos | Variables de entorno |
|---|---|---|
| `Cache` | `default: Drivers \| str`, `prefix: str`, `stores: Stores \| dict` | `CACHE_STORE`, `CACHE_PREFIX` |
| `Stores` | `file`, `memory`, `redis`, `memcached`, `database` | — |
| `File` | `driver: str = "file"`, `path: str` | `CACHE_FILE_PATH` |
| `Memory` | `driver: str = "memory"` | — |
| `Redis` | `driver`, `endpoint`, `port`, `db`, `password` | `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD` |
| `Memcached` | `driver`, `endpoint`, `port` | `MEMCACHED_HOST`, `MEMCACHED_PORT` |
| `Database` | `driver`, `connection`, `table`, `lock_table` | `DB_CACHE_CONNECTION`, `DB_CACHE_TABLE`, `DB_CACHE_LOCK_TABLE` |

`Drivers` es un `StrEnum` con `FILE`, `MEMCACHED`, `MEMORY`, `REDIS` y
`DATABASE`. `Cache.__post_init__` valida `default` contra esos nombres (sin
distinguir mayúsculas y recortando espacios) y lo normaliza al valor canónico en
minúsculas; un nombre desconocido lanza `ValueError` y un tipo incorrecto lanza
`TypeError`.

Detalles verificados en las entidades:

- En `Stores`, solo `file` tiene un valor por defecto distinto de `None`;
  `memory`, `redis`, `memcached` y `database` valen `None` por defecto, que es
  justo la condición que hace que `CacheManager` lance `CacheStoreException`.
- `Cache.prefix` vale `"orionis"` por defecto, pero el `BootstrapCache` de la
  aplicación sobrescribe ese valor con `Env.get("CACHE_PREFIX", "")`.
- `File.__post_init__` crea el directorio configurado como efecto secundario de
  construir la entidad.
- `Database.table` y `Database.lock_table` se validan contra el patrón
  `[a-z_]+`.

## Ejemplos de uso

Todos los fragmentos siguientes se ejecutaron contra este repositorio.

### 1. Leer y escribir con el manager resuelto

```python
import asyncio

from bootstrap.app import app
from orionis.cache.contracts.cache_manager import ICacheManager


async def main() -> None:
    manager: ICacheManager = await app.make(ICacheManager)
    repository = manager.store("memory")

    await repository.set("reports:daily", {"total": 42}, ttl=60)
    print(await repository.get("reports:daily"))
    print(await repository.has("reports:daily"))
    print(await repository.delete("reports:daily"))
    print(await repository.get("reports:daily"))


asyncio.run(main())
```

Salida: `{'total': 42}`, `True`, `True`, `None`.

### 2. Calcular en el fallo de caché con `remember`

```python
import asyncio

from bootstrap.app import app
from orionis.cache.contracts.cache_manager import ICacheManager

calls: list[int] = []


async def expensive_query() -> list[dict]:
    calls.append(1)
    await asyncio.sleep(0.01)
    return [{"id": 1, "name": "Ada"}]


async def main() -> None:
    manager: ICacheManager = await app.make(ICacheManager)
    repository = manager.store("memory")

    print(await repository.remember("users:all", 300, expensive_query))
    print(await repository.remember("users:all", 300, expensive_query))
    print("resolver calls:", len(calls))

    print(await repository.rememberForever("app:name", lambda: "Orionis"))
    print(await repository.pull("app:name"))
    print(await repository.get("app:name"))


asyncio.run(main())
```

El resolutor se ejecuta una sola vez (`resolver calls: 1`); `pull` devuelve
`"Orionis"` y el `get` siguiente devuelve `None`.

### 3. Exclusión mutua con `lock`

```python
import asyncio

from bootstrap.app import app
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.cache.contracts.repository import ICacheRepository


async def charge(repository: ICacheRepository, tag: str) -> None:
    async with repository.lock("billing:run", timeout=5):
        counter = await repository.increment("billing:runs")
        await asyncio.sleep(0.01)
        print(tag, "->", counter)


async def main() -> None:
    manager: ICacheManager = await app.make(ICacheManager)
    repository = manager.store("file")
    await repository.delete("billing:runs")

    await asyncio.gather(charge(repository, "A"), charge(repository, "B"))
    print("final:", await repository.get("billing:runs"))
    await repository.delete("billing:runs")


asyncio.run(main())
```

Las dos tareas nunca se solapan: `A -> 1`, `B -> 2`, `final: 2`.

### 4. Manejo de errores

```python
import asyncio

from bootstrap.app import app
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.cache.exceptions import CacheStoreException


async def main() -> None:
    manager: ICacheManager = await app.make(ICacheManager)

    # store() lanza CacheStoreException cuando se pide 'redis', 'memcached'
    # o 'database' y no están declarados en config/cache.py.
    try:
        repository = manager.store("memory")
    except CacheStoreException as exc:
        print("cache store unavailable:", exc)
        return

    # add() informa el conflicto devolviendo False en vez de lanzar.
    print(await repository.add("flag:once", value=True))
    print(await repository.add("flag:once", value=True))
    await repository.delete("flag:once")


asyncio.run(main())
```

Salida: `True` y después `False`.

### 5. Repositorio autónomo sin el contenedor

```python
import asyncio

from orionis.cache.repository import CacheRepository
from orionis.cache.stores.memory import build as build_memory


async def main() -> None:
    repository = CacheRepository(backend=build_memory(), prefix="orionis")

    await repository.setMany({"a": 1, "b": 2}, ttl=30)
    print(await repository.getMany(["a", "b", "missing"]))
    print(await repository.pull("a"))
    print(await repository.get("a"))
    print(await repository.clear())


asyncio.run(main())
```

Salida: `{'a': 1, 'b': 2, 'missing': None}`, `1`, `None`, `True`. El backend
recibe las claves `orionis:a` y `orionis:b`.

### 6. Integración con el framework: controlador

```python
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.http import HttpResponse, response


class DashboardController:
    async def index(self, cache: ICacheManager) -> HttpResponse:
        metrics = await cache.remember(
            "dashboard:metrics",
            300,
            self.__buildMetrics,
        )
        return response.json(metrics)

    async def __buildMetrics(self) -> dict:
        return {"users": 1, "orders": 0}
```

El contenedor inyecta `ICacheManager` a partir de la anotación de tipo, así que
el controlador nunca depende del estado de pin de la fachada.

### 7. `Serializer` y `FileBasedCache`

```python
import datetime
import decimal
import uuid
from pathlib import Path

from orionis.cache.file_based_cache import FileBasedCache
from orionis.cache.serializer import Serializer

payload = {
    "generated_at": datetime.datetime(2026, 1, 2, 3, 4, 5),
    "amount": decimal.Decimal("10.25"),
    "batch": uuid.UUID("12345678-1234-5678-1234-567812345678"),
    "tags": {"reports", "daily"},
}

restored = Serializer.loads(Serializer.dumps(payload))
print(restored == payload)

cache = FileBasedCache(
    path=Path("storage/framework/cache"),
    filename="docs-example.cache",
    monitored_dirs=[Path("config")],
)
version, sources_hash = cache.save({"commands": ["make:command"]})
print(version, len(sources_hash))
print(cache.get())
print(cache.clear())
```

Salida: `True`, `1 40`, `{'commands': ['make:command']}`, `True`. Tocar
cualquier archivo bajo `config/` invalida la entrada, así que el siguiente
`get()` devuelve `None`.

## Rendimiento y concurrencia

- Toda la API de caché de aplicación es `async`. `CacheRepository.lock()` y
  `CacheManager.store()`/`lock()` son los únicos métodos síncronos.
- `FileCacheBackend` lleva cada operación de sistema de archivos a
  `asyncio.to_thread`, de modo que la decodificación JSON de una entrada ocurre
  en el hilo trabajador y no en el bucle de eventos.
- Los vencimientos de `FileCacheBackend` son plazos de `time.monotonic()`,
  mientras que `DatabaseCacheBackend` usa `time.time()`. Solo el driver de base
  de datos guarda una marca temporal absoluta de reloj de pared.
- `FileCacheBackend.__writeSync` prepara cada escritura en un archivo hermano
  único, así que dos escritores concurrentes de la misma clave nunca comparten
  archivo de preparación y la entrada publicada siempre es un payload completo.
- `FileCacheBackend.add()` crea la entrada con una apertura exclusiva, de modo
  que dos llamadas concurrentes no pueden tener éxito a la vez, e `increment()`
  ejecuta su lectura-modificación-escritura dentro de un `asyncio.Lock` por
  instancia, así que las tareas intercaladas del mismo bucle no pierden ninguna
  actualización. En `increment()` esa garantía no se extiende entre procesos;
  `add()` sigue siendo exclusivo porque la creación exclusiva la impone el
  sistema operativo.
- `DatabaseCacheBackend.add()` se apoya en la clave primaria para elegir un
  único ganador, e `increment()` reintenta un compare-and-swap hasta `25` veces
  antes de lanzar `QueryException`, así que ambos son seguros bajo concurrencia.
- `DatabaseCacheBackend._ensureSchema()` está protegido por un `asyncio.Lock`
  con un flag `_ready` double-checked, de modo que los dos `CREATE TABLE` se
  ejecutan una sola vez por instancia.
- `CacheLock` sobre un backend de archivos usa `_FILE_LOCKS`, un dict de
  `asyncio.Lock` a nivel de módulo. Solo coordina tareas dentro de un mismo
  bucle de eventos y sus entradas nunca se eliminan, así que el dict crece con
  la cantidad de claves distintas bloqueadas.
- `CacheLock` sobre un backend de base de datos sondea cada `0.05 s`. Los
  bloqueos por fila no son FIFO: los esperadores no se atienden en orden de
  llegada.
- `CacheManager.store()` no contiene ningún `await`, así que dentro de un mismo
  bucle de eventos la comprobación de memoización y la inserción no se pueden
  intercalar; el diccionario memoizado no está protegido frente a accesos
  concurrentes desde varios hilos.
- `SimpleMemoryCache` guarda sus datos en un dict de instancia (aiocache
  `>=0.12.3`) y `CacheManager` memoiza un repositorio por nombre de store, así
  que un proceso comparte un único almacén en memoria por instancia de manager.
- `FileBasedCache.__computeSourcesHash` cachea su resultado durante `0.5 s` y
  hace `stat` de cada archivo monitoreado cuando falla la caché, de modo que el
  coste crece con el tamaño del árbol monitoreado.
- `Serializer.dumps` sin `indent` y `MsgspecSerializer` usan `msgspec.json`, la
  ruta más rápida disponible en el módulo; la variante con indentación recae en
  el codificador de la biblioteca estándar.

## Notas de compatibilidad

- Requiere Python `>=3.14` (`pyproject.toml`). El módulo usa `Self`
  (`CacheLock.__aenter__`), uniones `X | None` y
  `hashlib.sha1(usedforsecurity=False)`.
- Todas las dependencias forman parte de la instalación base:
  `aiocache[redis,memcached]`, `redis[hiredis]`, `msgspec`,
  `sqlalchemy[asyncio]`. No hace falta ningún paquete extra para los drivers
  `memory`, `file`, `redis` ni `memcached`.
- El driver `database` necesita además una conexión de base de datos alcanzable
  a través de `ConnectionResolver`, más el driver asíncrono que esa conexión
  requiera.
- El driver `database` crea sus tablas de forma perezosa. El repositorio incluye
  también las migraciones `m0000000002_create_cache_table.py` y
  `m0000000003_create_cache_locks_table.py`, que declaran `expiration` como
  `double`; una base de datos creada antes de ese cambio conserva el tipo de
  columna original hasta que se vuelva a migrar.
- En el driver `memory`, `increment()` guarda un `int` plano en el backend de
  aiocache saltándose el serializador: `MsgspecSerializer.loads` devuelve sin
  tocar los payloads que no son de bytes, así que el contador sigue siendo
  legible con `get()` y `getMany()`.
- Los valores deben sobrevivir a un viaje de ida y vuelta por JSON. Los drivers
  de aiocache codifican con `MsgspecSerializer`, así que `tuple`, `set` y
  `frozenset` vuelven como `list` y `bytes` vuelve como un `str` en base64; la
  codificación con etiquetas de tipo, más rica, de `Serializer` solo se aplica a
  `FileBasedCache`.
- `FileCacheBackend` escribe un archivo por clave en un directorio plano, y
  `clear()` elimina todos los `*.json` y `*.tmp` que haya en él, incluidos los
  escritos por otro `FileCacheBackend` apuntando a la misma ruta.
