# Queues and jobs

Queues separate requesting work from executing it. A `BaseJob` declares serializable state and an async `handle`; `Queue.dispatch()` creates deferred submission that reaches the backend only when awaited. Built-in drivers are `sync`, `database`, and `redis`.

1. [Write and dispatch jobs](jobs-and-dispatch.md): allowed state, DI, class identities, and one-shot dispatch.
2. [Choose and configure a backend](drivers-and-configuration.md): persistence, connections, tables, Redis, and transactions.
3. [Workers, retries, and failures](workers-and-failures.md): leases, concurrency, timeout, backoff, and recovery.

Choose database or Redis for durable work and run a separate worker. The default `sync` driver executes during dispatch without keeping work for another process. Message durability does not guarantee an external effect happens exactly once: make jobs idempotent.

Facades require a [booted application](../../../foundation/docs/en/README.md). Python 3.14+, msgspec, and Redis are declared dependencies; the database backend uses [Database](../../../database/docs/en/README.md).

## Bounded execution and performance

Redis transitions first send `EVALSHA` with a cached script digest. `NOSCRIPT` triggers one `EVAL` of the same operation on the owning node, loading its script cache atomically; the next invocation returns to `EVALSHA`. Script bodies, key hash tags, reservations and fencing tokens are unchanged. The driver adds this recovery only for `NOSCRIPT`; the Redis client's transport retry policy still applies. A Redis restart or script-cache eviction is supported without a process-global loaded flag.
