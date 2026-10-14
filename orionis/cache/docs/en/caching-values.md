# Storing and regenerating values

A cache stores regenerable data to avoid repeated queries or calculations. Design the key, lifetime, and invalidation first: no backend replaces the persistent source of truth.

## Requirements

- Python 3.14 or newer.
- `aiocache[redis,memcached]>=0.12.3`, installed by Orionis.
- Redis or Memcached services when those stores are selected.
- A configured Orionis database connection for the database store; non-SQLite databases may need the corresponding project extra.
- A writable directory for the file store and for `FileBasedCache`.

## Quick start

This standalone example uses the in-memory backend through the public repository API:

```python
import asyncio

from orionis.cache import CacheRepository
from orionis.cache.stores.memory import build


async def main() -> None:
    cache = CacheRepository(build(), prefix="docs")
    await cache.set("greeting", {"message": "hello"}, ttl=30)
    print(await cache.get("greeting"))


asyncio.run(main())  # {'message': 'hello'}
```

The physical key is `docs:greeting`; callers continue using the unprefixed name.

## Design keys and invalidation

Include every input that changes a result in its key: entity, tenant, locale, and format version where appropriate. `cache.prefix` separates names but does not enforce authorization. A predictable key does not make private data public; authorize access before retrieving or returning content.

`remember(key, ttl, resolver)` implements cache-aside: calculate and store on a miss. The resolver receives no arguments. Synchronous resolvers are called directly on the loop; when they perform blocking I/O, use an async resolver that delegates that work to an executor. The method also stores `None`, so a negative result remains cached for its TTL.

After updating the source, commit the persistent write and delete affected keys with `delete()`, or choose a TTL that tolerates the resulting staleness. Orionis does not infer dependencies between keys and models or invalidate automatically. Avoid `clear()` when invalidating one user's data: it flushes the complete backend even when the repository has a prefix.

If a cache read fails, decide in application code whether to regenerate from the source or abort. The repository propagates network and serialization errors; it has no automatic memory fallback. Store information that must not be lost in your database first.

### Understand operation boundaries

`add()` and `replace()` condition writes on absence or existence. `pull()` performs separate read and delete operations; two consumers could obtain the same value. `getMany()` returns a dict using requested keys and `None` for misses. `setMany()` does not imply a transaction across all backends. Counters accept integer deltas; behavior for missing keys or nonnumeric values depends on the backend.


### Manager, repository, and backend

`CacheManager` resolves configuration and owns repository instances. `CacheRepository` normalizes the application API and prefixes keys. A backend performs storage-specific primitives. Calls made directly on the manager proxy to the configured default repository.

### Cache-aside resolution

`remember(key, ttl, resolver)` reads with a private sentinel, so a stored `None` is a cache hit. On a miss it invokes a zero-argument sync or async resolver, stores the result, and returns it. It does not coalesce concurrent misses; use `lock()` around expensive regeneration when needed.

### Cache a resolver result, including `None`

```python
import asyncio

from orionis.cache import CacheRepository
from orionis.cache.stores.memory import build


async def main() -> None:
    cache = CacheRepository(build())
    calls = 0

    async def resolve() -> None:
        nonlocal calls
        calls += 1
        return None

    await cache.remember("nullable", 60, resolve)
    await cache.remember("nullable", 60, resolve)
    print(calls)  # 1


asyncio.run(main())
```

The sentinel prevents the stored `None` from being treated as another miss.

### Use atomic add and pull

```python
import asyncio

from orionis.cache import CacheRepository
from orionis.cache.stores.memory import build


async def main() -> None:
    cache = CacheRepository(build())
    print(await cache.add("ticket", "A"))  # True
    print(await cache.add("ticket", "B"))  # False
    print(await cache.pull("ticket"))       # A
    print(await cache.has("ticket"))        # False


asyncio.run(main())
```

`add` leaves the original value intact on conflict; `pull` removes it after reading.

### `CacheRepository`

```text
CacheRepository(backend: Any, prefix: str = "")
```

| Method | Behavior |
|---|---|
| `get(key)` / `has(key)` | Read a value or test a live entry. Missing `get` returns `None`. |
| `set(key, value, ttl=None)` | Store or overwrite a value. TTL is seconds. |
| `replace(key, value, ttl=None)` | Atomically replace only an existing live entry. |
| `delete(key)` / `clear()` | Delete one entry or flush the selected backend. |
| `getMany(keys)` | Return a mapping preserving the requested unprefixed keys. |
| `setMany(values, ttl=None)` | Store a mapping with one shared TTL. |
| `remember(key, ttl, resolver)` | Return cached data or compute/store a sync or async result. |
| `rememberForever(key, resolver)` | `remember` without expiry. |
| `pull(key)` | Read and then delete; missing returns `None`. |
| `add(key, value, ttl=None)` | Atomically store only if absent; conflicts return `False`. |
| `increment(key, amount=1)` / `decrement(...)` | Apply integer deltas and return the new value. |
| `lock(key, timeout=None)` | Return an async context manager for the prefixed key. |

Backend or serialization errors can propagate. `replace` raises `CacheStoreException` when a custom backend has no atomic replacement mechanism.

---

[Index](README.md) · [orm](../../../orm/docs/en/README.md) · [foundation](../../../foundation/docs/en/README.md)
