# Colas de Orionis

Queue ejecuta jobs asíncronos mediante el contenedor de dependencias de la
aplicación. La conexión `sync` ejecuta inmediatamente; `database` y `redis`
persisten trabajo para workers independientes. Las conexiones durables ofrecen
entrega **al menos una vez**.

## Instalación y configuración

Queue es un provider core. Orionis ya incluye `msgspec`, el cliente Redis
asíncrono y sus abstracciones de base de datos. Configura una base de datos o
servidor Redis accesible para utilizar una conexión durable. Las facades necesitan
que arranque el runtime: `Application.create()` por sí solo no ejecuta el boot
asíncrono de providers. Reactor y el arranque HTTP lo realizan automáticamente.

Los valores predeterminados viven en `orionis/foundation/config/queue`. `Queue`,
`Connections`, `Sync`, `Database`, `Redis`, `Failed` y `Worker` son dataclasses
inmutables, con argumentos por nombre, slots y validaciones estrictas en
`__post_init__`. `Drivers` enumera los backends admitidos. `config/queue.py`
declara todos los campos editables en `BootstrapQueue` y construye sus
conexiones con estas entidades.

`toDict()` serializa recursivamente las entidades para el arranque y el caché
compilado de configuración. Sus valores canónicos son:

```python
{
    "default": "sync",
    "connections": {
        "sync": {"driver": "sync", "queue": "default", "retry_after": 90.0},
        "database": {
            "driver": "database", "connection": None, "table": "jobs",
            "queue": "default", "retry_after": 90.0,
        },
        "redis": {
            "driver": "redis", "endpoint": "127.0.0.1", "port": 6379,
            "db": 0, "password": None,
            "prefix": "orionis:queues", "queue": "default", "retry_after": 90.0,
        },
    },
    "failed": {"connection": None, "table": "failed_jobs"},
    "worker": {
        "concurrency": 1, "sleep": 1.0, "timeout": 60.0,
        "tries": 3, "backoff": (0.0,),
    },
}
```

| Variable de entorno | Valor predeterminado | Función |
| --- | --- | --- |
| `QUEUE_CONNECTION` | `sync` | Nombre de la conexión predeterminada |
| `QUEUE_SYNC_QUEUE` | `default` | Cola lógica sync |
| `QUEUE_SYNC_RETRY_AFTER` | `90.0` | Segundos de reserva sync |
| `QUEUE_DB_CONNECTION` | BD predeterminada de la aplicación | BD de jobs |
| `QUEUE_TABLE` | `jobs` | Tabla de jobs |
| `QUEUE_DB_QUEUE` | `default` | Cola lógica de base de datos |
| `QUEUE_DB_RETRY_AFTER` | `90.0` | Segundos de reserva de base de datos |
| `REDIS_HOST` | `127.0.0.1` | Host Redis, compartido con la configuración de caché |
| `REDIS_PORT` | `6379` | Puerto TCP de Redis |
| `REDIS_DB` | `0` | Índice de base de datos Redis |
| `REDIS_PASSWORD` | `None` | Contraseña Redis opcional |
| `QUEUE_REDIS_PREFIX` | `orionis:queues` | Namespace de jobs Redis |
| `QUEUE_REDIS_QUEUE` | `default` | Cola lógica Redis |
| `QUEUE_REDIS_RETRY_AFTER` | `90.0` | Segundos de reserva Redis |
| `QUEUE_FAILED_DB_CONNECTION` | BD predeterminada de la aplicación | BD de fallos |
| `QUEUE_FAILED_TABLE` | `failed_jobs` | Tabla de fallos |
| `QUEUE_WORKER_CONCURRENCY` | `1` | Máximo de jobs concurrentes |
| `QUEUE_WORKER_SLEEP` | `1.0` | Segundos entre consultas |
| `QUEUE_WORKER_TIMEOUT` | `60.0` | Segundos de ejecución por job |
| `QUEUE_WORKER_TRIES` | `3` | Máximo de intentos, incluido el primero |
| `QUEUE_WORKER_BACKOFF` | `(0.0,)` | Secuencia de esperas entre intentos |

Cada valor configurable se lee mediante `Env.get()` al crear las entidades core
y la plantilla de la aplicación. Los drivers siguen siendo identificadores fijos
del tipo de conexión; los valores explícitos del constructor tienen prioridad.
Usa valores de entorno tipados para las secuencias de reintento, por ejemplo:

```dotenv
QUEUE_WORKER_BACKOFF="tuple:(1.0, 5.0)"
```

El entorno también pasa por las validaciones estrictas de las entidades. En
particular, el timeout del worker debe ser menor que la reserva de cada conexión.

Edita los campos declarados en `BootstrapQueue` para personalizar opciones.
También puedes proporcionar entidades tipadas directamente:

```python
from orionis.foundation.config.queue import (
    Connections, Database, Failed, Queue, Redis, Worker,
)

config = Queue(
    default="redis",
    connections=Connections(
        database=Database(table="pending_jobs"),
        redis=Redis(queue="high", retry_after=120.0),
    ),
    failed=Failed(table="queue_failures"),
    worker=Worker(concurrency=8, timeout=20.0, backoff=(1.0, 5.0)),
)
```

Los diccionarios parciales de conexiones y worker siguen admitidos y se
convierten en entidades validadas con sus valores predeterminados. Puedes
añadir nombres propios con opciones tipadas, por ejemplo
`connections={"reports": Database(table="report_jobs")}` y `default="reports"`.
Una connection identifica el backend; una queue como `emails`
o `high` identifica un canal dentro de ese backend. Sus nombres tienen entre
1 y 128 letras ASCII, dígitos, puntos, guiones o guiones bajos; comienzan con una
letra o dígito.
Las conexiones durables con nombres diferentes deben usar tablas o prefijos Redis
distintos. La configuración rechaza namespaces idénticos; si nombres de conexión
de BD o nombres de host Redis distintos alcanzan el mismo backend, asigna
almacenamiento separado explícitamente. Los namespaces Redis incluyen endpoint,
puerto, índice de base de datos y prefijo; cambiar la contraseña no aísla jobs.
La tabla de fallos también debe ser diferente de la tabla de jobs cuando ambas
usan la misma conexión de base de datos.

Redis sigue el patrón de caché: configura `endpoint`, `port`, `db` y `password`
por separado. No utiliza un campo URL ni la variable `QUEUE_REDIS_URL`. El puerto
debe ser un entero entre 1 y 65535, el índice de BD un entero no negativo y la
contraseña un string o `None`. Los booleanos no se admiten como valores numéricos.

La configuración alpha anterior (`async`, `brokers`, `strategy`,
`visibility_timeout` y `retry_delay`) fue sustituida. Actualiza la configuración
de la aplicación y limpia su caché compilada:

```bash
python reactor optimize:clear
```

La validación rechaza valores numéricos inválidos, opciones desconocidas, drivers
no soportados, nombres inseguros de tablas y `worker.timeout >= retry_after`.
El timeout del worker debe ser finito y positivo. `timeout=None` en un job hereda
ese límite predeterminado.

## Crear un job

```bash
python reactor make:job process_record
```

El generador usa `app.path("app_jobs")`, definido como `app/jobs` en
`orionis/foundation/core_paths.py`. Los workers usan ese mismo directorio
resuelto; la configuración de colas no declara otra lista de módulos. Puedes
personalizarlo centralmente antes de `app.create()`:

```python
app.withConfigPaths(app_jobs="app/custom_jobs")
```

Con la ruta predeterminada se genera `app/jobs/process_record_job.py`. Declara
datos persistentes mediante slots públicos y anotaciones primitivas; declara
servicios en `handle()`:

```python
from typing import ClassVar

from orionis.logging.contracts.logger import ILogger
from orionis.queues import BaseJob


class ProcessRecordJob(BaseJob):
    """Log processing of a persistent record identifier."""

    __slots__ = ("record_id",)

    record_id: int
    tries: ClassVar[int] = 3
    timeout: ClassVar[float] = 30.0
    backoff: ClassVar[tuple[float, ...]] = (1.0, 5.0)

    def __init__(self, record_id: int) -> None:
        """Store the persistent record identifier.

        Parameters
        ----------
        record_id : int
            Record identifier restored when the job executes.
        """
        self.record_id = record_id

    async def handle(self, logger: ILogger) -> None:
        """Log the record using an injected application service.

        Parameters
        ----------
        logger : ILogger
            Application logger resolved for this execution.
        """
        message = f"Queue job processed record {self.record_id}."
        logger.info(message)
```

No pospongas anotaciones en métodos resueltos por DI. Mantén imports de runtime
para que el contenedor pueda resolver los tipos de servicios. El constructor
recibe estado persistente; la deserialización restaura campos validados sin
invocarlo. Se admiten strings, bytes, enteros, floats finitos, booleanos, `None`,
listas, tuplas y diccionarios con claves string. No se serializan servicios,
facades, conexiones ni objetos arbitrarios.

El boot descubre recursivamente los módulos Python de `app.path("app_jobs")`
mediante el inspector del framework y registra las clases concretas `BaseJob`
definidas allí. No registra automáticamente clases abstractas ni clases importadas
desde otros directorios. Una carpeta de jobs ausente no impide el arranque.
Despachar localmente también registra la clase en ese proceso; los workers
independientes necesitan su clase declarada bajo la ruta de jobs configurada.
El payload contiene una identidad estable de módulo/clase y un
formato explícito `msgspec`. No permite imports controlados por payload, pickle,
`eval` ni `exec`. Identidades desconocidas y datos corruptos fallan explícitamente.
El formato persistente admite hasta 1 MiB.

## Dispatch, conexiones y jobs diferidos

```python
from app.jobs.process_record_job import ProcessRecordJob
from orionis.support.facades.queue import Queue

job_id = await Queue.dispatch(ProcessRecordJob(record_id=42))

job_id = await (
    Queue.dispatch(ProcessRecordJob(record_id=42))
    .onConnection("redis")
    .onQueue("high")
    .delay(seconds=30)
)
```

`dispatch()` devuelve inmediatamente un `PendingDispatch`. Serializa y persiste
cuando se espera con `await`. Una vez iniciada la operación no se pueden cambiar
sus opciones. Esperar varias veces el mismo objeto comparte un único envío y
resultado. El delay se mide desde el envío; el job no puede reservarse antes de
su fecha de disponibilidad.
El primer await envía en su propia tarea. Cancelar esa tarea iniciadora termina
el envío sin retry implícito; cancelar otra tarea que espera el mismo objeto
no cancela el envío iniciado.

`sync` ejecuta un intento usando el mismo pipeline de serialización, scope,
timeout y fallos. Propaga la excepción original y conserva el fallo terminal en
la BD configurada. No admite delays, release/retry persistente ni `queue:work`.

## Workers y concurrencia

```bash
python reactor queue:work redis --queue=high,default --concurrency=50
python reactor queue:work database --stop-when-empty
python reactor queue:work database --max-jobs=100
```

El orden establece prioridad: el worker busca jobs elegibles en `high` antes de
`default`; no interrumpe trabajo que ya está ejecutándose. Cada consumidor ejecuta
su job en una tarea asyncio con un nuevo scope `Application.beginScope()`:

```text
reserve -> validar envelope -> nuevo scope DI -> deserializar
        -> Application.call(job, "handle") -> ack / release / fail
```

Los servicios scoped y `JobContext` pertenecen a esa ejecución. Una excepción
individual activa la transición correspondiente y no detiene otros jobs.
`--max-jobs` cuenta intentos reservados procesados, incluyendo reintentos.
`--stop-when-empty` termina cuando los consumidores no encuentran trabajo listo;
pueden quedar jobs diferidos. Sin esos flags el consumo continúa mediante polling.

SIGINT/Ctrl+C y SIGTERM detienen nuevas reservas y esperan los jobs activos.
También puedes llamar `worker.stop()`. Cancelar `worker.run()` espera los jobs
activos antes de propagar la cancelación. Cancelar una llamada directa a
`worker.execute()` libera su reserva mientras conserve la propiedad. Si el
proceso muere abruptamente, la expiración del lease permite recuperar el job.
Mantén sincronizados los relojes del backend y los workers: disponibilidad y
leases utilizan timestamps epoch del reloj del sistema.

El timeout utiliza cancelación cooperativa de asyncio. No puede interrumpir
forzosamente Python que bloquea el event loop. Los jobs deben esperar I/O y
evitar trabajo CPU bloqueante. El aislamiento por procesos queda para otra versión.
El límite abarca creación del scope, deserialización, DI asíncrona y `handle()`.
Se reduce cuando el tiempo restante del lease es menor que el timeout declarado
para evitar que la ejecución sobrepase intencionalmente su reserva.

## Intentos, retries y leasing

`attempts` cuenta reservas adquiridas, comenzando en uno. Con `tries=3` y
`backoff=(1.0, 5.0)`, el primer fallo libera tras un segundo, el segundo tras cinco
segundos y el tercero es terminal. Cuando el backoff tiene menos entradas que
el presupuesto de intentos, se reutiliza su último valor. `retryUntil()` puede
devolver una fecha límite como epoch fraccionario —por ejemplo,
`DateTime.now().timestamp() + 300`— o `None`. No comienza un retry al llegar a la
fecha límite o después de ella.

Cada reserva vence en `now + retry_after`. Las reservas vencidas vuelven a ser
elegibles. Un token impide que un worker anterior borre o libere la reserva de
un nuevo propietario. El timeout propio del job también debe ser menor que
`retry_after` en la conexión elegida.

Database adquiere mediante un update condicional atómico que comprueba
elegibilidad e intentos observados. Encontrar un candidato no concede propiedad.
Redis utiliza Lua para las transiciones entre estructuras ready, delayed y
reserved. Ambos drivers conservan intentos y usan timestamps fraccionarios.

## Interactuar con el job actual

Inyecta `JobContext` en `handle()` para consultar `id`, `attempts`, `queue` y
`connection`. Sus operaciones son `await context.release(delay=30)`,
`await context.delete()` y `await context.fail(exception)`. Una transición
explícita evita el ack automático. Solo se admite una transición; si expira la
propiedad se lanza `QueueLeaseError`. Release consume el intento actual y
programa otra reserva.

## Fallos persistentes y almacenamiento

```bash
python reactor queue:failed
python reactor queue:retry FAILED_ID
python reactor queue:forget FAILED_ID
python reactor queue:clear database --queue=emails
```

Un fallo terminal tiene un ID de evento distinto del ID original del job.
Conserva envelope, intentos, connection, queue, tipo/mensaje
de excepción original, traceback y fecha. `queue:retry` envía el envelope con
el ID original del job; su argumento es el ID de evento mostrado por
`queue:failed`, que también muestra el ID del job. Reinicia los intentos del
backend y después elimina el fallo.
Una fecha límite vencida continúa siendo rechazada. `queue:forget` elimina
únicamente el registro fallido. `queue:clear` borra jobs ready, delayed y reserved
del canal, incluyendo reservas activas; no puede deshacer efectos ya ejecutados.

Las tablas se crean de manera perezosa mediante `TableDefinition` y
`IConnection.createTable`, siguiendo el patrón de cache/sessions. Configura los
permisos correspondientes. `orionis.queues.schema` contiene sus definiciones:

Para workers SQLite concurrentes, configura `SQLite(journal_mode="WAL",
busy_timeout=30000)` en `config/database.py`; `busy_timeout` se expresa en
milisegundos. Importa `SQLite` desde
`orionis.foundation.config.database.entities.sqlite`. Utiliza un fichero
compartido para que workers independientes accedan a los mismos jobs.

| Tabla | Columnas |
| --- | --- |
| `jobs` | id, queue, payload binario, attempts, available_at, reserved_until, reservation_token, created_at |
| `failed_jobs` | id, job_id, connection, queue, payload binario, attempts, exception_type, exception_message, traceback, failed_at |

Los índices cubren queue/disponibilidad/expiración y fecha de fallo. Queue no
importa SQLAlchemy directamente; utiliza las abstracciones de base de datos.
La persistencia y disponibilidad de Redis dependen de la configuración del
servidor. Los fallos de cualquier driver se guardan en la BD configurada.

## Garantías y límites transaccionales

La entrega es **al menos una vez**. No existe garantía exactly-once. Si un worker
ejecuta un efecto y muere antes del ack, el job puede repetirse. Diseña efectos
idempotentes usando identificadores de negocio, restricciones de base de datos
o claves de idempotencia de servicios externos.

DB no ofrece callbacks after-commit y Queue no expone `afterCommit`. Los envíos
a Database en la misma conexión y tarea participan en la transacción activa.
Redis u otra conexión pueden hacer visible el trabajo antes del commit.
Inicializa la tabla antes de despachar dentro de transacciones: crear el schema
por primera vez puede tener comportamiento DDL transaccional propio del dialecto.
Redis, sync y otra conexión de BD no difieren su ejecución hasta el commit.
Despacha después de salir de la transacción cuando el job dependa de datos
confirmados.
Las reservas Database deben adquirirse fuera de transacciones de la aplicación:
el claim debe estar confirmado antes de devolverlo al worker. El dispatch puede
seguir participando en su transacción de origen, como se describe arriba.

`BackgroundTask` ejecuta trabajo posterior a la respuesta en el mismo proceso,
sin retries durables. Scheduler decide cuándo iniciar acciones. Queue persiste
y ejecuta trabajo desacoplado en un runtime independiente; no pertenece al
lifecycle HTTP ni al almacenamiento del Scheduler. Unique jobs, middleware de
overlapping, chains, batches y ejecución CPU aislada se dejan para versiones futuras.

## Verificación

```bash
python -X utf8 reactor test --start-dir=tests/queues --no-panel
ruff check orionis/queues orionis/console/commands/queue tests/queues
```

La suite regular no necesita un servidor Redis externo. Las pruebas de transporte
utilizan un fake explícito del contrato de scripts atómicos; los scripts Lua se
se verifican además con una suite explícita que falla si falta el servidor:

```powershell
$env:ORIONIS_QUEUE_REDIS_HOST = "127.0.0.1"
$env:ORIONIS_QUEUE_REDIS_PORT = "6379"
$env:ORIONIS_QUEUE_REDIS_DB = "0"
python -X utf8 reactor test --start-dir=tests/queues/drivers --file-pattern=redis_integration.py --no-panel
```

El host y puerto deben apuntar a un servidor Redis con soporte para operaciones
Lua. Define `ORIONIS_QUEUE_REDIS_PASSWORD` en la terminal si necesita autenticación;
la contraseña se pasa al cliente directamente, sin codificación para URL.
Cada prueba utiliza prefijos aleatorios separados y elimina sus propios datos.
`-X utf8` evita además problemas de codificación heredada en consola Windows.
