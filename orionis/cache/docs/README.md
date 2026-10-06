# orionis.cache

> Provide async key/value repositories and locks, plus synchronous typed artifact caching.

Spanish version: [README.es.md](README.es.md).

## Table of contents

- [Requirements](#requirements)
- [Functional overview](#functional-overview)
- [Module structure](#module-structure)
- [API reference](#api-reference)
- [Usage examples](#usage-examples)
- [Design characteristics](#design-characteristics)
- [Performance and concurrency](#performance-and-concurrency)
- [Compatibility notes](#compatibility-notes)
- [Verification and limitations](#verification-and-limitations)

## Requirements

The framework installation includes the dependencies used by the module.
Redis and Memcached still require reachable services for data operations;
constructing their backends is not a connectivity check. Database caching
requires an Orionis `IConnection` and its async driver. SQLite is available
through the base installation; other database drivers follow the project's
extras. See [../../../pyproject.toml](../../../pyproject.toml) and
[Compatibility notes](#compatibility-notes).

For `CacheManager`, supply an application exposing `basePath` and
`config("cache")`. The manager converts a dictionary to the framework's cache
configuration entity; a non-dictionary is used directly and must expose
`default`, `prefix`, and `stores`. There is no fallback for a missing section
returning `None`. Construction captures the configuration and prefix;
subsequent application configuration changes do not rebuild cached stores.
Evidence: [../cache_manager.py](../cache_manager.py), `CacheManager.__init__`
and `store`.

### Configuration and resources

These are dependencies of the module, not additional `orionis.cache` exports:

| Configuration | Implemented settings | Evidence |
| --- | --- | --- |
| `Cache` | `default` is normalized to a supported driver; `prefix` must be a string; `stores` accepts `Stores` or a dictionary. Defaults read `CACHE_STORE` and `CACHE_PREFIX`. | [../../foundation/config/cache/entities/cache.py](../../foundation/config/cache/entities/cache.py) |
| `Stores` | Fixed fields `file`, `memory`, `redis`, `memcached`, `database`; all have entity factories. Optional fields may explicitly be `None`. | [../../foundation/config/cache/entities/stores.py](../../foundation/config/cache/entities/stores.py) |
| `File` | Nonempty string path from `CACHE_FILE_PATH`, default `storage/framework/cache/data`. Entity validation does not create directories. | [../../foundation/config/cache/entities/file.py](../../foundation/config/cache/entities/file.py) |
| `Redis` | `endpoint`, `port`, `db`, `password`, reading `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`; port is 1 through 65535 and db is nonnegative. | [../../foundation/config/cache/entities/redis.py](../../foundation/config/cache/entities/redis.py) |
| `Memcached` | `endpoint`, `port`, reading `MEMCACHED_HOST`, `MEMCACHED_PORT`; port is 1 through 65535. | [../../foundation/config/cache/entities/memcached.py](../../foundation/config/cache/entities/memcached.py) |
| `Database` | One connection for entries and locks; `connection`, `table`, `lock_table` read `DB_CACHE_CONNECTION`, `DB_CACHE_TABLE`, `DB_CACHE_LOCK_TABLE`. Entity table names must match `[a-z_]+`. | [../../foundation/config/cache/entities/database.py](../../foundation/config/cache/entities/database.py); [../stores/database.py](../stores/database.py) |

The manager selects a backend by the requested store name, not by an arbitrary
named-store registry or a configurable factory. Recognized names are exactly
`memory`, `file`, `redis`, `memcached`, and `database`. An unknown name raises
`CacheStoreException`; a missing Redis, Memcached, or database configuration
also raises it. Memory construction does not consult `stores.memory`.
Relative file paths are joined to `app.basePath`; `FileCacheBackend` resolves
them canonically and creates the directory. Evidence:
[../cache_manager.py](../cache_manager.py), `CacheManager._buildBackend`.

**Docstring discrepancies:** `Stores` describes some defaults as `None`, but
its field factories instantiate their entities. `Database` mentions an
independent connection for locks, but the backend uses the same `_connection`
for both tables. The behaviors described here follow the field declarations
and invoked code, not those descriptions.

Use backend-owned temporary directories for isolated checks: `clear()` is
not limited to a repository's prefix. Database operations create tables on
first use and execute SQL against the supplied connection. Direct database
backend construction does not validate or quote table identifiers; pass
trusted names appropriate for the connection. The raw SQL uses those names
literally, while table creation is delegated to `IConnection.createTable`.
The examples use an empty connection prefix and simple SQLite table names.
Evidence: [../stores/file.py](../stores/file.py), `FileCacheBackend.clear`,
and [../stores/database.py](../stores/database.py), `DatabaseCacheBackend`.

## Functional overview

`CacheManager` resolves and retains named backends; `CacheRepository` adds key
prefixes, batch helpers, conditional operations, and callback-based caching.
`CacheLock` supplies backend-dependent async context managers. Separately,
`FileBasedCache` and `Serializer` persist typed artifacts synchronously and
validate them against monitored source-file metadata.

The implementation paths are [../cache_manager.py](../cache_manager.py),
[../repository.py](../repository.py), [../locks/lock.py](../locks/lock.py),
[../file_based_cache.py](../file_based_cache.py), and
[../serializer.py](../serializer.py).

### Framework integration

`CacheProvider` declares `ICacheManager` as a deferrable service and binds it
to a singleton `CacheManager`. Its boot method pins the external `Cache`
facade. It is listed in core provider metadata. Evidence:
[../provider.py](../provider.py), `CacheProvider`, and
[../../foundation/core_providers.py](../../foundation/core_providers.py),
`CORE_PROVIDER_METADATA`.

The facade is `orionis.support.facades.cache.Cache`, not an export of this
module. Before pinning, a call produces a deferred dispatcher; awaiting it
resolves the manager and its deferred provider. After pinning, synchronous
methods such as `store` return their objects directly and must not be awaited.
Async methods still require await. `async with Cache.lock(...)` works through
the deferred context-manager protocol or the pinned direct object. Evidence:
[../../support/facades/cache.py](../../support/facades/cache.py),
`Cache.getFacadeAccessor`, and
[../../container/facades/meta.py](../../container/facades/meta.py),
`FacadeMeta.__getattr__` and `_FacadeDispatch`.

`CacheSessionStore` selects a repository through `cache.store(store)` and
uses `replace` when updating a live session, without recreating a deleted
entry. This directly explains the repository's replacement contract.
Evidence: [../../session/stores/cache.py](../../session/stores/cache.py),
`CacheSessionStore.__init__` and `update`.

## Module structure

All 21 Python files were inspected recursively. There is no referenced
non-Python runtime resource inside this module.

| Source | Responsibility and public symbols |
| --- | --- |
| [../__init__.py](../__init__.py) | Lazy exports `CacheManager`, `CacheRepository`, `FileBasedCache`; package `__getattr__`, `__dir__`, and `__all__`. |
| [../cache_manager.py](../cache_manager.py) | `CacheManager`: resolution and default-store proxies. |
| [../repository.py](../repository.py) | `CacheRepository`: prefixed application-cache API. |
| [../exceptions.py](../exceptions.py) | `CacheException`, `CacheStoreException`. |
| [../provider.py](../provider.py) | `CacheProvider`: singleton binding and facade pin. |
| [../file_based_cache.py](../file_based_cache.py) | `FileBasedCache` and `CACHE_VERSION`: synchronous artifacts. |
| [../serializer.py](../serializer.py) | `Serializer`: tagged JSON and file persistence. |
| [../contracts/__init__.py](../contracts/__init__.py) | Reexports three interfaces and declares `__all__`. |
| [../contracts/cache_manager.py](../contracts/cache_manager.py) | `ICacheManager`: manager contract. |
| [../contracts/repository.py](../contracts/repository.py) | `ICacheRepository`: repository contract, including `replace`. |
| [../contracts/file_based_cache.py](../contracts/file_based_cache.py) | `IFileBasedCache`: artifact contract. |
| [../locks/lock.py](../locks/lock.py) | `CacheLock`: file-loop, database-row, or RedLock context. |
| [../serializers/json.py](../serializers/json.py) | `MsgspecSerializer` and `DEFAULT_ENCODING`. |
| [../stores/file.py](../stores/file.py) | `FileCacheBackend`, `lockNamespace`, bulk-operation aliases. |
| [../stores/database.py](../stores/database.py) | `DatabaseCacheBackend`, `build`, bulk-operation aliases. |
| [../stores/memory.py](../stores/memory.py) | `build`: aiocache memory backend. |
| [../stores/redis.py](../stores/redis.py) | `build`: aiocache Redis backend with RESP2. |
| [../stores/memcached.py](../stores/memcached.py) | `build`: aiocache Memcached backend. |
| [../locks/__init__.py](../locks/__init__.py), [../serializers/__init__.py](../serializers/__init__.py), [../stores/__init__.py](../stores/__init__.py) | Empty initializers; no explicit symbol reexports. |

## API reference

Declaration blocks contain literal source headers without implementation
bodies. They are reference fragments, not complete scripts. Constructors
return `None`; ordinary class construction produces the new instance.
The runnable scripts are confined to [Usage examples](#usage-examples).

### Public imports and package behavior

| Symbol | Import location |
| --- | --- |
| `CacheManager`, `CacheRepository`, `FileBasedCache` | `orionis.cache` or their defining modules listed above. |
| `ICacheManager`, `ICacheRepository`, `IFileBasedCache` | `orionis.cache.contracts` or their defining contract modules. |
| `CacheException`, `CacheStoreException` | `orionis.cache.exceptions`. |
| `CacheProvider` | `orionis.cache.provider`. |
| `CacheLock` | `orionis.cache.locks.lock`. |
| `Serializer` | `orionis.cache.serializer`. |
| `MsgspecSerializer` | `orionis.cache.serializers.json`. |
| `FileCacheBackend` | `orionis.cache.stores.file`. |
| `DatabaseCacheBackend` | `orionis.cache.stores.database`. |
| Each `build` function | Its own `orionis.cache.stores.memory`, `.redis`, `.memcached`, or `.database` module. |

Both public `__all__` lists contain three strings. The root list is
`["CacheManager", "CacheRepository", "FileBasedCache"]`; the contracts list
is `["ICacheManager", "ICacheRepository", "IFileBasedCache"]`.
Source: [../__init__.py](../__init__.py) and
[../contracts/__init__.py](../contracts/__init__.py).

```python
def __getattr__(name: str) -> object:
```

```python
def __dir__() -> list[str]:
```

The root package resolves declared exports through
`orionis._exports.resolve_export`, importing the defining module and caching
the value in package globals. Unknown requested exports raise `AttributeError`.
`__dir__` returns sorted loaded names plus declared exports; it does not
resolve them. Importing only the package is distinct from requesting a class.
Evidence: [../__init__.py](../__init__.py) and
[../../_exports.py](../../_exports.py), `resolve_export`.

Private helpers, private sentinels, codec dispatch tables, and imported
dependencies are not additional public cache APIs. The four `build` names
are documented separately, not as a single interchangeable root function.
No public iterator protocol, enum, or standalone type alias is declared in
the 21 module files. Configuration entities and the facade remain external
integrations rather than extra root exports.

### CacheRepository

Import `orionis.cache.repository.CacheRepository` or the root reexport.
Source for every member below: [../repository.py](../repository.py),
`CacheRepository`. Implements `ICacheRepository`.

```python
class CacheRepository(ICacheRepository):
```

```python
def __init__(self, backend: Any, prefix: str = "") -> None:
```

`backend` is retained without protocol validation or ownership transfer.
`prefix` defaults to the empty string. A truthy prefix transforms each key
to `f"{prefix}:{key}"`; otherwise the raw key is forwarded. There is no
escaping or repository-level key validation. Keep prefixes and keys distinct
enough to avoid constructing the same final string. The constructor performs
no backend I/O; it has no close method and does not close supplied resources.

```python
async def replace(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def get(self, key: str) -> Any:
```

```python
async def set(
    self,
    key: str,
    value: Any,
    ttl: float | None = None,
) -> bool:
```

```python
async def has(self, key: str) -> bool:
```

```python
async def delete(self, key: str) -> bool:
```

```python
async def clear(self) -> bool:
```

```python
async def getMany(self, keys: list[str]) -> dict[str, Any]:
```

```python
async def setMany(
    self,
    values: dict[str, Any],
    ttl: float | None = None,
) -> bool:
```

```python
async def remember(
    self,
    key: str,
    ttl: float | None,
    resolver: Callable,
) -> Any:
```

```python
async def rememberForever(self, key: str, resolver: Callable) -> Any:
```

```python
async def pull(self, key: str) -> Any:
```

```python
async def add(
    self,
    key: str,
    value: Any,
    ttl: float | None = None,
) -> bool:
```

```python
async def increment(self, key: str, amount: int = 1) -> int:
```

```python
async def decrement(self, key: str, amount: int = 1) -> int:
```

```python
def lock(self, key: str, timeout: float | None = None) -> CacheLock:
```

| Operation | Parameters, awaited result, and effects |
| --- | --- |
| `get(key)` | Read the prefixed `str` key; return the backend value, normally `None` when absent. A stored `None` is indistinguishable through this method alone. |
| `set(key, value, ttl=None)` | Forward `value: Any` and `ttl: float | None`; coerce the backend result to `bool`. Values must meet backend serialization requirements. TTL behavior is backend-specific. |
| `replace(key, value, ttl=None)` | Replace a live existing entry, returning `bool`. Prefer a backend's callable `replace`; otherwise require `aiocache.BaseCache` and use `OptimisticLock`. Missing tokens and CAS conflicts return `False`. Unsupported custom backends raise `CacheStoreException`. |
| `has(key)` | Call backend `exists`, not `get`; coerce to `bool`. |
| `delete(key)` | Delete the prefixed key and coerce the backend count/result to `bool`. |
| `clear()` | Flush the whole backend, not only this prefix, and coerce its result to `bool`. |
| `getMany(keys)` | Materialize prefixed keys, call `multi_get`, then build `dict(zip(keys, values, strict=True))`. Original keys are returned; duplicate keys collapse in the dictionary. A mismatched result count raises `ValueError`. An empty input normally returns `{}`. |
| `setMany(values, ttl=None)` | Materialize prefixed `(key, value)` pairs from `dict[str, Any]`, forward to `multi_set`, return `bool`. No repository-level transaction is added. |
| `remember(key, ttl, resolver)` | `ttl` and a zero-argument `Callable` are required. Read with a private missing sentinel; on a miss invoke the resolver on the caller's loop, await an awaitable result, store it, then return it. A synchronous resolver is not offloaded. |
| `rememberForever(key, resolver)` | Delegate to `remember(key, None, resolver)`. No separate cache or invalidation policy is added. |
| `pull(key)` | Read with the sentinel, then delete on a hit, returning the value; return `None` on a miss. These are separate awaited operations, not an atomic read-and-delete. |
| `add(key, value, ttl=None)` | Await backend `add` and return `True` if it completes. Catch any backend `ValueError` and return `False`, not only errors proven to mean a duplicate key. |
| `increment(key, amount=1)` | Forward `amount: int` unchanged to backend `increment`; return its integer result. No positive-only validation is enforced. |
| `decrement(key, amount=1)` | Forward `-amount` to backend `increment`; return its result. |
| `lock(key, timeout=None)` | Synchronously construct a `CacheLock` for the prefixed key; acquisition occurs only on async entry. Timeout semantics differ by backend, as described below. |

Backend, codec, callback, and resource errors generally propagate. The
repository catches `OptimisticLockError` in its aiocache replacement path and
`ValueError` in `add`; it does not implement blanket cache-error translation.
`remember` is a check/read followed by callback and write without a lock;
concurrent misses can run the resolver repeatedly. Tests:
[../../../tests/cache/test_repository.py](../../../tests/cache/test_repository.py),
`TestCacheRepository` and `TestCacheRepositoryOnMemoryBackend`.

**Stored-None discrepancy:** the sentinel comment describes preserving
`None`, which file and database backends do. In inspected aiocache 0.12.3,
`BaseCache.get` returns its default whenever the decoded value is `None`.
Consequently `remember` resolves again, and `pull` returns `None` without
deleting that memory key. This was executed on the local memory, file, and
SQLite backends. Do not assume uniform null/miss behavior from the sentinel.
Evidence: [../repository.py](../repository.py), `remember` and `pull`, with
`aiocache.base.BaseCache.get` inspected in the validation environment.

### CacheManager

Import `orionis.cache.cache_manager.CacheManager` or the root reexport.
Source: [../cache_manager.py](../cache_manager.py), `CacheManager`.

```python
class CacheManager(ICacheManager):
```

```python
def __init__(self, app: IApplication) -> None:
```

```python
def store(self, name: str | None = None) -> CacheRepository:
```

The constructor's application requirements are listed above. `store`
resolves `name or self._default`, so `None` and `""` select the default.
It memoizes one repository/backend per resolved name for this manager's
lifetime. There is no public eviction, backend extension, or close method.
Failures during backend construction do not add a repository to the cache.
Unknown names are rejected rather than becoming a file store. Names passed
to `store` are not normalized like the configuration's `default` field.

The complete proxy declarations are literal source fragments:

```python
async def get(self, key: str) -> Any:
```

```python
async def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def has(self, key: str) -> bool:
```

```python
async def delete(self, key: str) -> bool:
```

```python
async def clear(self) -> bool:
```

```python
async def getMany(self, keys: list[str]) -> dict[str, Any]:
```

```python
async def setMany(
    self,
    values: dict[str, Any],
    ttl: float | None = None,
) -> bool:
```

```python
async def remember(
    self,
    key: str,
    ttl: float | None,
    resolver: Callable,
) -> Any:
```

```python
async def rememberForever(self, key: str, resolver: Callable) -> Any:
```

```python
async def pull(self, key: str) -> Any:
```

```python
async def add(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def increment(self, key: str, amount: int = 1) -> int:
```

```python
async def decrement(self, key: str, amount: int = 1) -> int:
```

```python
def lock(self, key: str, timeout: float | None = None) -> Any:
```

Every proxy uses `self.store()` and the identically named repository method.
Its parameter meanings, results, effects, and errors are those documented
for `CacheRepository`, plus first-use store resolution failures. The runtime
result of `lock` is a `CacheLock`, despite the declared `Any` annotation.
There is no `replace` proxy: call `manager.store().replace(...)` explicitly.
Tests: [../../../tests/cache/test_cache_manager.py](../../../tests/cache/test_cache_manager.py),
`TestCacheManager`.

### Contracts

All members below are `@abstractmethod` declarations with docstring-only
bodies, not executable default implementations. Direct or incomplete
subclass instantiation raises Python's `TypeError`. The ABC machinery does
not enforce runtime parameter types or override coroutine semantics.

#### ICacheRepository

Import `orionis.cache.contracts.repository.ICacheRepository` or the contracts
reexport. Source: [../contracts/repository.py](../contracts/repository.py).
The 14 operations declare the repository semantics above; `lock` is absent.
There is no explicit constructor; `__slots__ = ()` is declared.

```python
class ICacheRepository(ABC):
```

```python
@abstractmethod
async def replace(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
@abstractmethod
async def get(self, key: str) -> Any:
```

```python
@abstractmethod
async def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
@abstractmethod
async def has(self, key: str) -> bool:
```

```python
@abstractmethod
async def delete(self, key: str) -> bool:
```

```python
@abstractmethod
async def clear(self) -> bool:
```

```python
@abstractmethod
async def getMany(self, keys: list[str]) -> dict[str, Any]:
```

```python
@abstractmethod
async def setMany(
    self,
    values: dict[str, Any],
    ttl: float | None = None,
) -> bool:
```

```python
@abstractmethod
async def remember(
    self,
    key: str,
    ttl: float | None,
    resolver: Callable,
) -> Any:
```

```python
@abstractmethod
async def rememberForever(self, key: str, resolver: Callable) -> Any:
```

```python
@abstractmethod
async def pull(self, key: str) -> Any:
```

```python
@abstractmethod
async def add(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
@abstractmethod
async def increment(self, key: str, amount: int = 1) -> int:
```

```python
@abstractmethod
async def decrement(self, key: str, amount: int = 1) -> int:
```

#### ICacheManager

Import `orionis.cache.contracts.cache_manager.ICacheManager` or the contracts
reexport. Source: [../contracts/cache_manager.py](../contracts/cache_manager.py).
The 14 members are `store` and 13 default-store operations. Neither `lock`
nor `replace` is declared. There is no explicit constructor or `__slots__`.

```python
class ICacheManager(ABC):
```

```python
@abstractmethod
def store(self, name: str | None = None) -> ICacheRepository:
```

```python
@abstractmethod
async def get(self, key: str) -> Any:
```

```python
@abstractmethod
async def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
@abstractmethod
async def has(self, key: str) -> bool:
```

```python
@abstractmethod
async def delete(self, key: str) -> bool:
```

```python
@abstractmethod
async def clear(self) -> bool:
```

```python
@abstractmethod
async def getMany(self, keys: list[str]) -> dict[str, Any]:
```

```python
@abstractmethod
async def setMany(
    self,
    values: dict[str, Any],
    ttl: float | None = None,
) -> bool:
```

```python
@abstractmethod
async def remember(
    self,
    key: str,
    ttl: float | None,
    resolver: Callable,
) -> Any:
```

```python
@abstractmethod
async def rememberForever(self, key: str, resolver: Callable) -> Any:
```

```python
@abstractmethod
async def pull(self, key: str) -> Any:
```

```python
@abstractmethod
async def add(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
@abstractmethod
async def increment(self, key: str, amount: int = 1) -> int:
```

```python
@abstractmethod
async def decrement(self, key: str, amount: int = 1) -> int:
```

#### IFileBasedCache

Import `orionis.cache.contracts.file_based_cache.IFileBasedCache` or the
contracts reexport. Source:
[../contracts/file_based_cache.py](../contracts/file_based_cache.py).
Declares three synchronous artifact operations, with no constructor or slots.
`FileBasedCache` matches this surface but does not inherit this ABC.

```python
class IFileBasedCache(ABC):
```

```python
@abstractmethod
def get(self) -> dict | None:
```

```python
@abstractmethod
def save(self, data: dict) -> tuple[int, str]:
```

```python
@abstractmethod
def clear(self) -> bool:
```

### FileCacheBackend

Import `orionis.cache.stores.file.FileCacheBackend`. Source for all members:
[../stores/file.py](../stores/file.py), `FileCacheBackend`.

```python
class FileCacheBackend:
```

```python
def __init__(self, path: Path) -> None:
```

```python
@property
def lockNamespace(self) -> Path:
```

`path` is a required `Path`, resolved to an absolute canonical directory.
Construction creates it and allocates an asyncio counter lock, a thread
rename lock, and 64 `FileLock` objects with a 10-second acquisition timeout.
`lockNamespace` is a read-only property returning that canonical directory;
it has no setter/deleter. Filesystem/setup errors propagate. There is no
explicit backend close method.

Each `str` key is UTF-8 encoded, SHA-256 hashed, and stored as a flat
`<digest>.json` entry with `{"v": value, "e": deadline_or_none}`. Values use
`msgspec.json`, not the tagged `Serializer`. An explicit TTL, including zero,
sets `time.monotonic() + ttl`; `None` means no expiration. Expired entries are
removed during reads. Invalid JSON, non-dictionary entries, and read `OSError`
become misses; other malformed-field, lock, or deletion errors can propagate.

```python
async def get(self, key: str, default: Any = None) -> Any:
```

```python
async def replace(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def exists(self, key: str) -> bool:
```

```python
async def delete(self, key: str) -> int:
```

```python
async def clear(self) -> bool:
```

```python
async def multiGet(self, keys: list[str], default: Any = None) -> list[Any]:
```

```python
async def multiSet(
    self,
    pairs: list[tuple[str, Any]],
    ttl: float | None = None,
) -> bool:
```

```python
async def add(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def increment(self, key: str, delta: int = 1) -> int:
```

| Operation | Implemented result and effects |
| --- | --- |
| `get(key, default=None)` | Return entry value, including a stored `None`; use `default: Any` only for a missing/expired/invalid entry. Read and JSON decoding run in a worker. |
| `set(key, value, ttl=None)` | Publish a full JSON entry through a unique sibling staging file and rename; return `True`. Encoding/writing errors propagate. |
| `replace(key, value, ttl=None)` | Under the file's stripe lock, require a live readable entry, replace it with the new value and TTL, and return `True`; otherwise `False`. |
| `exists(key)` | Read with a sentinel and return `bool`; a live `None` value counts as present. |
| `delete(key)` | Unlink under the stripe lock; return `1` when removed and `0` when absent. An expired-but-unread file can still be deleted. |
| `clear()` | Remove all `*.json` and `*.tmp` in the directory, including other prefixes; return `True`. Stripe-lock files are not removed. No store-wide transaction is added. |
| `multiGet(keys, default=None)` | Sequential reads, returning `list[Any]` in input order, including duplicates; empty input gives `[]`. |
| `multiSet(pairs, ttl=None)` | Sequential writes of `list[tuple[str, Any]]`; duplicates overwrite in order. Empty input returns `True`; an error can leave preceding writes committed. |
| `add(key, value, ttl=None)` | Exclusive `open("xb")` under the stripe lock; retry once if reading the existing slot finds it expired/absent. Return `True`, or raise `ValueError` if creation still loses. Corrupt existing files need not be removed by the read path. |
| `increment(key, delta=1)` | Serialize through the instance's asyncio lock and the file's stripe lock, compute `int(current_value or 0) + delta`, preserve a live entry's expiry, and return the new value. Missing/expired entries start without expiry. Conversion/encoding errors propagate. |

The literal aliases `multi_get = multiGet` and `multi_set = multiSet` expose
the same coroutine methods, not wrappers with distinct signatures.
No direct `decrement` method is declared; the repository negates its amount.
Source/tests: [../stores/file.py](../stores/file.py) and
[../../../tests/cache/test_stores_file.py](../../../tests/cache/test_stores_file.py).

Reads, writes, exclusive creation, replacement, and deletion select a stripe
using `crc32(file.name.encode()) % 64`. Staged writes use random unique names;
publication retries `PermissionError` up to three attempts with 0.005-second
backoff under an instance thread lock. Failed `OSError` writes try to remove
their own staging file before re-raising. These mechanisms coordinate actual
file operations; they are separate from the user-facing `CacheLock`.

### DatabaseCacheBackend

Import `orionis.cache.stores.database.DatabaseCacheBackend`. Source:
[../stores/database.py](../stores/database.py), `DatabaseCacheBackend`.

```python
class DatabaseCacheBackend:
```

```python
def __init__(
    self,
    connection: IConnection,
    table: str,
    lock_table: str | None = None,
) -> None:
```

`connection` and entry `table` are required and retained. A falsey
`lock_table`, including `None` or `""`, selects `"cache_locks"`. Construction
does not perform SQL. First-use `_ensureSchema` creates both tables under
an instance asyncio lock; it marks readiness only after both calls succeed.
The backend neither closes the supplied connection nor migrates an existing
table schema.

| Table | Columns built by the inspected helpers |
| --- | --- |
| Entries | `cache_key`: `String(255).primary()`; `cache_value`: nullable `Text`; `expiration`: nullable `Double`. |
| Locks | `cache_key`: `String(255).primary()`; `owner`: nullable `String(255)`; `expiration`: nullable `Double`. |

Private `_build_entries_table` and `_build_locks_table` are schema helpers,
not additional public factories. Entry/lock expiry uses `time.time()` epoch
seconds, retaining fractional TTLs. JSON payloads are stored as strings.
An invalid JSON payload decodes to `None`; that is still an existing row for
the sentinel-based existence check. Expiry reads use SELECT followed by
DELETE, not an atomic read-and-evict operation.

```python
async def get(self, key: str, default: Any = None) -> Any:
```

```python
async def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def replace(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def exists(self, key: str) -> bool:
```

```python
async def delete(self, key: str) -> int:
```

```python
async def clear(self) -> bool:
```

```python
async def multiGet(self, keys: list[str], default: Any = None) -> list[Any]:
```

```python
async def multiSet(
    self,
    pairs: list[tuple[str, Any]],
    ttl: float | None = None,
) -> bool:
```

```python
async def add(self, key: str, value: Any, ttl: float | None = None) -> bool:
```

```python
async def increment(self, key: str, delta: int = 1) -> int:
```

```python
async def acquireLock(self, key: str, owner: str, lease: float) -> bool:
```

```python
async def releaseLock(self, key: str, owner: str) -> None:
```

| Operation | Implemented result and effects |
| --- | --- |
| `get(key, default=None)` | SELECT a row; return `default` on absence/expiry, otherwise its decoded payload, including `None`. Expired rows trigger a separate delete. |
| `set(key, value, ttl=None)` | Encode value, UPDATE, then INSERT if no row changed. A caught insert `QueryException` retries UPDATE. Return `True` after completion; this is not a single database-native upsert statement. |
| `replace(key, value, ttl=None)` | One conditional UPDATE requiring existing and unexpired data; set the new value/expiry and return `affected > 0`. It does not create a missing row. |
| `exists(key)` | Use the sentinel-based `get` check; a present `None` or invalid decoded payload counts as an existing row. |
| `delete(key)` | DELETE the key, returning the connection's affected-row count. |
| `clear()` | DELETE every entry-table row and return `True`; it does not clear the lock table or filter prefixes. |
| `multiGet(keys, default=None)` | Sequential single-key reads in input order, returning a list; empty input gives `[]`. |
| `multiSet(pairs, ttl=None)` | Sequential writes; duplicate keys overwrite and partial completion is possible on error. Return `True`, including for an empty input. |
| `add(key, value, ttl=None)` | Delete an expired slot, then INSERT. On `QueryException`, check whether the key exists: raise `ValueError` from that error if taken, otherwise re-raise the query error. |
| `increment(key, delta=1)` | Up to 25 read/CAS rounds; create through `add` when missing/expired, otherwise compute `int(decoded_value or 0) + delta` and UPDATE where the old JSON payload matches. Existing expiry is not updated. Return the new value or raise `QueryException` after exhausted contention. |
| `acquireLock(key, owner, lease)` | One attempt: INSERT a lock row, or on query failure conditionally UPDATE an expired or same-owner row. Return `bool`; positive lease validation is not added here. Same-owner acquisition refreshes expiry. |
| `releaseLock(key, owner)` | DELETE only the matching owner row; return `None`. It does not independently bootstrap the schema. |

`multi_get = multiGet` and `multi_set = multiSet` are literal aliases.
Connection errors, codec errors, and integer-conversion errors may propagate
in addition to explicit duplicate/contended-operation exceptions. A CAS is
based on the old payload, not a version column or a guaranteed FIFO policy.
Tests: [../../../tests/cache/test_stores_database.py](../../../tests/cache/test_stores_database.py),
`TestDatabaseCacheBackend` and `TestDatabaseCacheBackendConcurrency`.

### Backend factories

Each is a module-level public function with its own import path. None adds a
repository prefix, retries connectivity, or owns an application lifecycle.

#### Memory

Import `orionis.cache.stores.memory.build`. Source:
[../stores/memory.py](../stores/memory.py).

```python
def build() -> SimpleMemoryCache:
```

Construct a fresh `aiocache.SimpleMemoryCache(serializer=MsgspecSerializer())`.
Each instance has its own data dictionary; it is not a shared process-global
cache. The inherited backend API and close behavior belong to aiocache,
not newly declared Orionis methods.

#### Redis

Import `orionis.cache.stores.redis.build`. Source:
[../stores/redis.py](../stores/redis.py).

```python
def build(
    endpoint: str = "127.0.0.1",
    port: int = 6379,
    db: int = 0,
    password: str | None = None,
) -> RedisCache:
```

Construct `RedisCache` with the supplied endpoint, integer-coerced port/db,
`password or None`, `MsgspecSerializer`, and
`connection_pool_kwargs={"protocol": 2}`. Defaults are literal constructor
arguments, not values read from environment by this function. The manager
passes entity settings separately. Data operations require a Redis service;
backend/network/coercion errors are not converted by this factory.

#### Memcached

Import `orionis.cache.stores.memcached.build`. Source:
[../stores/memcached.py](../stores/memcached.py).

```python
def build(
    endpoint: str = "127.0.0.1",
    port: int = 11211,
) -> MemcachedCache:
```

Construct `MemcachedCache` with the endpoint, integer-coerced port, and
`MsgspecSerializer`. Data operations require Memcached. Annotations do not
override the client's actual key, TTL, or protocol restrictions; the factory
does not catch coercion, dependency, or network errors.

#### Database

Import `orionis.cache.stores.database.build`. Source:
[../stores/database.py](../stores/database.py), `build`.

```python
def build(
    connection: IConnection,
    table: str,
    lock_table: str | None = None,
) -> DatabaseCacheBackend:
```

Delegate the required connection/table and optional lock table to the backend
constructor described above. No connection is resolved or opened by `build`
itself; the manager resolves `ConnectionResolver.connection(...)` before
calling it. Resolver failures propagate. Evidence:
[../../orm/resolver.py](../../orm/resolver.py), `ConnectionResolver.connection`,
and [../cache_manager.py](../cache_manager.py), `_buildDatabaseBackend`.

### CacheLock

Import `orionis.cache.locks.lock.CacheLock`. Source for all members:
[../locks/lock.py](../locks/lock.py), `CacheLock`.

```python
class CacheLock:
```

```python
def __init__(
    self,
    backend: Any,
    key: str,
    timeout: float | None = None,
) -> None:
```

```python
async def __aenter__(self) -> Self:
```

```python
async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: types.TracebackType | None,
) -> None:
```

Construction retains the raw backend, key, and timeout; it does not acquire
anything. Entry returns this `CacheLock` instance. Exit releases the selected
implementation and returns `None`, without suppressing the protected block's
exception. Backend/cleanup errors can propagate. Use one context object per
active acquisition: there is one `_impl`/`_owner` slot, not an acquisition
stack or reentrancy check.

| Backend | Acquisition, timeout, and release |
| --- | --- |
| `FileCacheBackend` | Look up an `asyncio.Lock` in a weak-value registry keyed by `(running_loop, canonical_directory, key)`. Await acquisition with `asyncio.wait_for` when timeout is not `None`; otherwise wait without a deadline. Timeout only limits acquisition, not the protected work. Exit releases and clears `_impl`. |
| `DatabaseCacheBackend` | Generate a UUID owner; attempt `acquireLock` and poll every 0.05 seconds after a failed attempt. Waiting deadline is `loop.time() + timeout` when specified; lease is `timeout or 10`. Exit awaits owner-checked release. No automatic lease renewal or FIFO guarantee is implemented. |
| Other backends | Delegate to `aiocache.lock.RedLock` with `lease=timeout or 10`; exit delegates to it. This is not the file-loop lock algorithm. |

`timeout` is not normalized or validated by this wrapper. `None`, zero,
negative, and positive values therefore follow each branch's actual
wait/lease behavior. For database entry the first acquisition is attempted
before testing the waiting deadline; a failed attempt can overshoot a tight
deadline by backend latency or the polling interval. Lease expiry can permit
a later owner while a previous protected block is still running.

File-user locks are local to the event loop/directory/key combination, not
cross-process locks. Their weak registry does not retain unused lock objects
once holders, waiters, and other strong references are gone. It is distinct
from file-operation stripe locks. Tests:
[../../../tests/cache/test_cache_lock.py](../../../tests/cache/test_cache_lock.py),
`TestCacheLock` and `TestDatabaseCacheLock`.

**RedLock limitation:** aiocache 0.12.3 documents that its single-instance
RedLock is not strict resource exclusion. Its wait path can proceed after
lease timeout, and does not reacquire the key after release notification.
A local memory probe entered a second context while the first still held
its key. Redis/Memcached deployment behavior was not executed here. Evidence:
[../locks/lock.py](../locks/lock.py), with `aiocache.lock.RedLock` inspected
and the memory case executed during validation.

For inspected aiocache 0.12.3, Memcached's lock release deletes the key
without atomically checking its owner. Its backend also maps spaces in keys
to underscores and encodes them as bytes. The memory/Redis/Memcached factories
retain aiocache's default operation timeout of five seconds. These are
dependency behaviors, not extra options exposed by the Orionis factories.
Evidence: the invoked `aiocache.backends.memcached.MemcachedBackend`,
`MemcachedCache._build_key`, and `aiocache.base.BaseCache.__init__`, inspected
locally; the factories are linked in their API sections.

### MsgspecSerializer

Import `orionis.cache.serializers.json.MsgspecSerializer`. Source:
[../serializers/json.py](../serializers/json.py), `MsgspecSerializer`.

```python
class MsgspecSerializer(BaseSerializer):
```

```python
def dumps(self, value: Any) -> bytes:
```

```python
def loads(self, data: bytes | str | float | None) -> Any:
```

The public class constant is `DEFAULT_ENCODING = None`. There is no explicit
constructor; `aiocache.serializers.BaseSerializer.__init__` initializes
`encoding`, defaulting to that constant. `dumps` returns UTF-8 JSON bytes
from `msgspec.json.encode`. `loads` returns `None` for `None`, encodes strings
before JSON decoding, decodes `bytes`/`bytearray`/`memoryview`, and returns
other native values unchanged. The observed implementation accepts those
buffers beyond its literal declared union.

This passthrough keeps memory counters readable after aiocache's increment
path stores native integers without `dumps`. JSON does not preserve arbitrary
Python types: tuples/sets/frozensets become lists and bytes become base64 text.
Codec/encoding errors propagate; the serializer adds no exception translation
or per-instance decoded-value cache. Tests:
[../../../tests/cache/test_serializers_json.py](../../../tests/cache/test_serializers_json.py).

### Serializer

Import `orionis.cache.serializer.Serializer`. Source:
[../serializer.py](../serializer.py), `Serializer` and its private codecs.
This is the synchronous artifact codec, not the application-backend codec.

```python
class Serializer:
```

```python
@staticmethod
def dumps(data: Any, indent: int | None = None) -> str:
```

```python
@staticmethod
def loads(raw: str | bytes) -> Any:
```

```python
@staticmethod
def dumpToFile(data: Any, file_path: Path) -> None:
```

```python
@staticmethod
def loadFromFile(file_path: Path) -> Any:
```

| Operation | Parameters, result, and side effects |
| --- | --- |
| `dumps(data, indent=None)` | Recursively encode supported `Any` data. With `indent=None`, return compact msgspec JSON decoded to `str`; otherwise use `json.dumps(indent=indent, separators=(",", ":"))`. Unsupported values raise `TypeError`; recursive/cyclic graphs are not given cycle handling. |
| `loads(raw)` | Parse `str | bytes` JSON, recursively decode tags, and return the reconstructed value. Invalid JSON, malformed wrappers, unknown tags, or type resolution can raise codec errors, `ValueError`, `KeyError`, import errors, or attribute errors. |
| `dumpToFile(data, file_path)` | Encode data, write a random unique `.tmp` sibling, then `Path.replace` the target. Return `None`; no parent directory creation, stripe lock, fsync, or rename retry is added. On `OSError`, try to remove its staging file and re-raise. |
| `loadFromFile(file_path)` | Read bytes synchronously. Return `None` for any read `OSError` or empty content; otherwise decode. Corrupt nonempty JSON and malformed tagged data are not swallowed. |

Primitive scalars pass through; dictionaries and lists recursively encode
their values/elements. Supported tagged values are `Path`, bytes, datetime,
date, time, timedelta, `Decimal`, `UUID`, complex, tuple, set, frozenset,
class objects, enum members, and Orionis's `MISSING` sentinel. The reserved
wrapper keys are `__type__` and `__value__`; their tags are `path`, `bytes`,
`datetime`, `date`, `time`, `timedelta`, `decimal`, `uuid`, `complex`, `tuple`,
`set`, `frozenset`, `type`, `enum`, and `missing`.

Dictionary keys are not passed through the custom codec. Subclasses handled
through the collection/Path/datetime fallback need not keep their subclass
identity. Class/enum tags use module and qualified-name strings, then
`rpartition(".")`, module import, and `getattr`; arbitrary local or nested
classes are not guaranteed reconstructible. Enum values must themselves fit
the emitted representation.

A user dictionary containing `__type__` is interpreted as a tagged wrapper
during decoding, not automatically escaped. A reserved-tag collision was
executed and raised `ValueError`. Type/enum decoding can import modules and
construct enum values; do not treat it as an inert decoder for untrusted
payloads. Tests: [../../../tests/cache/test_serializer.py](../../../tests/cache/test_serializer.py),
`TestSerializer`.

### FileBasedCache

Import `orionis.cache.file_based_cache.FileBasedCache` or the root reexport.
Source: [../file_based_cache.py](../file_based_cache.py), `FileBasedCache`.

```python
class FileBasedCache:
```

```python
def __init__(
    self,
    path: Path,
    filename: str,
    monitored_dirs: list[Path] | None = None,
    monitored_files: list[Path] | None = None,
) -> None:
```

```python
def get(self) -> dict | None:
```

```python
def save(self, data: dict) -> tuple[int, str]:
```

```python
def clear(self) -> bool:
```

The public class constant is `CACHE_VERSION = 1`. Construction explicitly
requires `path` to be a `Path` or raises `TypeError`; it creates that
directory. `filename` is combined through `path / filename`, without a
containment check or filename validation. A supplied nonempty monitored
list is retained; falsey lists/`None` become new empty lists. Keep all paths
within the intended artifact tree.

`save(data)` requires a dictionary or raises `TypeError`. It writes
`{"__meta__": metadata, "__data__": data}` through `Serializer.dumpToFile`,
where metadata contains `version`, `generatedAt`, and `sourcesHash`.
If version, source hash, and existing data match, it skips writing.
It returns `(CACHE_VERSION, sources_hash)` in both paths.

`get()` reads through `Serializer.loadFromFile`, returning `None` for a
falsey payload, missing metadata, version mismatch, or source-hash mismatch;
otherwise it returns `payload.get("__data__")`. It does not enforce that
externally edited metadata/data have the annotated structure. Corrupt JSON,
invalid tagged values, and non-mapping payload structures can raise rather
than produce a miss. `clear()` returns `True` when the artifact was unlinked,
`False` only for `FileNotFoundError`; it does not reset the source-hash cache.

Source monitoring collects existing explicit files and recursively found
`*.py` files in monitored directories. It resolves paths, excludes the cache
file itself, deduplicates, sorts, and hashes each POSIX path plus packed
`st_mtime_ns`/`st_size` with SHA-1 (`usedforsecurity=False`). It does not hash
source contents or monitor all non-Python files in a directory. A change
preserving both metadata fields can therefore leave this hash unchanged.

The hash is cached per instance for 0.5 seconds using a monotonic clock.
Changes are not necessarily visible to immediate calls within that window;
a fresh instance recomputes without that retained hash. No public reset or
watcher is declared. Stat/traversal/codec/write errors can propagate.
Tests: [../../../tests/cache/test_file_based_cache.py](../../../tests/cache/test_file_based_cache.py),
`TestFileBasedCache`.

### CacheProvider

Import `orionis.cache.provider.CacheProvider`. Source:
[../provider.py](../provider.py), `CacheProvider`.

```python
class CacheProvider(ServiceProvider, DeferrableProvider):
```

```python
@classmethod
def provides(cls) -> list[type]:
```

```python
def register(self) -> None:
```

```python
async def boot(self) -> None:
```

There is no explicit constructor; it inherits `ServiceProvider.__init__`
which stores the supplied `IApplication` in `self.app`. Evidence:
[../../container/providers/service_provider.py](../../container/providers/service_provider.py).
`provides()` returns a new `[ICacheManager]` list. `register()` performs
`self.app.singleton(ICacheManager, CacheManager)` and returns `None`.
`boot()` awaits `CacheFacade.pin()` and returns `None`. Container/binding or
facade-resolution errors propagate; it does not implement backend teardown.
Registration and facade-state effects are distinct from data operations.

### Exceptions

Import both from `orionis.cache.exceptions`. Source:
[../exceptions.py](../exceptions.py).

```python
class CacheException(Exception):
```

```python
class CacheStoreException(CacheException):
```

Neither declares a constructor or extra state; they inherit standard
exception arguments and string behavior. `CacheException` is the cache
exception base, not a wrapper automatically applied to every dependency
error. `CacheStoreException` is explicitly raised for unknown/unconfigured
manager stores and unsupported repository replacement primitives. Actual
failure messages are produced at those call sites; upstream I/O, SQL, codec,
callback, or conversion failures generally retain their own types.
Tests: [../../../tests/cache/test_exceptions.py](../../../tests/cache/test_exceptions.py).

## Usage examples

Each block is a separate complete script for an installed local framework
and Python 3.14+. None uses a Redis/Memcached service, private credentials,
the checkout's bootstrap application, or shared application storage. Resources
are in memory or temporary directories. The verification table distinguishes
syntax, local imports, and execution.

### 1. Memory repository and JSON behavior

```python
import asyncio
from orionis.cache import CacheRepository
from orionis.cache.stores.memory import build

async def main() -> None:
    """Exercise prefixed values, batch operations, and counters."""
    backend = build()
    repository = CacheRepository(backend, prefix="example")
    try:
        assert await repository.set("payload", {"items": (1, 2), "raw": b"a"})
        assert await repository.get("payload") == {"items": [1, 2], "raw": "YQ=="}
        assert await repository.setMany({"a": 1, "b": 2})
        assert await repository.getMany(["a", "b", "absent"]) == {
            "a": 1, "b": 2, "absent": None,
        }
        assert await repository.getMany([]) == {}
        assert not await repository.replace("missing", "value")
        assert await repository.replace("a", 3)
        assert await repository.add("once", True)
        assert not await repository.add("once", False)
        assert await repository.increment("hits", 5) == 5
        assert await repository.decrement("hits", 2) == 3
        assert await repository.get("hits") == 3
        assert await repository.has("a")
        assert await repository.delete("a")
        assert not await repository.delete("a")
        assert await repository.clear()
    finally:
        await backend.close()

asyncio.run(main())
```

JSON-normalized values are returned, not the original tuple/bytes types.
Memory counters remain readable through the serializer's native passthrough.

### 2. Observe stored None across backends

```python
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.cache import CacheRepository
from orionis.cache.stores.file import FileCacheBackend
from orionis.cache.stores.memory import build

async def compare(backend: object) -> tuple[object, int, bool]:
    """Return the resolver outcome and null-key deletion behavior."""
    repository = CacheRepository(backend)
    calls: list[str] = []

    def resolve() -> str:
        """Record a cache miss and return a replacement value."""
        calls.append("resolved")
        return "replacement"

    await repository.set("null-value", None)
    result = await repository.remember("null-value", None, resolve)
    await repository.set("null-pull", None)
    assert await repository.pull("null-pull") is None
    return result, len(calls), await repository.has("null-pull")

async def main() -> None:
    """Compare memory with an isolated file backend."""
    memory = build()
    try:
        with TemporaryDirectory(prefix="orionis-cache-null-") as directory:
            file = FileCacheBackend(Path(directory))
            assert await compare(memory) == ("replacement", 1, True)
            assert await compare(file) == (None, 0, False)
    finally:
        await memory.close()

asyncio.run(main())
```

This intentionally asserts the implemented difference rather than assuming
that every backend treats `None` as a hit in `remember`/`pull`.

### 3. Manager selection and a real store error

```python
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from orionis.cache import CacheManager
from orionis.cache.exceptions import CacheStoreException

class Settings:
    """Supply the application surface consumed by CacheManager."""

    __slots__ = ("basePath",)

    def __init__(self, root: Path) -> None:
        """Retain a temporary base path."""
        self.basePath = root

    def config(self, section: str) -> SimpleNamespace:
        """Return the cache settings without booting an application."""
        assert section == "cache"
        return SimpleNamespace(
            default="memory", prefix="demo", stores=SimpleNamespace(),
        )

async def main() -> None:
    """Use default-store proxies and reject an unknown store."""
    with TemporaryDirectory(prefix="orionis-cache-manager-") as directory:
        root = Path(directory)
        manager = CacheManager(Settings(root))
        assert manager.store() is manager.store("") is manager.store("memory")
        try:
            manager.store("unknown")
        except CacheStoreException:
            assert list(root.iterdir()) == []
        else:
            error_msg = "Expected an unknown-store error"
            raise AssertionError(error_msg)
        assert await manager.set("value", 1)
        assert await manager.get("value") == 1
        assert await manager.store().replace("value", 2)
        assert await manager.get("value") == 2
        assert await manager.clear()

asyncio.run(main())
```

The small settings object supplies the exact runtime dependency surface;
this does not redefine `IApplication` or claim a container binding.

### 4. File locking and prefix-wide cleanup limits

```python
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.cache import CacheRepository
from orionis.cache.stores.file import FileCacheBackend

async def main() -> None:
    """Serialize local work and demonstrate backend-wide clear."""
    with TemporaryDirectory(prefix="orionis-cache-file-") as directory:
        backend = FileCacheBackend(Path(directory))
        left = CacheRepository(backend, prefix="left")
        right = CacheRepository(backend, prefix="right")
        assert backend.lockNamespace == Path(directory).resolve()
        state = {"inside": 0, "peak": 0}

        async def update() -> None:
            """Increment while holding the same loop-local user lock."""
            async with left.lock("workflow", timeout=5):
                state["inside"] += 1
                state["peak"] = max(state["peak"], state["inside"])
                await left.increment("count")
                state["inside"] -= 1

        await asyncio.gather(*(update() for index in range(6)))
        assert state["peak"] == 1
        assert await left.get("count") == 6
        await left.set("expired", "old", ttl=-1)
        assert not await left.has("expired")
        assert not await left.replace("expired", "late")
        await right.set("value", "other prefix")
        assert await left.clear()
        assert not await right.has("value")

asyncio.run(main())
```

The protected work is local to the same loop/path/key. `clear` removes the
other prefix's data because both repositories share a backend directory.

### 5. Database backend with a temporary SQLite connection

```python
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.cache import CacheRepository
from orionis.cache.stores.database import build
from orionis.database.connection import Connection

async def main() -> None:
    """Exercise cache rows and owned locks without an external database."""
    with TemporaryDirectory(prefix="orionis-cache-sqlite-") as directory:
        connection = Connection("example", {
            "driver": "sqlite",
            "database": str(Path(directory) / "cache.sqlite"),
            "prefix": "",
        })
        backend = build(connection, "cache", "cache_locks")
        repository = CacheRepository(backend, prefix="example")
        try:
            assert await repository.set("value", {"total": 1})
            assert await repository.replace("value", {"total": 2})
            assert await repository.get("value") == {"total": 2}
            assert await repository.setMany({"a": 1, "b": 2})
            assert await repository.getMany(["a", "b"]) == {"a": 1, "b": 2}
            assert await repository.increment("count", 3) == 3
            assert await repository.decrement("count") == 2
            assert await backend.acquireLock("owned", "first", lease=5)
            assert not await backend.acquireLock("owned", "second", lease=5)
            await backend.releaseLock("owned", "first")
            async with repository.lock("workflow", timeout=5):
                assert await repository.add("once", True)
                assert not await repository.add("once", False)
            await repository.set("expired", "value", ttl=-1)
            assert not await repository.replace("expired", "new")
            assert await repository.clear()
        finally:
            await connection.disconnect()

asyncio.run(main())
```

The first operation creates tables. The connection is closed before the
temporary directory is removed; no framework database migration is run.

### 6. Typed serialization and monitored artifacts

```python
from datetime import UTC, datetime
from decimal import Decimal
from http import HTTPStatus
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID
from orionis.cache import FileBasedCache
from orionis.cache.serializer import Serializer
from orionis.support.types.sentinel import MISSING

payload = {
    "created": datetime(2026, 1, 2, tzinfo=UTC),
    "amount": Decimal("10.25"),
    "identifier": UUID("12345678-1234-5678-1234-567812345678"),
    "path": Path("report.txt"),
    "values": (b"content", {"alpha", "beta"}),
    "status": HTTPStatus.OK,
    "class": Path,
    "missing": MISSING,
}
assert Serializer.loads(Serializer.dumps(payload)) == payload
assert Serializer.loads(Serializer.dumps(payload, indent=2)) == payload

with TemporaryDirectory(prefix="orionis-cache-artifact-") as directory:
    root = Path(directory)
    source = root / "source.py"
    source.write_text("value = 1\n", encoding="utf-8")
    artifact = FileBasedCache(root, "artifact.json", monitored_files=[source])
    version, source_hash = artifact.save(payload)
    assert version == FileBasedCache.CACHE_VERSION
    assert len(source_hash) == 40
    assert artifact.get() == payload
    assert artifact.save(payload) == (version, source_hash)
    source.write_text("value = 10000\n", encoding="utf-8")
    fresh = FileBasedCache(root, "artifact.json", monitored_files=[source])
    assert fresh.get() is None
    assert fresh.clear()
    assert not fresh.clear()
    standalone = root / "typed.json"
    Serializer.dumpToFile(payload, standalone)
    assert Serializer.loadFromFile(standalone) == payload
    assert Serializer.loadFromFile(root / "missing.json") is None
```

A fresh reader avoids the retained 0.5-second source-hash window. Typed
serialization is an artifact capability, not the application-cache codec.

### 7. Resolve the provider and facade in an isolated application

```python
import asyncio
import inspect
import os
from pathlib import Path
from tempfile import TemporaryDirectory

with TemporaryDirectory(prefix="orionis-cache-application-") as directory:
    original_cwd = Path.cwd()
    os.chdir(directory)
    try:
        from orionis import Application
        from orionis.cache.contracts import ICacheManager
        from orionis.support.facades.cache import Cache

        app = Application(base_path=Path(directory)).create()
        app.config("cache", {"default": "memory", "prefix": "example", "stores": {}})

        async def main() -> None:
            """Resolve a deferred store and use the now-pinned facade."""
            pending = Cache.store("memory")
            assert inspect.isawaitable(pending)
            repository = await pending
            manager = await app.make(ICacheManager)
            assert manager.store("memory") is repository
            assert Cache.store("memory") is repository
            assert await Cache.set("value", 7)
            assert await Cache.get("value") == 7
            assert await manager.store().replace("value", 8)
            assert await Cache.get("value") == 8
            assert await Cache.clear()

        asyncio.run(main())
    finally:
        Cache.unpin()
        os.chdir(original_cwd)
```

This exercises real deferred registration and facade pinning without loading
the checkout's bootstrap application. It is an independent process example,
not a recipe for constructing a second application inside an existing worker.

## Design characteristics

| Observed mechanism | Concrete consequence | Evidence |
| --- | --- | --- |
| Lazy root exports | Importing the package does not eagerly resolve its three public classes; resolved exports remain in package globals. | [../__init__.py](../__init__.py) |
| Singleton service binding | An application's resolved manager retains its backend/repository map and captured prefix for its lifetime. | [../provider.py](../provider.py); [../cache_manager.py](../cache_manager.py) |
| Backend composition rather than an enforced protocol | Direct repositories can use custom backend objects; missing methods/errors appear when invoked. | [../repository.py](../repository.py) |
| Slots and ABC inheritance | Repository, lock, file/database backend, and artifact instances are slotted. `CacheManager` still has an instance `__dict__` through its unslotted `ICacheManager` base, confirmed at runtime. | The corresponding classes and [../contracts/cache_manager.py](../contracts/cache_manager.py) |
| Separate JSON codecs | Application values use msgspec JSON normalization; tagged artifact values can reconstruct extra Python types. | [../serializers/json.py](../serializers/json.py); [../serializer.py](../serializer.py) |
| No shared backend close abstraction | A direct caller retains responsibility for clients/connections it owns; no manager/repository teardown API is declared. | [../cache_manager.py](../cache_manager.py); [../repository.py](../repository.py); [../stores/database.py](../stores/database.py) |

There is no dataclass-generated constructor, generator API, or public cache
enum in the target module. The configuration dataclasses and `Drivers` belong
to `orionis.foundation.config.cache`, not this public inventory.

## Performance and concurrency

- Manager store creation contains no await and memoizes by resolved name.
  It is not guarded by a thread lock; concurrent cross-thread first use has
  no module-declared single-construction guarantee.
- Repository batch helpers materialize prefixed lists/pairs and returned
  dictionaries. File/database batch methods are sequential, not transactional
  or parallel database batches. Errors may leave earlier writes completed.
- Ordinary application values cross JSON encoding/decoding boundaries;
  they are not a general reference-preserving object store. Memory counters
  are a documented native-value exception to the normal codec path.
- `remember` invokes a synchronous callback on the event-loop thread and does
  not lock a miss. `pull` and database expired-row reads split operations
  across awaits. Do not infer atomic compound operations from their names.
- File backend disk work and decoding are dispatched with `asyncio.to_thread`.
  Encoding happens in the worker paths for writes. Constructor directory
  resolution/creation is synchronous. Worker file-lock waits and rename
  backoff can occupy threads; async methods are not an allocation-free or
  resource-free guarantee.
- File-operation stripes are separate from loop-local user locks. Counter
  updates include both an instance asyncio lock and a file stripe lock;
  existing tests cover multiple backend instances sharing a directory.
  This does not certify every multi-process/platform failure scenario.
- Database schema readiness is per backend instance. Two successful creation
  calls mark it ready; first-use errors leave it unready for a later retry.
  There is no shared readiness cache across instances.
- Database `add` uses the primary-key conflict path; increments use at most
  25 compare-and-swap rounds and can fail on exhausted contention. Existing
  file-SQLite tests exercise concurrent operations, not every supported driver.
- User database/RedLock contexts are lease-based, without renewal. File-user
  locks use a weak registry scoped by loop, directory, and key. Redis/Memory/
  Memcached RedLock behavior must not be equated with the file algorithm.
- Artifact APIs perform synchronous recursive codec work, file reads/writes,
  directory traversal, path resolution, sorting, and stat calls. Source hashes
  are cached for 0.5 seconds per instance; no content hash or active watcher
  is implemented. Unique staging prevents sharing one temp name, but is not
  a store-wide transaction or a cross-platform durability certification.
- Cancellation has no module-specific shielding protocol. An already started
  file worker or backend operation is not forcibly stopped by these wrappers;
  retain resources until actual work has ended.

Evidence: [../cache_manager.py](../cache_manager.py), [../repository.py](../repository.py),
[../stores/file.py](../stores/file.py), [../stores/database.py](../stores/database.py),
[../locks/lock.py](../locks/lock.py), [../serializer.py](../serializer.py), and
[../file_based_cache.py](../file_based_cache.py), with the exact symbols
described in their API sections. No benchmarks were performed.

> ⚠️ Not specified in the source code: a module-wide cross-thread safety
> contract, nested reuse of one active `CacheLock`, or crash/power-loss
> durability of cache files. Individual locks and staging mechanisms do not
> establish those broader guarantees.

## Compatibility notes

The project declares Python `>=3.14` in
[../../../pyproject.toml](../../../pyproject.toml). Validation used the local
repository interpreter, Windows CPython **3.14.6**. Union annotations,
`typing.Self`, and strict zip are observable language features; their use
does not independently certify older Python releases. Several annotation-only
imports are under `TYPE_CHECKING`; do not assume unrestricted runtime
`get_type_hints` resolution. Examples target Python 3.14+.

| Dependency | Declared constraint | Lockfile | Installed for validation |
| --- | --- | --- | --- |
| `aiocache[redis,memcached]` | `>=0.12.3` | `0.12.3` | `0.12.3` |
| `redis[hiredis]` | `>=8.1.0` | `8.1.0` | `8.1.0` |
| `msgspec` | `>=0.21.1` | `0.22.0` | `0.22.0` |
| `filelock` | `>=4.0.1` | `4.0.8` | `4.0.8` |
| `sqlalchemy[asyncio]` | `>=2.0.54,<3.0` | `2.1.1` | `2.1.1` |
| `aiosqlite` | `>=0.22.1` | `0.22.1` | `0.22.1` |
| `aiomcache`, transitive aiocache extra | `>=0.5.2` in installed aiocache metadata | `0.8.2` | `0.8.2` |
| `ruff`, development-only | `>=0.16.8` | `0.16.9` | `0.16.9` |

Manifest/lock evidence: [../../../pyproject.toml](../../../pyproject.toml)
and [../../../uv.lock](../../../uv.lock); installed versions and aiocache's
extra requirements were queried during this task. A lockfile version is not
a minimum supported version. Third-party behavior observations above refer
to the inspected installed versions, not all releases accepted by the ranges.

TTL interpretation is not uniform. In the local memory backend, `ttl=0`
keeps an entry without scheduling expiry; in file/SQLite it immediately
expires on the next read. File deadlines use monotonic time; database
deadlines use wall-clock epoch time. Redis/Memcached constraints remain those
of their clients and services. An arbitrary float annotation does not prove
portable fractional TTL support on Memcached. Source: the backend factories,
[../stores/file.py](../stores/file.py), [../stores/database.py](../stores/database.py),
and inspected `aiocache.backends.memory.SimpleMemoryBackend._set`.

## Verification and limitations

### Inventory and tests

The inventory covers 21 Python files, 14 public classes, four module-specific
`build` functions, package attribute/directory hooks, all public methods and
the `lockNamespace` property: **124 literal declaration fragments**. It also
accounts for root/contracts reexports and `__all__`, two public class constants,
and four bulk-operation aliases. Imported names and private helpers/state are
excluded as explained above; no public symbol was silently omitted.

All nine existing test files under
[../../../tests/cache](../../../tests/cache) were inspected. Native
`TestingEngine` discovery and `TestRunner` execution completed **210/210 tests
successfully**, with zero raw failures, raw errors, or skips, using a created
temporary application and no result cache. This was not the checkout's
configured Reactor bootstrap or a full-framework run.

Additional isolated probes verified local import origins, unknown-store
rejection, manager reuse/layout, absent manager `replace`, alias identities,
stored-None behavior, zero TTL in memory/file/SQLite, reserved-tag collisions,
corrupt artifact decoding, and RedLock's memory wait limitation. They are
checked cases, not deployment-wide guarantees. Earlier documentation's live
Redis certification was not repeated or carried forward as a result of this
task.

### Example results

| Example | Syntax | Local imports | Execution |
| --- | --- | --- | --- |
| 1. Memory repository | Passed | Passed | Executed successfully. |
| 2. Stored None | Passed | Passed | Executed successfully. |
| 3. Manager error | Passed | Passed | Executed successfully. |
| 4. File workflow | Passed | Passed | Executed successfully. |
| 5. SQLite backend | Passed | Passed | Executed successfully. |
| 6. Typed artifacts | Passed | Passed | Executed successfully. |
| 7. Provider/facade | Passed | Passed | Executed successfully. |

All 124 declaration fragments matched the inspected local source. The seven
scripts were extracted from this README, compiled, checked for local imports
separately, and executed in independent temporary working directories without
runtime warnings. Both README files have 43 corresponding headings, 131
identical fenced blocks, and 114 valid local links/anchors each. The skill's
20 links and two-field YAML frontmatter were independently checked, including
the derived `orionis-cache` identity. Scoped Ruff checks passed for
`orionis/cache` and `tests/cache` without fixes or cache writes. Validation
resources and reports stay outside the repository.

### Remaining limits

The documented source-description discrepancies concern configuration
defaults, lock connection/timeout meanings, and sentinel null behavior.
They do not authorize source changes. Dependency/callback exception lists
are not exhaustive. Code inspection of mutex/CAS mechanisms is distinct
from executing every concurrency and failure scenario.

> ⚠️ Not verifiable with the available files: a complete byte-for-byte
> starting-state comparison for this documentation execution. Its initial
> snapshot recorded 7,421 files but omitted 1,186 pre-existing hidden files.
> Recorded files showed no out-of-scope changes; omitted files had earlier
> dates and matched an earlier complete workspace fingerprint. That auxiliary
> check is not presented as a complete fresh initial snapshot. Git index and
> HEAD were unchanged, and the output contains exactly the three requested
> documents without extra content.

> ⚠️ Not executed in this environment: real Redis/Memcached services,
> external database drivers, multi-process/free-threaded deployment,
> Linux/macOS, and Python versions other than Windows CPython 3.14.6.
> Validation used isolated memory, local files, and SQLite resources only.
