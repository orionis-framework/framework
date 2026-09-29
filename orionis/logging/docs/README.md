# orionis.logging

> Application logging: a single stdlib logger driven by named channels, with time-based and size-based file rotation.

## Table of contents

- [Functional description](#functional-description)
  - [Where it fits in the framework](#where-it-fits-in-the-framework)
  - [Resolution pipeline](#resolution-pipeline)
  - [File map](#file-map)
  - [Design decisions](#design-decisions)
- [API reference](#api-reference)
  - [`Log` facade](#log-facade)
  - [`ILogger`](#ilogger)
  - [`Logger`](#logger)
  - [`SuffixResolver`](#suffixresolver)
  - [Suffix resolvers](#suffix-resolvers)
  - [`AdvancedRotatingFileHandler`](#advancedrotatingfilehandler)
  - [`RotatingHandlerFactory`](#rotatinghandlerfactory)
  - [`LoggerProvider`](#loggerprovider)
  - [Configuration entities](#configuration-entities)
- [Usage examples](#usage-examples)
  - [1. Logging from a controller](#1-logging-from-a-controller)
  - [2. Resolving the service through the container](#2-resolving-the-service-through-the-container)
  - [3. Standalone `Logger` without the container](#3-standalone-logger-without-the-container)
  - [4. Switching channels and handling errors](#4-switching-channels-and-handling-errors)
  - [5. Custom `SuffixResolver`](#5-custom-suffixresolver)
  - [6. Building a handler with the factory](#6-building-a-handler-with-the-factory)
- [Performance and concurrency](#performance-and-concurrency)
- [Compatibility notes](#compatibility-notes)

## Functional description

`orionis.logging` writes application log lines to files. It wraps a single
standard-library `logging.Logger` named `__orionis__` and configures it from the
`logging` section of the application configuration, which declares **channels**
(`stack`, `hourly`, `daily`, `weekly`, `monthly`, `chunked`). Exactly one channel
is attached at a time; `switchChannel()` swaps it at runtime.

Rotation is not delegated to `logging.handlers`: the module ships its own
`AdvancedRotatingFileHandler`, parameterised by a `SuffixResolver` strategy that
decides the file-name suffix (`daily_2026-08-21.log`, `hourly_2026-08-21_14.log`,
…) and, for the `chunked` channel, produces a unique suffix per rotation so
rotation is driven by file size instead of time.

### Where it fits in the framework

| Piece | Value |
|---|---|
| Contract | `orionis.logging.contracts.logger.ILogger` |
| Implementation | `orionis.logging.logger.Logger` |
| Container binding | `singleton(ILogger, Logger, alias="x-orionis-ILogger")` |
| Provider | `orionis.logging.provider.LoggerProvider` (listed in `CORE_PROVIDERS`, eager — not deferrable) |
| Facade | `orionis.support.facades.logger.Log` (accessor `"x-orionis-ILogger"`) |
| Configuration | `orionis.foundation.config.logging` entities, published by `config/logging.py` |

The provider registers the binding in `register()` and pins the facade in
`boot()`. Eager providers are booted by `Application.__onStartup()`, i.e. when
the HTTP or CLI runtime starts. Before that moment the facade is **not** pinned
and every attribute access returns a `_FacadeDispatch` that has to be awaited
(`await Log.getAvailableChannels()`); after the pin, calls are direct
pass-throughs (`Log.info("...")`, no `await`). Framework code that runs during
startup itself — or standalone scripts — should either inject `ILogger` or call
`await Log.pin()` explicitly.

Other framework modules consume the service directly: the console `Reactor`
reports command failures through `ILogger`, and the scheduler warns through the
`Log` facade when a per-task listener is overwritten.

### Resolution pipeline

```text
Log (facade)  ─┐
               ├─► ILogger ──► Logger ──► logging.Logger("__orionis__")
DI: ILogger   ─┘                 │
                                 ├─ channel "stack"  ──► logging.FileHandler
                                 └─ other channels   ──► RotatingHandlerFactory
                                                              │
                                                              ├─ HourlySuffixResolver
                                                              ├─ DailySuffixResolver   ─┐
                                                              ├─ WeeklySuffixResolver   ├─► AdvancedRotatingFileHandler
                                                              ├─ MonthlySuffixResolver ─┘
                                                              └─ ChunkedSuffixResolver
```

Handler creation is **lazy**: `Logger.__init__` only snapshots
`app.config("logging")`. The stdlib logger and its handler are built on the first
`info()`/`error()`/`warning()`/`debug()`/`critical()`/`getLogger()`/`switchChannel()`
call, under a double-checked `threading.Lock`. Until then
`getActiveChannels()` returns `[]`.

### File map

| File | Contents |
|---|---|
| `__init__.py` | Re-exports `Logger` (`__all__ = ["Logger"]`) |
| `logger.py` | `Logger`, the only public service of the module |
| `provider.py` | `LoggerProvider` (binding + facade pin) |
| `contracts/logger.py` | `ILogger` (ABC) |
| `contracts/suffix_resolver.py` | `SuffixResolver` (ABC, `__slots__ = ()`) |
| `handlers/advanced_rotating_file_handler.py` | `AdvancedRotatingFileHandler` |
| `handlers/rotating_handler_factory.py` | `RotatingHandlerFactory` + the six private `_create_*` builders |
| `handlers/hourly_suffix_resolver.py` | `HourlySuffixResolver` |
| `handlers/daily_suffix_resolver.py` | `DailySuffixResolver` |
| `handlers/weekly_suffix_resolver.py` | `WeeklySuffixResolver` |
| `handlers/monthly_suffix_resolver.py` | `MonthlySuffixResolver` |
| `handlers/chunked_suffix_resolver.py` | `ChunkedSuffixResolver` |
| `handlers/__init__.py` | Empty (handlers are imported by full path) |

The module defines **no exceptions of its own**: failures are reported as
`RuntimeError`, as boolean return values (`switchChannel`), or swallowed
(cleanup and compression paths).

### Design decisions

- **Strategy pattern for rotation.** `AdvancedRotatingFileHandler` knows how to
  write, rotate, compress and prune; *when* to rotate is delegated to a
  `SuffixResolver`. Adding a rotation policy means writing one class, not a
  handler.
- **One active channel.** The handler cache holds at most one entry (or the key
  `"fallback"`), so `getActiveChannel()` is meaningful and switching channels is
  a complete swap, not an addition.
- **Class-level formatter cache.** `Logger._formatter_cache` is shared by every
  instance in the process and keyed by `format|datefmt`, so repeated
  initialisations reuse the same `logging.Formatter`.
- **`name` as a `ClassVar`.** `Logger.name` is a plain class attribute that
  shadows the abstract property declared by `ILogger` through the MRO, avoiding
  a property descriptor call on each access.
- **`__slots__` on the resolvers.** All five resolvers and the `SuffixResolver`
  ABC declare `__slots__`, so resolver instances carry no `__dict__`. `Logger`
  and `AdvancedRotatingFileHandler` do not declare `__slots__`.
- **No `from __future__ import annotations` in `logger.py`.** The class is built
  by the DI container, which resolves constructor dependencies by reflection;
  string annotations would break that resolution. Every other file of the module
  does use the future import.

## API reference

### `Log` facade

`orionis.support.facades.logger.Log`

```python
class Log(Facade):
    @classmethod
    def getFacadeAccessor(cls) -> str: ...
```

Returns the string `"x-orionis-ILogger"`, the alias under which `LoggerProvider`
registers the service. The facade declares no logging methods of its own: every
method of `ILogger` is exposed dynamically by `FacadeMeta`. A parallel
`logger.pyi` stub exists for editor completion only and is never executed.

State matters:

| Facade state | Behaviour |
|---|---|
| Not pinned (before runtime startup) | `Log.anything` returns a `_FacadeDispatch`; must be awaited: `await Log.getAvailableChannels()` |
| Pinned (`LoggerProvider.boot()` or explicit `await Log.pin()`) | Direct pass-through: `Log.info("...")`, `Log.getActiveChannel()` |

### `ILogger`

`orionis.logging.contracts.logger.ILogger` — `abc.ABC`. Does **not** declare
`__slots__ = ()`, so implementations keep a `__dict__`.

| Member | Signature |
|---|---|
| `name` | `@property def name(self) -> str` |
| `info` | `def info(self, message: str) -> None` |
| `error` | `def error(self, message: str) -> None` |
| `warning` | `def warning(self, message: str) -> None` |
| `debug` | `def debug(self, message: str) -> None` |
| `critical` | `def critical(self, message: str) -> None` |
| `getLogger` | `def getLogger(self) -> logging.Logger` |
| `reloadConfiguration` | `def reloadConfiguration(self) -> None` |
| `switchChannel` | `def switchChannel(self, channel_name: str) -> bool` |
| `close` | `def close(self) -> None` |
| `getActiveChannels` | `def getActiveChannels(self) -> list[str]` |
| `getActiveChannel` | `def getActiveChannel(self) -> str \| None` |
| `getAvailableChannels` | `def getAvailableChannels(self) -> list[str]` |

Every abstract method has an empty body: the contract cannot be called through
`super()`.

### `Logger`

`orionis.logging.logger.Logger(ILogger)`

```python
def __init__(self, app: IApplication) -> None: ...
```

**Parameters**

- `app` (`IApplication`) — application instance. Only two hooks are used:
  `app.config("logging")` (read once in the constructor, and again on
  `reloadConfiguration()`) and `app.path("root")` (read when a handler is
  built).

**Side effects of the constructor:** none on the filesystem. It stores the
configuration snapshot and initialises the internal state; no directory is
created and no file is opened.

**Class attributes**

| Attribute | Value |
|---|---|
| `name` | `ClassVar[str] = "__orionis__"` |
| `_formatter_cache` | `dict[str, logging.Formatter]`, class-level, keyed by `f"{log_format}\|{date_format}"` |

**Fixed settings, assigned in `__init__` and not configurable**

| Setting | Value |
|---|---|
| Message format | `"%(asctime)s [%(levelname)s]: %(message)s"` |
| Date format | `"%Y-%m-%d %H:%M:%S"` |
| Stdlib logger name | `"__orionis__"` |
| Logger level | `logging.DEBUG` |

The logger level is `DEBUG` and `propagate` is set to `False`; effective
filtering is performed by the **handler** level, which comes from the channel
configuration.

**Methods**

| Method | Returns | Behaviour |
|---|---|---|
| `info(message: str)` | `None` | Ensures initialisation, then `logging.Logger.info(message)` |
| `error(message: str)` | `None` | Same, `error` level |
| `warning(message: str)` | `None` | Same, `warning` level |
| `debug(message: str)` | `None` | Same, `debug` level |
| `critical(message: str)` | `None` | Same, `critical` level |
| `getLogger()` | `logging.Logger` | Ensures initialisation and returns the underlying stdlib logger |
| `reloadConfiguration()` | `None` | Closes handlers, clears caches, re-reads `app.config("logging")`, re-initialises and logs `"Logger configuration reloaded successfully"` |
| `switchChannel(channel_name: str)` | `bool` | Replaces the active handler with the one declared by `channel_name` |
| `close()` | `None` | Closes and removes every handler, clears the cache and drops the logger reference |
| `getActiveChannels()` | `list[str]` | Keys currently present in the handler cache |
| `getActiveChannel()` | `str \| None` | First key of the cache, or `None` |
| `getAvailableChannels()` | `list[str]` | Keys of `channels` in the configuration snapshot held by the instance |
| `__del__()` | `None` | Calls `close()` with every exception suppressed |

**Raises**

- `RuntimeError` — from `getLogger()` and from any logging method whenever
  initialisation fails; the original exception is chained
  (`"Failed to initialize logger: …"`). `reloadConfiguration()` raises
  `RuntimeError("Failed to reload logger configuration: …")` on any failure.
- `switchChannel()` never raises: it returns `False` for an unknown channel,
  for a channel the factory cannot build, and when an `OSError`,
  `RuntimeError` or `ValueError` is caught.
- `close()` suppresses `OSError`, `RuntimeError` and `ValueError`.

**Initialisation algorithm** (private `__initializeLogger`)

1. `logging.getLogger("__orionis__")`; if it already has handlers, they are
   cleared.
2. `setLevel(logging.DEBUG)`, `propagate = False`.
3. Reads `default` and `channels` from the snapshot, plus `app.path("root")`.
4. If `default` is present in `channels`, the configuration is normalised and:
   - channel `"stack"` → a `logging.FileHandler(f"{root}/{path}", encoding="utf-8")`
     is created directly (parent directory created with `mkdir(parents=True,
     exist_ok=True)`); `path` defaults to `storage/logs/stack.log`;
   - any other channel → `RotatingHandlerFactory.createHandler(...)`.
   The handler receives the cached formatter and
   `setLevel(channel_config.get("level", logging.INFO))`, and is cached under
   the channel name.
5. If `default` is **not** present in `channels`, a fallback
   `logging.FileHandler(f"{root}/storage/logs/default.log")` is created and
   cached under the key `"fallback"`. No level is applied to this handler, so it
   stays at `NOTSET` and the `DEBUG` logger level governs.

**Level normalisation** (private `__normalizeChannelConfig`) copies the channel
dict and rewrites `level`:

| Input | Result |
|---|---|
| `Level` enum (or any object with `.value`) | `level.value` |
| `str` | `getattr(logging, value.upper(), logging.INFO)` — case-insensitive, unknown names fall back to `INFO` |
| `None` | `logging.INFO` |
| `int` | left untouched |

**`switchChannel` details.** The channel name is checked against the
configuration *before* anything is initialised, so an invalid name never forces
initialisation. Initialisation then happens **outside** the lock
(`__init_lock` is a non-reentrant `threading.Lock`), after which the current
handlers are closed and removed, the cache is cleared, and the new handler is
built through the factory — including for `"stack"`, which therefore ends up as
the factory's `FileHandler(delay=True)` rather than the eagerly opened handler
used at initialisation. On success an informational line
`"Successfully switched to channel: <name>"` is written through the new handler.

### `SuffixResolver`

`orionis.logging.contracts.suffix_resolver.SuffixResolver` — `abc.ABC` with
`__slots__ = ()`.

```python
def getSuffix(self, dt: datetime | None = None) -> str: ...
def getNextRotationTime(self, current_time: datetime) -> datetime: ...
```

`getSuffix` returns the string substituted into the `{suffix}` placeholder of a
path template; `None` means "use the current time". `getNextRotationTime` is
part of the contract and is implemented by all five resolvers, but
`AdvancedRotatingFileHandler` does not call it: rotation is decided by comparing
suffixes and by `max_bytes`.

### Suffix resolvers

All five live in `orionis.logging.handlers`, implement `SuffixResolver`, declare
`__slots__`, and capture `self.tz = DateTime.getZoneInfo()` in their constructor
— that is, the application timezone as configured at construction time
(`config app.timezone`, loaded by `Application.create()` before providers boot).

| Class | Constructor | `getSuffix` format | Example |
|---|---|---|---|
| `HourlySuffixResolver` | `()` | `%Y-%m-%d_%H` | `2026-08-21_14` |
| `DailySuffixResolver` | `(at_time: time \| None = None)` | `%Y-%m-%d` | `2026-08-21` |
| `WeeklySuffixResolver` | `(at_time: time \| None = None)` | `{iso_year}-week{iso_week:02d}` | `2026-week34` |
| `MonthlySuffixResolver` | `(at_time: time \| None = None)` | `%Y-%m` | `2026-08` |
| `ChunkedSuffixResolver` | `()` | `%Y%m%d_%H%M%S_{counter:04d}` | `20260821_143705_0001` |

`at_time` defaults to `time(0, 0, 0)` (midnight) and only affects
`getNextRotationTime`, never the suffix.

`getNextRotationTime` per class, evaluated for `2026-08-21 14:37:05+00:00`:

| Class | Rule | Result |
|---|---|---|
| `HourlySuffixResolver` | Truncate to the hour (replacing `tzinfo` with the resolver timezone) and add one hour | `2026-08-21 15:00:00+00:00` |
| `DailySuffixResolver` | Today at `at_time`; add one day if that is not in the future | `2026-08-22 00:00:00+00:00` |
| `WeeklySuffixResolver` | Next Monday at `at_time`; add seven days if that is not in the future | `2026-08-24 00:00:00+00:00` |
| `MonthlySuffixResolver` | First day of next month at `at_time` | `2026-09-01 00:00:00+00:00` |
| `ChunkedSuffixResolver` | `current_time + timedelta(hours=1)` (size-based rotation ignores it) | `2026-08-21 15:37:05+00:00` |

`ChunkedSuffixResolver` is the only stateful resolver: it holds a counter
incremented under a `threading.Lock`, so **every call to `getSuffix()` returns a
different value**. That is what turns `AdvancedRotatingFileHandler` into a
size-based rotator — the suffix always differs from the current one, so
rotation is effectively decided by the `max_bytes` check performed before the
suffix is consumed.

### `AdvancedRotatingFileHandler`

`orionis.logging.handlers.advanced_rotating_file_handler.AdvancedRotatingFileHandler`,
subclass of `logging.Handler`.

```python
def __init__(
    self,
    path_template: str,
    suffix_resolver: SuffixResolver,
    max_bytes: int | None = None,
    backup_count: int = 5,
    encoding: str = "utf-8",
    *,
    delay: bool = True,
    compress_rotated: bool = False,
    app_root: str = ".",
) -> None: ...
```

**Parameters**

| Parameter | Type | Meaning |
|---|---|---|
| `path_template` | `str` | Path relative to `app_root`, containing `{suffix}` |
| `suffix_resolver` | `SuffixResolver` | Strategy deciding the suffix |
| `max_bytes` | `int \| None` | Size threshold; `None` disables size-based rotation |
| `backup_count` | `int` | Number of rotated files kept, besides the one being written |
| `encoding` | `str` | Encoding used to open the file |
| `delay` | `bool` (keyword-only) | `True` (default) postpones opening the file until the first record; `False` opens it in the constructor |
| `compress_rotated` | `bool` (keyword-only) | Gzip the previous file on rotation |
| `app_root` | `str` (keyword-only) | Base directory prefixed to `path_template` |

**Public attributes:** `path_template`, `suffix_resolver`, `max_bytes`,
`backup_count`, `encoding`, `delay`, `compress_rotated`, `app_root` (a `Path`),
plus the mutable state `stream` (`None` until the first write), `current_path`,
`current_suffix` and `file_size`.

**Public methods**

| Method | Behaviour |
|---|---|
| `emit(record: LogRecord) -> None` | Formats the record **outside** the lock, then, holding `self._lock`, ensures the stream, writes `msg + "\n"` and adds `len(msg) + 1` to `file_size`. Catches `OSError` only and reports it through `Handler.handleError(record)` |
| `close() -> None` | Closes the stream under the lock and calls `logging.Handler.close()` |

**Rotation algorithm** (`_ensureStream` → `_shouldRotate` → `_rotateFile`)

1. `current_suffix = suffix_resolver.getSuffix()`.
2. Rotate when the suffix differs from the active one, **or** when
   `max_bytes is not None and file_size >= max_bytes`.
3. Rotating closes the stream, gzips the previous file when `compress_rotated`
   is enabled (`<file>.gz`, original removed; a failed compression removes the
   partial `.gz`), prunes old files, and resets `current_path`,
   `current_suffix` and `file_size`.
4. The new path is resolved and opened in append mode with `buffering=1` (line
   buffered). `file_size` is seeded from `stat().st_size` when the file already
   exists.

**Path resolution** (`_resolvePath`) substitutes `{suffix}`, joins the result
with `app_root`, creates the parent directory (`mkdir(parents=True,
exist_ok=True)`) and caches the string for 300 seconds using `time.monotonic()`.
The cache is cleared once it exceeds 50 entries, which bounds it for chunked
rotation (one unique suffix per chunk).

**Pruning** (`_cleanupOldFiles`) lists the directory of the current file, keeps
the names matched by a regex precompiled in the constructor (the template
basename with `{suffix}` replaced by `.*`), sorts them by modification time
newest-first and unlinks everything past `backup_count`, along with the matching
`.gz` file when present. All `OSError`s are ignored so pruning never breaks
logging. The net effect is at most `backup_count` rotated files plus the file
currently being written.

### `RotatingHandlerFactory`

`orionis.logging.handlers.rotating_handler_factory.RotatingHandlerFactory`

```python
@staticmethod
def createHandler(
    channel_name: str,
    channel_config: dict,
    app_root: str,
) -> Handler | None: ...
```

Reads `channel_config["path"]` (default `"storage/logs/default.log"`) and
`channel_config["level"]` (default `20`, i.e. `INFO`), then dispatches through
the module-level dict `_CHANNEL_CREATORS`. **Returns `None` for an unknown
channel name** — no exception is raised. Every builder calls
`handler.setLevel(level)` before returning.

| `channel_name` | Handler | Resolver | Config keys read | Defaults |
|---|---|---|---|---|
| `stack` | `logging.FileHandler(delay=True)` | — | — | Parent directory created eagerly |
| `hourly` | `AdvancedRotatingFileHandler` | `HourlySuffixResolver()` | `retention_hours` → `backup_count` | `24` |
| `daily` | `AdvancedRotatingFileHandler` | `DailySuffixResolver(at)` | `at`, `retention_days` → `backup_count` | `at=None` → midnight, `7` |
| `weekly` | `AdvancedRotatingFileHandler` | `WeeklySuffixResolver(at)` | `at`, `retention_weeks` → `backup_count` | `at=None` → midnight, `4` |
| `monthly` | `AdvancedRotatingFileHandler` | `MonthlySuffixResolver(at)` | `at`, `retention_months` → `backup_count` | `at=None` → midnight, `4` |
| `chunked` | `AdvancedRotatingFileHandler` | `ChunkedSuffixResolver()` | `mb_size` → `max_bytes = mb_size * 1024 * 1024`, `files` → `backup_count` | `10` MB, `5` files; `compress_rotated=True` |

`chunked` is the only channel built with `compress_rotated=True`, so its rotated
files end in `.log.gz`.

The `weekly` and `monthly` builders read `channel_config.get("at")`, but the
matching configuration entities (`Weekly`, `Monthly`) declare no `at` field —
only `Daily` does. With the framework entities those two channels therefore
always receive `None` and their resolvers fall back to midnight; a hand-written
`dict` configuration can supply `at` explicitly.

### `LoggerProvider`

`orionis.logging.provider.LoggerProvider(ServiceProvider)`

```python
def register(self) -> None: ...
async def boot(self) -> None: ...
```

- `register()` — `self.app.singleton(ILogger, Logger, alias="x-orionis-ILogger")`.
  A single `Logger` instance is shared per process; resolving `ILogger` or the
  alias returns the same object.
- `boot()` — `await LoggerFacade.pin()`, which makes `Log` a direct
  pass-through. The provider is **not** deferrable, so it boots during
  application startup along with the other core providers.

### Configuration entities

Declared in `orionis.foundation.config.logging`, published by the application's
`config/logging.py` (class `BootstrapLogging`). `app.config("logging")` returns a
plain `dict` (`{"default": ..., "channels": {...}}`); levels are already
integers there, while `Daily.at` remains a `datetime.time`.

| Entity | Fields | Defaults |
|---|---|---|
| `Logging` | `default: str`, `channels: Channels \| dict` | `Env.get("LOG_CHANNEL", "stack")`, `Channels()` |
| `Channels` | `stack`, `hourly`, `daily`, `weekly`, `monthly`, `chunked` | One entity per channel |
| `Stack` | `path`, `level` | `storage/logs/stack.log`, `INFO` |
| `Hourly` | `path`, `level`, `retention_hours` | `storage/logs/hourly_{suffix}.log`, `INFO`, `24` |
| `Daily` | `path`, `level`, `retention_days`, `at` | `storage/logs/daily_{suffix}.log`, `INFO`, `7`, `time(0, 0)` |
| `Weekly` | `path`, `level`, `retention_weeks` | `storage/logs/weekly_{suffix}.log`, `INFO`, `4` |
| `Monthly` | `path`, `level`, `retention_months` | `storage/logs/monthly_{suffix}.log`, `INFO`, `4` |
| `Chunked` | `path`, `level`, `mb_size`, `files` | `storage/logs/chunked_{suffix}.log`, `INFO`, `10`, `5` |

All of them are `@dataclass(frozen=True, kw_only=True)` extending `BaseEntity`
and validate in `__post_init__`:

- `IsValidPath` — `path` must be a non-empty string ending in `.log`; every
  channel except `stack` also requires the literal `{suffix}` in the path.
- `IsValidLevel` — `level` accepts a `Level` enum, one of the integers
  `10/20/30/40/50`, or a case-insensitive level name; it is normalised to its
  integer value.
- Ranges: `retention_hours` 1–168, `retention_days` 1–90, `retention_weeks`
  1–12, `retention_months` 1–12, `mb_size` 1–1000 MB, `files` ≥ 1.
- `Logging.default` must name one of the six fields of `Channels`, otherwise
  `ValueError` is raised at configuration build time.
- `Daily.at` accepts a `datetime.time` or an ISO `HH:MM:SS` string, which is
  converted; anything else raises.

`Level` (`orionis.foundation.config.logging.enums.levels.Level`) is an `Enum`
mirroring the stdlib values: `DEBUG=10`, `INFO=20`, `WARNING=30`, `ERROR=40`,
`CRITICAL=50`.

## Usage examples

### 1. Logging from a controller

Inside a booted application the facade is pinned, so calls are synchronous. The
contract can also be injected as a parameter, which the container resolves.

```python
from orionis.http import HttpResponse, response
from orionis.logging.contracts.logger import ILogger
from orionis.support.facades.logger import Log


class ReportController:
    """Emit application log lines while serving a request."""

    async def index(self, logger: ILogger) -> HttpResponse:
        logger.info("report requested")
        return response.json({"status": "ok"})

    async def store(self) -> HttpResponse:
        Log.warning("disk usage above 80%")
        return response.noContent()
```

### 2. Resolving the service through the container

Dependency injection works regardless of the facade state, which makes it the
safe option in scripts and during startup.

```python
from bootstrap.app import app
from orionis.aio.loop import Loop
from orionis.logging.contracts.logger import ILogger
from orionis.support.facades.logger import Log


async def main() -> None:
    logger = await app.make(ILogger)
    logger.info("resolved through the container")
    print("active channel:", logger.getActiveChannel())

    # The facade is pinned by LoggerProvider.boot() during runtime startup;
    # a standalone script has to request the pin explicitly.
    await Log.pin()
    Log.warning("disk usage above 80%")
    print("available channels:", Log.getAvailableChannels())
    print("same instance:", Log.getLogger() is logger.getLogger())


Loop.run(main())
```

Output with the default configuration:

```text
active channel: stack
available channels: ['stack', 'hourly', 'daily', 'weekly', 'monthly', 'chunked']
same instance: True
```

### 3. Standalone `Logger` without the container

`Logger` only needs an object exposing `config(key)` and `path(name)`, which
makes it usable in isolated scripts and tests.

```python
import logging
import tempfile
from pathlib import Path

from orionis.logging import Logger


class MiniApp:
    """Minimal stand-in exposing the two hooks Logger consumes."""

    def __init__(self, root: str) -> None:
        self._root = root

    def config(self, key: str) -> dict:
        return {
            "default": "daily",
            "channels": {
                "daily": {
                    "path": "logs/app_{suffix}.log",
                    "level": logging.DEBUG,
                    "retention_days": 3,
                },
            },
        }

    def path(self, name: str) -> str:
        return self._root


with tempfile.TemporaryDirectory() as root:
    logger = Logger(MiniApp(root))
    logger.info("service started")
    logger.debug("cache warm-up finished")
    print("active:", logger.getActiveChannels())
    print("files:", sorted(p.name for p in (Path(root) / "logs").iterdir()))
    logger.close()
    print("after close:", logger.getActiveChannels())
```

Output (run on 2026-08-21):

```text
active: ['daily']
files: ['app_2026-08-21.log']
after close: []
```

### 4. Switching channels and handling errors

`switchChannel` reports failure with `False`; `reloadConfiguration` is the only
method that raises on failure.

```python
import logging
import tempfile

from orionis.logging import Logger


class MiniApp:
    """Minimal stand-in exposing the two hooks Logger consumes."""

    def __init__(self, root: str) -> None:
        self._root = root

    def config(self, key: str) -> dict:
        return {
            "default": "daily",
            "channels": {
                "daily": {
                    "path": "logs/app_{suffix}.log",
                    "level": logging.DEBUG,
                    "retention_days": 3,
                },
            },
        }

    def path(self, name: str) -> str:
        return self._root


with tempfile.TemporaryDirectory() as root:
    logger = Logger(MiniApp(root))
    logger.info("written to the default channel")

    if not logger.switchChannel("hourly"):
        print("channel 'hourly' is not declared; staying on the current one")

    print("available:", logger.getAvailableChannels())
    print("active:", logger.getActiveChannel())

    try:
        logger.reloadConfiguration()
    except RuntimeError as exc:
        print("reload failed:", exc)
    else:
        print("reloaded, active:", logger.getActiveChannel())

    logger.close()
```

Output:

```text
channel 'hourly' is not declared; staying on the current one
available: ['daily']
active: daily
reloaded, active: daily
```

### 5. Custom `SuffixResolver`

Implementing the contract is enough to plug a new rotation policy into
`AdvancedRotatingFileHandler`.

```python
import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from orionis.logging.contracts.suffix_resolver import SuffixResolver
from orionis.logging.handlers.advanced_rotating_file_handler import (
    AdvancedRotatingFileHandler,
)


class ShiftSuffixResolver(SuffixResolver):
    """Rotate twice a day: one file for the morning, one for the afternoon."""

    __slots__ = ()

    def getSuffix(self, dt: datetime | None = None) -> str:
        moment = dt or datetime.now()
        half = "am" if moment.hour < 12 else "pm"
        return f"{moment:%Y-%m-%d}-{half}"

    def getNextRotationTime(self, current_time: datetime) -> datetime:
        if current_time.hour < 12:
            return current_time.replace(hour=12, minute=0, second=0, microsecond=0)
        midnight = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight + timedelta(days=1)


with tempfile.TemporaryDirectory() as root:
    handler = AdvancedRotatingFileHandler(
        path_template="logs/shift_{suffix}.log",
        suffix_resolver=ShiftSuffixResolver(),
        backup_count=4,
        app_root=root,
    )
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))

    native = logging.getLogger("shift-demo")
    native.setLevel(logging.INFO)
    native.addHandler(handler)
    native.info("payment accepted")
    native.handlers.clear()
    handler.close()

    print("files:", sorted(p.name for p in (Path(root) / "logs").iterdir()))
```

Output (run at 18:57 local time):

```text
files: ['shift_2026-08-21-pm.log']
```

### 6. Building a handler with the factory

Useful to attach an Orionis rotating handler to a third-party logger, and to see
how channel options map onto handler parameters.

```python
import logging
import tempfile

from orionis.logging.handlers.rotating_handler_factory import RotatingHandlerFactory

with tempfile.TemporaryDirectory() as root:
    built = RotatingHandlerFactory.createHandler(
        channel_name="chunked",
        channel_config={
            "path": "logs/audit_{suffix}.log",
            "level": logging.INFO,
            "mb_size": 1,
            "files": 3,
        },
        app_root=root,
    )
    print("handler:", type(built).__name__)
    print("max_bytes:", built.max_bytes, "backup_count:", built.backup_count)
    print("compress_rotated:", built.compress_rotated)

    unknown = RotatingHandlerFactory.createHandler(
        channel_name="syslog",
        channel_config={"path": "logs/syslog.log", "level": logging.INFO},
        app_root=root,
    )
    print("unsupported channel ->", unknown)
    built.close()
```

Output:

```text
handler: AdvancedRotatingFileHandler
max_bytes: 1048576 backup_count: 3
compress_rotated: True
unsupported channel -> None
```

## Performance and concurrency

- **Lazy initialisation.** Building the logger costs nothing until the first
  message. `__ensureLoggerReady()` uses double-checked locking over a
  `threading.Lock`, so the fast path is a single `is not None` check.
- **Inlined guard on the hot path.** Every logging method repeats the
  `if self.__logger is None` check inline instead of always calling the helper,
  and calls the stdlib level method directly rather than `log(level, …)`.
- **Formatter cache.** `Logger._formatter_cache` is a plain class-level `dict`
  with no lock. Concurrent misses may build the same formatter twice; because
  the value is a pure function of the key, the surviving entry is equivalent.
- **Handler-level thread safety.** `AdvancedRotatingFileHandler` guards
  `_ensureStream()` and the write with its own `threading.Lock`, and formats the
  record *before* taking it. `logging.Logger` adds its own per-record locking.
- **Resolvers.** `ChunkedSuffixResolver` increments its counter under a lock and
  is safe to share. The other four are effectively immutable after construction
  (they only store `tz` and `at_time`) and hold no per-call state.
- **Path cache.** Resolution results are cached per handler instance for 300
  seconds and read only inside `_ensureStream()`, i.e. always under the handler
  lock. The 50-entry cap prevents unbounded growth when each rotation produces a
  unique suffix.
- **I/O is synchronous.** The module exposes no async API: a log call performs a
  buffered write to an open file and, because the stream is opened with
  `buffering=1`, flushes one line per record. Inside a coroutine this blocks the
  event loop for the duration of the write; rotation additionally pays for
  `stat`, `mkdir`, directory listing and — for `chunked` — gzip compression of
  the previous file.
- **Process scope.** The stdlib logger `"__orionis__"` is global to the process,
  so any `Logger` instance built against it shares its handlers; the container
  registers a single instance anyway. There is **no** inter-process locking:
  several processes writing to the same file rely on OS append semantics, and
  concurrent rotation or pruning between processes is not coordinated.
- **Cleanup cost.** `_cleanupOldFiles()` runs on every rotation and performs a
  full `glob("*")` of the log directory plus a `stat()` per matching file, so it
  is proportional to the number of files kept in that directory.

## Compatibility notes

- **Python.** Requires Python ≥ 3.14, matching the project's `requires-python`.
  Type hints use PEP 604 unions (`int | None`) and PEP 649 deferred annotations.
- **Dependencies.** Standard library only (`logging`, `gzip`, `shutil`, `re`,
  `threading`, `pathlib`, `time`, `datetime`), plus
  `orionis.support.facades.datetime.DateTime` — the framework's single source of
  truth for the timezone, which wraps `pendulum`. No extra installation is
  needed beyond the framework itself.
- **`from __future__ import annotations`.** Used by the provider, contracts,
  handlers and resolvers; deliberately **not** used in `logger.py`, because the
  DI container resolves `Logger.__init__` by reflection and string annotations
  would be interpreted as literal forward references.
- **Windows.** Log files are opened in text mode, so `\n` is written as `\r\n`.
  `file_size` is tracked as `len(msg) + 1` per record, meaning the counter
  understates the real size and size-based rotation triggers slightly later than
  the configured `max_bytes` suggests.
- **Path separators.** `path_template` is split with `rsplit("/", 1)` when the
  cleanup regex is built, so templates should use forward slashes even on
  Windows; the resolved path itself is built with `pathlib`.
- **Timezone.** Resolvers capture `DateTime.getZoneInfo()` at construction time.
  Since `Application.create()` configures the timezone before providers boot,
  handlers built during startup already use the application timezone; a resolver
  instantiated before that configuration would keep the default (`UTC`).
