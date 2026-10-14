# Recording application events

The logger records application events in UTF-8 files with one active channel and severity filtering.

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

## Add logging to a service

Use `from orionis.support.facades import Log` after application initialization, or inject `ILogger` from `orionis.logging.contracts.logger`. Its synchronous methods accept a single `str` message: `info`, `warning`, `error`, `debug`, and `critical`. Do not add `await` or pass interpolation arguments as with the standard logger.

Include an operation identifier and a stable event, for example `Log.info("invoice=42 event=sent")`. Retain complete errors only where needed and remove secrets before constructing messages. Automatic redaction, request context, and a JSON formatter are not supplied. User-controlled newlines can make records ambiguous; normalize untrusted data before interpolation.

For exception tracebacks, obtain the standard logger with `getLogger()` and use its normal APIs, such as `.exception(...)` inside an `except` block. This uses the same file and shared handlers. The Orionis logger disables propagation: root logger handlers do not automatically receive these records.

Every wrapper uses the global name `__orionis__`. Initializing two isolated wrappers in one process can replace each other's handlers; applications should use the provider singleton. Examples with application doubles are isolated scenarios, not a recommendation to create one logger per request.


### Logger and channel

`Logger` wraps the standard logger named `__orionis__`, disables propagation, and sets the logger itself to `DEBUG`; the active handler enforces the configured threshold. A channel describes one handler and path policy. Only one channel is active at a time, even though several may be configured.

### Lazy initialization

Constructing `Logger` performs no filesystem work. The first message or `getLogger()` initializes under a lock with double checking. Formatter instances are shared by format/date-format key. `close()` removes and closes every owned handler and resets the wrapper so later use can initialize again.

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

### Use the application facade

```python
from orionis.support.facades import Log

Log.info("Request completed")
Log.warning("Retry budget is low")
Log.error("Job failed")
```

## Integration with Orionis

`LoggerProvider` binds `ILogger` to `Logger` as a singleton with alias `x-orionis-ILogger`, then pins `Log` during boot. Failure handling injects `ILogger`; background tasks use the facade to report success/failure. Other framework code can depend on the contract without knowing rotation details.

The standard logger name is shared process-wide. Creating or initializing another Orionis `Logger` closes and replaces handlers on that same logger, so application code should use the provider singleton.



### `Logger(app)`

- `info(message)`, `error(message)`, `warning(message)`, `debug(message)`, and `critical(message)` forward strings to the standard logger.
- `getLogger()` returns the configured `logging.Logger` for advanced standard-library features.
- `switchChannel(name)` replaces the handler and returns whether it succeeded.
- `reloadConfiguration()` closes handlers, rereads `app.config("logging")`, rebuilds, and records a success message.
- `close()` releases file handles and permits later lazy reconstruction.
- `getActiveChannels()` / `getActiveChannel()` report handler-cache state.
- `getAvailableChannels()` reports names in configuration without initializing I/O.

---

[Index](README.md) · [foundation](../../../foundation/docs/en/README.md) · [failure](../../../failure/docs/en/README.md)
