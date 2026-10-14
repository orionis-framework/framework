# Configurar stores y coordinar regeneraciones

La elección del store determina dónde se comparte la caché y qué significa un lock.

## Elegir un backend según su alcance

| Store | Persistencia y alcance | Coordinación |
|---|---|---|
| `memory` | Solo esta instancia/proceso; se pierde al reiniciar | RedLock sobre el mismo backend; no coordina workers. |
| `file` | JSON en un directorio local compartido | Escrituras con locks de archivo y reemplazo; `cache.lock()` solo coordina el mismo loop y directorio. |
| `redis` | Servicio Redis configurado | Lease RedLock de aiocache; no es una transacción de negocio. |
| `memcached` | Servicio Memcached, sujeto a eviction | Lease RedLock con las garantías del backend. |
| `database` | Tablas en una conexión Orionis | Filas únicas y leases; requiere constraints únicos efectivos. |

El manager acepta los nombres integrados `memory`, `file`, `redis`, `memcached` y `database`; no ofrece un registro `extend()` de stores nombrados. Para un backend propio puedes construir `CacheRepository(backend, prefix)` con la API aiocache utilizada por el repositorio, o reemplazar `ICacheManager` mediante el contenedor. La propiedad `driver` de una entidad store no selecciona arbitrariamente otra implementación.

Los stores serializan con JSON de msgspec: limita el contrato de tus valores a estructuras JSON y verifica round trips si necesitas fechas, tuplas o tipos propios. El `Serializer` enriquecido documentado en [artefactos](source-artifacts.md) no participa en estos stores. Una fecha puede volver como texto y una tupla como lista; no presupongas identidad de tipos.

El store database crea sus tablas de entradas y locks de forma lazy; la conexión necesita permisos de creación. Rechaza conexiones sin restricciones únicas efectivas, como Redshift. No depende de que ejecutes una migración de caché específica. Mantén los nombres de tablas exclusivos de la aplicación. El store file usa expiraciones basadas en reloj monotónico; no lo uses como persistencia duradera ni compartas sus archivos entre máquinas con relojes monotónicos distintos.

### Evitar regeneraciones simultáneas

`remember()` por sí solo puede ejecutar varios resolvers para la misma ausencia. Adquiere un lock y vuelve a comprobar dentro de la sección antes de calcular. El significado de `timeout` cambia según store: en file limita la espera para adquirir; en database sirve además como lease; en RedLock es la duración del lease. La expiración del lease no cancela tu código y puede permitir otro escritor mientras aún estás dentro.

Usa locks de caché para reducir trabajo duplicado. Para invariantes de saldo, inventario o unicidad, utiliza transacciones o constraints en el sistema persistente. No se incluye renovación automática de leases ni fencing tokens.


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


El `BootstrapCache` incluido usa prefijo vacío; la entidad base `Cache` usa `orionis` cuando se construye directamente sin override. Verifica qué configuración crea tu aplicación.


## Integración con Orionis

`CacheProvider` es diferible: el contenedor registra el manager singleton cuando se necesita `ICacheManager` y después fija la fachada `Cache`. El store database obtiene su conexión mediante `ConnectionResolver`. Los stores file y database serializan mediante JSON de msgspec.

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



### Fachada `Cache` y `CacheManager`

Usa `from orionis.support.facades.cache import Cache` en una aplicación iniciada. `CacheProvider` registra `ICacheManager` como singleton y fija la fachada. `store(name=None)` es síncrono y devuelve un repositorio; los demás métodos delegan al store predeterminado:

```python
from orionis.support.facades import Cache


async def cache_example() -> None:
    repo = Cache.store("redis")
    value = await repo.get("key")
    await repo.set("key", value, ttl=60)
```

Los nombres soportados son `file`, `memory`, `redis`, `memcached` y `database`. Un store desconocido o ausente provoca `CacheStoreException`.

### API de extensión

`ICacheManager`, `ICacheRepository` e `IFileBasedCache` definen contratos sustituibles. Backends personalizados entregados a `CacheRepository` deben proporcionar los métodos estilo aiocache utilizados (`get`, `set`, `exists`, `delete`, lotes, `add` e `increment`).

## Referencia de implementación para extensiones

| Área | Responsabilidad |
|---|---|
| `cache_manager.py`, `provider.py` | Construcción/reutilización de stores, proxy predeterminado y registro de fachada/contenedor. |
| `repository.py` | Operaciones async uniformes y prefijos. |
| `stores/` | Backends memory, file, Redis, Memcached y database. |
| `locks/` | Context manager async adaptado al backend. |
| `serializer.py`, `serializers/` | Codificación enriquecida compatible con JSON y serializer aiocache. |
| `file_based_cache.py` | Caché de un archivo invalidada por hash de fuentes. |
| `contracts/`, `exceptions.py` | Interfaces de extensión y errores. |

---

[Índice](README.md) · [database](../../../database/docs/es/README.md) · [orm](../../../orm/docs/es/README.md)
