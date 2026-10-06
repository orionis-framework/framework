# orionis.cache

> `orionis.cache` provides asynchronous key/value repositories over memory, files, Redis, Memcached, or a database, plus cache-backed locks and source-aware file artifacts.

## Overview

Application code normally calls the pinned `Cache` facade or obtains a named `CacheRepository` with `Cache.store(name)`. The manager reads `cache` configuration, builds each backend lazily, applies the global key prefix, and reuses one repository per store name. The repository supplies reads, writes, batch operations, counters, cache-aside resolvers, atomic add/replace, pull, and async locks.

The separately exported `FileBasedCache` serves a different purpose: it stores one serialized dictionary in a file and invalidates it when monitored Python sources change. Orionis uses that style of cache for compiled framework artifacts rather than general application key/value data.

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

Validation: **Executed successfully** on CPython 3.14.6.

## Core concepts

### Manager, repository, and backend

`CacheManager` resolves configuration and owns repository instances. `CacheRepository` normalizes the application API and prefixes keys. A backend performs storage-specific primitives. Calls made directly on the manager proxy to the configured default repository.

### Store lifetime and key prefix

Stores are constructed on first access and cached inside that manager instance. Repeated `store("redis")` calls return the same repository. `cache.prefix` is applied to all repository keys, including locks; `clear()` still clears the entire selected backend, not only prefixed entries.

### Cache-aside resolution

`remember(key, ttl, resolver)` reads with a private sentinel, so a stored `None` is a cache hit. On a miss it invokes a zero-argument sync or async resolver, stores the result, and returns it. It does not coalesce concurrent misses; use `lock()` around expensive regeneration when needed.

### Store-specific locking

File locks use an `asyncio.Lock` shared by the event loop, directory, and key. Database locks use leased rows and polling. Other aiocache backends use `RedLock`; Redis/Memcached lock behavior therefore follows aiocache's lease-based semantics.

## Module structure

| Area | Responsibility |
|---|---|
| `cache_manager.py`, `provider.py` | Store construction, reuse, default-store proxy, and facade/container registration. |
| `repository.py` | Uniform high-level async cache operations and prefixes. |
| `stores/` | Memory, file, Redis, Memcached, and database backends. |
| `locks/` | Backend-aware async lock context manager. |
| `serializer.py`, `serializers/` | Rich JSON-compatible encoding and aiocache serializer. |
| `file_based_cache.py` | Source-hash-aware single-file artifact cache. |
| `contracts/`, `exceptions.py` | Extension interfaces and cache errors. |

## Public API

### `Cache` facade and `CacheManager`

Use `from orionis.support.facades.cache import Cache` in a booted application. `CacheProvider` registers `ICacheManager` as a singleton and pins the facade. `store(name=None)` is synchronous and returns a repository; all other manager methods proxy to the default store:

```python
repo = Cache.store("redis")
value = await Cache.get("key")
await Cache.set("key", value, ttl=60)
```

Supported configured names are `file`, `memory`, `redis`, `memcached`, and `database`. An unknown or absent store raises `CacheStoreException`.

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

### `FileBasedCache`

```text
FileBasedCache(
    path: Path,
    filename: str,
    monitored_dirs: list[Path] | None = None,
    monitored_files: list[Path] | None = None,
)
```

`save(data)` writes a versioned payload and returns `(CACHE_VERSION, sources_hash)`; identical data and source hash skip the rewrite. `get()` returns the dictionary only when version and source hash still match, otherwise `None`. `clear()` reports whether the cache file existed. Only Python files from monitored directories participate, and the cache file itself is excluded.

### Extension API

`ICacheManager`, `ICacheRepository`, and `IFileBasedCache` define replacement contracts. Custom key/value backends supplied to `CacheRepository` must provide the aiocache-style methods used by the repository (`get`, `set`, `exists`, `delete`, batch methods, `add`, and `increment`).

## Common workflows

### Use the configured default store

Call facade methods directly. The first operation builds the configured store; later operations reuse its repository. Set TTL in seconds or use `None` for no expiry.

### Select an explicit store

Call `Cache.store("memory")` or another configured name, then retain the repository or ask the manager again. All stores receive the same global prefix.

### Regenerate expensive data safely

Check through `remember`; if duplicate concurrent work is unacceptable, acquire `async with cache.lock("resource", timeout=...)`, check the cache again inside the lock, compute, and set.

### Cache compiled artifacts

Construct `FileBasedCache` with the relevant source paths, call `get`, rebuild when it returns `None`, then `save`. A source change invalidates the stored data without deleting the file first.

## Examples

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

Validation: **Executed successfully** on CPython 3.14.6.

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

Validation: **Executed successfully** on CPython 3.14.6.

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

Validation: **Executed successfully** on CPython 3.14.6.

### Invalidate a file artifact when source changes

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from orionis.cache import FileBasedCache


with TemporaryDirectory() as directory:
    root = Path(directory)
    source = root / "feature.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")

    cache = FileBasedCache(root, "compiled.cache", monitored_files=[source])
    cache.save({"routes": ["/"]})
    print(cache.get())  # {'routes': ['/']}

    source.write_text("VALUE = 2\n", encoding="utf-8")
    time.sleep(0.6)  # FileBasedCache refreshes its source hash every 0.5 s.
    print(cache.get())  # None
```

Validation: **Executed successfully** on CPython 3.14.6.

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

## Integration with Orionis

`CacheProvider` is deferrable: the container registers the singleton manager when `ICacheManager` is needed, then pins the `Cache` facade. The database store obtains its connection through `ConnectionResolver`. File and database backends use Orionis's serializer so framework values can round-trip beyond plain JSON types.

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

## Compatibility

Orionis declares Python 3.14+ and aiocache 0.12.3 or newer; validation used CPython 3.14.6 on Windows. The file and memory stores require no service. Redis, Memcached, and database compatibility depends on the corresponding configured service/driver. File locking uses the cross-platform `filelock` dependency declared by the project.

## Verification notes

Manager, repository, all stores, locks, serializers, file artifact cache, provider/facade, configuration, and `tests/cache` were inspected. All 210 cache tests passed through the Orionis runner on CPython 3.14.6. All five Quick start/Examples programs were executed successfully without external services.
