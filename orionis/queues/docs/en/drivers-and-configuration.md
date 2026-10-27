# Choose and configure a backend

Configure `queue` in `config/queue.py`. `BootstrapQueue` combines `default`, `connections`, `failed`, and `worker`, using entities from `orionis.foundation.config.queue`. A queue connection has a driver and logical channels; it is distinct from a SQL connection name.

## Compare drivers

| Driver | Execution | Persistence / requirements |
|---|---|---|
| `sync` | During `await dispatch` in the producer. | No durable storage; rejects delay and persistent retry. |
| `database` | Separate worker. | SQL table, enforced unique constraints, and a Database connection. |
| `redis` | Separate worker. | Reachable Redis; keys under a dedicated prefix. |

The default is `sync`. Select `QUEUE_CONNECTION=database` or `redis` before expecting deferred work. A worker cannot be created for `sync`: reservation always yields no work and the manager rejects the operation.

The database driver creates its schema lazily. The `jobs` table contains `id`, `queue`, `payload`, `attempts`, `available_at`, `reserved_until`, `reservation_token`, and `created_at`. Redis uses atomic transitions and reservation tokens. Both can recover work after reservations expire; neither guarantees external effects exactly once.

## Variables and defaults

| Area | Variables | Defaults |
|---|---|---|
| Selection | `QUEUE_CONNECTION` | `sync` |
| Sync | `QUEUE_SYNC_QUEUE`, `QUEUE_SYNC_RETRY_AFTER` | `default`, 90 s |
| Database | `QUEUE_DB_CONNECTION`, `QUEUE_TABLE`, `QUEUE_DB_QUEUE`, `QUEUE_DB_RETRY_AFTER` | default DB, `jobs`, `default`, 90 s |
| Redis | `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD` | `127.0.0.1`, 6379, 0, no password |
| Redis namespace | `QUEUE_REDIS_PREFIX`, `QUEUE_REDIS_QUEUE`, `QUEUE_REDIS_RETRY_AFTER` | `orionis:queues`, `default`, 90 s |
| Failures | `QUEUE_FAILED_DB_CONNECTION`, `QUEUE_FAILED_TABLE` | default DB, `failed_jobs` |
| Worker | `QUEUE_WORKER_CONCURRENCY`, `QUEUE_WORKER_SLEEP`, `QUEUE_WORKER_TIMEOUT`, `QUEUE_WORKER_TRIES`, `QUEUE_WORKER_BACKOFF` | 1, 1 s, 60 s, 3, `(0.0,)` |

Durations are seconds. `tries` includes the first attempt. Effective job timeout must be **strictly below** the connection's `retry_after`. Connection/queue names accept 1–128 alphanumeric characters, dots, hyphens, and underscores, starting alphanumerically. Durations must be finite and nonnegative; timeout/retry_after must be positive and concurrency a positive integer.

Named durable connections must use distinct tables or Redis prefixes. Failed storage must not reuse the jobs table on the same SQL connection. Validation prevents known collisions; it does not replace permissions, environment namespaces, or application separation.

## Failures need SQL even with Redis

The built-in failed-job repository uses the database. It initializes lazily when required; choosing Redis or sync does not remove this requirement for terminal failures. Prepare its connection and permissions before production. Redshift is rejected for database queues and failed-job storage because it does not enforce required unique keys.

## Prepare queue tables

Create queue storage before dispatching jobs or starting workers:

```shell
python reactor queue:migrate
```

The command creates missing jobs tables for **every** configured `database` queue connection and the central failed-job table, even when the default queue connection is `sync` or `redis`. It respects configured SQL connections, table names, and database prefixes, without connecting to Redis.

It is safe to repeat: existing tables and their data are preserved. It does not alter existing schemas or run application migrations. Automatic lazy table creation remains available. The equivalent service operation is `await Queue.migrate()`.

Inspect schemas without database access:

```python
from orionis.queues.schema import build_failed_jobs_table, build_jobs_table

jobs = build_jobs_table("jobs")
failed = build_failed_jobs_table("failed_jobs")
assert jobs.hasColumn("reservation_token")
assert failed.hasColumn("traceback")
```

## Transactions and lifecycle

Database dispatch uses the managed SQL connection and participates in a task-owned [transaction](../../../database/docs/en/transactions.md) on that same connection. Rollback removes the pending message too. Another connection or Redis is outside that SQL unit. There is no general dispatch `afterCommit` API or distributed protocol coordinating these systems.

The provider registers serializer and manager singletons, discovers jobs, pins `Queue`, and closes owned resources during shutdown. `await Queue.connection(name)` returns a cached driver; `await Queue.close()` closes queue clients without disconnecting shared database services. Application lifecycle should normally own cleanup.

For extensions, `IQueueDriver` defines async `push`, `reserve`, `release`, `delete`, `size`, `clear`, and `close`. Drivers must honor fencing, expiration, and envelope/reservation contracts. Stock configuration recognizes only the three built-in drivers; implementing the contract does not automatically register a new driver name with the manager.
