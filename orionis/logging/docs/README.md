# orionis.logging

> `orionis.logging` provides Orionis' lazy, channel-based file logger with time- and size-based rotation.

## Overview

The package root exports `Logger`, an `ILogger` implementation backed by Python's standard `logging` module. It reads validated application configuration, creates its first handler only on demand, writes UTF-8 log files, and can switch or reload channels at runtime.

Orionis supports a plain `stack` file plus `hourly`, `daily`, `weekly`, `monthly`, and size-based `chunked` rotation. The core provider binds the service as a singleton and pins the `Log` facade for application-wide use.

## Requirements

- Python 3.14 or newer.
- A writable application log directory for configured file channels.
- A valid `logging` configuration mapping, normally built by `config/logging.py`.
- A booted Orionis application when using `orionis.support.facades.Log`.

## Quick start

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.logging import Logger


class App:
    def __init__(self, root: str) -> None:
        self.root = root

    def config(self, name: str) -> dict:
        assert name == "logging"
        return {
            "default": "stack",
            "channels": {"stack": {"path": "app.log", "level": "INFO"}},
        }

    def path(self, name: str) -> str:
        assert name == "root"
        return self.root


with TemporaryDirectory() as root:
    logger = Logger(App(root))
    logger.info("Orionis is ready")
    logger.close()
    assert "Orionis is ready" in (Path(root) / "app.log").read_text(encoding="utf-8")
    print(Logger.name)
```

Validation: **Executed successfully** on CPython 3.14.6; the temporary directory is removed automatically.

## Core concepts

### Logger and channel

`Logger` wraps the standard logger named `__orionis__`, disables propagation, and sets the logger itself to `DEBUG`; the active handler enforces the configured threshold. A channel describes one handler and path policy. Only one channel is active at a time, even though several may be configured.

### Lazy initialization

Constructing `Logger` performs no filesystem work. The first message or `getLogger()` initializes under a lock with double checking. Formatter instances are shared by format/date-format key. `close()` removes and closes every owned handler and resets the wrapper so later use can initialize again.

### Rotation

Time channels use a suffix resolver and rotate when its suffix changes. Hourly uses `YYYY-MM-DD_HH`, daily `YYYY-MM-DD`, weekly the ISO year/week, and monthly `YYYY-MM`. `chunked` rotates when the tracked encoded byte size reaches `mb_size`, generates timestamp/counter suffixes, and gzip-compresses rotated files.

### Retention

Rotating handlers scan only files matching their path template, sort them by modification time, and delete entries beyond the configured backup count. Retention values represent channel periods: hours, days, weeks, months, or a file count—not a universal duration.

## Module structure

| Path | Responsibility |
|---|---|
| `logger.py` | Lazy logger construction, levels, channel switch/reload, and cleanup. |
| `provider.py` | Container singleton and `Log` facade pinning. |
| `contracts/logger.py` | `ILogger` service contract. |
| `contracts/suffix_resolver.py` | Rotation suffix/time contract. |
| `handlers/rotating_handler_factory.py` | Channel-to-handler dispatch. |
| `handlers/advanced_rotating_file_handler.py` | Thread-safe writing, rotation, compression, and retention. |
| `handlers/*_suffix_resolver.py` | Hourly, daily, weekly, monthly, and chunk suffix policies. |

## Public API

The root package deliberately exports only `Logger`. Infrastructure users may import `ILogger`, handler classes, and suffix resolvers from their defining subpackages.

### `Logger(app)`

- `info(message)`, `error(message)`, `warning(message)`, `debug(message)`, and `critical(message)` forward strings to the standard logger.
- `getLogger()` returns the configured `logging.Logger` for advanced standard-library features.
- `switchChannel(name)` replaces the handler and returns whether it succeeded.
- `reloadConfiguration()` closes handlers, rereads `app.config("logging")`, rebuilds, and records a success message.
- `close()` releases file handles and permits later lazy reconstruction.
- `getActiveChannels()` / `getActiveChannel()` report handler-cache state.
- `getAvailableChannels()` reports names in configuration without initializing I/O.

### Rotation internals

`RotatingHandlerFactory.createHandler(channel_name, channel_config, app_root)` returns a standard `FileHandler`, an `AdvancedRotatingFileHandler`, or `None` for an unsupported channel. Each `SuffixResolver` provides `getSuffix(dt=None)` and `getNextRotationTime(current_time)`.

## Common workflows

### Log through the facade

Use `Log.info`, `Log.warning`, or the severity matching the event. Do not include passwords, tokens, raw authorization headers, encryption keys, or personal data. Prefer concise messages with stable identifiers.

### Change the configured channel

Set `LOG_CHANNEL` before application boot. Runtime `switchChannel()` is process-local and replaces the only active handler. Check its boolean result; unknown or uncreatable channels do not become active.

### Reload configuration

After updating the application's configuration source, call `reloadConfiguration()`. The operation is locked, but writes from other threads share the same underlying named logger; coordinate administrative reloads instead of invoking them frequently.

### Integrate standard logging features

Call `getLogger()` only when the five convenience methods are insufficient. Adding external handlers changes a shared standard-library logger; ownership and cleanup then become the caller's responsibility, and a subsequent close/reload may remove them.

## Examples

### Inspect configured channels without opening files

```python
from orionis.logging import Logger


class App:
    def config(self, name: str) -> dict:
        return {
            "default": "stack",
            "channels": {
                "stack": {"path": "storage/logs/stack.log", "level": "INFO"},
                "daily": {"path": "storage/logs/daily_{suffix}.log", "level": "WARNING"},
            },
        }


logger = Logger(App())
assert logger.getAvailableChannels() == ["stack", "daily"]
assert logger.getActiveChannel() is None
logger.close()
print("configuration inspected")
```

Validation: **Executed successfully** on CPython 3.14.6; no handler or file was created.

### Switch channels at runtime

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.logging import Logger


class App:
    def __init__(self, root: str) -> None:
        self.root = root

    def config(self, name: str) -> dict:
        return {
            "default": "stack",
            "channels": {
                "stack": {"path": "stack.log", "level": "INFO"},
                "chunked": {"path": "chunk_{suffix}.log", "level": "INFO", "mb_size": 1, "files": 2},
            },
        }

    def path(self, name: str) -> str:
        return self.root


with TemporaryDirectory() as root:
    logger = Logger(App(root))
    assert logger.switchChannel("chunked")
    logger.warning("written to chunked channel")
    assert logger.getActiveChannel() == "chunked"
    logger.close()
    assert any(Path(root).glob("chunk_*.log"))
    print("channel switched")
```

Validation: **Executed successfully** on CPython 3.14.6; temporary log files were removed automatically.

### Resolve deterministic time suffixes

```python
from datetime import datetime, time
from orionis.logging.handlers.daily_suffix_resolver import DailySuffixResolver
from orionis.logging.handlers.monthly_suffix_resolver import MonthlySuffixResolver
from orionis.logging.handlers.weekly_suffix_resolver import WeeklySuffixResolver

moment = datetime(2026, 10, 6, 15, 30)
assert DailySuffixResolver(time(2, 0)).getSuffix(moment) == "2026-10-06"
assert WeeklySuffixResolver().getSuffix(moment) == "2026-week41"
assert MonthlySuffixResolver().getSuffix(moment) == "2026-10"
print(DailySuffixResolver(time(2, 0)).getNextRotationTime(moment))
```

Validation: **Executed successfully** on CPython 3.14.6.

### Create a delayed handler

```python
import logging
from tempfile import TemporaryDirectory
from orionis.logging.handlers.rotating_handler_factory import RotatingHandlerFactory

with TemporaryDirectory() as root:
    handler = RotatingHandlerFactory.createHandler(
        "stack",
        {"path": "logs/example.log", "level": logging.WARNING},
        root,
    )
    assert handler is not None
    assert handler.level == logging.WARNING
    assert handler.stream is None
    handler.close()
    print(type(handler).__name__)
```

Validation: **Executed successfully** on CPython 3.14.6; delayed mode did not create a log file.

### Use the application facade

```python
from orionis.support.facades import Log

Log.info("Request completed")
Log.warning("Retry budget is low")
Log.error("Job failed")
```

Validation: **Import-only** on CPython 3.14.6; calls require a booted application and pinned facade.

## Configuration

`config/logging.py` builds frozen entities for every channel:

| Setting | Environment | Default |
|---|---|---|
| Default channel | `LOG_CHANNEL` | `stack` |
| Handler level | `LOG_LEVEL` | `INFO` |
| Selected channel path | `LOG_PATH` | Channel-specific path under `storage/logs/` |
| Selected time-channel retention | `LOG_RETENTION` | hourly 24, daily 7, weekly 4, monthly 4 |
| Daily rotation time | `LOG_ROTATION_TIME` | `00:00:00` |
| Chunk size | `LOG_MB_SIZE` | 10 MiB |
| Chunk retention | `LOG_FILES` | 5 files |

`LOG_PATH` and `LOG_RETENTION` override only the channel selected by `LOG_CHANNEL`; edit `config/logging.py` or use dedicated environment keys if several channels need independent overrides. Paths are resolved below the application root. Rotating path templates should contain `{suffix}` to avoid writing every period to the same file.

## Integration with Orionis

`LoggerProvider` binds `ILogger` to `Logger` as a singleton with alias `x-orionis-ILogger`, then pins `Log` during boot. Failure handling injects `ILogger`; background tasks use the facade to report success/failure. Other framework code can depend on the contract without knowing rotation details.

The standard logger name is shared process-wide. Creating or initializing another Orionis `Logger` closes and replaces handlers on that same logger, so application code should use the provider singleton.

## Errors and edge cases

- Initialization and configuration reload failures are wrapped in `RuntimeError`.
- An absent configured default creates `storage/logs/default.log`; a present but unsupported channel may leave the logger with no handlers.
- `switchChannel()` returns `False` for missing, unsupported, or failed channels and suppresses common I/O/config errors.
- String levels are normalized through standard logging names; unknown strings become `INFO`.
- Rotation/compression/retention I/O errors are handled defensively so logging does not normally interrupt application work; standard logging may report handler errors.
- Retention `0` removes matching rotated files during cleanup. Misconfigured templates without `{suffix}` defeat distinct time files.
- `close()` is idempotent and suppresses common cleanup errors; using the wrapper afterward rebuilds it.
- Multiple processes write independently and do not coordinate rotation locks across process boundaries.

## Performance and concurrency

The hot path uses standard logger filtering and one handler. Initialization, reload, channel switch, file emission, and chunk suffix generation use locks. Rotating handlers cache up to roughly 50 resolved suffix paths for five minutes and track written encoded bytes without stat calls on every record.

Locks are thread-level, not process-level. Avoid several workers targeting the same rotating filename unless the deployment supplies external coordination. File writes are synchronous and can affect event-loop latency at high volume; use an application-level queue/aggregation architecture when logging throughput is substantial.

## Compatibility

Orionis declares Python 3.14+ and relies on the standard `logging`, `pathlib`, `gzip`, and timezone facilities. Files use UTF-8 and explicit LF newlines in advanced handlers. Paths are built with `pathlib` in handlers; the base logger also accepts application roots on Windows and POSIX. Suffix dates use the timezone exposed by Orionis' `DateTime` facade.

## Verification notes

Validation used CPython 3.14.6. The public export, `ILogger`, logger lifecycle, formatter/handler caches, all channel factories and suffix resolvers, rotation/compression/retention, configuration entities, provider/facade, and framework consumers were inspected. All **178** logging test methods passed through the Orionis runner. Five direct programs executed successfully; the facade example was import-validated only.
