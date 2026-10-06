# orionis.queues

> `orionis.queues` proporciona jobs diferidos, serializados y reintentables sobre backends síncrono, database y Redis.

## Descripción general

Las aplicaciones declaran clases importables `BaseJob` con `handle()` async. `Queue.dispatch()` devuelve un `PendingDispatch`: se pueden elegir conexión, cola lógica y demora antes de esperarlo, y no se envía nada hasta entonces. Workers durables reservan jobs con leases, abren un ámbito aislado por ejecución, inyectan servicios y confirman, reintentan o preservan fallos terminales.

El formato wire contiene solo identidades registradas y estado primitivo declarado. Nunca deserializa clases arbitrarias con pickle. Todos los backends comparten un envelope y usan esquemas portables Orionis u operaciones Redis con fencing.

## Requisitos

- Python 3.14 o posterior.
- Aplicación Orionis iniciada para fachada `Queue`, descubrimiento, DI y workers.
- Base de datos configurada para colas database y fallos.
- Redis accesible y dependencia instalada al seleccionar Redis.
- Clases importables bajo la ruta `app_jobs` configurada.

## Inicio rápido

```python
from orionis.queues import BaseJob


class SendWelcomeEmail(BaseJob):
    __slots__ = ("recipient",)
    recipient: str
    tries = 3
    timeout = 30.0
    backoff = (1.0, 5.0)

    def __init__(self, recipient: str) -> None:
        self.recipient = recipient

    async def handle(self) -> None:
        print(f"Welcome, {self.recipient}")


job = SendWelcomeEmail("ada@example.test")
assert job.recipient == "ada@example.test"
assert job.backoff == (1.0, 5.0)
```

Validación: **Ejecutado correctamente** en CPython 3.14.6; se construyó el job sin despacharlo.

## Conceptos principales

### Estado persistente explícito

Los campos salen de `__slots__` públicos y anotaciones no `ClassVar` de la jerarquía. Se admiten strings, bytes, enteros, floats finitos, booleanos, `None` y listas, tuplas y diccionarios de claves string anidados. `tries`, `timeout` y `backoff` son política de clase, no estado serializado.

### Despacho diferido

`PendingDispatch` es fluido y awaitable. `onConnection()`, `onQueue()` y `delay()` solo mutan antes del primer await. Esperarlo envía una vez y comparte el resultado con awaiters concurrentes. Desecharlo sin await no envía nada.

### Reservas y leases

Los drivers durables reservan atómicamente por `retry_after` segundos con token de fencing. El worker rechaza reservas discordantes o vencidas. `timeout` debe ser estrictamente menor que `retry_after` para dejar margen de confirmación/liberación.

### Intentos, backoff y fallo terminal

`tries` incluye el primer intento. Cada fallo elige una demora (reutilizando la última) hasta agotar intentos o `retryUntil()`. Los fallos terminales conservan envelope y excepción en el repositorio.

### Ejecución con ámbito

Cada job corre dentro de `app.beginScope()`. El worker registra `JobContext` y llama `handle` mediante la aplicación, por lo que servicios tipados y contexto se inyectan sin serializarlos.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `job.py`, `pending.py` | Declaración y despacho diferido de una sola ejecución. |
| `manager.py`, `provider.py` | Conexiones, descubrimiento, fachada, workers y fallos. |
| `serializer.py`, `entities/envelope.py` | Registro confiable, MessagePack y envelope inmutable. |
| `worker.py`, `context.py` | Consumidores, DI, leases, reintentos y transiciones. |
| `drivers/sync.py` | Ejecución inmediata durante dispatch. |
| `drivers/database.py`, `drivers/redis.py` | Colas durables con reserva atómica. |
| `failed/repository.py` | Fallos terminales durables. |
| `schema.py` | Definiciones portables de tablas. |
| `contracts/`, `exceptions.py` | Interfaces y fallos de colas. |

## API pública

La raíz exporta de forma diferida `BaseJob`, `JobContext`, `JobEnvelope` y `PendingDispatch`. El acceso operativo normal es `orionis.support.facades.Queue`.

### `BaseJob`

Implemente `async handle(...)`. Sobrescriba `tries`, `timeout`, `backoff` y opcionalmente `retryUntil()`. Los parámetros de `handle` se inyectan; el estado persistente debe declararse.

### Fachada `Queue` / manager

- `dispatch(job)` devuelve `PendingDispatch`.
- `connection(name=None)` resuelve driver compartido y perezoso.
- `worker(connection=None, queues=None, concurrency=None)` crea worker independiente.
- `failed()` abre perezosamente el repositorio compartido.
- `retryFailed(id)` reencola y elimina el fallo tras push exitoso.
- `close()` libera clientes propios sin cerrar database compartida.

### `JobContext`

Expone `id`, `attempts`, `queue`, `connection`, `finished` y `failure`. `release(delay)`, `delete()` y `fail(exception)` son transiciones terminales exclusivas; el worker omite su transición automática tras una exitosa.

## Flujos de trabajo comunes

### Despachar ahora o después

Espere `Queue.dispatch(job)` para defaults. Encadene routing/demora antes. Demora cero significa disponible ya; solo el driver `sync` fuerza ejecución inline.

### Ejecutar workers durables

Use `reactor queue:work [connection]` con `--queue`, `--concurrency`, `--stop-when-empty` o `--max-jobs`. El orden de colas es prioridad. Sync no tiene worker persistente.

### Administrar fallos

Use `queue:failed`, `queue:retry <id>`, `queue:forget <id>` y `queue:clear`. Los comandos usan servicios configurados, no imports dinámicos desde payloads.

### Generar jobs

`reactor make:job Name` crea un job. Mantenga la clase a nivel de módulo para conservar la identidad `module:qualname`.

## Ejemplos

### Hacer round-trip del estado declarado

```python
from orionis.queues.serializer import JobSerializer

serializer = JobSerializer()
serializer.register(SendWelcomeEmail)
identity, payload = serializer.encode(SendWelcomeEmail("grace@example.test"))
restored = serializer.decode(identity, payload)

assert identity.endswith(":SendWelcomeEmail")
assert isinstance(restored, SendWelcomeEmail)
assert restored.recipient == "grace@example.test"
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Probar que dispatch es diferido y único

```python
import asyncio
from orionis.queues import PendingDispatch


async def example() -> None:
    calls = []

    async def submit(job, connection, queue, delay):
        calls.append((job, connection, queue, delay))
        return "job-1"

    pending = PendingDispatch(submit, SendWelcomeEmail("a@example.test"))
    pending.onConnection("database").onQueue("emails").delay(2.5)
    assert calls == []
    assert await pending == "job-1"
    assert await pending == "job-1"
    assert len(calls) == 1


asyncio.run(example())
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Inspeccionar esquemas durables portables

```python
from orionis.queues.schema import build_failed_jobs_table, build_jobs_table

jobs = build_jobs_table("jobs")
failed = build_failed_jobs_table("failed_jobs")

assert jobs.columnNames() == (
    "id", "queue", "payload", "attempts", "available_at",
    "reserved_until", "reservation_token", "created_at",
)
assert failed.hasColumn("traceback")
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Validar opciones de worker

```python
from orionis.queues.worker import WorkerOptions

options = WorkerOptions(
    connection="database",
    queues=("high", "default"),
    concurrency=4,
    retry_after=90.0,
    sleep=0.5,
)
assert options.queues[0] == "high"
assert options.concurrency == 4
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Despachar mediante la fachada

```python
from orionis.support.facades import Queue


async def enqueue_welcome() -> str:
    return await (
        Queue.dispatch(SendWelcomeEmail("ada@example.test"))
        .onConnection("database")
        .onQueue("emails")
        .delay(5.0)
    )
```

Validación: **Importación y sintaxis validadas** en CPython 3.14.6; requiere aplicación iniciada y conexión configurada.

## Configuración

| Área | Variables | Predeterminados |
|---|---|---|
| Selección | `QUEUE_CONNECTION` | `sync` |
| Sync | `QUEUE_SYNC_QUEUE`, `QUEUE_SYNC_RETRY_AFTER` | `default`, 90s |
| Database | `QUEUE_DB_CONNECTION`, `QUEUE_TABLE`, `QUEUE_DB_QUEUE`, `QUEUE_DB_RETRY_AFTER` | DB default, `jobs`, `default`, 90s |
| Redis | `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`, `QUEUE_REDIS_PREFIX`, `QUEUE_REDIS_QUEUE`, `QUEUE_REDIS_RETRY_AFTER` | Redis local, DB 0, `orionis:queues`, `default`, 90s |
| Fallos | `QUEUE_FAILED_DB_CONNECTION`, `QUEUE_FAILED_TABLE` | DB default, `failed_jobs` |
| Worker | `QUEUE_WORKER_CONCURRENCY`, `QUEUE_WORKER_SLEEP`, `QUEUE_WORKER_TIMEOUT`, `QUEUE_WORKER_TRIES`, `QUEUE_WORKER_BACKOFF` | 1, 1s, 60s, 3, `(0.0,)` |

Conexiones durables nombradas requieren tablas o prefijos Redis distintos. Fallos no puede reutilizar la tabla jobs en la misma conexión. Identificadores y límites se validan estrictamente.

## Integración con Orionis

`QueueProvider` registra serializer/manager como singletons, descubre `app_jobs`, fija `Queue` y cierra recursos al apagar. Las colas database reutilizan el manager y participan en transacciones de la tarea. Workers invocan `handle` mediante el contenedor.

Los esquemas se crean perezosamente con definiciones `orionis.orm`. Los comandos usan el mismo manager que la aplicación.

## Errores y casos límite

- Se rechazan clases locales, `handle` síncrono, campos privados, estado no declarado, tipos no compatibles, floats no finitos, profundidad excesiva y payloads mayores de 1 MiB.
- Modificar `PendingDispatch` tras await produce `QueueDispatchError`.
- `timeout >= retry_after` se rechaza.
- Un worker cancelado libera reservas pendientes cuando puede; un lease perdido no se confirma.
- `stop_when_empty` termina sin jobs listos aunque queden demorados.
- Reintentar rechaza deadlines vencidos y conserva el fallo si push falla.
- Sync ejecuta durante dispatch y propaga el resultado; no ofrece durabilidad.

## Rendimiento y concurrencia

Drivers y fallos se inicializan perezosamente. Cada worker tiene consumidores hasta su concurrencia y cada job un ámbito DI. Las reservas son atómicas y con fencing; colas lógicas comparten backend.

Codecs y metadatos se reutilizan. Payload máximo 1 MiB y profundidad 32. El apagado elegante deja terminar ejecuciones activas. No reutilice un `JobContext` entre ejecuciones.

## Compatibilidad

El envelope estable tiene versión 1. El estado usa MessagePack y extensión privada para tuplas. La identidad es `module:qualname`; mover una clase puede dejar payloads antiguos desconocidos sin migración. Los drivers durables soportan dialectos Orionis y Redis bajo el mismo contrato.

## Notas de verificación

- `tests/queues`: **134 métodos de prueba aprobados** con el runner de Orionis en CPython 3.14.6.
- Se compilaron seis programas bilingües; cinco programas autónomos se ejecutaron correctamente.
- El ejemplo de fachada se validó por importación/sintaxis porque requiere una aplicación iniciada.
- La evidencia incluyó configuración, límites/ataques de serialización, dialectos, Redis, leases, reintentos, fallos, consola, ámbitos DI, transacciones e integración.

