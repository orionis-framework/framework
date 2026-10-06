# orionis.cache

> `orionis.cache` proporciona repositorios clave/valor asíncronos sobre memoria, archivos, Redis, Memcached o base de datos, además de locks y artefactos de archivo sensibles a cambios de fuentes.

## Descripción general

El código de aplicación normalmente llama a la fachada fijada `Cache` u obtiene un `CacheRepository` nombrado mediante `Cache.store(name)`. El manager lee la configuración `cache`, construye cada backend de forma diferida, aplica el prefijo global y reutiliza un repositorio por nombre de store. El repositorio ofrece lecturas, escrituras, lotes, contadores, resolvers cache-aside, add/replace atómicos, pull y locks async.

El `FileBasedCache` exportado por separado tiene otra finalidad: almacena un único diccionario serializado en un archivo y lo invalida cuando cambian fuentes Python monitorizadas. Orionis usa ese estilo para artefactos compilados del framework, no como almacenamiento general clave/valor.

## Requisitos

- Python 3.14 o posterior.
- `aiocache[redis,memcached]>=0.12.3`, instalado por Orionis.
- Servicios Redis o Memcached cuando se seleccionen esos stores.
- Una conexión de base de datos Orionis configurada para el store database; bases distintas de SQLite pueden necesitar el extra correspondiente.
- Un directorio escribible para el store file y para `FileBasedCache`.

## Inicio rápido

Este ejemplo independiente usa el backend de memoria mediante la API pública del repositorio:

```python
import asyncio

from orionis.cache import CacheRepository
from orionis.cache.stores.memory import build


async def main() -> None:
    cache = CacheRepository(build(), prefix="docs")
    await cache.set("greeting", {"message": "hello"}, ttl=30)
    print(await cache.get("greeting"))


asyncio.run(main())  # {'message': 'hello'}
```

La clave física es `docs:greeting`; quienes llaman siguen usando el nombre sin prefijo.

Validación: **Executed successfully** en CPython 3.14.6.

## Conceptos principales

### Manager, repositorio y backend

`CacheManager` resuelve configuración y posee instancias de repositorio. `CacheRepository` normaliza la API y añade prefijos. Un backend realiza las primitivas específicas del almacenamiento. Las llamadas directas al manager se delegan al repositorio predeterminado.

### Ciclo del store y prefijo

Los stores se construyen en el primer acceso y quedan almacenados en esa instancia del manager. Llamadas repetidas a `store("redis")` devuelven el mismo repositorio. `cache.prefix` se aplica a todas las claves, incluidos locks; `clear()` aun así limpia todo el backend seleccionado, no solo entradas con prefijo.

### Resolución cache-aside

`remember(key, ttl, resolver)` lee con un sentinel privado, por lo que un `None` almacenado cuenta como hit. En un miss invoca un resolver sync o async sin argumentos, guarda el resultado y lo devuelve. No agrupa misses concurrentes; usa `lock()` alrededor de regeneración costosa cuando sea necesario.

### Locks según el store

Los locks file usan un `asyncio.Lock` compartido por event loop, directorio y clave. Los locks database usan filas con lease y polling. Otros backends aiocache usan `RedLock`; el comportamiento Redis/Memcached sigue por tanto la semántica de lease de aiocache.

## Estructura del módulo

| Área | Responsabilidad |
|---|---|
| `cache_manager.py`, `provider.py` | Construcción/reutilización de stores, proxy predeterminado y registro de fachada/contenedor. |
| `repository.py` | Operaciones async uniformes y prefijos. |
| `stores/` | Backends memory, file, Redis, Memcached y database. |
| `locks/` | Context manager async adaptado al backend. |
| `serializer.py`, `serializers/` | Codificación enriquecida compatible con JSON y serializer aiocache. |
| `file_based_cache.py` | Caché de un archivo invalidada por hash de fuentes. |
| `contracts/`, `exceptions.py` | Interfaces de extensión y errores. |

## API pública

### Fachada `Cache` y `CacheManager`

Usa `from orionis.support.facades.cache import Cache` en una aplicación iniciada. `CacheProvider` registra `ICacheManager` como singleton y fija la fachada. `store(name=None)` es síncrono y devuelve un repositorio; los demás métodos delegan al store predeterminado:

```python
repo = Cache.store("redis")
value = await Cache.get("key")
await Cache.set("key", value, ttl=60)
```

Los nombres soportados son `file`, `memory`, `redis`, `memcached` y `database`. Un store desconocido o ausente provoca `CacheStoreException`.

### `CacheRepository`

```text
CacheRepository(backend: Any, prefix: str = "")
```

| Método | Comportamiento |
|---|---|
| `get(key)` / `has(key)` | Lee un valor o comprueba una entrada viva. Un `get` ausente devuelve `None`. |
| `set(key, value, ttl=None)` | Guarda o sobrescribe. TTL está en segundos. |
| `replace(key, value, ttl=None)` | Reemplaza atómicamente solo una entrada viva existente. |
| `delete(key)` / `clear()` | Elimina una entrada o vacía el backend seleccionado. |
| `getMany(keys)` | Devuelve un mapping que conserva las claves pedidas sin prefijo. |
| `setMany(values, ttl=None)` | Guarda un mapping con TTL compartido. |
| `remember(key, ttl, resolver)` | Devuelve caché o calcula/guarda un resultado sync o async. |
| `rememberForever(key, resolver)` | `remember` sin expiración. |
| `pull(key)` | Lee y después elimina; ausente devuelve `None`. |
| `add(key, value, ttl=None)` | Guarda atómicamente solo si falta; conflictos devuelven `False`. |
| `increment(key, amount=1)` / `decrement(...)` | Aplica deltas enteros y devuelve el nuevo valor. |
| `lock(key, timeout=None)` | Devuelve un context manager async para la clave prefijada. |

Pueden propagarse errores del backend o serialización. `replace` lanza `CacheStoreException` si un backend personalizado no tiene reemplazo atómico.

### `FileBasedCache`

```text
FileBasedCache(
    path: Path,
    filename: str,
    monitored_dirs: list[Path] | None = None,
    monitored_files: list[Path] | None = None,
)
```

`save(data)` escribe un payload versionado y devuelve `(CACHE_VERSION, sources_hash)`; datos y hash idénticos omiten reescritura. `get()` devuelve el diccionario solo si versión y hash coinciden, o `None`. `clear()` indica si existía el archivo. Solo participan archivos Python de directorios monitorizados y se excluye el propio archivo de caché.

### API de extensión

`ICacheManager`, `ICacheRepository` e `IFileBasedCache` definen contratos sustituibles. Backends personalizados entregados a `CacheRepository` deben proporcionar los métodos estilo aiocache utilizados (`get`, `set`, `exists`, `delete`, lotes, `add` e `increment`).

## Flujos de trabajo comunes

### Usar el store predeterminado

Llama directamente métodos de fachada. La primera operación construye el store configurado; las siguientes reutilizan su repositorio. Especifica TTL en segundos o `None` para no expirar.

### Seleccionar un store explícito

Llama `Cache.store("memory")` u otro nombre configurado y conserva el repositorio o vuelve a pedirlo al manager. Todos reciben el mismo prefijo global.

### Regenerar datos costosos con seguridad

Consulta mediante `remember`; si el trabajo concurrente duplicado es inaceptable, adquiere `async with cache.lock("resource", timeout=...)`, vuelve a comprobar dentro del lock, calcula y guarda.

### Guardar artefactos compilados

Construye `FileBasedCache` con fuentes relevantes, llama `get`, reconstruye si devuelve `None` y ejecuta `save`. Un cambio de fuente invalida los datos sin eliminar primero el archivo.

## Ejemplos

### Almacenar un resultado de resolver, incluido `None`

```python
import asyncio

from orionis.cache import CacheRepository
from orionis.cache.stores.memory import build


async def main() -> None:
    cache = CacheRepository(build())
    calls = 0

    async def resolve() -> None:
        nonlocal calls
        calls += 1
        return None

    await cache.remember("nullable", 60, resolve)
    await cache.remember("nullable", 60, resolve)
    print(calls)  # 1


asyncio.run(main())
```

El sentinel evita tratar el `None` almacenado como otro miss.

Validación: **Executed successfully** en CPython 3.14.6.

### Usar add atómico y pull

```python
import asyncio

from orionis.cache import CacheRepository
from orionis.cache.stores.memory import build


async def main() -> None:
    cache = CacheRepository(build())
    print(await cache.add("ticket", "A"))  # True
    print(await cache.add("ticket", "B"))  # False
    print(await cache.pull("ticket"))       # A
    print(await cache.has("ticket"))        # False


asyncio.run(main())
```

`add` conserva el valor original en conflicto; `pull` lo elimina después de leer.

Validación: **Executed successfully** en CPython 3.14.6.

### Proteger una sección crítica

```python
import asyncio

from orionis.cache import CacheRepository
from orionis.cache.stores.memory import build


async def main() -> None:
    cache = CacheRepository(build())
    async with cache.lock("inventory:7", timeout=2):
        current = await cache.get("inventory:7") or 0
        await cache.set("inventory:7", current + 1)
    print(await cache.get("inventory:7"))  # 1


asyncio.run(main())
```

Para memory esto usa el `RedLock` basado en lease de aiocache y coordina usuarios de la misma instancia backend.

Validación: **Executed successfully** en CPython 3.14.6.

### Invalidar un artefacto cuando cambia una fuente

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from orionis.cache import FileBasedCache


with TemporaryDirectory() as directory:
    root = Path(directory)
    source = root / "feature.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")

    cache = FileBasedCache(root, "compiled.cache", monitored_files=[source])
    cache.save({"routes": ["/"]})
    print(cache.get())  # {'routes': ['/']}

    source.write_text("VALUE = 2\n", encoding="utf-8")
    time.sleep(0.6)  # FileBasedCache refreshes its source hash every 0.5 s.
    print(cache.get())  # None
```

Validación: **Executed successfully** en CPython 3.14.6.

## Configuración

| Clave | Variable de entorno | Valor predeterminado |
|---|---|---|
| `cache.default` | `CACHE_STORE` | `file` |
| `cache.prefix` | `CACHE_PREFIX` | vacío |
| `cache.stores.file.path` | `CACHE_FILE_PATH` | `storage/framework/cache/data` |
| `cache.stores.redis.endpoint/port/db/password` | `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD` | `127.0.0.1`, `6379`, `0`, `None` |
| `cache.stores.memcached.endpoint/port` | `MEMCACHED_HOST`, `MEMCACHED_PORT` | `127.0.0.1`, `11211` |
| `cache.stores.database.connection` | `DB_CACHE_CONNECTION` | conexión DB predeterminada |
| `cache.stores.database.table` | `DB_CACHE_TABLE` | `cache` |
| `cache.stores.database.lock_table` | `DB_CACHE_LOCK_TABLE` | `cache_locks` |

Las rutas file relativas se resuelven contra `app.basePath`. Las entidades validan nombres de driver y opciones durante la preparación.

## Integración con Orionis

`CacheProvider` es diferible: el contenedor registra el manager singleton cuando se necesita `ICacheManager` y después fija la fachada `Cache`. El store database obtiene su conexión mediante `ConnectionResolver`. Los backends file y database usan el serializer de Orionis para round-trip de valores más allá de JSON simple.

El paquete también se usa en compilación del framework y otros módulos con estado almacenado. Importar `orionis.cache` no construye un backend ni conecta un servicio.

## Errores y casos límite

- Ausencia y `None` almacenado son indistinguibles mediante `get`, pero `remember` los distingue internamente.
- `clear()` vacía el namespace del backend y no filtra por prefijo.
- `pull` es lectura seguida de eliminación, no una primitiva backend atómica.
- Misses concurrentes de `remember` pueden ejecutar varias veces el resolver.
- Stores inválidos o no configurados lanzan `CacheStoreException`; pueden propagarse errores de conexión, serializer y backend.
- `add` convierte el `ValueError` de duplicado en `False`; no suprime excepciones no relacionadas.
- Locks file/database con timeout finito pueden lanzar `TimeoutError`. El lease puede expirar durante una sección crítica larga.
- `FileBasedCache.save` solo acepta diccionarios y actualiza su hash con un intervalo interno corto (0,5 segundos).

## Rendimiento y concurrencia

La creación de repositorios es diferida y se almacena por manager. Memory es local al proceso; file desplaza operaciones bloqueantes y usa file locks/reemplazo atómico; Redis y Memcached delegan a aiocache; database asegura su esquema de forma diferida y usa operaciones DB para coordinación compartida.

Los locks async de file se comparten solo dentro del mismo event loop y directorio. Database hace polling cada 0,05 segundos y usa lease predeterminado de 10 segundos sin timeout. Los demás backends usan RedLock con lease predeterminado de 10 segundos. Los métodos por lotes delegan a multi-operaciones del backend.

## Compatibilidad

Orionis declara Python 3.14+ y aiocache 0.12.3 o posterior; se validó con CPython 3.14.6 en Windows. File y memory no requieren servicios. Redis, Memcached y database dependen del servicio/driver configurado. El locking de archivos usa la dependencia multiplataforma `filelock` declarada por el proyecto.

## Notas de verificación

Se inspeccionaron manager, repositorio, stores, locks, serializers, caché de artefactos, provider/fachada, configuración y `tests/cache`. Las 210 pruebas pasaron mediante el ejecutor Orionis en CPython 3.14.6. Los cinco programas de Inicio rápido/Ejemplos se ejecutaron correctamente sin servicios externos.
