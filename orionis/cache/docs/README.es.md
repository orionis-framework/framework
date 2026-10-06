# orionis.cache

> Proporciona repositorios clave/valor y bloqueos async, además de caché síncrona de artefactos tipados.

Versión en inglés: [README.md](README.md).

## Tabla de contenidos

- [Requisitos](#requisitos)
- [Descripción funcional](#descripción-funcional)
- [Estructura del módulo](#estructura-del-módulo)
- [Referencia de API](#referencia-de-api)
- [Ejemplos de uso](#ejemplos-de-uso)
- [Características de diseño](#características-de-diseño)
- [Rendimiento y concurrencia](#rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)
- [Verificación y limitaciones](#verificación-y-limitaciones)

## Requisitos

La instalación del framework incluye las dependencias utilizadas por el
módulo. Redis y Memcached siguen necesitando servicios accesibles para sus
operaciones de datos; construir sus backends no comprueba conectividad.
La caché de base de datos requiere una `IConnection` de Orionis y su driver
async. SQLite está disponible en la instalación base; los demás drivers de
base de datos siguen los extras del proyecto. Consulta
[../../../pyproject.toml](../../../pyproject.toml) y
[Notas de compatibilidad](#notas-de-compatibilidad).

Para `CacheManager`, proporciona una aplicación que exponga `basePath` y
`config("cache")`. El manager convierte un diccionario a la entidad de
configuración de caché del framework; un valor que no sea diccionario se usa
directamente y debe exponer `default`, `prefix` y `stores`. No hay fallback
para una sección ausente que devuelva `None`. La construcción captura la
configuración y el prefijo; cambiar después la configuración de la aplicación
no reconstruye los stores guardados. Evidencia:
[../cache_manager.py](../cache_manager.py), `CacheManager.__init__` y `store`.

### Configuración y recursos

Son dependencias del módulo, no exportaciones adicionales de `orionis.cache`:

| Configuración | Ajustes implementados | Evidencia |
| --- | --- | --- |
| `Cache` | `default` se normaliza a un driver admitido; `prefix` debe ser una cadena; `stores` acepta `Stores` o un diccionario. Los predeterminados leen `CACHE_STORE` y `CACHE_PREFIX`. | [../../foundation/config/cache/entities/cache.py](../../foundation/config/cache/entities/cache.py) |
| `Stores` | Campos fijos `file`, `memory`, `redis`, `memcached`, `database`; todos tienen factories de entidad. Los campos opcionales pueden ser explícitamente `None`. | [../../foundation/config/cache/entities/stores.py](../../foundation/config/cache/entities/stores.py) |
| `File` | Ruta de cadena no vacía desde `CACHE_FILE_PATH`, predeterminado `storage/framework/cache/data`. Validar la entidad no crea directorios. | [../../foundation/config/cache/entities/file.py](../../foundation/config/cache/entities/file.py) |
| `Redis` | `endpoint`, `port`, `db`, `password`, leyendo `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`; el puerto está entre 1 y 65535 y db es no negativo. | [../../foundation/config/cache/entities/redis.py](../../foundation/config/cache/entities/redis.py) |
| `Memcached` | `endpoint`, `port`, leyendo `MEMCACHED_HOST`, `MEMCACHED_PORT`; el puerto está entre 1 y 65535. | [../../foundation/config/cache/entities/memcached.py](../../foundation/config/cache/entities/memcached.py) |
| `Database` | Una conexión para entradas y bloqueos; `connection`, `table`, `lock_table` leen `DB_CACHE_CONNECTION`, `DB_CACHE_TABLE`, `DB_CACHE_LOCK_TABLE`. Los nombres de tabla de la entidad deben cumplir `[a-z_]+`. | [../../foundation/config/cache/entities/database.py](../../foundation/config/cache/entities/database.py); [../stores/database.py](../stores/database.py) |

El manager selecciona el backend por el nombre de store solicitado, no
mediante un registro arbitrario de stores nombrados ni una factory
configurable. Los nombres reconocidos son exactamente `memory`, `file`,
`redis`, `memcached` y `database`. Un nombre desconocido lanza
`CacheStoreException`; también lo hace una configuración ausente de Redis,
Memcached o base de datos. La construcción de memoria no consulta
`stores.memory`. Las rutas de archivo relativas se unen a `app.basePath`;
`FileCacheBackend` las resuelve canónicamente y crea el directorio. Evidencia:
[../cache_manager.py](../cache_manager.py), `CacheManager._buildBackend`.

**Discrepancias de docstring:** `Stores` describe algunos predeterminados como
`None`, pero sus factories de campo instancian las entidades. `Database`
menciona una conexión independiente para bloqueos, pero el backend usa la
misma `_connection` para ambas tablas. Los comportamientos descritos aquí
siguen las declaraciones de campos y el código invocado, no esas descripciones.

Utiliza directorios temporales propiedad del backend para comprobaciones
aisladas: `clear()` no se limita al prefijo de un repositorio. Las operaciones
de base de datos crean tablas al primer uso y ejecutan SQL en la conexión
suministrada. La construcción directa del backend de base de datos no valida
ni entrecomilla identificadores de tabla; proporciona nombres de confianza
apropiados para la conexión. El SQL crudo los usa literalmente, mientras que
la creación de tablas se delega en `IConnection.createTable`. Los ejemplos
usan un prefijo de conexión vacío y nombres de tabla simples de SQLite.
Evidencia: [../stores/file.py](../stores/file.py), `FileCacheBackend.clear`, y
[../stores/database.py](../stores/database.py), `DatabaseCacheBackend`.

## Descripción funcional

`CacheManager` resuelve y retiene backends nombrados; `CacheRepository` añade
prefijos de claves, helpers por lotes, operaciones condicionales y caché basada
en callbacks. `CacheLock` proporciona context managers async según el backend.
Por separado, `FileBasedCache` y `Serializer` persisten artefactos tipados de
forma síncrona y los validan contra metadatos de archivos fuente monitoreados.

Las rutas de implementación son [../cache_manager.py](../cache_manager.py),
[../repository.py](../repository.py), [../locks/lock.py](../locks/lock.py),
[../file_based_cache.py](../file_based_cache.py) y
[../serializer.py](../serializer.py).

### Integración con el framework

`CacheProvider` declara `ICacheManager` como servicio diferido y lo vincula a
un `CacheManager` singleton. Su método boot fija la fachada externa `Cache`.
Está listado en los metadatos de proveedores del núcleo. Evidencia:
[../provider.py](../provider.py), `CacheProvider`, y
[../../foundation/core_providers.py](../../foundation/core_providers.py),
`CORE_PROVIDER_METADATA`.

La fachada es `orionis.support.facades.cache.Cache`, no una exportación de
este módulo. Antes del pin, una llamada produce un dispatcher diferido;
esperarlo resuelve el manager y su proveedor diferido. Después del pin, los
métodos síncronos como `store` retornan sus objetos directamente y no deben
esperarse. Los métodos async siguen requiriendo await.
`async with Cache.lock(...)` funciona mediante el protocolo de context manager
diferido o el objeto directo fijado. Evidencia:
[../../support/facades/cache.py](../../support/facades/cache.py),
`Cache.getFacadeAccessor`, y
[../../container/facades/meta.py](../../container/facades/meta.py),
`FacadeMeta.__getattr__` y `_FacadeDispatch`.

`CacheSessionStore` selecciona un repositorio mediante `cache.store(store)` y
usa `replace` al actualizar una sesión viva, sin recrear una entrada eliminada.
Esto explica directamente el contrato de reemplazo del repositorio. Evidencia:
[../../session/stores/cache.py](../../session/stores/cache.py),
`CacheSessionStore.__init__` y `update`.

## Estructura del módulo

Se inspeccionaron recursivamente los 21 archivos Python. Dentro del módulo
no hay recursos de ejecución referenciados que no sean Python.

| Fuente | Responsabilidad y símbolos públicos |
| --- | --- |
| [../__init__.py](../__init__.py) | Exportaciones diferidas `CacheManager`, `CacheRepository`, `FileBasedCache`; `__getattr__`, `__dir__` y `__all__` del paquete. |
| [../cache_manager.py](../cache_manager.py) | `CacheManager`: resolución y proxies del store predeterminado. |
| [../repository.py](../repository.py) | `CacheRepository`: API de caché de aplicación con prefijos. |
| [../exceptions.py](../exceptions.py) | `CacheException`, `CacheStoreException`. |
| [../provider.py](../provider.py) | `CacheProvider`: binding singleton y pin de fachada. |
| [../file_based_cache.py](../file_based_cache.py) | `FileBasedCache` y `CACHE_VERSION`: artefactos síncronos. |
| [../serializer.py](../serializer.py) | `Serializer`: JSON etiquetado y persistencia en archivos. |
| [../contracts/__init__.py](../contracts/__init__.py) | Reexporta tres interfaces y declara `__all__`. |
| [../contracts/cache_manager.py](../contracts/cache_manager.py) | `ICacheManager`: contrato del manager. |
| [../contracts/repository.py](../contracts/repository.py) | `ICacheRepository`: contrato del repositorio, incluido `replace`. |
| [../contracts/file_based_cache.py](../contracts/file_based_cache.py) | `IFileBasedCache`: contrato de artefactos. |
| [../locks/lock.py](../locks/lock.py) | `CacheLock`: contexto de bloqueo por bucle/archivo, fila de base de datos o RedLock. |
| [../serializers/json.py](../serializers/json.py) | `MsgspecSerializer` y `DEFAULT_ENCODING`. |
| [../stores/file.py](../stores/file.py) | `FileCacheBackend`, `lockNamespace`, alias de operaciones por lotes. |
| [../stores/database.py](../stores/database.py) | `DatabaseCacheBackend`, `build`, alias de operaciones por lotes. |
| [../stores/memory.py](../stores/memory.py) | `build`: backend de memoria de aiocache. |
| [../stores/redis.py](../stores/redis.py) | `build`: backend Redis de aiocache con RESP2. |
| [../stores/memcached.py](../stores/memcached.py) | `build`: backend Memcached de aiocache. |
| [../locks/__init__.py](../locks/__init__.py), [../serializers/__init__.py](../serializers/__init__.py), [../stores/__init__.py](../stores/__init__.py) | Inicializadores vacíos; sin reexportaciones explícitas de símbolos. |

## Referencia de API

Los bloques de declaraciones contienen cabeceras literales del código fuente
sin cuerpos de implementación. Son fragmentos de referencia, no scripts
completos. Los constructores retornan `None`; la construcción normal de la
clase produce la nueva instancia. Los scripts ejecutables se limitan a
[Ejemplos de uso](#ejemplos-de-uso).

### Importaciones públicas y comportamiento del paquete

| Símbolo | Ubicación del import |
| --- | --- |
| `CacheManager`, `CacheRepository`, `FileBasedCache` | `orionis.cache` o sus módulos de definición listados arriba. |
| `ICacheManager`, `ICacheRepository`, `IFileBasedCache` | `orionis.cache.contracts` o sus módulos de contrato. |
| `CacheException`, `CacheStoreException` | `orionis.cache.exceptions`. |
| `CacheProvider` | `orionis.cache.provider`. |
| `CacheLock` | `orionis.cache.locks.lock`. |
| `Serializer` | `orionis.cache.serializer`. |
| `MsgspecSerializer` | `orionis.cache.serializers.json`. |
| `FileCacheBackend` | `orionis.cache.stores.file`. |
| `DatabaseCacheBackend` | `orionis.cache.stores.database`. |
| Cada función `build` | Su módulo propio `orionis.cache.stores.memory`, `.redis`, `.memcached` o `.database`. |

Ambas listas públicas `__all__` contienen tres cadenas. La lista raíz es
`["CacheManager", "CacheRepository", "FileBasedCache"]`; la de contratos es
`["ICacheManager", "ICacheRepository", "IFileBasedCache"]`. Fuente:
[../__init__.py](../__init__.py) y
[../contracts/__init__.py](../contracts/__init__.py).

```python
def __getattr__(name: str) -> object:
```

```python
def __dir__() -> list[str]:
```

El paquete raíz resuelve las exportaciones declaradas mediante
`orionis._exports.resolve_export`, importando el módulo de definición y
guardando el valor en los globals del paquete. Solicitar exportaciones
desconocidas lanza `AttributeError`. `__dir__` retorna los nombres cargados
y las exportaciones declaradas, ordenados; no las resuelve. Importar solo el
paquete es distinto de solicitar una clase. Evidencia:
[../__init__.py](../__init__.py) y [../../_exports.py](../../_exports.py),
`resolve_export`.

Los helpers privados, centinelas privados, tablas de despacho de codecs y
dependencias importadas no son API públicas adicionales de caché. Los cuatro
nombres `build` se documentan por separado, no como una función raíz
intercambiable. No se declara un protocolo público de iteración, enum ni alias
de tipo independiente en los 21 archivos del módulo. Las entidades de
configuración y la fachada siguen siendo integraciones externas, no
exportaciones raíz adicionales.

### CacheRepository

Importa `orionis.cache.repository.CacheRepository` o la reexportación raíz.
Fuente de todos los miembros siguientes: [../repository.py](../repository.py),
`CacheRepository`. Implementa `ICacheRepository`.

```python
class CacheRepository(ICacheRepository):
```

```python
def __init__(self, backend: Any, prefix: str = "") -> None:
```

Se retiene `backend` sin validación de protocolo ni transferencia de propiedad.
`prefix` es una cadena vacía por defecto. Un prefijo truthy transforma cada
clave en `f"{prefix}:{key}"`; en caso contrario, se reenvía la clave original.
No hay escapado ni validación de claves a nivel de repositorio. Mantén
prefijos y claves suficientemente distintos para no construir la misma cadena
final. El constructor no realiza E/S del backend; no tiene método close ni
cierra recursos suministrados.

```python
async def replace(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def get(self, key: str) -> Any:
```

```python
async def set(
    self,
    key: str,
    value: Any,
    ttl: float | None = None,
) -> bool:
```

```python
async def has(self, key: str) -> bool:
```

```python
async def delete(self, key: str) -> bool:
```

```python
async def clear(self) -> bool:
```

```python
async def getMany(self, keys: list[str]) -> dict[str, Any]:
```

```python
async def setMany(
    self,
    values: dict[str, Any],
    ttl: float | None = None,
) -> bool:
```

```python
async def remember(
    self,
    key: str,
    ttl: float | None,
    resolver: Callable,
) -> Any:
```

```python
async def rememberForever(self, key: str, resolver: Callable) -> Any:
```

```python
async def pull(self, key: str) -> Any:
```

```python
async def add(
    self,
    key: str,
    value: Any,
    ttl: float | None = None,
) -> bool:
```

```python
async def increment(self, key: str, amount: int = 1) -> int:
```

```python
async def decrement(self, key: str, amount: int = 1) -> int:
```

```python
def lock(self, key: str, timeout: float | None = None) -> CacheLock:
```

| Operación | Parámetros, resultado esperado y efectos |
| --- | --- |
| `get(key)` | Lee la clave `str` prefijada; devuelve el valor del backend, normalmente `None` si está ausente. Este método por sí solo no distingue un `None` almacenado. |
| `set(key, value, ttl=None)` | Reenvía `value: Any` y `ttl: float | None`; convierte el resultado del backend a `bool`. Los valores deben cumplir los requisitos de serialización del backend. El TTL depende del backend. |
| `replace(key, value, ttl=None)` | Reemplaza una entrada existente viva y devuelve `bool`. Prefiere el `replace` callable del backend; de lo contrario, exige `aiocache.BaseCache` y usa `OptimisticLock`. Tokens ausentes y conflictos CAS devuelven `False`. Backends personalizados incompatibles lanzan `CacheStoreException`. |
| `has(key)` | Llama a `exists` del backend, no a `get`; convierte a `bool`. |
| `delete(key)` | Elimina la clave prefijada y convierte el conteo o resultado del backend a `bool`. |
| `clear()` | Vacía todo el backend, no solo este prefijo, y convierte su resultado a `bool`. |
| `getMany(keys)` | Materializa claves prefijadas, llama a `multi_get` y construye `dict(zip(keys, values, strict=True))`. Retorna las claves originales; las duplicadas colapsan en el diccionario. Un conteo de resultados distinto lanza `ValueError`. La entrada vacía normalmente retorna `{}`. |
| `setMany(values, ttl=None)` | Materializa pares prefijados `(key, value)` desde `dict[str, Any]`, los reenvía a `multi_set` y retorna `bool`. No añade una transacción de repositorio. |
| `remember(key, ttl, resolver)` | `ttl` y un `Callable` sin argumentos son obligatorios. Lee con un centinela privado de ausencia; ante un miss invoca el resolver en el bucle del llamador, espera un resultado awaitable, lo almacena y lo retorna. Un resolver síncrono no se delega a un worker. |
| `rememberForever(key, resolver)` | Delega en `remember(key, None, resolver)`. No añade caché ni política de invalidación separadas. |
| `pull(key)` | Lee con el centinela y elimina ante un hit, retornando el valor; devuelve `None` ante un miss. Son operaciones esperadas por separado, no una lectura y eliminación atómica. |
| `add(key, value, ttl=None)` | Espera `add` del backend y devuelve `True` si termina. Captura cualquier `ValueError` del backend y devuelve `False`, no solo errores demostrados como duplicados. |
| `increment(key, amount=1)` | Reenvía `amount: int` sin cambios a `increment` del backend; retorna su resultado entero. No impone validación exclusiva de valores positivos. |
| `decrement(key, amount=1)` | Reenvía `-amount` a `increment` del backend; retorna su resultado. |
| `lock(key, timeout=None)` | Construye síncronamente un `CacheLock` para la clave prefijada; la adquisición solo ocurre al entrar de forma async. El timeout depende del backend, como se describe abajo. |

Generalmente se propagan los errores del backend, codec, callback y recursos.
El repositorio captura `OptimisticLockError` en el reemplazo de aiocache y
`ValueError` en `add`; no traduce todos los errores a errores de caché.
`remember` comprueba y lee, luego ejecuta callback y escritura sin lock;
los misses concurrentes pueden repetir el resolver. Pruebas:
[../../../tests/cache/test_repository.py](../../../tests/cache/test_repository.py),
`TestCacheRepository` y `TestCacheRepositoryOnMemoryBackend`.

**Discrepancia de None almacenado:** el comentario del centinela describe
preservar `None`, lo que hacen los backends de archivo y base de datos. En
aiocache 0.12.3 inspeccionado, `BaseCache.get` devuelve su default cuando el
valor decodificado es `None`. Por eso `remember` vuelve a resolver y `pull`
devuelve `None` sin eliminar esa clave de memoria. Esto se ejecutó en los
backends locales de memoria, archivo y SQLite. No asumas comportamiento
uniforme de null y miss por la presencia del centinela. Evidencia:
[../repository.py](../repository.py), `remember` y `pull`, con
`aiocache.base.BaseCache.get` inspeccionado en el entorno de validación.

### CacheManager

Importa `orionis.cache.cache_manager.CacheManager` o la reexportación raíz.
Fuente: [../cache_manager.py](../cache_manager.py), `CacheManager`.

```python
class CacheManager(ICacheManager):
```

```python
def __init__(self, app: IApplication) -> None:
```

```python
def store(self, name: str | None = None) -> CacheRepository:
```

Los requisitos de aplicación del constructor se listan arriba. `store`
resuelve `name or self._default`, por lo que `None` y `""` eligen el
predeterminado. Memoiza un repositorio y backend por nombre resuelto durante
la vida de este manager. No hay API pública de desalojo, extensión de backends
ni close. Los fallos al construir un backend no añaden un repositorio a la
caché. Los nombres desconocidos se rechazan, no se convierten en un store de
archivo. Los nombres pasados a `store` no se normalizan como el campo
`default` de configuración.

Las declaraciones completas de proxies son fragmentos literales:

```python
async def get(self, key: str) -> Any:
```

```python
async def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def has(self, key: str) -> bool:
```

```python
async def delete(self, key: str) -> bool:
```

```python
async def clear(self) -> bool:
```

```python
async def getMany(self, keys: list[str]) -> dict[str, Any]:
```

```python
async def setMany(
    self,
    values: dict[str, Any],
    ttl: float | None = None,
) -> bool:
```

```python
async def remember(
    self,
    key: str,
    ttl: float | None,
    resolver: Callable,
) -> Any:
```

```python
async def rememberForever(self, key: str, resolver: Callable) -> Any:
```

```python
async def pull(self, key: str) -> Any:
```

```python
async def add(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def increment(self, key: str, amount: int = 1) -> int:
```

```python
async def decrement(self, key: str, amount: int = 1) -> int:
```

```python
def lock(self, key: str, timeout: float | None = None) -> Any:
```

Cada proxy usa `self.store()` y el método del repositorio con el mismo nombre.
El significado de parámetros, resultados, efectos y errores es el documentado
para `CacheRepository`, más los fallos de resolución de store al primer uso.
El resultado de `lock` en runtime es `CacheLock`, pese a su anotación `Any`.
No hay proxy `replace`: llama explícitamente a
`manager.store().replace(...)`. Pruebas:
[../../../tests/cache/test_cache_manager.py](../../../tests/cache/test_cache_manager.py),
`TestCacheManager`.

### Contratos

Todos los miembros siguientes son declaraciones `@abstractmethod` con cuerpos
que solo contienen docstrings, no implementaciones predeterminadas ejecutables.
Instanciar directamente o con una subclase incompleta lanza el `TypeError` de
Python. La maquinaria ABC no exige tipos de parámetros en runtime ni la
semántica de corrutina de las sobrescrituras.

#### ICacheRepository

Importa `orionis.cache.contracts.repository.ICacheRepository` o la
reexportación de contratos. Fuente:
[../contracts/repository.py](../contracts/repository.py). Las 14 operaciones
declaran la semántica del repositorio anterior; `lock` no está incluido. No
hay constructor explícito; se declara `__slots__ = ()`.

```python
class ICacheRepository(ABC):
```

```python
@abstractmethod
async def replace(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
@abstractmethod
async def get(self, key: str) -> Any:
```

```python
@abstractmethod
async def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
@abstractmethod
async def has(self, key: str) -> bool:
```

```python
@abstractmethod
async def delete(self, key: str) -> bool:
```

```python
@abstractmethod
async def clear(self) -> bool:
```

```python
@abstractmethod
async def getMany(self, keys: list[str]) -> dict[str, Any]:
```

```python
@abstractmethod
async def setMany(
    self,
    values: dict[str, Any],
    ttl: float | None = None,
) -> bool:
```

```python
@abstractmethod
async def remember(
    self,
    key: str,
    ttl: float | None,
    resolver: Callable,
) -> Any:
```

```python
@abstractmethod
async def rememberForever(self, key: str, resolver: Callable) -> Any:
```

```python
@abstractmethod
async def pull(self, key: str) -> Any:
```

```python
@abstractmethod
async def add(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
@abstractmethod
async def increment(self, key: str, amount: int = 1) -> int:
```

```python
@abstractmethod
async def decrement(self, key: str, amount: int = 1) -> int:
```

#### ICacheManager

Importa `orionis.cache.contracts.cache_manager.ICacheManager` o la
reexportación de contratos. Fuente:
[../contracts/cache_manager.py](../contracts/cache_manager.py). Los 14 miembros
son `store` y 13 operaciones del store predeterminado. No se declara `lock`
ni `replace`. No hay constructor explícito ni `__slots__`.

```python
class ICacheManager(ABC):
```

```python
@abstractmethod
def store(self, name: str | None = None) -> ICacheRepository:
```

```python
@abstractmethod
async def get(self, key: str) -> Any:
```

```python
@abstractmethod
async def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
@abstractmethod
async def has(self, key: str) -> bool:
```

```python
@abstractmethod
async def delete(self, key: str) -> bool:
```

```python
@abstractmethod
async def clear(self) -> bool:
```

```python
@abstractmethod
async def getMany(self, keys: list[str]) -> dict[str, Any]:
```

```python
@abstractmethod
async def setMany(
    self,
    values: dict[str, Any],
    ttl: float | None = None,
) -> bool:
```

```python
@abstractmethod
async def remember(
    self,
    key: str,
    ttl: float | None,
    resolver: Callable,
) -> Any:
```

```python
@abstractmethod
async def rememberForever(self, key: str, resolver: Callable) -> Any:
```

```python
@abstractmethod
async def pull(self, key: str) -> Any:
```

```python
@abstractmethod
async def add(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
@abstractmethod
async def increment(self, key: str, amount: int = 1) -> int:
```

```python
@abstractmethod
async def decrement(self, key: str, amount: int = 1) -> int:
```

#### IFileBasedCache

Importa `orionis.cache.contracts.file_based_cache.IFileBasedCache` o la
reexportación de contratos. Fuente:
[../contracts/file_based_cache.py](../contracts/file_based_cache.py).
Declara tres operaciones síncronas de artefactos, sin constructor ni slots.
`FileBasedCache` coincide con esta superficie, pero no hereda de esta ABC.

```python
class IFileBasedCache(ABC):
```

```python
@abstractmethod
def get(self) -> dict | None:
```

```python
@abstractmethod
def save(self, data: dict) -> tuple[int, str]:
```

```python
@abstractmethod
def clear(self) -> bool:
```

### FileCacheBackend

Importa `orionis.cache.stores.file.FileCacheBackend`. Fuente de sus miembros:
[../stores/file.py](../stores/file.py), `FileCacheBackend`.

```python
class FileCacheBackend:
```

```python
def __init__(self, path: Path) -> None:
```

```python
@property
def lockNamespace(self) -> Path:
```

`path` es un `Path` obligatorio, resuelto a un directorio canónico absoluto.
La construcción lo crea y asigna un lock asyncio de contadores, un lock de
hilo para renombrado y 64 objetos `FileLock` con timeout de adquisición de
10 segundos. `lockNamespace` es una propiedad de solo lectura que retorna
ese directorio canónico; no tiene setter ni deleter. Se propagan los errores
de filesystem o preparación. No hay método close explícito del backend.

Cada clave `str` se codifica en UTF-8, se hashea con SHA-256 y se almacena
como entrada plana `<digest>.json` con `{"v": value, "e": deadline_or_none}`.
Los valores usan `msgspec.json`, no el `Serializer` etiquetado. Un TTL
explícito, incluido cero, fija `time.monotonic() + ttl`; `None` significa
sin expiración. Las entradas expiradas se eliminan durante las lecturas.
JSON inválido, entradas que no sean diccionarios y `OSError` de lectura
se convierten en misses; pueden propagarse otros errores de campos
malformados, bloqueo o eliminación.

```python
async def get(self, key: str, default: Any = None) -> Any:
```

```python
async def replace(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def exists(self, key: str) -> bool:
```

```python
async def delete(self, key: str) -> int:
```

```python
async def clear(self) -> bool:
```

```python
async def multiGet(self, keys: list[str], default: Any = None) -> list[Any]:
```

```python
async def multiSet(
    self,
    pairs: list[tuple[str, Any]],
    ttl: float | None = None,
) -> bool:
```

```python
async def add(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def increment(self, key: str, delta: int = 1) -> int:
```

| Operación | Resultado implementado y efectos |
| --- | --- |
| `get(key, default=None)` | Retorna el valor de la entrada, incluido `None` almacenado; usa `default: Any` solo para una entrada ausente, expirada o inválida. La lectura y decodificación JSON se realizan en un worker. |
| `set(key, value, ttl=None)` | Publica una entrada JSON completa mediante un archivo hermano de staging único y renombrado; retorna `True`. Se propagan errores de codificación o escritura. |
| `replace(key, value, ttl=None)` | Bajo el lock de franja del archivo, exige una entrada viva legible, la reemplaza con el nuevo valor y TTL y retorna `True`; de lo contrario, `False`. |
| `exists(key)` | Lee con un centinela y retorna `bool`; un valor `None` vivo cuenta como presente. |
| `delete(key)` | Elimina bajo el lock de franja; retorna `1` si se eliminó y `0` si no existía. Un archivo expirado que no se haya leído aún puede eliminarse. |
| `clear()` | Elimina todos los `*.json` y `*.tmp` del directorio, incluidos otros prefijos; retorna `True`. No elimina archivos de locks de franja. No añade una transacción de todo el store. |
| `multiGet(keys, default=None)` | Lecturas secuenciales, retornando `list[Any]` en orden de entrada, incluidos duplicados; la entrada vacía da `[]`. |
| `multiSet(pairs, ttl=None)` | Escrituras secuenciales de `list[tuple[str, Any]]`; los duplicados sobrescriben en orden. La entrada vacía retorna `True`; un error puede dejar escrituras previas confirmadas. |
| `add(key, value, ttl=None)` | `open("xb")` exclusivo bajo el lock de franja; reintenta una vez si leer el slot existente lo encuentra expirado o ausente. Retorna `True` o lanza `ValueError` si la creación sigue perdiendo. La ruta de lectura no tiene por qué eliminar archivos existentes corruptos. |
| `increment(key, delta=1)` | Serializa mediante el lock asyncio de la instancia y el lock de franja del archivo, calcula `int(current_value or 0) + delta`, conserva la expiración de una entrada viva y retorna el nuevo valor. Entradas ausentes o expiradas comienzan sin expiración. Se propagan errores de conversión o codificación. |

Los alias literales `multi_get = multiGet` y `multi_set = multiSet` exponen
los mismos métodos de corrutina, no wrappers con firmas diferentes.
No se declara `decrement` directo; el repositorio niega su cantidad.
Fuente y pruebas: [../stores/file.py](../stores/file.py) y
[../../../tests/cache/test_stores_file.py](../../../tests/cache/test_stores_file.py).

Lecturas, escrituras, creación exclusiva, reemplazo y eliminación seleccionan
una franja mediante `crc32(file.name.encode()) % 64`. Las escrituras con
staging usan nombres aleatorios únicos; la publicación reintenta
`PermissionError` hasta tres intentos con backoff de 0.005 segundos bajo un
lock de hilo por instancia. Ante `OSError`, las escrituras intentan eliminar
su propio archivo de staging antes de relanzar. Estos mecanismos coordinan
operaciones reales de archivo; son distintos del `CacheLock` de usuario.

### DatabaseCacheBackend

Importa `orionis.cache.stores.database.DatabaseCacheBackend`. Fuente:
[../stores/database.py](../stores/database.py), `DatabaseCacheBackend`.

```python
class DatabaseCacheBackend:
```

```python
def __init__(
    self,
    connection: IConnection,
    table: str,
    lock_table: str | None = None,
) -> None:
```

`connection` y la tabla de entradas `table` son obligatorias y se retienen.
Un `lock_table` falsy, incluido `None` o `""`, selecciona `"cache_locks"`.
La construcción no ejecuta SQL. `_ensureSchema` crea ambas tablas al primer
uso bajo un lock asyncio de instancia; marca la preparación solo después de
que ambas llamadas tengan éxito. El backend no cierra la conexión suministrada
ni migra el esquema de una tabla existente.

| Tabla | Columnas construidas por los helpers inspeccionados |
| --- | --- |
| Entradas | `cache_key`: `String(255).primary()`; `cache_value`: `Text` nullable; `expiration`: `Double` nullable. |
| Bloqueos | `cache_key`: `String(255).primary()`; `owner`: `String(255)` nullable; `expiration`: `Double` nullable. |

Los privados `_build_entries_table` y `_build_locks_table` son helpers de
esquema, no factories públicas adicionales. La expiración de entradas y
bloqueos usa segundos epoch de `time.time()`, conservando TTL fraccionarios.
Los payloads JSON se almacenan como cadenas. Un JSON inválido se decodifica
a `None`; sigue siendo una fila existente para la comprobación con centinela.
Las lecturas de expiración usan SELECT seguido de DELETE, no una operación
atómica de lectura y desalojo.

```python
async def get(self, key: str, default: Any = None) -> Any:
```

```python
async def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def replace(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def exists(self, key: str) -> bool:
```

```python
async def delete(self, key: str) -> int:
```

```python
async def clear(self) -> bool:
```

```python
async def multiGet(self, keys: list[str], default: Any = None) -> list[Any]:
```

```python
async def multiSet(
    self,
    pairs: list[tuple[str, Any]],
    ttl: float | None = None,
) -> bool:
```

```python
async def add(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def increment(self, key: str, delta: int = 1) -> int:
```

```python
async def acquireLock(self, key: str, owner: str, lease: float) -> bool:
```

```python
async def releaseLock(self, key: str, owner: str) -> None:
```

| Operación | Resultado implementado y efectos |
| --- | --- |
| `get(key, default=None)` | SELECT de una fila; retorna `default` ante ausencia o expiración, y en otro caso su payload decodificado, incluido `None`. Las filas expiradas provocan una eliminación separada. |
| `set(key, value, ttl=None)` | Codifica el valor, hace UPDATE y luego INSERT si no cambió una fila. Un `QueryException` capturado del insert reintenta UPDATE. Retorna `True` al terminar; no es una única sentencia upsert nativa. |
| `replace(key, value, ttl=None)` | Un UPDATE condicional que exige datos existentes no expirados; fija el nuevo valor y expiración y retorna `affected > 0`. No crea una fila ausente. |
| `exists(key)` | Usa `get` con centinela; un `None` presente o un payload decodificado inválido cuentan como fila existente. |
| `delete(key)` | DELETE de la clave, retornando el conteo de filas afectadas de la conexión. |
| `clear()` | DELETE de todas las filas de la tabla de entradas y retorna `True`; no limpia la tabla de locks ni filtra prefijos. |
| `multiGet(keys, default=None)` | Lecturas secuenciales por clave en orden de entrada, retornando una lista; la entrada vacía da `[]`. |
| `multiSet(pairs, ttl=None)` | Escrituras secuenciales; los duplicados sobrescriben y un error permite finalización parcial. Retorna `True`, incluso para entrada vacía. |
| `add(key, value, ttl=None)` | Elimina un slot expirado y hace INSERT. Ante `QueryException`, comprueba si existe la clave: lanza `ValueError` encadenado si está ocupada y relanza el error de consulta en otro caso. |
| `increment(key, delta=1)` | Hasta 25 rondas de lectura y CAS; crea mediante `add` si falta o expiró; de lo contrario, calcula `int(decoded_value or 0) + delta` y hace UPDATE si coincide el JSON anterior. No actualiza la expiración existente. Retorna el nuevo valor o lanza `QueryException` al agotar la contención. |
| `acquireLock(key, owner, lease)` | Un intento: INSERT de una fila de lock o, ante un fallo de consulta, UPDATE condicional de una fila expirada o del mismo propietario. Retorna `bool`; aquí no se añade validación de lease positivo. La adquisición del mismo propietario renueva la expiración. |
| `releaseLock(key, owner)` | DELETE solo de la fila del propietario coincidente; retorna `None`. No prepara el esquema de forma independiente. |

`multi_get = multiGet` y `multi_set = multiSet` son alias literales.
Pueden propagarse errores de conexión, codec y conversión a enteros, además
de las excepciones explícitas de operaciones duplicadas o contenciosas.
El CAS se basa en el payload previo, no en una columna de versión ni una
política FIFO garantizada. Pruebas:
[../../../tests/cache/test_stores_database.py](../../../tests/cache/test_stores_database.py),
`TestDatabaseCacheBackend` y `TestDatabaseCacheBackendConcurrency`.

### Factories de backend

Cada una es una función pública de módulo con su propio import. Ninguna añade
un prefijo de repositorio, reintenta conectividad ni posee un ciclo de vida de
aplicación.

#### Memoria

Importa `orionis.cache.stores.memory.build`. Fuente:
[../stores/memory.py](../stores/memory.py).

```python
def build() -> SimpleMemoryCache:
```

Construye un `aiocache.SimpleMemoryCache(serializer=MsgspecSerializer())`
nuevo. Cada instancia tiene su propio diccionario de datos; no es una caché
global compartida del proceso. La API heredada y el comportamiento close del
backend pertenecen a aiocache, no a métodos recién declarados de Orionis.

#### Redis

Importa `orionis.cache.stores.redis.build`. Fuente:
[../stores/redis.py](../stores/redis.py).

```python
def build(
    endpoint: str = "127.0.0.1",
    port: int = 6379,
    db: int = 0,
    password: str | None = None,
) -> RedisCache:
```

Construye `RedisCache` con el endpoint suministrado, port y db convertidos a
enteros, `password or None`, `MsgspecSerializer` y
`connection_pool_kwargs={"protocol": 2}`. Los predeterminados son argumentos
literales del constructor, no valores que esta función lea del entorno.
El manager pasa los ajustes de entidad por separado. Las operaciones de datos
requieren un servicio Redis; esta factory no convierte los errores del
backend, red o conversión.

#### Memcached

Importa `orionis.cache.stores.memcached.build`. Fuente:
[../stores/memcached.py](../stores/memcached.py).

```python
def build(
    endpoint: str = "127.0.0.1",
    port: int = 11211,
) -> MemcachedCache:
```

Construye `MemcachedCache` con el endpoint, port convertido a entero y
`MsgspecSerializer`. Las operaciones de datos requieren Memcached. Las
anotaciones no sustituyen las restricciones reales de claves, TTL o protocolo
del cliente; la factory no captura errores de conversión, dependencia o red.

#### Base de datos

Importa `orionis.cache.stores.database.build`. Fuente:
[../stores/database.py](../stores/database.py), `build`.

```python
def build(
    connection: IConnection,
    table: str,
    lock_table: str | None = None,
) -> DatabaseCacheBackend:
```

Delega la conexión y tabla obligatorias y la tabla opcional de locks al
constructor del backend descrito arriba. `build` no resuelve ni abre una
conexión por sí mismo; el manager resuelve
`ConnectionResolver.connection(...)` antes de llamarlo. Los fallos del
resolver se propagan. Evidencia: [../../orm/resolver.py](../../orm/resolver.py),
`ConnectionResolver.connection`, y [../cache_manager.py](../cache_manager.py),
`_buildDatabaseBackend`.

### CacheLock

Importa `orionis.cache.locks.lock.CacheLock`. Fuente de todos sus miembros:
[../locks/lock.py](../locks/lock.py), `CacheLock`.

```python
class CacheLock:
```

```python
def __init__(
    self,
    backend: Any,
    key: str,
    timeout: float | None = None,
) -> None:
```

```python
async def __aenter__(self) -> Self:
```

```python
async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: types.TracebackType | None,
) -> None:
```

La construcción retiene el backend crudo, la clave y el timeout; no adquiere
nada. La entrada retorna esta instancia `CacheLock`. La salida libera la
implementación elegida y retorna `None`, sin suprimir la excepción del bloque
protegido. Pueden propagarse errores del backend o limpieza. Usa un objeto
de contexto por adquisición activa: hay un único slot `_impl`/`_owner`, no
una pila de adquisiciones ni comprobación de reentrancia.

| Backend | Adquisición, timeout y liberación |
| --- | --- |
| `FileCacheBackend` | Busca un `asyncio.Lock` en un registro de valores débiles por `(running_loop, canonical_directory, key)`. Espera adquisición con `asyncio.wait_for` cuando timeout no es `None`; de lo contrario, espera sin deadline. El timeout limita solo la adquisición, no el trabajo protegido. La salida libera y limpia `_impl`. |
| `DatabaseCacheBackend` | Genera un propietario UUID; intenta `acquireLock` y hace polling cada 0.05 segundos después de un intento fallido. El deadline es `loop.time() + timeout` si se especifica; el lease es `timeout or 10`. La salida espera la liberación comprobando propietario. No hay renovación automática de lease ni garantía FIFO. |
| Otros backends | Delega en `aiocache.lock.RedLock` con `lease=timeout or 10`; la salida también delega. No es el algoritmo de lock local por bucle y archivo. |

Este wrapper no normaliza ni valida `timeout`. Por eso `None`, cero, valores
negativos y positivos siguen el comportamiento real de espera y lease de
cada rama. En la entrada de base de datos se intenta la primera adquisición
antes de comprobar el deadline; un intento fallido puede exceder un deadline
ajustado por la latencia del backend o el intervalo de polling. La expiración
del lease puede permitir otro propietario mientras el bloque protegido
anterior sigue ejecutándose.

Los locks de usuario de archivo son locales a la combinación bucle,
directorio y clave, no locks entre procesos. Su registro débil no retiene
objetos de lock sin uso cuando desaparecen holders, waiters y otras referencias
fuertes. Es distinto de los locks de franja de operaciones de archivo.
Pruebas: [../../../tests/cache/test_cache_lock.py](../../../tests/cache/test_cache_lock.py),
`TestCacheLock` y `TestDatabaseCacheLock`.

**Limitación de RedLock:** aiocache 0.12.3 documenta que su RedLock de instancia
única no proporciona exclusión estricta de recursos. Su ruta de espera puede
continuar al vencer el lease y no vuelve a adquirir la clave tras una
notificación de liberación. Un probe local de memoria entró en un segundo
contexto mientras el primero seguía manteniendo su clave. Aquí no se ejecutó
el comportamiento de despliegues Redis/Memcached. Evidencia:
[../locks/lock.py](../locks/lock.py), con `aiocache.lock.RedLock` inspeccionado
y el caso de memoria ejecutado durante la validación.

En aiocache 0.12.3 inspeccionado, liberar el lock de Memcached elimina la
clave sin comprobar atómicamente su propietario. Su backend también
convierte espacios de claves a guiones bajos y las codifica como bytes. Las
factories de memoria, Redis y Memcached conservan el timeout predeterminado de
operación de cinco segundos de aiocache. Son comportamientos de dependencias,
no opciones adicionales expuestas por las factories de Orionis. Evidencia:
`aiocache.backends.memcached.MemcachedBackend`, `MemcachedCache._build_key` y
`aiocache.base.BaseCache.__init__` invocados, inspeccionados localmente; las
factories se enlazan en sus secciones de API.

### MsgspecSerializer

Importa `orionis.cache.serializers.json.MsgspecSerializer`. Fuente:
[../serializers/json.py](../serializers/json.py), `MsgspecSerializer`.

```python
class MsgspecSerializer(BaseSerializer):
```

```python
def dumps(self, value: Any) -> bytes:
```

```python
def loads(self, data: bytes | str | float | None) -> Any:
```

La constante pública de clase es `DEFAULT_ENCODING = None`. No hay
constructor explícito; `aiocache.serializers.BaseSerializer.__init__`
inicializa `encoding` usando esa constante por defecto. `dumps` retorna bytes
JSON UTF-8 desde `msgspec.json.encode`. `loads` retorna `None` para `None`,
codifica cadenas antes de decodificar JSON, decodifica
`bytes`/`bytearray`/`memoryview` y retorna otros valores nativos sin cambios.
La implementación observada acepta esos buffers más allá de la unión
literal declarada.

Este passthrough mantiene legibles los contadores de memoria después de que
increment de aiocache almacene enteros nativos sin `dumps`. JSON no conserva
tipos Python arbitrarios: tuples, sets y frozensets se convierten en listas,
y bytes en texto base64. Se propagan errores de codec o codificación; el
serializer no traduce excepciones ni guarda una caché por instancia de
valores decodificados. Pruebas:
[../../../tests/cache/test_serializers_json.py](../../../tests/cache/test_serializers_json.py).

### Serializer

Importa `orionis.cache.serializer.Serializer`. Fuente:
[../serializer.py](../serializer.py), `Serializer` y sus codecs privados.
Es el codec síncrono de artefactos, no el de los backends de aplicación.

```python
class Serializer:
```

```python
@staticmethod
def dumps(data: Any, indent: int | None = None) -> str:
```

```python
@staticmethod
def loads(raw: str | bytes) -> Any:
```

```python
@staticmethod
def dumpToFile(data: Any, file_path: Path) -> None:
```

```python
@staticmethod
def loadFromFile(file_path: Path) -> Any:
```

| Operación | Parámetros, resultado y efectos secundarios |
| --- | --- |
| `dumps(data, indent=None)` | Codifica recursivamente datos `Any` compatibles. Con `indent=None`, retorna JSON compacto de msgspec decodificado a `str`; de lo contrario, usa `json.dumps(indent=indent, separators=(",", ":"))`. Los valores incompatibles lanzan `TypeError`; no añade manejo de ciclos para grafos recursivos o cíclicos. |
| `loads(raw)` | Parsea JSON `str | bytes`, decodifica etiquetas recursivamente y retorna el valor reconstruido. JSON inválido, wrappers malformados, etiquetas desconocidas o resolución de tipos pueden lanzar errores de codec, `ValueError`, `KeyError`, import o atributos. |
| `dumpToFile(data, file_path)` | Codifica datos, escribe un hermano `.tmp` aleatorio único y reemplaza el destino con `Path.replace`. Retorna `None`; no añade creación de directorios padres, lock de franja, fsync ni reintento de renombrado. Ante `OSError`, intenta eliminar su staging y relanza. |
| `loadFromFile(file_path)` | Lee bytes síncronamente. Retorna `None` ante cualquier `OSError` de lectura o contenido vacío; de lo contrario, decodifica. No oculta JSON no vacío corrupto ni datos etiquetados malformados. |

Los escalares primitivos pasan sin cambios; los diccionarios y listas
codifican recursivamente sus valores o elementos. Los valores etiquetados
compatibles son `Path`, bytes, datetime, date, time, timedelta, `Decimal`,
`UUID`, complex, tuple, set, frozenset, objetos de clase, miembros enum y el
centinela `MISSING` de Orionis. Las claves reservadas del wrapper son
`__type__` y `__value__`; sus etiquetas son `path`, `bytes`, `datetime`, `date`,
`time`, `timedelta`, `decimal`, `uuid`, `complex`, `tuple`, `set`, `frozenset`,
`type`, `enum` y `missing`.

Las claves de diccionario no pasan por el codec personalizado. Las subclases
tratadas mediante el fallback de colecciones, Path o datetime no tienen por
qué conservar su identidad de subclase. Las etiquetas de clase y enum usan
cadenas de módulo y nombre cualificado, luego `rpartition(".")`, import de
módulo y `getattr`; no se garantiza reconstruir clases locales o anidadas
arbitrarias. Los valores de enums deben ajustarse a la representación emitida.

Un diccionario de usuario con `__type__` se interpreta como wrapper
etiquetado al decodificar, no se escapa automáticamente. Se ejecutó una colisión
de etiqueta reservada y lanzó `ValueError`. Decodificar type o enum puede
importar módulos y construir valores enum; no lo trates como un decoder
inerte para payloads no confiables. Pruebas:
[../../../tests/cache/test_serializer.py](../../../tests/cache/test_serializer.py),
`TestSerializer`.

### FileBasedCache

Importa `orionis.cache.file_based_cache.FileBasedCache` o la reexportación
raíz. Fuente: [../file_based_cache.py](../file_based_cache.py), `FileBasedCache`.

```python
class FileBasedCache:
```

```python
def __init__(
    self,
    path: Path,
    filename: str,
    monitored_dirs: list[Path] | None = None,
    monitored_files: list[Path] | None = None,
) -> None:
```

```python
def get(self) -> dict | None:
```

```python
def save(self, data: dict) -> tuple[int, str]:
```

```python
def clear(self) -> bool:
```

La constante pública de clase es `CACHE_VERSION = 1`. La construcción exige
explícitamente que `path` sea `Path` o lanza `TypeError`; crea ese directorio.
Combina `filename` mediante `path / filename`, sin comprobar contención ni
validar el nombre de archivo. Retiene una lista monitoreada no vacía
suministrada; listas falsy o `None` se convierten en listas vacías nuevas.
Mantén todas las rutas dentro del árbol de artefactos previsto.

`save(data)` exige un diccionario o lanza `TypeError`. Escribe
`{"__meta__": metadata, "__data__": data}` mediante `Serializer.dumpToFile`,
donde metadata contiene `version`, `generatedAt` y `sourcesHash`. Si coinciden
versión, hash de fuentes y datos existentes, omite la escritura. Retorna
`(CACHE_VERSION, sources_hash)` en ambas rutas.

`get()` lee mediante `Serializer.loadFromFile`, retornando `None` ante payload
falsy, metadata ausente, versión distinta o hash de fuentes distinto; de lo
contrario, retorna `payload.get("__data__")`. No impone que metadata o datos
editados externamente tengan la estructura anotada. JSON corrupto, etiquetas
inválidas o payloads que no sean mappings pueden lanzar errores en vez de
producir un miss. `clear()` retorna `True` si se eliminó el artefacto y `False`
solo ante `FileNotFoundError`; no reinicia la caché de hash de fuentes.

El monitoreo recoge archivos explícitos existentes y archivos `*.py`
encontrados recursivamente en los directorios monitoreados. Resuelve rutas,
excluye el propio archivo de caché, deduplica, ordena y hashea cada ruta POSIX
más `st_mtime_ns` y `st_size` empaquetados, con SHA-1
(`usedforsecurity=False`). No hashea contenidos fuente ni monitorea todos los
archivos no Python del directorio. Un cambio que conserve ambos campos de
metadata puede dejar el hash sin cambios.

El hash se guarda por instancia durante 0.5 segundos con un reloj monotónico.
Los cambios no se ven necesariamente en llamadas inmediatas dentro de esa
ventana; una instancia nueva recalcula sin ese hash retenido. No se declara
reset público ni watcher. Pueden propagarse errores de stat, recorrido,
codec o escritura. Pruebas:
[../../../tests/cache/test_file_based_cache.py](../../../tests/cache/test_file_based_cache.py),
`TestFileBasedCache`.

### CacheProvider

Importa `orionis.cache.provider.CacheProvider`. Fuente:
[../provider.py](../provider.py), `CacheProvider`.

```python
class CacheProvider(ServiceProvider, DeferrableProvider):
```

```python
@classmethod
def provides(cls) -> list[type]:
```

```python
def register(self) -> None:
```

```python
async def boot(self) -> None:
```

No hay constructor explícito; hereda `ServiceProvider.__init__`, que almacena
la `IApplication` suministrada en `self.app`. Evidencia:
[../../container/providers/service_provider.py](../../container/providers/service_provider.py).
`provides()` retorna una nueva lista `[ICacheManager]`. `register()` realiza
`self.app.singleton(ICacheManager, CacheManager)` y retorna `None`. `boot()`
espera `CacheFacade.pin()` y retorna `None`. Se propagan errores del contenedor,
binding o resolución de fachada; no implementa cierre de backends. Los
efectos de registro y estado de fachada son distintos de las operaciones de
datos.

### Excepciones

Importa ambas desde `orionis.cache.exceptions`. Fuente:
[../exceptions.py](../exceptions.py).

```python
class CacheException(Exception):
```

```python
class CacheStoreException(CacheException):
```

Ninguna declara constructor ni estado adicional; heredan argumentos y
comportamiento de cadena de las excepciones estándar. `CacheException` es
la base de excepciones de caché, no un wrapper aplicado automáticamente a
todos los errores de dependencias. `CacheStoreException` se lanza explícitamente
para stores desconocidos o no configurados del manager y primitivas de
reemplazo incompatibles del repositorio. Los mensajes reales se producen en
esos puntos de llamada; los fallos de E/S, SQL, codec, callback o conversión
de dependencias generalmente conservan su propio tipo. Pruebas:
[../../../tests/cache/test_exceptions.py](../../../tests/cache/test_exceptions.py).

## Ejemplos de uso

Cada bloque es un script completo separado para el framework local instalado
y Python 3.14+. Ninguno usa servicios Redis/Memcached, credenciales privadas,
la aplicación bootstrap del checkout ni almacenamiento compartido de
aplicación. Los recursos están en memoria o en directorios temporales.
La tabla de verificación distingue sintaxis, imports locales y ejecución.

### 1. Repositorio de memoria y comportamiento JSON

```python
import asyncio
from orionis.cache import CacheRepository
from orionis.cache.stores.memory import build

async def main() -> None:
    """Exercise prefixed values, batch operations, and counters."""
    backend = build()
    repository = CacheRepository(backend, prefix="example")
    try:
        assert await repository.set("payload", {"items": (1, 2), "raw": b"a"})
        assert await repository.get("payload") == {"items": [1, 2], "raw": "YQ=="}
        assert await repository.setMany({"a": 1, "b": 2})
        assert await repository.getMany(["a", "b", "absent"]) == {
            "a": 1, "b": 2, "absent": None,
        }
        assert await repository.getMany([]) == {}
        assert not await repository.replace("missing", "value")
        assert await repository.replace("a", 3)
        assert await repository.add("once", True)
        assert not await repository.add("once", False)
        assert await repository.increment("hits", 5) == 5
        assert await repository.decrement("hits", 2) == 3
        assert await repository.get("hits") == 3
        assert await repository.has("a")
        assert await repository.delete("a")
        assert not await repository.delete("a")
        assert await repository.clear()
    finally:
        await backend.close()

asyncio.run(main())
```

Se retornan valores normalizados por JSON, no los tipos tuple/bytes
originales. Los contadores de memoria siguen legibles mediante el passthrough
nativo del serializer.

### 2. Observar None almacenado entre backends

```python
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.cache import CacheRepository
from orionis.cache.stores.file import FileCacheBackend
from orionis.cache.stores.memory import build

async def compare(backend: object) -> tuple[object, int, bool]:
    """Return the resolver outcome and null-key deletion behavior."""
    repository = CacheRepository(backend)
    calls: list[str] = []

    def resolve() -> str:
        """Record a cache miss and return a replacement value."""
        calls.append("resolved")
        return "replacement"

    await repository.set("null-value", None)
    result = await repository.remember("null-value", None, resolve)
    await repository.set("null-pull", None)
    assert await repository.pull("null-pull") is None
    return result, len(calls), await repository.has("null-pull")

async def main() -> None:
    """Compare memory with an isolated file backend."""
    memory = build()
    try:
        with TemporaryDirectory(prefix="orionis-cache-null-") as directory:
            file = FileCacheBackend(Path(directory))
            assert await compare(memory) == ("replacement", 1, True)
            assert await compare(file) == (None, 0, False)
    finally:
        await memory.close()

asyncio.run(main())
```

Esto comprueba intencionadamente la diferencia implementada, en vez de asumir
que todo backend trata `None` como un hit en `remember`/`pull`.

### 3. Selección del manager y un error real de store

```python
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from orionis.cache import CacheManager
from orionis.cache.exceptions import CacheStoreException

class Settings:
    """Supply the application surface consumed by CacheManager."""

    __slots__ = ("basePath",)

    def __init__(self, root: Path) -> None:
        """Retain a temporary base path."""
        self.basePath = root

    def config(self, section: str) -> SimpleNamespace:
        """Return the cache settings without booting an application."""
        assert section == "cache"
        return SimpleNamespace(
            default="memory", prefix="demo", stores=SimpleNamespace(),
        )

async def main() -> None:
    """Use default-store proxies and reject an unknown store."""
    with TemporaryDirectory(prefix="orionis-cache-manager-") as directory:
        root = Path(directory)
        manager = CacheManager(Settings(root))
        assert manager.store() is manager.store("") is manager.store("memory")
        try:
            manager.store("unknown")
        except CacheStoreException:
            assert list(root.iterdir()) == []
        else:
            error_msg = "Expected an unknown-store error"
            raise AssertionError(error_msg)
        assert await manager.set("value", 1)
        assert await manager.get("value") == 1
        assert await manager.store().replace("value", 2)
        assert await manager.get("value") == 2
        assert await manager.clear()

asyncio.run(main())
```

El pequeño objeto de ajustes suministra la superficie de dependencia exacta
en runtime; no redefine `IApplication` ni afirma un binding del contenedor.

### 4. Bloqueo de archivo y límites de limpieza por prefijo

```python
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.cache import CacheRepository
from orionis.cache.stores.file import FileCacheBackend

async def main() -> None:
    """Serialize local work and demonstrate backend-wide clear."""
    with TemporaryDirectory(prefix="orionis-cache-file-") as directory:
        backend = FileCacheBackend(Path(directory))
        left = CacheRepository(backend, prefix="left")
        right = CacheRepository(backend, prefix="right")
        assert backend.lockNamespace == Path(directory).resolve()
        state = {"inside": 0, "peak": 0}

        async def update() -> None:
            """Increment while holding the same loop-local user lock."""
            async with left.lock("workflow", timeout=5):
                state["inside"] += 1
                state["peak"] = max(state["peak"], state["inside"])
                await left.increment("count")
                state["inside"] -= 1

        await asyncio.gather(*(update() for index in range(6)))
        assert state["peak"] == 1
        assert await left.get("count") == 6
        await left.set("expired", "old", ttl=-1)
        assert not await left.has("expired")
        assert not await left.replace("expired", "late")
        await right.set("value", "other prefix")
        assert await left.clear()
        assert not await right.has("value")

asyncio.run(main())
```

El trabajo protegido es local al mismo bucle, ruta y clave. `clear` elimina
los datos del otro prefijo porque ambos repositorios comparten directorio
de backend.

### 5. Backend de base de datos con conexión SQLite temporal

```python
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.cache import CacheRepository
from orionis.cache.stores.database import build
from orionis.database.connection import Connection

async def main() -> None:
    """Exercise cache rows and owned locks without an external database."""
    with TemporaryDirectory(prefix="orionis-cache-sqlite-") as directory:
        connection = Connection("example", {
            "driver": "sqlite",
            "database": str(Path(directory) / "cache.sqlite"),
            "prefix": "",
        })
        backend = build(connection, "cache", "cache_locks")
        repository = CacheRepository(backend, prefix="example")
        try:
            assert await repository.set("value", {"total": 1})
            assert await repository.replace("value", {"total": 2})
            assert await repository.get("value") == {"total": 2}
            assert await repository.setMany({"a": 1, "b": 2})
            assert await repository.getMany(["a", "b"]) == {"a": 1, "b": 2}
            assert await repository.increment("count", 3) == 3
            assert await repository.decrement("count") == 2
            assert await backend.acquireLock("owned", "first", lease=5)
            assert not await backend.acquireLock("owned", "second", lease=5)
            await backend.releaseLock("owned", "first")
            async with repository.lock("workflow", timeout=5):
                assert await repository.add("once", True)
                assert not await repository.add("once", False)
            await repository.set("expired", "value", ttl=-1)
            assert not await repository.replace("expired", "new")
            assert await repository.clear()
        finally:
            await connection.disconnect()

asyncio.run(main())
```

La primera operación crea tablas. La conexión se cierra antes de eliminar el
directorio temporal; no se ejecuta una migración de base de datos del framework.

### 6. Serialización tipada y artefactos monitoreados

```python
from datetime import UTC, datetime
from decimal import Decimal
from http import HTTPStatus
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID
from orionis.cache import FileBasedCache
from orionis.cache.serializer import Serializer
from orionis.support.types.sentinel import MISSING

payload = {
    "created": datetime(2026, 1, 2, tzinfo=UTC),
    "amount": Decimal("10.25"),
    "identifier": UUID("12345678-1234-5678-1234-567812345678"),
    "path": Path("report.txt"),
    "values": (b"content", {"alpha", "beta"}),
    "status": HTTPStatus.OK,
    "class": Path,
    "missing": MISSING,
}
assert Serializer.loads(Serializer.dumps(payload)) == payload
assert Serializer.loads(Serializer.dumps(payload, indent=2)) == payload

with TemporaryDirectory(prefix="orionis-cache-artifact-") as directory:
    root = Path(directory)
    source = root / "source.py"
    source.write_text("value = 1\n", encoding="utf-8")
    artifact = FileBasedCache(root, "artifact.json", monitored_files=[source])
    version, source_hash = artifact.save(payload)
    assert version == FileBasedCache.CACHE_VERSION
    assert len(source_hash) == 40
    assert artifact.get() == payload
    assert artifact.save(payload) == (version, source_hash)
    source.write_text("value = 10000\n", encoding="utf-8")
    fresh = FileBasedCache(root, "artifact.json", monitored_files=[source])
    assert fresh.get() is None
    assert fresh.clear()
    assert not fresh.clear()
    standalone = root / "typed.json"
    Serializer.dumpToFile(payload, standalone)
    assert Serializer.loadFromFile(standalone) == payload
    assert Serializer.loadFromFile(root / "missing.json") is None
```

Un lector nuevo evita la ventana retenida de 0.5 segundos del hash de fuentes.
La serialización tipada es una capacidad de artefactos, no el codec de la
caché de aplicación.

### 7. Resolver el proveedor y la fachada en una aplicación aislada

```python
import asyncio
import inspect
import os
from pathlib import Path
from tempfile import TemporaryDirectory

with TemporaryDirectory(prefix="orionis-cache-application-") as directory:
    original_cwd = Path.cwd()
    os.chdir(directory)
    try:
        from orionis import Application
        from orionis.cache.contracts import ICacheManager
        from orionis.support.facades.cache import Cache

        app = Application(base_path=Path(directory)).create()
        app.config("cache", {"default": "memory", "prefix": "example", "stores": {}})

        async def main() -> None:
            """Resolve a deferred store and use the now-pinned facade."""
            pending = Cache.store("memory")
            assert inspect.isawaitable(pending)
            repository = await pending
            manager = await app.make(ICacheManager)
            assert manager.store("memory") is repository
            assert Cache.store("memory") is repository
            assert await Cache.set("value", 7)
            assert await Cache.get("value") == 7
            assert await manager.store().replace("value", 8)
            assert await Cache.get("value") == 8
            assert await Cache.clear()

        asyncio.run(main())
    finally:
        Cache.unpin()
        os.chdir(original_cwd)
```

Esto ejercita el registro diferido real y el pin de fachada sin cargar la
aplicación bootstrap del checkout. Es un ejemplo de proceso independiente,
no una receta para construir una segunda aplicación dentro de un worker
existente.

## Características de diseño

| Mecanismo observado | Consecuencia concreta | Evidencia |
| --- | --- | --- |
| Exportaciones raíz diferidas | Importar el paquete no resuelve inmediatamente sus tres clases públicas; las exportaciones resueltas permanecen en los globals del paquete. | [../__init__.py](../__init__.py) |
| Binding singleton del servicio | El manager resuelto por la aplicación retiene su mapa de backends y repositorios y el prefijo capturado durante su vida. | [../provider.py](../provider.py); [../cache_manager.py](../cache_manager.py) |
| Composición de backends sin protocolo exigido | Los repositorios directos pueden usar backends personalizados; los métodos ausentes y errores aparecen al invocarlos. | [../repository.py](../repository.py) |
| Slots y herencia ABC | Repositorio, lock, backends de archivo y base de datos y artefactos usan slots. `CacheManager` sigue teniendo `__dict__` de instancia por su base `ICacheManager` sin slots, confirmado en runtime. | Las clases correspondientes y [../contracts/cache_manager.py](../contracts/cache_manager.py) |
| Codecs JSON separados | Los valores de aplicación usan normalización JSON de msgspec; los artefactos etiquetados pueden reconstruir tipos Python adicionales. | [../serializers/json.py](../serializers/json.py); [../serializer.py](../serializer.py) |
| Sin abstracción compartida de close de backends | Un llamador directo conserva responsabilidad sobre clientes y conexiones que posee; no se declara API de cierre del manager o repositorio. | [../cache_manager.py](../cache_manager.py); [../repository.py](../repository.py); [../stores/database.py](../stores/database.py) |

No hay constructor generado por dataclass, API de generadores ni enum público
de caché en el módulo objetivo. Los dataclasses de configuración y `Drivers`
pertenecen a `orionis.foundation.config.cache`, no a este inventario público.

## Rendimiento y concurrencia

- La creación de stores del manager no contiene await y memoiza por nombre
  resuelto. No está protegida por un lock de hilo; el primer uso concurrente
  entre hilos no tiene una garantía de construcción única declarada por el
  módulo.
- Los helpers por lotes del repositorio materializan listas prefijadas, pares
  y diccionarios retornados. Los métodos por lotes de archivo o base de datos
  son secuenciales, no lotes transaccionales o paralelos de base de datos.
  Los errores pueden dejar escrituras anteriores completadas.
- Los valores normales de aplicación cruzan límites de codificación y
  decodificación JSON; no forman un almacén general de objetos que conserve
  referencias. Los contadores de memoria son una excepción documentada de
  valores nativos a la ruta normal de codec.
- `remember` invoca un callback síncrono en el hilo del event loop y no bloquea
  un miss. `pull` y las lecturas de filas expiradas de base de datos separan
  operaciones entre awaits. No deduzcas operaciones compuestas atómicas de
  sus nombres.
- El trabajo de disco y decodificación del backend de archivo se delega
  mediante `asyncio.to_thread`. La codificación de escrituras ocurre en las
  rutas de worker. Resolver y crear el directorio en el constructor es
  síncrono. Las esperas de file locks y el backoff de renombrado pueden ocupar
  hilos; los métodos async no garantizan ausencia de asignaciones o recursos.
- Las franjas de operaciones de archivo son distintas de los locks de usuario
  locales al bucle. Los contadores incluyen un lock asyncio de instancia y un
  lock de franja del archivo; las pruebas existentes cubren varias instancias
  de backend sobre un directorio compartido. Esto no certifica todos los
  escenarios de fallo entre procesos o plataformas.
- La preparación de esquema de base de datos es por instancia de backend.
  Dos llamadas de creación exitosas la marcan lista; los fallos iniciales la
  dejan sin preparar para reintentar después. No hay caché de preparación
  compartida entre instancias.
- `add` de base de datos usa el conflicto de clave primaria; increment usa
  hasta 25 rondas compare-and-swap y puede fallar al agotar la contención.
  Las pruebas existentes de SQLite en archivo ejercitan operaciones
  concurrentes, no todos los drivers compatibles.
- Los contextos de usuario de base de datos y RedLock usan leases sin
  renovación. Los locks de usuario de archivo usan un registro débil por
  bucle, directorio y clave. El comportamiento RedLock de Redis, Memory o
  Memcached no debe equipararse al algoritmo de archivo.
- Las API de artefactos realizan trabajo síncrono de codec recursivo, lectura
  y escritura, recorrido de directorios, resolución de rutas, ordenación y
  llamadas stat. Los hashes de fuentes se guardan por instancia durante
  0.5 segundos; no hay hash de contenido ni watcher activo. El staging único
  evita compartir un nombre temporal, pero no es una transacción de todo el
  store ni una certificación de durabilidad multiplataforma.
- La cancelación no tiene protocolo de shielding específico del módulo.
  Estos wrappers no detienen forzosamente un worker de archivo ni una
  operación de backend ya iniciados; conserva los recursos hasta finalizar
  realmente el trabajo.

Evidencia: [../cache_manager.py](../cache_manager.py),
[../repository.py](../repository.py), [../stores/file.py](../stores/file.py),
[../stores/database.py](../stores/database.py), [../locks/lock.py](../locks/lock.py),
[../serializer.py](../serializer.py) y
[../file_based_cache.py](../file_based_cache.py), con los símbolos exactos
descritos en sus secciones de API. No se realizaron benchmarks.

> ⚠️ No especificado en el código fuente: un contrato de thread safety global
> del módulo, reutilización anidada de un `CacheLock` activo o durabilidad de
> archivos ante caída o pérdida de energía. Los locks y mecanismos de staging
> individuales no establecen esas garantías más amplias.

## Notas de compatibilidad

El proyecto declara Python `>=3.14` en
[../../../pyproject.toml](../../../pyproject.toml). Se validó con el intérprete
local del repositorio, **CPython 3.14.6 en Windows**. Las anotaciones de unión,
`typing.Self` y strict zip son características de lenguaje observables; su
uso no certifica por sí solo versiones anteriores de Python. Varios imports
exclusivos de anotaciones están bajo `TYPE_CHECKING`; no asumas una resolución
runtime irrestricta de `get_type_hints`. Los ejemplos tienen como objetivo
Python 3.14+.

| Dependencia | Restricción declarada | Lockfile | Instalada para validar |
| --- | --- | --- | --- |
| `aiocache[redis,memcached]` | `>=0.12.3` | `0.12.3` | `0.12.3` |
| `redis[hiredis]` | `>=8.1.0` | `8.1.0` | `8.1.0` |
| `msgspec` | `>=0.21.1` | `0.22.0` | `0.22.0` |
| `filelock` | `>=4.0.1` | `4.0.8` | `4.0.8` |
| `sqlalchemy[asyncio]` | `>=2.0.54,<3.0` | `2.1.1` | `2.1.1` |
| `aiosqlite` | `>=0.22.1` | `0.22.1` | `0.22.1` |
| `aiomcache`, extra transitivo de aiocache | `>=0.5.2` en metadata de aiocache instalado | `0.8.2` | `0.8.2` |
| `ruff`, exclusivo de desarrollo | `>=0.16.8` | `0.16.9` | `0.16.9` |

Evidencia del manifiesto y lockfile:
[../../../pyproject.toml](../../../pyproject.toml) y
[../../../uv.lock](../../../uv.lock); las versiones instaladas y requisitos
de extras de aiocache se consultaron durante esta tarea. Una versión de
lockfile no es una mínima soportada. Las observaciones sobre terceros se
refieren a las versiones instaladas inspeccionadas, no a todas las versiones
aceptadas por los rangos.

La interpretación de TTL no es uniforme. En el backend local de memoria,
`ttl=0` conserva una entrada sin programar expiración; en archivo y SQLite,
expira inmediatamente en la siguiente lectura. Los deadlines de archivo usan
tiempo monotónico; los de base de datos usan epoch de reloj de pared.
Las restricciones de Redis/Memcached siguen siendo las de sus clientes y
servicios. Una anotación float arbitraria no demuestra TTL fraccionario
portable en Memcached. Fuente: las factories de backend,
[../stores/file.py](../stores/file.py), [../stores/database.py](../stores/database.py)
y `aiocache.backends.memory.SimpleMemoryBackend._set` inspeccionado.

## Verificación y limitaciones

### Inventario y pruebas

El inventario cubre 21 archivos Python, 14 clases públicas, cuatro funciones
`build` específicas de módulo, los hooks de atributos y directorio del
paquete, todos los métodos públicos y la propiedad `lockNamespace`:
**124 fragmentos literales de declaración**. También cubre reexportaciones
raíz y de contratos y `__all__`, dos constantes públicas de clase y cuatro
alias de operaciones por lotes. Los nombres importados y helpers o estado
privados se excluyen como se explica arriba; no se omitió silenciosamente
un símbolo público.

Se inspeccionaron los nueve archivos de pruebas existentes de
[../../../tests/cache](../../../tests/cache). El descubrimiento nativo con
`TestingEngine` y la ejecución con `TestRunner` completaron **210/210 pruebas
correctamente**, sin fallos crudos, errores crudos ni omisiones, usando una
aplicación temporal creada y sin caché de resultados. No fue el bootstrap
Reactor configurado del checkout ni una ejecución de todo el framework.

Otros probes aislados verificaron procedencia de imports locales, rechazo de
store desconocido, reutilización y layout del manager, ausencia de `replace`
en el manager, identidad de alias, comportamiento de `None`, TTL cero en
memoria, archivo y SQLite, colisiones de etiquetas reservadas, decodificación
de artefactos corruptos y la limitación de espera de RedLock en memoria.
Son casos comprobados, no garantías de todo un despliegue. No se repitió ni
trasladó la certificación Redis real de documentación anterior como resultado
de esta tarea.

### Resultados de ejemplos

| Ejemplo | Sintaxis | Imports locales | Ejecución |
| --- | --- | --- | --- |
| 1. Repositorio de memoria | Correcta | Correctos | Ejecutado correctamente. |
| 2. None almacenado | Correcta | Correctos | Ejecutado correctamente. |
| 3. Error del manager | Correcta | Correctos | Ejecutado correctamente. |
| 4. Flujo de archivo | Correcta | Correctos | Ejecutado correctamente. |
| 5. Backend SQLite | Correcta | Correctos | Ejecutado correctamente. |
| 6. Artefactos tipados | Correcta | Correctos | Ejecutado correctamente. |
| 7. Proveedor y fachada | Correcta | Correctos | Ejecutado correctamente. |

Los 124 fragmentos de declaración coincidieron con el código local
inspeccionado. Los siete scripts se extrajeron de este README, se compilaron,
se comprobaron sus imports locales por separado y se ejecutaron en directorios
de trabajo temporales independientes, sin warnings. Ambos README tienen 43
encabezados correspondientes, 131 bloques idénticos y 114 enlaces y anclas
locales válidos cada uno. Los 20 enlaces del skill y su frontmatter YAML de
dos campos se comprobaron independientemente, incluida la identidad derivada
`orionis-cache`. Ruff pasó para `orionis/cache` y `tests/cache`, sin
correcciones ni escrituras de caché. Los recursos e informes de validación
permanecen fuera del repositorio.

### Límites restantes

Las discrepancias documentadas de descripción del código conciernen a
predeterminados de configuración, significados de conexión y timeout de
bloqueos y el comportamiento null del centinela. No autorizan cambios de
fuente. Las listas de excepciones de dependencias y callbacks no son
exhaustivas. Inspeccionar mecanismos mutex o CAS es distinto de ejecutar
todos los escenarios de concurrencia y fallo.

> ⚠️ No verificable con los archivos disponibles: una comparación completa
> byte a byte del estado inicial de esta ejecución documental. Su instantánea
> inicial registró 7.421 archivos, pero omitió 1.186 archivos ocultos
> preexistentes. Los archivos registrados no mostraron cambios fuera de
> alcance; los omitidos tenían fechas anteriores y coincidieron con una
> huella completa previa del espacio de trabajo. Esa comprobación auxiliar
> no se presenta como una instantánea inicial nueva completa. El índice y
> HEAD de Git no cambiaron y la salida contiene exactamente los tres
> documentos solicitados, sin contenido adicional.

> ⚠️ No ejecutado en este entorno: servicios Redis/Memcached reales,
> drivers de base de datos externos, despliegue entre procesos o free-threaded,
> Linux/macOS y versiones de Python distintas de CPython 3.14.6 en Windows.
> Se validó solo con memoria, archivos locales y SQLite aislados.
