# Configuring stores and coordinating regeneration

Store selection determines where cache data is shared and what a lock means.

## Choose a backend by its scope

| Store | Persistence and scope | Coordination |
|---|---|---|
| `memory` | This instance/process only; lost on restart | RedLock on the same backend; does not coordinate workers. |
| `file` | JSON in a local shared directory | File-locked writes and replacement; `cache.lock()` coordinates only the same loop and directory. |
| `redis` | Configured Redis service | aiocache RedLock lease; not a business transaction. |
| `memcached` | Memcached service, subject to eviction | RedLock lease with backend-specific guarantees. |
| `database` | Tables in an Orionis connection | Unique rows and leases; requires enforced unique constraints. |

The manager accepts built-in names `memory`, `file`, `redis`, `memcached`, and `database`; it has no `extend()` registry for named stores. For a custom backend, construct `CacheRepository(backend, prefix)` with the aiocache API used by the repository, or replace `ICacheManager` through the container. A store entity's `driver` property does not arbitrarily select another implementation.

Stores serialize through msgspec JSON: keep value contracts JSON-compatible and test round trips when using dates, tuples, or custom types. The rich `Serializer` described under [artifacts](source-artifacts.md) is not used by these stores. Dates may return as strings and tuples as lists; do not assume type identity.

The database store creates entry and lock tables lazily; its connection needs table-creation permissions. It rejects connections lacking enforced unique constraints, such as Redshift. It does not require a dedicated cache migration. Keep table names exclusive to your application. The file store uses monotonic-clock expirations; do not treat it as durable persistence or share its files across machines with different monotonic clocks.

### Avoid simultaneous regeneration

`remember()` alone can run several resolvers for the same miss. Acquire a lock and check again inside the critical section before computing. The meaning of `timeout` varies by store: file uses it as an acquisition deadline; database also uses it as the lease; RedLock uses it as the lease duration. Lease expiry does not cancel your code and may admit another writer while you are still inside.

Use cache locks to reduce duplicate work. For balance, inventory, or uniqueness invariants, use transactions or constraints in the persistent system. Automatic lease renewal and fencing tokens are not provided.


### Protect a critical section

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

For the memory backend this uses aiocache's lease-based `RedLock`; it coordinates users of the same backend instance.

## Configuration

| Key | Environment variable | Default |
|---|---|---|
| `cache.default` | `CACHE_STORE` | `file` |
| `cache.prefix` | `CACHE_PREFIX` | empty |
| `cache.stores.file.path` | `CACHE_FILE_PATH` | `storage/framework/cache/data` |
| `cache.stores.redis.endpoint/port/db/password` | `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD` | `127.0.0.1`, `6379`, `0`, `None` |
| `cache.stores.memcached.endpoint/port` | `MEMCACHED_HOST`, `MEMCACHED_PORT` | `127.0.0.1`, `11211` |
| `cache.stores.database.connection` | `DB_CACHE_CONNECTION` | default DB connection |
| `cache.stores.database.table` | `DB_CACHE_TABLE` | `cache` |
| `cache.stores.database.lock_table` | `DB_CACHE_LOCK_TABLE` | `cache_locks` |

Relative file paths resolve against `app.basePath`. Configuration entities validate driver names and store options during application setup.


The shipped `BootstrapCache` uses an empty prefix; the base `Cache` entity defaults to `orionis` when constructed without an override. Check which configuration your application builds.


## Integration with Orionis

`CacheProvider` is deferrable: the container registers the singleton manager when `ICacheManager` is needed, then pins the `Cache` facade. The database store obtains its connection through `ConnectionResolver`. File and database stores use msgspec JSON encoding.

The cache package is also used by framework compilation and other modules that need cached state. Importing `orionis.cache` alone does not build a backend or connect to a service.



## Errors and edge cases

- Missing and stored `None` are indistinguishable through `get`, but `remember` distinguishes them internally.
- `clear()` flushes the backend namespace and does not filter by repository prefix.
- `pull` is a read followed by delete, not one backend atomic primitive.
- Concurrent `remember` misses can run the resolver more than once.
- Invalid store names and unavailable store configuration raise `CacheStoreException`; connection, serializer, and backend exceptions may propagate.
- `add` converts the backend's duplicate-key `ValueError` to `False`; it does not suppress unrelated exception types.
- File/database lock acquisition with a finite timeout may raise `TimeoutError`. Leases can expire while a long critical section is still running.
- `FileBasedCache.save` accepts only dictionaries and its invalidation hash is refreshed on a short internal interval (0.5 seconds).



## Performance and concurrency

Repository creation is lazy and cached per manager. Memory is process-local; file storage offloads blocking file operations and uses file locks/atomic replacement; Redis and Memcached delegate network behavior to aiocache; database storage ensures its schema lazily and uses database operations for shared coordination.

File-cache async locks are shared only within the same event loop and cache directory. Database locks poll every 0.05 seconds and use a default 10-second lease when no timeout is supplied. Other backends use a 10-second default RedLock lease. Batch methods delegate to backend multi-operations rather than looping in the repository.



### `Cache` facade and `CacheManager`

Use `from orionis.support.facades.cache import Cache` in a booted application. `CacheProvider` registers `ICacheManager` as a singleton and pins the facade. `store(name=None)` is synchronous and returns a repository; all other manager methods proxy to the default store:

```python
from orionis.support.facades import Cache


async def cache_example() -> None:
    repo = Cache.store("redis")
    value = await repo.get("key")
    await repo.set("key", value, ttl=60)
```

Supported configured names are `file`, `memory`, `redis`, `memcached`, and `database`. An unknown or absent store raises `CacheStoreException`.

### Extension API

`ICacheManager`, `ICacheRepository`, and `IFileBasedCache` define replacement contracts. Custom key/value backends supplied to `CacheRepository` must provide the aiocache-style methods used by the repository (`get`, `set`, `exists`, `delete`, batch methods, `add`, and `increment`).

## Implementation reference for extensions

| Area | Responsibility |
|---|---|
| `cache_manager.py`, `provider.py` | Store construction, reuse, default-store proxy, and facade/container registration. |
| `repository.py` | Uniform high-level async cache operations and prefixes. |
| `stores/` | Memory, file, Redis, Memcached, and database backends. |
| `locks/` | Backend-aware async lock context manager. |
| `serializer.py`, `serializers/` | Rich JSON-compatible encoding and aiocache serializer. |
| `file_based_cache.py` | Source-hash-aware single-file artifact cache. |
| `contracts/`, `exceptions.py` | Extension interfaces and cache errors. |

---

[Index](README.md) · [database](../../../database/docs/en/README.md) · [orm](../../../orm/docs/en/README.md)
