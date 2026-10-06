# orionis.queues

> `orionis.queues` provides deferred, serialized, retryable background jobs over synchronous, database, and Redis backends.

## Overview

Applications declare importable `BaseJob` classes with an async `handle()` method. `Queue.dispatch()` returns a `PendingDispatch`: connection, logical queue, and delay can be selected before the object is awaited, and no submission occurs until then. Durable workers reserve jobs with leases, open an isolated application scope per execution, inject services into `handle`, and acknowledge, retry, or preserve terminal failures.

The wire format contains only registered job identities and explicitly declared primitive state. It never unpickles arbitrary classes. Queue backends share one envelope contract and use portable Orionis database schemas or fenced Redis operations.

## Requirements

- Python 3.14 or newer.
- A booted Orionis application for the `Queue` facade, job discovery, DI, and worker execution.
- A configured database for database queues and failed-job storage.
- A reachable Redis server and dependency when selecting a Redis connection.
- Importable job classes under the configured `app_jobs` path.

## Quick start

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

Validation: **Executed successfully** on CPython 3.14.6; the job was constructed but not dispatched.

## Core concepts

### Explicit persistent state

Persistent fields come from public `__slots__` and non-`ClassVar` annotations across the `BaseJob` hierarchy. Supported values are strings, bytes, integers, finite floats, booleans, `None`, and nested lists, tuples, and string-keyed dictionaries. Options `tries`, `timeout`, and `backoff` are class policy, not serialized fields.

### Deferred dispatch

`PendingDispatch` is both fluent and awaitable. `onConnection()`, `onQueue()`, and `delay()` mutate it only before first await. Awaiting submits exactly once and shares that result with concurrent awaiters. Discarding the object without awaiting it submits nothing.

### Reservations and leases

Durable drivers atomically reserve ready jobs for `retry_after` seconds and attach a fencing token. Workers reject mismatched or expired reservations. Job `timeout` must be strictly shorter than `retry_after`, leaving time to acknowledge or release the lease safely.

### Attempts, backoff, and terminal failure

`tries` counts the first attempt. Each failure selects a delay from the backoff sequence (reusing the last value when needed) until attempts or `retryUntil()` are exhausted. Terminal failures preserve the original envelope and exception details in the failed-job repository.

### Scoped execution

Every job runs inside `app.beginScope()`. The worker registers its `JobContext` in that scope and calls `handle` through the application, so type-hinted services and the context can be injected without serializing them into job state.

## Module structure

| Path | Responsibility |
|---|---|
| `job.py`, `pending.py` | Job declaration and one-shot deferred dispatch. |
| `manager.py`, `provider.py` | Connection selection, discovery, facade lifecycle, workers, failures. |
| `serializer.py`, `entities/envelope.py` | Trusted registry, MessagePack state, immutable execution envelope. |
| `worker.py`, `context.py` | Concurrent consumers, scoped calls, leases, retries, explicit transitions. |
| `drivers/sync.py` | Immediate in-process execution during dispatch. |
| `drivers/database.py`, `drivers/redis.py` | Durable queues with atomic reservation fencing. |
| `failed/repository.py` | Durable terminal-failure records. |
| `schema.py` | Portable jobs and failed-jobs table definitions. |
| `contracts/`, `exceptions.py` | Backend/service interfaces and queue failures. |

## Public API

The root package lazily exports `BaseJob`, `JobContext`, `JobEnvelope`, and `PendingDispatch`. Operational access is normally through `orionis.support.facades.Queue`.

### `BaseJob`

Implement `async handle(...)`. Override `tries`, `timeout`, `backoff`, and optionally `retryUntil()` for per-job policy. Service parameters on `handle` are dependency-injected; persistent constructor state must be declared explicitly.

### `Queue` facade / manager

- `dispatch(job)` returns a `PendingDispatch`.
- `connection(name=None)` resolves a lazy shared backend driver.
- `worker(connection=None, queues=None, concurrency=None)` creates an independent worker.
- `failed()` opens the shared failed-job repository lazily.
- `retryFailed(id)` requeues preserved payload and removes its failure record after a successful push.
- `close()` releases queue-owned clients without closing shared database services.

### `JobContext`

Provides `id`, `attempts`, `queue`, `connection`, `finished`, and `failure`. `release(delay)`, `delete()`, and `fail(exception)` are exclusive terminal transitions for the current reservation; the worker skips its automatic transition after one succeeds.

## Common workflows

### Dispatch immediately or later

Await `Queue.dispatch(job)` for the configured default. Chain `onConnection`, `onQueue`, or `delay` first when routing differs. A zero delay means available immediately; it does not force inline execution except on the `sync` driver.

### Run durable workers

Use `reactor queue:work [connection]` with `--queue`, `--concurrency`, `--stop-when-empty`, or `--max-jobs`. Queue order is priority order. The sync backend has no persistent worker because it executes during dispatch.

### Administer failures

Use `queue:failed`, `queue:retry <id>`, and `queue:forget <id>`. `queue:clear` removes jobs from a selected logical queue. These commands use configured services rather than importing payload classes dynamically.

### Generate jobs

`reactor make:job Name` creates an application job in the jobs path. Keep the class importable at module scope so workers can register the same stable `module:qualname` identity.

## Examples

### Round-trip declared job state

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

Validation: **Executed successfully** on CPython 3.14.6.

### Prove that dispatch is deferred and one-shot

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

Validation: **Executed successfully** on CPython 3.14.6.

### Inspect portable durable schemas

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

Validation: **Executed successfully** on CPython 3.14.6.

### Validate worker options

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

Validation: **Executed successfully** on CPython 3.14.6.

### Dispatch through the application facade

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

Validation: **Import and syntax validated** on CPython 3.14.6; submission requires a booted application and configured connection.

## Configuration

| Area | Environment variables | Defaults |
|---|---|---|
| Selection | `QUEUE_CONNECTION` | `sync` |
| Sync | `QUEUE_SYNC_QUEUE`, `QUEUE_SYNC_RETRY_AFTER` | `default`, 90s |
| Database | `QUEUE_DB_CONNECTION`, `QUEUE_TABLE`, `QUEUE_DB_QUEUE`, `QUEUE_DB_RETRY_AFTER` | default DB, `jobs`, `default`, 90s |
| Redis | `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`, `QUEUE_REDIS_PREFIX`, `QUEUE_REDIS_QUEUE`, `QUEUE_REDIS_RETRY_AFTER` | local Redis, DB 0, `orionis:queues`, `default`, 90s |
| Failures | `QUEUE_FAILED_DB_CONNECTION`, `QUEUE_FAILED_TABLE` | default DB, `failed_jobs` |
| Worker | `QUEUE_WORKER_CONCURRENCY`, `QUEUE_WORKER_SLEEP`, `QUEUE_WORKER_TIMEOUT`, `QUEUE_WORKER_TRIES`, `QUEUE_WORKER_BACKOFF` | 1, 1s, 60s, 3, `(0.0,)` |

Named durable connections must use distinct database tables or Redis prefixes. Failed-job storage cannot reuse the jobs table on the same database connection. All identifiers and numeric limits are strictly validated.

## Integration with Orionis

`QueueProvider` registers `JobSerializer` and `QueueManager` as singletons, discovers jobs from `app_jobs`, pins the `Queue` facade, and closes owned resources at application shutdown. Database queues reuse the framework connection manager and participate in task-owned transactions. Workers resolve each `handle` through normal container invocation.

The jobs/failed schemas are created lazily by their repositories and are expressed with `orionis.orm` definitions. Console commands expose the same manager used by application code.

## Errors and edge cases

- Local/nested job classes, synchronous `handle`, private persistent fields, undeclared instance state, unsupported types, nonfinite floats, excessive nesting, and payloads over 1 MiB are rejected.
- Modifying a `PendingDispatch` after awaiting raises `QueueDispatchError`.
- Timeout equal to or above `retry_after` is unsafe and rejected.
- A cancelled worker releases unfinished reservations when possible; an expired or lost lease cannot be acknowledged.
- `stop_when_empty` exits when no job is ready, even if delayed jobs remain.
- Retrying a failed job rejects expired retry deadlines and keeps the failure record if pushing fails.
- The sync driver executes inside dispatch and propagates its execution outcome; it is useful for local/test behavior, not durability.

## Performance and concurrency

Drivers and failed storage initialize lazily. Each durable worker has independent consumers up to its concurrency value, while every job gets an isolated DI scope. Database and Redis reservations are atomic and fenced; logical queues share a backend connection.

Serializer codecs and trusted type metadata are reused. Backpressure comes from worker concurrency and backend polling; payloads are capped at 1 MiB and nesting at 32. Graceful stop lets active executions finish. Do not reuse a single `JobContext` or active factory-like job object across executions.

## Compatibility

The stable envelope version is 1. State uses MessagePack plus a private tuple extension. Stored job identity is `module:qualname`, so moving or renaming a class can make old payloads unknown unless migration/compatibility code is provided. Durable drivers support Orionis database dialects and Redis; operational semantics are tested through the shared driver contract.

## Verification notes

- `tests/queues`: **134 test methods passed** with the Orionis runner on CPython 3.14.6.
- Six bilingual documentation programs were compiled; five standalone programs were executed successfully.
- The facade dispatch program was import/syntax validated because it requires a booted application.
- Evidence included config validation, serialization attacks/bounds, database dialects, Redis behavior, leases, retries, failure storage, console commands, DI scopes, transactions, and integration tests.

