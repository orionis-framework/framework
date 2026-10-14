# Configuring rotation and lifecycle

A channel determines file growth and retention. Configuration must match worker count and your operations policy.

## Operate rotated files

`stack` writes one file without rotation; its name does not mean a stack of channels. Time channels rotate when a record arrives with a different suffix: no thread creates files during idle periods. `daily.at` computes the resolver's next rotation time, but the handler decides by suffix changes; do not assume a scheduler rotates precisely at the configured time.

The size limit is checked before writing against bytes already recorded; one entry can push a file beyond the limit before the next check. Retention counts files matching the pattern, ordered by mtime; it does not guarantee deletion at a precise age. Include available disk space and external retention in operations.

`switchChannel()` removes handlers before building the replacement. A `False` result after a failure does not mean the previous channel remains active. Check `getActiveChannel()` and report failure through an available operational channel. `reloadConfiguration()` rereads `app.config("logging")`: it does not automatically reload `.env` or Python files. Editing a file on disk does not itself change a running application's configuration.

### Extend output

`getLogger()` allows standard handlers. A subsequent reload or close may remove them: coordinate ownership. For a custom rotation policy, construct `AdvancedRotatingFileHandler` with a `SuffixResolver` implementation (`getSuffix`, `getNextRotationTime`); the built-in factory only knows the six documented names. `Logger` has no channel `extend()` registry. Replace `ILogger` in your provider for another global policy.

Locks are thread-level, not process-level. Workers using the same pattern can rotate or delete each other's files. Use per-worker paths or external aggregation infrastructure. Emission, compression, and cleanup are synchronous and can add event-loop latency.


### Rotation

Time channels use a suffix resolver and rotate when its suffix changes. Hourly uses `YYYY-MM-DD_HH`, daily `YYYY-MM-DD`, weekly the ISO year/week, and monthly `YYYY-MM`. `chunked` rotates when the tracked encoded byte size reaches `mb_size`, generates timestamp/counter suffixes, and gzip-compresses rotated files.

### Retention

Rotating handlers scan only files matching their path template, sort them by modification time, and delete entries beyond the configured backup count. Retention values represent channel periods: hours, days, weeks, months, or a file count—not a universal duration.

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

### Resolve deterministic time suffixes

```python
from datetime import UTC, datetime, time
from orionis.logging.handlers.daily_suffix_resolver import DailySuffixResolver
from orionis.logging.handlers.monthly_suffix_resolver import MonthlySuffixResolver
from orionis.logging.handlers.weekly_suffix_resolver import WeeklySuffixResolver

moment = datetime(2026, 10, 6, 15, 30, tzinfo=UTC)
assert DailySuffixResolver(time(2, 0)).getSuffix(moment) == "2026-10-06"
assert WeeklySuffixResolver().getSuffix(moment) == "2026-week41"
assert MonthlySuffixResolver().getSuffix(moment) == "2026-10"
print(DailySuffixResolver(time(2, 0)).getNextRotationTime(moment))
```

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



### Rotation internals

`RotatingHandlerFactory.createHandler(channel_name, channel_config, app_root)` returns a standard `FileHandler`, an `AdvancedRotatingFileHandler`, or `None` for an unsupported channel. Each `SuffixResolver` provides `getSuffix(dt=None)` and `getNextRotationTime(current_time)`.

## Implementation reference for extensions

| Path | Responsibility |
|---|---|
| `logger.py` | Lazy logger construction, levels, channel switch/reload, and cleanup. |
| `provider.py` | Container singleton and `Log` facade pinning. |
| `contracts/logger.py` | `ILogger` service contract. |
| `contracts/suffix_resolver.py` | Rotation suffix/time contract. |
| `handlers/rotating_handler_factory.py` | Channel-to-handler dispatch. |
| `handlers/advanced_rotating_file_handler.py` | Thread-safe writing, rotation, compression, and retention. |
| `handlers/*_suffix_resolver.py` | Hourly, daily, weekly, monthly, and chunk suffix policies. |

---

[Index](README.md) · [foundation](../../../foundation/docs/en/README.md)
