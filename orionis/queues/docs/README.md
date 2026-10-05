# Orionis Queues

Queues execute asynchronous jobs through the application's existing dependency
container. The `sync` connection runs immediately; `database` and `redis`
persist jobs for independent workers. Durable connections provide **at-least-once
delivery**.

## Setup and configuration

Queue is a core provider. Orionis already includes `msgspec`, the asynchronous
Redis client, and its database abstractions. Configure a reachable database or
Redis server when selecting a durable connection. Start the application runtime
before using facades; `Application.create()` alone does not run async provider
boot. Custom scripts can use `await app.boot()`; Reactor and HTTP application
startup perform that boot automatically. See the [readiness contract](../../foundation/docs/README.md#explicit-readiness-and-headless-startup).

Core defaults live in `orionis/foundation/config/queue`. `Queue`, `Connections`,
`Sync`, `Database`, `Redis`, `Failed`, and `Worker` are frozen, keyword-only,
slotted dataclasses with strict post-init validation. `Drivers` enumerates the
supported backends. `config/queue.py` explicitly declares every editable field
in `BootstrapQueue` and builds its connections with these entities.

`toDict()` recursively serializes the entities for application startup and the
compiled configuration cache. Its canonical defaults are:

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

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `QUEUE_CONNECTION` | `sync` | Default configured connection name |
| `QUEUE_SYNC_QUEUE` | `default` | Sync logical queue |
| `QUEUE_SYNC_RETRY_AFTER` | `90.0` | Sync reservation seconds |
| `QUEUE_DB_CONNECTION` | application DB default | Jobs database connection |
| `QUEUE_TABLE` | `jobs` | Jobs table |
| `QUEUE_DB_QUEUE` | `default` | Database logical queue |
| `QUEUE_DB_RETRY_AFTER` | `90.0` | Database reservation seconds |
| `REDIS_HOST` | `127.0.0.1` | Redis host, shared with cache configuration |
| `REDIS_PORT` | `6379` | Redis TCP port |
| `REDIS_DB` | `0` | Redis database index |
| `REDIS_PASSWORD` | `None` | Optional Redis password |
| `QUEUE_REDIS_PREFIX` | `orionis:queues` | Redis jobs namespace |
| `QUEUE_REDIS_QUEUE` | `default` | Redis logical queue |
| `QUEUE_REDIS_RETRY_AFTER` | `90.0` | Redis reservation seconds |
| `QUEUE_FAILED_DB_CONNECTION` | application DB default | Failure database |
| `QUEUE_FAILED_TABLE` | `failed_jobs` | Failure table |
| `QUEUE_WORKER_CONCURRENCY` | `1` | Maximum concurrent jobs |
| `QUEUE_WORKER_SLEEP` | `1.0` | Polling seconds |
| `QUEUE_WORKER_TIMEOUT` | `60.0` | Job execution timeout seconds |
| `QUEUE_WORKER_TRIES` | `3` | Maximum attempts, including the first |
| `QUEUE_WORKER_BACKOFF` | `(0.0,)` | Retry delay sequence in seconds |

Every configurable scalar is read lazily through `Env.get()` in both the core
entities and the application template. Drivers remain fixed identifiers for
their connection types; explicit constructor values override the environment.
Use typed environment values for retry sequences, for example:

```dotenv
QUEUE_WORKER_BACKOFF="tuple:(1.0, 5.0)"
```

All environment values still pass strict entity validation. In particular,
worker timeout must remain below every configured connection's reservation.

Edit the declared fields in `BootstrapQueue` to customize settings. Typed
entities can also be passed directly:

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

Partial worker and connection dictionaries remain accepted and are converted
to validated entities with their defaults. Additional named connections can
use typed settings, for example `connections={"reports": Database(table="report_jobs")}`
with `default="reports"`. A connection identifies a backend;
a queue such as `emails` or `high` identifies a channel within that backend.
Connection and queue names contain 1–128 ASCII letters, digits, periods, hyphens,
or underscores, and start with a letter or digit.
Named durable connections must use distinct database tables or Redis prefixes.
Configuration rejects identical storage namespaces; aliases that reach the same
backend through different database connection names or Redis hostnames must also
be assigned separate storage explicitly. Redis namespaces use endpoint, port,
database index, and prefix; different passwords do not isolate stored jobs.
Failed-job storage must likewise use a table distinct from jobs on the same
database connection.

Redis follows the cache connection pattern: configure `endpoint`, `port`, `db`,
and `password` separately. No URL field or `QUEUE_REDIS_URL` variable is used.
Ports must be integers from 1 to 65535, database indexes must be nonnegative
integers, and passwords must be strings or `None`. Booleans are not numbers.
Owned clients explicitly use RESP2 instead of relying on redis-py's protocol
default. The multiprocess certification probe passed against Redis 5.0.14.1 on
Windows, including lease expiration and fenced acknowledgements. This does not
certify Redis persistence, failover or other deployment versions.

The previous alpha configuration (`async`, `brokers`, ordering `strategy`,
`visibility_timeout`, and `retry_delay`) has been replaced. Update application
configuration to the fields above, then run:

```bash
python reactor optimize:clear
```

Configuration rejects invalid numbers, unknown settings, unsupported drivers,
unsafe table names, and `worker.timeout >= retry_after`. Worker timeout must be
finite and positive; a job's `timeout=None` inherits that bounded default.

## Create a job

```bash
python reactor make:job process_record
```

The generator uses `app.path("app_jobs")`, defined as `app/jobs` in
`orionis/foundation/core_paths.py`. Workers use that same resolved directory;
queue configuration does not declare a separate module list. Override the
directory centrally before `app.create()` when needed:

```python
app.withConfigPaths(app_jobs="app/custom_jobs")
```

With the default path, the generator creates `app/jobs/process_record_job.py`.
Define persistent fields using public slots and runtime primitive annotations.
Put service dependencies in `handle()`:

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

Do not use postponed annotations on DI methods. Runtime imports must make service
types available to the container. Constructors declare persistent data;
deserialization restores validated fields without invoking the constructor.
Supported state comprises strings, bytes, integers, finite floats, booleans,
`None`, lists, tuples, and dictionaries with string keys. Services, facades,
database connections, and arbitrary objects cannot be serialized.

Worker bootstrap recursively discovers Python modules under
`app.path("app_jobs")` using the framework module inspector and registers concrete
`BaseJob` classes defined there. Abstract classes and classes imported from other
directories are not automatically registered. An absent jobs directory does not
block startup. A job dispatched locally is also registered in that process;
independent workers need its class declared under the configured jobs path.
Payloads contain a stable module/class identity and explicit `msgspec` wire data.
Payload-controlled imports, pickle, `eval`, and `exec` are never used. Unknown
identities and malformed payloads fail explicitly. Wire data is limited to 1 MiB.

## Dispatch, connections, and delayed availability

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

`dispatch()` returns `PendingDispatch` immediately. It performs serialization and
push only when awaited. Fluent settings cannot change after submission starts;
multiple awaits of the same pending operation share one submission and result.
The first await submits inline in its current task. Canceling that initiating
task ends its submission without an implicit retry; canceling a concurrent
follower leaves the initiating submission running.
Delay is measured from submission time, and no worker can reserve the job before
its availability deadline.

`sync` executes one attempt through the same scope, serialization, timeout, and
failure pipeline. It propagates the original exception, preserving terminal
failure in the configured database. It does not support delayed execution,
persistent release/retry, or `queue:work`.

## Workers and concurrency

```bash
python reactor queue:work redis --queue=high,default --concurrency=50
python reactor queue:work database --stop-when-empty
python reactor queue:work database --max-jobs=100
```

Queue order establishes priority: workers look for eligible `high` jobs before
`default` jobs. Existing in-flight work is not preempted. Each concurrent consumer
executes a job in its own asyncio task and fresh `Application.beginScope()`:

```text
reserve -> validate envelope -> new DI scope -> deserialize
        -> Application.call(job, "handle") -> acknowledge / release / fail
```

Scoped services and injected `JobContext` belong to that execution. An individual
job exception triggers its lifecycle transition and does not stop other jobs.
`--max-jobs` counts processed reservation attempts, including retries.
`--stop-when-empty` stops when consumers observe no ready work; delayed jobs may
remain stored. Without either flag the worker continuously polls.

SIGINT/Ctrl+C and SIGTERM stop new reservations and drain in-flight jobs.
Programmatic consumers may call `worker.stop()`. Explicit task cancellation
of `worker.run()` also drains current executions before propagating cancellation.
Canceling a directly invoked `worker.execute()` releases the interrupted
reservation when ownership remains valid. Abrupt process death is recovered
through lease expiry. Keep worker and backend system clocks synchronized because
availability and leases use wall-clock epoch timestamps.

Timeout uses cooperative asyncio cancellation. Python code that blocks the event
loop cannot be forcibly interrupted. Jobs should await I/O and avoid blocking
CPU work; process isolation is outside this version's scope.
The execution bound includes scope setup, deserialization, asynchronous DI, and
`handle()`. It is shortened when the remaining reservation lifetime is smaller
than the declared timeout so execution does not intentionally outlive its lease.

## Attempts, retries, and leasing

`attempts` counts successful reservations, starting at one. With `tries=3` and
`backoff=(1.0, 5.0)`, failure of attempt one releases after one second; failure
of attempt two releases after five seconds; failure of attempt three is terminal.
When backoff is shorter than the attempt budget, its final delay is reused.
`retryUntil()` may return an absolute fractional epoch deadline, such as
`DateTime.now().timestamp() + 300`, or `None` for no deadline. No retry starts at
or after the deadline.

Each reservation expires at `now + retry_after`. Expired jobs can be reclaimed;
reservation tokens prevent a superseded worker from deleting or releasing a new
worker's reservation. Job-specific timeouts must also be shorter than the chosen
connection's `retry_after`.

Database claims use a conditional atomic update checking eligibility and the
observed attempt count. Candidate lookup alone never confers ownership. Redis
uses Lua for transitions among ready, delayed, and reserved structures. Both
drivers retain attempt counts and use fractional timestamps.

## Interact with the current job

Inject `JobContext` into `handle()` to inspect `id`, `attempts`, `queue`, and
`connection`, or call `await context.release(delay=30)`,
`await context.delete()`, and `await context.fail(exception)`. An explicit
transition prevents automatic acknowledgement. Only one transition is allowed;
expired ownership raises `QueueLeaseError`. Releasing a job consumes its current
attempt and schedules another reservation.

## Failed jobs and storage

```bash
python reactor queue:failed
python reactor queue:retry FAILED_ID
python reactor queue:forget FAILED_ID
python reactor queue:clear database --queue=emails
```

Terminal failure has its own event ID, separate from the original job ID. It
preserves the envelope, attempt count, connection, queue,
original exception type/message, traceback, and failure time. `queue:retry`
uses the event ID printed by `queue:failed`, which also displays the original
job ID. The retry operation
pushes the preserved envelope with its existing job ID and resets backend attempts,
then removes the failure record. Expired retry deadlines remain rejected.
`queue:forget` removes only a failure record. `queue:clear` removes every ready,
delayed, and reserved job from the selected queue, including active reservations;
already-running side effects cannot be undone.

Jobs and failed jobs tables are created lazily through Orionis `TableDefinition`
and `IConnection.createTable`, matching cache/session storage behavior. Configure
database permissions accordingly. Their schemas are available in
`orionis.queues.schema`:

For concurrent SQLite workers, configure the real SQLite connection with
`SQLite(journal_mode="WAL", busy_timeout=30000)` in `config/database.py`;
`busy_timeout` is measured in milliseconds. Import `SQLite` from
`orionis.foundation.config.database.entities.sqlite`. Use a shared file-backed
database so independent workers see the same durable jobs.

| Table | Columns |
| --- | --- |
| `jobs` | id, queue, binary payload, attempts, available_at, reserved_until, reservation_token, created_at |
| `failed_jobs` | id, job_id, connection, queue, binary payload, attempts, exception_type, exception_message, traceback, failed_at |

Queue indexes cover queue/availability/lease expiry; failures are indexed by
failure time. SQLAlchemy is encapsulated by database abstractions; Queue does
not import it. Redis persistence and availability depend on the server's own
configuration. Failed jobs for all drivers are stored in the configured database.

## Delivery guarantees and transaction boundaries

Delivery is **at least once**, with no exactly-once guarantee. If a worker applies
a side effect and dies before acknowledgement, the job may execute again.
Make application effects idempotent using business identifiers and appropriate
database constraints or external idempotency keys.

Database transactions have no after-commit callback API. Queue exposes no
`afterCommit` operation. Database queue pushes on the same connection and task
join the existing transaction; a different connection or Redis can expose work
before that transaction commits. Initialize the jobs table before transactional
dispatch; initial schema creation may have dialect-specific DDL transaction
behavior. Redis, sync execution, and dispatch on another DB connection have no
commit deferral. Dispatch after leaving the transaction when jobs depend on
committed application data.
Database reservations must occur outside application-owned transactions: a claim
must be committed before it can be returned to a worker. Database dispatch may
still participate in the originating transaction as described above.

`BackgroundTask` is response-associated, in-process work without durable retries.
Scheduler determines when to initiate actions. Queue persists and executes
decoupled work in an independent runtime; it belongs to neither HTTP lifecycle
nor Scheduler storage. Unique jobs, overlap middleware, chains, batches, and
process-isolated CPU execution are left for later versions.

## Verification

```bash
python -X utf8 reactor test --start-dir=tests/queues --no-panel
ruff check orionis/queues orionis/console/commands/queue tests/queues
```

The regular suite does not require an external Redis server. Redis transport
tests use an explicit fake implementing the atomic script contract; executable
Lua integration is discovered normally and explicitly skipped until
`ORIONIS_QUEUE_REDIS_HOST` is set. Once configured, server errors remain failures:

```powershell
$env:ORIONIS_QUEUE_REDIS_HOST = "127.0.0.1"
$env:ORIONIS_QUEUE_REDIS_PORT = "6379"
$env:ORIONIS_QUEUE_REDIS_DB = "0"
python -X utf8 reactor test --start-dir=tests/queues/drivers --file-pattern=test_redis_integration.py --no-panel
```

The selected host and port must reach a Redis server supporting atomic Lua
operations. Set `ORIONIS_QUEUE_REDIS_PASSWORD` in the terminal when authentication
is required; the password is passed directly to the client without URL encoding.
Integration tests use separate random prefixes and remove their own state.
`-X utf8` also avoids legacy Windows console encoding errors in test output.
