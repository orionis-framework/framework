# orionis.cache

> Async, driver-based cache layer (memory, file, Redis, Memcached, database) plus the synchronous artefact cache used by the framework bootstrap.

## Table of contents

- [Functional description](#functional-description)
  - [Where it fits in the framework](#where-it-fits-in-the-framework)
  - [Resolution pipeline](#resolution-pipeline)
  - [File map](#file-map)
  - [Design decisions](#design-decisions)
- [API reference](#api-reference)
  - [`Cache` facade](#cache-facade)
  - [`ICacheManager` / `CacheManager`](#icachemanager--cachemanager)
  - [`ICacheRepository` / `CacheRepository`](#icacherepository--cacherepository)
  - [`CacheLock`](#cachelock)
  - [`FileCacheBackend`](#filecachebackend)
  - [`DatabaseCacheBackend`](#databasecachebackend)
  - [Backend factories](#backend-factories)
  - [`MsgspecSerializer`](#msgspecserializer)
  - [`Serializer`](#serializer)
  - [`IFileBasedCache` / `FileBasedCache`](#ifilebasedcache--filebasedcache)
  - [`CacheProvider`](#cacheprovider)
  - [Exceptions](#exceptions)
  - [Configuration entities](#configuration-entities)
- [Usage examples](#usage-examples)
- [Performance and concurrency](#performance-and-concurrency)
- [Compatibility notes](#compatibility-notes)

## Functional description

`orionis.cache` solves two unrelated problems that happen to share the word
*cache*:

1. **Application cache** — an async key/value store with pluggable drivers
   (`memory`, `file`, `redis`, `memcached`, `database`), TTLs, batch reads and
   writes, memoisation helpers (`remember`) and distributed locks. It is reached
   through the `Cache` facade or by injecting `ICacheManager`.
2. **Artefact cache** — `FileBasedCache` plus `Serializer`, a *synchronous*
   single-file cache with source-change invalidation, used internally by
   `orionis.foundation.application`, `orionis.console.core.loader` and
   `orionis.http.routes.loader` to avoid re-scanning the project on every boot.

### Where it fits in the framework

| Consumer | What it uses |
|---|---|
| `orionis.foundation.core_providers` | Registers `CacheProvider` as a core provider |
| `orionis.session.stores.cache.CacheSessionStore` | Receives an `ICacheManager` and calls `store(name)` |
| `orionis.foundation.application` | Builds a `FileBasedCache` for the compiled bootstrap state |
| `orionis.console.core.loader.Loader` | Caches discovered console command metadata in a `FileBasedCache` |
| `orionis.http.routes.loader` | Caches compiled routes in a `FileBasedCache` |
| `orionis.orm.resolver.ConnectionResolver` | Supplies the `IConnection` used by the `database` driver |

### Resolution pipeline

```text
Cache (facade, orionis.support.facades.cache)
 └── ICacheManager ──singleton──► CacheManager(app)
        │  app.config("cache") → Cache entity (default, prefix, stores)
        └── store(name) ─────────► CacheRepository(backend, prefix)   [memoised per name]
                                      └── backend
                                          memory     → aiocache.SimpleMemoryCache
                                          redis      → aiocache.backends.redis.RedisCache
                                          memcached  → aiocache.backends.memcached.MemcachedCache
                                          database   → DatabaseCacheBackend(IConnection)
                                          <any other name> → FileCacheBackend(path)
```

`CacheRepository.lock(key, timeout)` returns a `CacheLock`, which picks its
implementation from the backend type: `asyncio.Lock` for `FileCacheBackend`, a
row-based lock for `DatabaseCacheBackend`, and `aiocache.lock.RedLock` for
everything else.

### File map

| Path | Contents |
|---|---|
| `__init__.py` | Exports `CacheManager`, `CacheRepository`, `FileBasedCache` |
| `cache_manager.py` | `CacheManager` — store resolution and default-store proxy |
| `repository.py` | `CacheRepository` — prefixing and the high-level API |
| `exceptions.py` | `CacheException`, `CacheStoreException` |
| `file_based_cache.py` | `FileBasedCache` — synchronous artefact cache |
| `serializer.py` | `Serializer` — type-tagged JSON encoder/decoder |
| `provider.py` | `CacheProvider` — container bindings and facade pin |
| `contracts/` | `ICacheManager`, `ICacheRepository`, `IFileBasedCache` |
| `locks/lock.py` | `CacheLock` — async context-manager lock |
| `serializers/json.py` | `MsgspecSerializer` — aiocache serializer built on msgspec |
| `stores/memory.py` | `build()` → `SimpleMemoryCache` |
| `stores/redis.py` | `build()` → `RedisCache` |
| `stores/memcached.py` | `build()` → `MemcachedCache` |
| `stores/file.py` | `FileCacheBackend` — one JSON file per key |
| `stores/database.py` | `DatabaseCacheBackend` + table definitions + `build()` |

`locks/__init__.py`, `stores/__init__.py` and `serializers/__init__.py` are
empty; import the concrete modules directly.

### Design decisions

- `CacheManager`, `CacheRepository`, `CacheLock`, `FileCacheBackend` and
  `DatabaseCacheBackend` declare `__slots__` — instances carry no `__dict__`.
- `CacheProvider` inherits both `ServiceProvider` and `DeferrableProvider`, so
  the binding (and the facade pin) only happens when `ICacheManager` is first
  resolved. This changes how the facade behaves — see
  [`Cache` facade](#cache-facade).
- `CacheManager.store()` memoises one `CacheRepository` per resolved store name,
  so a store name maps to exactly one backend instance per manager.
- The key prefix is applied by `CacheRepository._k()`, not by the backends; a
  repository built by hand with `prefix=""` writes unprefixed keys.
- `remember()` and `pull()` read through a private `_MISSING` sentinel, so a
  stored `None` is a hit, not a miss.
- `FileCacheBackend` and `DatabaseCacheBackend` expose both camelCase
  (`multiGet`, `multiSet`) and aiocache-style snake_case (`multi_get`,
  `multi_set`) methods, which is what lets `CacheRepository` talk to aiocache
  backends and to the bespoke ones with the same code.
- All aiocache backends are built with `MsgspecSerializer`, so values are JSON
  encoded on every driver instead of being pickled or stored raw.
- `FileBasedCache` does **not** inherit `IFileBasedCache` and is not registered
  in the container; consumers instantiate it directly.
- Neither `ICacheManager` nor `ICacheRepository` declares `lock()`, although
  both `CacheManager` and `CacheRepository` implement it.

## API reference

### `Cache` facade

`orionis.support.facades.cache.Cache` is a `Facade` whose accessor is
`ICacheManager`:

```python
class Cache(Facade):
    @classmethod
    def getFacadeAccessor(cls) -> type: ...
```

Because `CacheProvider` is deferrable, the facade is **not** pinned when the
application starts. The behaviour of each access depends on that state:

| Access | Facade not pinned | Facade pinned |
|---|---|---|
| `await Cache.get("k")` | Works (the dispatcher resolves and awaits) | Works |
| `async with Cache.lock("k"):` | Works (`_FacadeDispatch.__aenter__`) | Works |
| `Cache.store("memory")` | Returns a `_FacadeDispatch`, not a repository | Returns `CacheRepository` |
| `await Cache.store("memory")` | Returns `CacheRepository` | `TypeError: 'CacheRepository' object can't be awaited` |

The first `await` through the facade resolves `ICacheManager`, which triggers
the deferred registration, runs `CacheProvider.boot()` and pins the facade —
after which the synchronous methods (`store`, `lock`) must be called *without*
`await`. Code that must work in both states should inject `ICacheManager`
instead of using the facade.

### `ICacheManager` / `CacheManager`

`ICacheManager` (`contracts/cache_manager.py`) is an `ABC` declaring `store`
plus the thirteen default-store proxies. `CacheManager` implements it.

```python
class CacheManager(ICacheManager):
    __slots__ = (
        "_app",
        "_base_path",
        "_config",
        "_default",
        "_prefix",
        "_repositories",
    )

    def __init__(self, app: IApplication) -> None: ...
```

`__init__` reads `app.config("cache")`. When that value is a `dict` it is
converted to the `Cache` configuration entity; otherwise it is used as-is.
`_default` and `_prefix` are coerced with `str()`, and `_base_path` is
`app.basePath`.

| Method | Signature | Notes |
|---|---|---|
| `store` | `store(self, name: str \| None = None) -> CacheRepository` | Memoised per name; `None` selects `config.default` |
| `get` | `async get(self, key: str) -> Any` | Delegates to `store().get` |
| `set` | `async set(self, key: str, value: Any, ttl: float \| None = None) -> bool` | |
| `has` | `async has(self, key: str) -> bool` | |
| `delete` | `async delete(self, key: str) -> bool` | |
| `clear` | `async clear(self) -> bool` | |
| `getMany` | `async getMany(self, keys: list[str]) -> dict[str, Any]` | |
| `setMany` | `async setMany(self, values: dict[str, Any], ttl: float \| None = None) -> bool` | |
| `remember` | `async remember(self, key: str, ttl: float \| None, resolver: Callable) -> Any` | |
| `rememberForever` | `async rememberForever(self, key: str, resolver: Callable) -> Any` | |
| `pull` | `async pull(self, key: str) -> Any` | |
| `add` | `async add(self, key: str, value: Any, ttl: float \| None = None) -> bool` | |
| `increment` | `async increment(self, key: str, amount: int = 1) -> int` | |
| `decrement` | `async decrement(self, key: str, amount: int = 1) -> int` | |
| `lock` | `lock(self, key: str, timeout: float \| None = None) -> Any` | Not declared in `ICacheManager` |

**Store resolution** (`_buildBackend`, called once per store name):

| `name` | Backend | Raises |
|---|---|---|
| `"memory"` | `SimpleMemoryCache` | — |
| `"redis"` | `RedisCache` | `CacheStoreException` when `stores.redis` is `None` |
| `"memcached"` | `MemcachedCache` | `CacheStoreException` when `stores.memcached` is `None` |
| `"database"` | `DatabaseCacheBackend` | `CacheStoreException` when `stores.database` is `None` |
| any other value | `FileCacheBackend` | — |

The last row is the fallback branch of `_buildBackend`: an unrecognised store
name silently produces a file-backed repository rather than an error. The file
path comes from `stores.file.path` (default `storage/framework/cache/data`) and
is resolved against `app.basePath` when relative.

The `database` branch resolves its connection through
`ConnectionResolver.connection(...)`, so it requires the ORM connection manager
to be installed; otherwise `ConnectionResolver` raises
`OrmConfigurationException`.

### `ICacheRepository` / `CacheRepository`

`replace(key, value, ttl=None) -> bool` atomically replaces a live entry without
creating a missing key. File storage uses cross-process `filelock` stripes;
database storage uses a conditional UPDATE; aiocache backends use OptimisticLock
CAS with an explicit missing-key rejection. A concurrent change can return False.
Custom repositories must implement this contract for safe cache-backed sessions.

```python
class CacheRepository(ICacheRepository):
    __slots__ = ("_backend", "_prefix")

    def __init__(self, backend: Any, prefix: str = "") -> None: ...
```

Keys are transformed by `_k(key)`, which returns `f"{prefix}:{key}"` when a
prefix is configured and the raw key otherwise.

| Method | Signature | Behaviour |
|---|---|---|
| `get` | `async get(self, key: str) -> Any` | `backend.get(_k(key))`; `None` when absent |
| `set` | `async set(self, key: str, value: Any, ttl: float \| None = None) -> bool` | Result coerced with `bool()` |
| `has` | `async has(self, key: str) -> bool` | Uses `backend.exists()`, never deserialises |
| `delete` | `async delete(self, key: str) -> bool` | `True` when the key existed |
| `clear` | `async clear(self) -> bool` | Flushes the whole backend |
| `getMany` | `async getMany(self, keys: list[str]) -> dict[str, Any]` | `backend.multi_get`; re-keyed with `zip(..., strict=True)` on the original names |
| `setMany` | `async setMany(self, values: dict[str, Any], ttl: float \| None = None) -> bool` | `backend.multi_set` with prefixed pairs |
| `remember` | `async remember(self, key: str, ttl: float \| None, resolver: Callable) -> Any` | On a miss calls `resolver()`, awaits it when awaitable, stores it, returns it |
| `rememberForever` | `async rememberForever(self, key: str, resolver: Callable) -> Any` | `remember(key, None, resolver)` |
| `pull` | `async pull(self, key: str) -> Any` | Reads then deletes; `None` when absent |
| `add` | `async add(self, key: str, value: Any, ttl: float \| None = None) -> bool` | Catches the backend's `ValueError` and returns `False` |
| `increment` | `async increment(self, key: str, amount: int = 1) -> int` | `backend.increment(_k(key), amount)` |
| `decrement` | `async decrement(self, key: str, amount: int = 1) -> int` | `backend.increment(_k(key), -amount)` |
| `lock` | `lock(self, key: str, timeout: float \| None = None) -> CacheLock` | Synchronous; returns an async context manager. Not declared in `ICacheRepository` |

`remember` and `pull` call `backend.get(key, default=_MISSING)` with a private
module-level sentinel, so a cached `None` is returned instead of triggering a
recomputation.

### `CacheLock`

```python
class CacheLock:
    __slots__ = ("_backend", "_impl", "_key", "_owner", "_timeout")

    def __init__(
        self,
        backend: Any,
        key: str,
        timeout: float | None = None,
    ) -> None: ...
```

Module constants: `_DEFAULT_LEASE = 10`, `_POLL_INTERVAL = 0.05`, and
`_FILE_LOCKS: dict[str, asyncio.Lock]`.

`__aenter__` dispatches on the backend type:

| Backend | Implementation | Timeout behaviour |
|---|---|---|
| `FileCacheBackend` | `asyncio.Lock` from the process-wide `_FILE_LOCKS` dict | `asyncio.wait_for` → `TimeoutError` |
| `DatabaseCacheBackend` | Polls `backend.acquireLock(key, owner, lease)` every `0.05 s`; `owner` is a `uuid4().hex`, `lease` is `timeout or 10` | `TimeoutError` once the deadline passes |
| anything else | `aiocache.lock.RedLock(backend, key, lease=timeout or 10)` | Delegated to `RedLock` |

`__aexit__` releases the `asyncio.Lock`, calls `backend.releaseLock(key, owner)`
or delegates to `RedLock.__aexit__`, matching the branch taken on entry.

### `FileCacheBackend`

```python
class FileCacheBackend:
    __slots__ = ("_counter_lock", "_path", "_rename_lock")

    def __init__(self, path: Path) -> None: ...
```

Creates the directory on construction. Each key is hashed with SHA-256 and
stored as `<digest>.json`, holding `{"v": <value>, "e": <deadline | None>}`
encoded with `msgspec.json`. The deadline is `time.monotonic() + ttl`.

| Method | Signature | Notes |
|---|---|---|
| `get` | `async get(self, key: str, default: Any = None) -> Any` | Deletes the file when expired (lazy eviction) |
| `set` | `async set(self, key: str, value: Any, ttl: float \| None = None) -> bool` | Always `True` |
| `exists` | `async exists(self, key: str) -> bool` | |
| `delete` | `async delete(self, key: str) -> int` | `1` / `0` |
| `clear` | `async clear(self) -> bool` | Removes `*.json` and `*.tmp` |
| `multiGet` / `multi_get` | `async multiGet(self, keys: list[str], default: Any = None) -> list[Any]` | Sequential `get` per key |
| `multiSet` / `multi_set` | `async multiSet(self, pairs: list[tuple[str, Any]], ttl: float \| None = None) -> bool` | Sequential `set` per pair |
| `add` | `async add(self, key: str, value: Any, ttl: float \| None = None) -> bool` | Exclusive create; raises `ValueError` when the key exists |
| `increment` | `async increment(self, key: str, delta: int = 1) -> int` | Serialised read-modify-write that keeps the entry expiry |

Reads, writes and unlinks run through `asyncio.to_thread`. Writes are staged in
a sibling that carries a random infix (`<file>.<random>.tmp`) and published with
`Path.replace`; the rename is serialised by an instance-level `threading.Lock`
and retried up to `_REPLACE_ATTEMPTS = 3` times with a `5 ms` backoff when the
operating system reports a sharing violation. A failed write removes its own
staging file before propagating the `OSError`.

### `DatabaseCacheBackend`

```python
class DatabaseCacheBackend:
    __slots__ = ("_connection", "_lock_table", "_ready", "_ready_lock", "_table")

    def __init__(
        self,
        connection: IConnection,
        table: str,
        lock_table: str | None = None,
    ) -> None: ...
```

`lock_table` defaults to `_DEFAULT_LOCK_TABLE = "cache_locks"`.
`_ensureSchema()` creates both tables on first use, guarded by an
`asyncio.Lock` and a `_ready` flag (double-checked).

Schema built by `_buildEntriesTable(table)` and `_buildLocksTable(table)`:

| Table | Columns |
|---|---|
| entries | `cache_key` `String(255)` primary key, `cache_value` `Text` nullable, `expiration` `Double` nullable |
| locks | `cache_key` `String(255)` primary key, `owner` `String(255)` nullable, `expiration` `Double` nullable |

`expiration` is a wall-clock epoch (`time.time()`) stored as a floating point
number, which preserves sub-second TTLs and leases.

| Method | Signature | Notes |
|---|---|---|
| `get` | `async get(self, key: str, default: Any = None) -> Any` | Deletes the row when expired |
| `set` | `async set(self, key: str, value: Any, ttl: float \| None = None) -> bool` | `UPDATE`, then `INSERT` when no row matched; a conflicting `INSERT` retries as `UPDATE` |
| `exists` | `async exists(self, key: str) -> bool` | |
| `delete` | `async delete(self, key: str) -> int` | Affected rows |
| `clear` | `async clear(self) -> bool` | `DELETE FROM <table>` |
| `multiGet` / `multi_get` | `async multiGet(self, keys: list[str], default: Any = None) -> list[Any]` | Sequential |
| `multiSet` / `multi_set` | `async multiSet(self, pairs: list[tuple[str, Any]], ttl: float \| None = None) -> bool` | Sequential |
| `add` | `async add(self, key: str, value: Any, ttl: float \| None = None) -> bool` | Deletes an already-expired row, then `INSERT`; raises `ValueError` when the key is taken and re-raises `QueryException` otherwise |
| `increment` | `async increment(self, key: str, delta: int = 1) -> int` | Compare-and-swap loop, `_INCREMENT_ATTEMPTS = 25`; raises `QueryException` when exhausted |
| `acquireLock` | `async acquireLock(self, key: str, owner: str, lease: float) -> bool` | Single attempt: `INSERT`, or conditional `UPDATE` when the row is expired or self-owned |
| `releaseLock` | `async releaseLock(self, key: str, owner: str) -> None` | `DELETE ... WHERE cache_key = :k AND owner = :o` |

Values are encoded with `msgspec.json`; a payload that fails to decode is read
back as `None`.

### Backend factories

Every store module exposes a module-level `build()` function; `CacheManager`
imports them under aliases (`_build_memory`, `_build_redis`, …).

```python
# orionis/cache/stores/memory.py
def build() -> SimpleMemoryCache: ...

# orionis/cache/stores/redis.py
def build(
    endpoint: str = "127.0.0.1",
    port: int = 6379,
    db: int = 0,
    password: str | None = None,
) -> RedisCache: ...

# orionis/cache/stores/memcached.py
def build(endpoint: str = "127.0.0.1", port: int = 11211) -> MemcachedCache: ...

# orionis/cache/stores/database.py
def build(
    connection: IConnection,
    table: str,
    lock_table: str | None = None,
) -> DatabaseCacheBackend: ...
```

The three aiocache backends are always constructed with
`serializer=MsgspecSerializer()`.

### `MsgspecSerializer`

```python
class MsgspecSerializer(BaseSerializer):
    DEFAULT_ENCODING = None

    def dumps(self, value: Any) -> bytes: ...
    def loads(self, data: bytes | str | float | None) -> Any: ...
```

Subclass of `aiocache.serializers.BaseSerializer`. `DEFAULT_ENCODING = None`
keeps backend payloads as raw bytes. `loads` returns `None` for `None` input,
encodes `str` input before decoding, and returns any other non-bytes payload
unchanged — which is what keeps a counter written by the memory driver's
`increment()` readable, since aiocache stores it as a native `int`.

### `Serializer`

Static utility used by `FileBasedCache` (it is unrelated to the aiocache
serializer above).

```python
class Serializer:
    @staticmethod
    def dumps(data: Any, indent: int | None = None) -> str: ...
    @staticmethod
    def loads(raw: str | bytes) -> Any: ...
    @staticmethod
    def dumpToFile(data: Any, file_path: Path) -> None: ...
    @staticmethod
    def loadFromFile(file_path: Path) -> Any: ...
```

Values that JSON cannot express natively are wrapped in a type-tagged mapping
`{"__type__": ..., "__value__": ...}`. Supported tags: `path`, `bytes`,
`datetime`, `date`, `time`, `timedelta`, `decimal`, `uuid`, `complex`, `tuple`,
`set`, `frozenset`, `type`, `enum` and `missing` (the `MISSING` sentinel from
`orionis.support.types.sentinel`). `dict` and `list` are encoded recursively;
`str`, `int`, `float`, `bool` and `None` pass through untouched.

- `dumps` uses `msgspec.json` when `indent` is `None`, and the standard library
  `json` module when an indent is given.
- Encoding an unsupported type raises `TypeError`; decoding an unknown
  `__type__` raises `ValueError`.
- `dumpToFile` stages the payload in a sibling that carries a random infix
  (`<file>.<random>.tmp`), publishes it with `Path.replace`, and removes its own
  staging file before propagating an `OSError`.
- `loadFromFile` returns `None` when the file is missing (any `OSError`) or
  empty.
- `type` and `enum` payloads are resolved by importing the recorded dotted path,
  so decoding executes an import when the module is not already loaded.

### `IFileBasedCache` / `FileBasedCache`

```python
class FileBasedCache:
    __slots__ = (
        "__file",
        "__file_resolved",
        "__hashInterval",
        "__lasthashcheck",
        "__monitored_dirs",
        "__monitored_files",
        "__path",
        "__sourceshashcache",
    )

    CACHE_VERSION = 1

    def __init__(
        self,
        path: Path,
        filename: str,
        monitored_dirs: list[Path] | None = None,
        monitored_files: list[Path] | None = None,
    ) -> None: ...
```

`__init__` raises `TypeError` when `path` is not a `Path` and creates the
directory with `mkdir(parents=True, exist_ok=True)`.

| Method | Signature | Behaviour |
|---|---|---|
| `get` | `get(self) -> dict \| None` | Returns `__data__` only when the payload exists, `__meta__.version` equals `CACHE_VERSION` and `__meta__.sourcesHash` still matches |
| `save` | `save(self, data: dict) -> tuple[int, str]` | Raises `TypeError` when `data` is not a `dict`; skips the write when version, hash and data are unchanged; returns `(CACHE_VERSION, sources_hash)` |
| `clear` | `clear(self) -> bool` | `True` when the file was removed, `False` when it did not exist |

The stored payload is
`{"__meta__": {"version", "generatedAt", "sourcesHash"}, "__data__": data}`.
`sourcesHash` is a SHA-1 (constructed with `usedforsecurity=False`) over the
sorted, deduplicated set of monitored files — every `*.py` found by `rglob` in
`monitored_dirs` plus the existing entries of `monitored_files`, excluding the
cache file itself. For each file the hash absorbs the POSIX path bytes and
`struct.pack(">QQ", st_mtime_ns, st_size)`. The result is memoised for
`0.5 s` (`time.monotonic()`), so consecutive calls within that window reuse it.

`IFileBasedCache` (`contracts/file_based_cache.py`) declares the same three
methods, but `FileBasedCache` does not inherit from it; the contract is used as
a type annotation by `orionis.console.core.loader` and
`orionis.http.routes.loader`.

### `CacheProvider`

```python
class CacheProvider(ServiceProvider, DeferrableProvider):
    @classmethod
    def provides(cls) -> list[type]: ...
    def register(self) -> None: ...
    async def boot(self) -> None: ...
```

- `provides()` returns `[ICacheManager]`.
- `register()` performs `self.app.singleton(ICacheManager, CacheManager)`.
- `boot()` awaits `Cache.pin()`.
- Listed in `orionis.foundation.core_providers.CORE_PROVIDERS`; because it is
  deferrable, registration and boot are triggered by the first resolution of
  `ICacheManager`.

### Exceptions

```python
class CacheException(Exception): ...
class CacheStoreException(CacheException): ...
```

`CacheStoreException` is raised by `CacheManager._buildBackend` /
`_buildDatabaseBackend` with the messages `"Redis store is not configured."`,
`"Memcached store is not configured."` and `"Database store is not
configured."`. No other module code raises `CacheException` directly.

### Configuration entities

Configuration lives in `orionis.foundation.config.cache` and is materialised by
the application in `config/cache.py` (`BootstrapCache`).

| Entity | Fields | Environment variables |
|---|---|---|
| `Cache` | `default: Drivers \| str`, `prefix: str`, `stores: Stores \| dict` | `CACHE_STORE`, `CACHE_PREFIX` |
| `Stores` | `file`, `memory`, `redis`, `memcached`, `database` | — |
| `File` | `driver: str = "file"`, `path: str` | `CACHE_FILE_PATH` |
| `Memory` | `driver: str = "memory"` | — |
| `Redis` | `driver`, `endpoint`, `port`, `db`, `password` | `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD` |
| `Memcached` | `driver`, `endpoint`, `port` | `MEMCACHED_HOST`, `MEMCACHED_PORT` |
| `Database` | `driver`, `connection`, `table`, `lock_table` | `DB_CACHE_CONNECTION`, `DB_CACHE_TABLE`, `DB_CACHE_LOCK_TABLE` |

`Drivers` is a `StrEnum` with `FILE`, `MEMCACHED`, `MEMORY`, `REDIS` and
`DATABASE`. `Cache.__post_init__` validates `default` against those names
(case-insensitive, trimmed) and normalises it to the canonical lowercase value;
an unknown name raises `ValueError`, a wrong type raises `TypeError`.

Notes verified in the entities:

- In `Stores`, only `file` has a non-`None` default; `memory`, `redis`,
  `memcached` and `database` default to `None`, which is exactly the condition
  that makes `CacheManager` raise `CacheStoreException`.
- `Cache.prefix` defaults to `"orionis"`, but the application's
  `BootstrapCache` overrides that default with `Env.get("CACHE_PREFIX", "")`.
- `File.__post_init__` creates the configured directory as a side effect of
  building the entity.
- `Database.table` and `Database.lock_table` are validated against the pattern
  `[a-z_]+`.

## Usage examples

Every snippet below was executed against this repository.

### 1. Read and write through the resolved manager

```python
import asyncio

from bootstrap.app import app
from orionis.cache.contracts.cache_manager import ICacheManager


async def main() -> None:
    manager: ICacheManager = await app.make(ICacheManager)
    repository = manager.store("memory")

    await repository.set("reports:daily", {"total": 42}, ttl=60)
    print(await repository.get("reports:daily"))
    print(await repository.has("reports:daily"))
    print(await repository.delete("reports:daily"))
    print(await repository.get("reports:daily"))


asyncio.run(main())
```

Output: `{'total': 42}`, `True`, `True`, `None`.

### 2. Compute on miss with `remember`

```python
import asyncio

from bootstrap.app import app
from orionis.cache.contracts.cache_manager import ICacheManager

calls: list[int] = []


async def expensive_query() -> list[dict]:
    calls.append(1)
    await asyncio.sleep(0.01)
    return [{"id": 1, "name": "Ada"}]


async def main() -> None:
    manager: ICacheManager = await app.make(ICacheManager)
    repository = manager.store("memory")

    print(await repository.remember("users:all", 300, expensive_query))
    print(await repository.remember("users:all", 300, expensive_query))
    print("resolver calls:", len(calls))

    print(await repository.rememberForever("app:name", lambda: "Orionis"))
    print(await repository.pull("app:name"))
    print(await repository.get("app:name"))


asyncio.run(main())
```

The resolver runs once (`resolver calls: 1`); `pull` returns `"Orionis"` and the
following `get` returns `None`.

### 3. Mutual exclusion with `lock`

```python
import asyncio

from bootstrap.app import app
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.cache.contracts.repository import ICacheRepository


async def charge(repository: ICacheRepository, tag: str) -> None:
    async with repository.lock("billing:run", timeout=5):
        counter = await repository.increment("billing:runs")
        await asyncio.sleep(0.01)
        print(tag, "->", counter)


async def main() -> None:
    manager: ICacheManager = await app.make(ICacheManager)
    repository = manager.store("file")
    await repository.delete("billing:runs")

    await asyncio.gather(charge(repository, "A"), charge(repository, "B"))
    print("final:", await repository.get("billing:runs"))
    await repository.delete("billing:runs")


asyncio.run(main())
```

The two tasks never overlap: `A -> 1`, `B -> 2`, `final: 2`.

### 4. Error handling

```python
import asyncio

from bootstrap.app import app
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.cache.exceptions import CacheStoreException


async def main() -> None:
    manager: ICacheManager = await app.make(ICacheManager)

    # store() raises CacheStoreException when 'redis', 'memcached' or
    # 'database' is requested but absent from config/cache.py.
    try:
        repository = manager.store("memory")
    except CacheStoreException as exc:
        print("cache store unavailable:", exc)
        return

    # add() reports the conflict as False instead of raising.
    print(await repository.add("flag:once", value=True))
    print(await repository.add("flag:once", value=True))
    await repository.delete("flag:once")


asyncio.run(main())
```

Output: `True` then `False`.

### 5. Standalone repository without the container

```python
import asyncio

from orionis.cache.repository import CacheRepository
from orionis.cache.stores.memory import build as build_memory


async def main() -> None:
    repository = CacheRepository(backend=build_memory(), prefix="orionis")

    await repository.setMany({"a": 1, "b": 2}, ttl=30)
    print(await repository.getMany(["a", "b", "missing"]))
    print(await repository.pull("a"))
    print(await repository.get("a"))
    print(await repository.clear())


asyncio.run(main())
```

Output: `{'a': 1, 'b': 2, 'missing': None}`, `1`, `None`, `True`. The backend
receives the keys `orionis:a` and `orionis:b`.

### 6. Framework integration: controller

```python
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.http import HttpResponse, response


class DashboardController:
    async def index(self, cache: ICacheManager) -> HttpResponse:
        metrics = await cache.remember(
            "dashboard:metrics",
            300,
            self.__buildMetrics,
        )
        return response.json(metrics)

    async def __buildMetrics(self) -> dict:
        return {"users": 1, "orders": 0}
```

The container injects `ICacheManager` from the type annotation, so the
controller never depends on the facade's pin state.

### 7. `Serializer` and `FileBasedCache`

```python
import datetime
import decimal
import uuid
from pathlib import Path

from orionis.cache.file_based_cache import FileBasedCache
from orionis.cache.serializer import Serializer

payload = {
    "generated_at": datetime.datetime(2026, 1, 2, 3, 4, 5),
    "amount": decimal.Decimal("10.25"),
    "batch": uuid.UUID("12345678-1234-5678-1234-567812345678"),
    "tags": {"reports", "daily"},
}

restored = Serializer.loads(Serializer.dumps(payload))
print(restored == payload)

cache = FileBasedCache(
    path=Path("storage/framework/cache"),
    filename="docs-example.cache",
    monitored_dirs=[Path("config")],
)
version, sources_hash = cache.save({"commands": ["make:command"]})
print(version, len(sources_hash))
print(cache.get())
print(cache.clear())
```

Output: `True`, `1 40`, `{'commands': ['make:command']}`, `True`. Touching any
file under `config/` invalidates the entry, so the next `get()` returns `None`.

## Performance and concurrency

- The whole application-cache API is `async`. `CacheRepository.lock()` and
  `CacheManager.store()`/`lock()` are the only synchronous methods.
- `FileCacheBackend` moves every filesystem operation to `asyncio.to_thread`,
  so JSON decoding of a cache entry happens in the worker thread and not on the
  event loop.
- `FileCacheBackend` expiries are `time.monotonic()` deadlines, while
  `DatabaseCacheBackend` uses `time.time()`. Only the database driver stores an
  absolute wall-clock timestamp.
- `FileCacheBackend.__writeSync` stages every write in a unique sibling file, so
  two concurrent writers of the same key never share a staging file and the
  published entry is always one complete payload.
- `FileCacheBackend.add()` creates the entry with an exclusive open, so
  concurrent callers cannot both succeed, and `increment()` runs its
  read-modify-write inside an instance-level `asyncio.Lock`, so interleaved
  tasks on the same loop never lose an update. Neither guarantee extends across
  processes for `increment()`; `add()` stays exclusive because the exclusive
  creation is enforced by the operating system.
- `DatabaseCacheBackend.add()` relies on the primary key to elect a single
  winner, and `increment()` retries a compare-and-swap up to `25` times before
  raising `QueryException`, so both are safe under concurrency.
- `DatabaseCacheBackend._ensureSchema()` is guarded by an `asyncio.Lock` with a
  double-checked `_ready` flag, so the two `CREATE TABLE` statements run once
  per instance.
- `CacheLock` on a file backend uses `_FILE_LOCKS`, a module-level dict of
  `asyncio.Lock`. It coordinates tasks inside a single event loop only, and
  entries are never evicted, so the dict grows with the number of distinct
  locked keys.
- `CacheLock` on a database backend polls every `0.05 s`. Row-based locks are
  not FIFO: waiters are not served in arrival order.
- `CacheManager.store()` contains no `await`, so within one event loop the
  memoisation check and the insertion cannot interleave; the memoised dictionary
  is not protected against concurrent access from multiple threads.
- `SimpleMemoryCache` keeps its data in an instance-level dict (aiocache
  `>=0.12.3`), and `CacheManager` memoises one repository per store name, so a
  process shares a single in-memory store per manager instance.
- `FileBasedCache.__computeSourcesHash` caches its result for `0.5 s` and stats
  every monitored file on a miss, so the cost grows with the size of the
  monitored tree.
- `Serializer.dumps` without `indent` and `MsgspecSerializer` both use
  `msgspec.json`, the fastest path available in the module; the indented variant
  falls back to the standard library encoder.

## Compatibility notes

- Requires Python `>=3.14` (`pyproject.toml`). The module uses `Self`
  (`CacheLock.__aenter__`), `X | None` unions and `hashlib.sha1(usedforsecurity=False)`.
- All dependencies are part of the base install: `aiocache[redis,memcached]`,
  `redis[hiredis]`, `msgspec`, `sqlalchemy[asyncio]`. No extra package is needed
  for the `memory`, `file`, `redis` or `memcached` drivers.
- The `database` driver additionally needs a database connection reachable
  through `ConnectionResolver`, plus whichever async driver that connection
  requires.
- The `database` driver creates its tables lazily. The repository also ships the
  migrations `m0000000002_create_cache_table.py` and
  `m0000000003_create_cache_locks_table.py`, which declare `expiration` as
  `double`; an existing database created before that change keeps its original
  column type until it is migrated again.
- On the `memory` driver, `increment()` stores a plain `int` in the aiocache
  backend, bypassing the serializer: `MsgspecSerializer.loads` returns
  non-bytes payloads unchanged so the counter stays readable with `get()` and
  `getMany()`.
- Values must survive a JSON round trip. The aiocache drivers encode with
  `MsgspecSerializer`, so `tuple`, `set` and `frozenset` come back as `list`
  and `bytes` come back as a base64 `str`; the richer type-tagged encoding of
  `Serializer` applies only to `FileBasedCache`.
- `FileCacheBackend` writes one file per key inside a flat directory, and
  `clear()` removes every `*.json` and `*.tmp` in it, including files written by
  another `FileCacheBackend` pointed at the same path.
