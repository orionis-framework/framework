# Cache

A cache stores regenerable data to avoid repeated queries or calculations. Design the key, lifetime, and invalidation first: no backend replaces the persistent source of truth.

## Learning path

1. [Storing and regenerating values](caching-values.md): keys, TTL, cache-aside, batches, and counters.
2. [Stores and locks](stores-and-locks.md): configuration, scope, consistency, and extensions.
3. [Source-derived artifacts](source-artifacts.md): source invalidation and local serialization.

Related: [orm](../../../orm/docs/en/README.md) · [foundation](../../../foundation/docs/en/README.md)

## Bounded execution and performance

Use `await Cache.rememberOnce(key, ttl, resolver, wait_timeout=10)` or the repository equivalent to coalesce overlapping misses on the same backend, prefix, key and event loop. Waiters share the result, including `None`; successful storage and later hits retain the backend's TTL/serialization semantics. Owners that fail or are cancelled release admission so a later caller can retry. Recursive resolution of the same key raises explicitly. The weak registry retains no completed key without active callers. `remember` and `rememberForever` remain compatible.

Optional `lease=seconds` also uses the backend lock, then rechecks storage. Redis waits through atomic NX acquisition with a TTL and only releases the current owner's lease. This is best-effort cross-process coordination with that backend's guarantees, not exactly-once execution: file/memory locks are process-local and a lease may expire during the resolver. Resolvers with side effects still require idempotency. `wait_timeout` bounds each local or Redis admission phase and Redis lease cleanup, not resolver execution or ordinary cache reads/writes. File `multiGet`/`multiSet` now use one worker transition per batch, preserve per-key locks/order/TTL and stop between entries on cancellation after draining the current operation.
