# Elegir y configurar un backend

Configura `queue` en `config/queue.py`. `BootstrapQueue` reúne `default`, `connections`, `failed` y `worker`, utilizando entidades de `orionis.foundation.config.queue`. Una conexión de cola tiene un driver y uno o más canales lógicos; no equivale a un nombre de conexión SQL.

## Comparar drivers

| Driver | Ejecución | Persistencia / requisitos |
|---|---|---|
| `sync` | Durante `await dispatch` en el productor. | Sin almacenamiento durable; no acepta delay ni retry persistente. |
| `database` | Worker separado. | Tabla SQL, restricciones únicas impuestas y conexión de Database. |
| `redis` | Worker separado. | Redis accesible; claves bajo un prefijo propio. |

El default es `sync`. Cambia `QUEUE_CONNECTION=database` o `redis` antes de esperar comportamiento de trabajo diferido. El worker no se puede crear para `sync`: su reserve siempre queda vacío y el manager rechaza esa operación.

El driver database crea su esquema perezosamente. La tabla `jobs` contiene `id`, `queue`, `payload`, `attempts`, `available_at`, `reserved_until`, `reservation_token` y `created_at`. Redis utiliza transiciones atómicas y tokens de reserva. En ambos casos se puede recuperar trabajo después de vencer una reserva; no existe garantía de efectos externos exactamente una vez.

## Variables y defaults

| Área | Variables | Defaults |
|---|---|---|
| Selección | `QUEUE_CONNECTION` | `sync` |
| Sync | `QUEUE_SYNC_QUEUE`, `QUEUE_SYNC_RETRY_AFTER` | `default`, 90 s |
| Database | `QUEUE_DB_CONNECTION`, `QUEUE_TABLE`, `QUEUE_DB_QUEUE`, `QUEUE_DB_RETRY_AFTER` | DB default, `jobs`, `default`, 90 s |
| Redis | `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD` | `127.0.0.1`, 6379, 0, sin contraseña |
| Redis namespace | `QUEUE_REDIS_PREFIX`, `QUEUE_REDIS_QUEUE`, `QUEUE_REDIS_RETRY_AFTER` | `orionis:queues`, `default`, 90 s |
| Fallos | `QUEUE_FAILED_DB_CONNECTION`, `QUEUE_FAILED_TABLE` | DB default, `failed_jobs` |
| Worker | `QUEUE_WORKER_CONCURRENCY`, `QUEUE_WORKER_SLEEP`, `QUEUE_WORKER_TIMEOUT`, `QUEUE_WORKER_TRIES`, `QUEUE_WORKER_BACKOFF` | 1, 1 s, 60 s, 3, `(0.0,)` |

Los tiempos están en segundos. `tries` incluye el primer intento. El timeout efectivo del job debe ser **estrictamente menor** que el `retry_after` de la conexión. Nombres de conexión/cola permiten 1–128 caracteres alfanuméricos, punto, guion y underscore, empezando por alfanumérico. Duraciones deben ser finitas y no negativas; timeout/retry_after deben ser positivos y concurrencia un entero positivo.

Conexiones durables con nombre deben usar tablas o prefijos Redis distintos. La tabla de fallos no puede reutilizar la tabla jobs de la misma conexión SQL. La validación previene colisiones conocidas; no sustituye permisos, namespaces por entorno ni separación entre aplicaciones.

## Fallos requieren SQL incluso con Redis

El repositorio de fallos incluido es database. Se resuelve de manera perezosa cuando se necesita; utilizar Redis o sync no elimina ese requisito para fallos terminales. Prepara su conexión y permisos antes de producción. Redshift se rechaza como backend database y como repositorio de fallos porque no impone las claves únicas requeridas.

Puedes comprobar los esquemas sin acceder a una base:

```python
from orionis.queues.schema import build_failed_jobs_table, build_jobs_table

jobs = build_jobs_table("jobs")
failed = build_failed_jobs_table("failed_jobs")
assert jobs.hasColumn("reservation_token")
assert failed.hasColumn("traceback")
```

## Transacciones y ciclo de vida

Una inserción en cola database utiliza la conexión SQL administrada y participa en la [transacción](../../../database/docs/es/transactions.md) propiedad de la tarea si usa esa misma conexión. Al revertir, el mensaje tampoco queda enviado. Otra conexión o Redis no forman parte de esa unidad SQL. No hay API general de dispatch `afterCommit` ni protocolo distribuido que coordine esos sistemas.

El provider registra serializer y manager como singletons, descubre jobs y fija la facade `Queue`; durante shutdown cierra recursos propios. `await Queue.connection(name)` obtiene el driver cacheado; `await Queue.close()` cierra clientes de cola sin desconectar servicios database compartidos. Normalmente el ciclo de aplicación debe encargarse del cierre.

Para extensiones, `IQueueDriver` define `push`, `reserve`, `release`, `delete`, `size`, `clear` y `close`, todos async. Un driver debe respetar fencing, vencimiento y los contratos de envelope/reserva. La configuración stock solo reconoce los tres drivers incluidos; implementar el contrato no registra automáticamente un nuevo nombre en el manager.
