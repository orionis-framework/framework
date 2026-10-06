# orionis.logging

> API reference derived from the current implementation.

## Table of contents

- Requirements
- Functional overview
- Module structure
- API reference
- Usage examples
- Design characteristics
- Performance and concurrency
- Compatibility notes
- Verification and limitations

## Requirements

Python 3.14 or newer, as declared by pyproject.toml.

## Functional overview

The orionis.logging initializer exports 1 public symbols. This reference uses __all__, export routes, and current source files as evidence.

## Module structure

| Path | Responsibility |
| --- | --- |
| ../__init__.py | Defines package exports. |
| orionis.logging/ | Implementations and subpackages for those exports. |

## API reference

| Symbol | Verified import | Source | Declaration | Observed behavior |
| --- | --- | --- | --- | --- |
| Logger | from orionis.logging import Logger | [logger.py](../logger.py) | Logger | Exported public constant or alias. |
| Logger.info | from orionis.logging import Logger | [logger.py](../logger.py) | def info(self, message: str) -> None | Log an informational message. Parameters ---------- message : str The message to log. Returns ------- None This method does not return a value. |
| Logger.error | from orionis.logging import Logger | [logger.py](../logger.py) | def error(self, message: str) -> None | Log an error message. Parameters ---------- message : str Error message to log. Returns ------- None This method does not return a value. |
| Logger.warning | from orionis.logging import Logger | [logger.py](../logger.py) | def warning(self, message: str) -> None | Log a warning message. Parameters ---------- message : str Warning message to log. Returns ------- None This method does not return a value. |
| Logger.debug | from orionis.logging import Logger | [logger.py](../logger.py) | def debug(self, message: str) -> None | Log a debug message. Parameters ---------- message : str Debug message to log. Returns ------- None This method does not return a value. |
| Logger.critical | from orionis.logging import Logger | [logger.py](../logger.py) | def critical(self, message: str) -> None | Log a critical message. Parameters ---------- message : str Critical message to log. Returns ------- None This method does not return a value. |
| Logger.getLogger | from orionis.logging import Logger | [logger.py](../logger.py) | def getLogger(self) -> logging.Logger | Return the internal logger instance for advanced usage. Returns ------- logging.Logger The configured logger instance. Raises ------ RuntimeError If the logger is not available. |
| Logger.reloadConfiguration | from orionis.logging import Logger | [logger.py](../logger.py) | def reloadConfiguration(self) -> None | Reload the logger configuration from the application. This method allows dynamic reloading of logger settings without restarting the application. Returns ------- None This method does not return a value. |
| Logger.switchChannel | from orionis.logging import Logger | [logger.py](../logger.py) | def switchChannel(self, channel_name: str) -> bool | Switch to a different logging channel. Initialize the logger when needed, close current handlers, clear caches, and create a new handler for the specified channel. Only one channel is active at a time. Parameters ---------- channel_name : str Name of the channel to switch to. Returns ------- bool True if the switch was successful, False otherwise. |
| Logger.close | from orionis.logging import Logger | [logger.py](../logger.py) | def close(self) -> None | Close all handlers and release logger resources. This method should be called when the logger is no longer needed to ensure that all file handles and resources are properly released. Returns ------- None This method does not return a value. |
| Logger.getActiveChannels | from orionis.logging import Logger | [logger.py](../logger.py) | def getActiveChannels(self) -> list[str] | Return the names of active logging channels. Returns ------- list[str] List containing the names of active logging channels. |
| Logger.getActiveChannel | from orionis.logging import Logger | [logger.py](../logger.py) | def getActiveChannel(self) -> str / None | Return the name of the currently active logging channel. Returns ------- str / None The name of the active channel, or None if no channel is active. |
| Logger.getAvailableChannels | from orionis.logging import Logger | [logger.py](../logger.py) | def getAvailableChannels(self) -> list[str] | Return all available logging channels from configuration. Returns ------- list[str] List of all configured channel names. |

## Usage examples

    from orionis.logging import Logger

The import path matches the API table. Import status: executed successfully under Python 3.14.3.

## Design characteristics

The package uses an explicit public surface. Private names are excluded; declarations link to their concrete owner.

## Performance and concurrency

No uniform guarantee is declared at package level. Inspect each linked file for I/O, coroutines, caches, locks, and shared state.

## Compatibility notes

Declared minimum: Python 3.14. Validation used Python 3.14.3. Dependency bounds are in pyproject.toml.

## Verification and limitations

Python files were analysed and exports verified. Failures from dependencies, callbacks, I/O, or configuration may propagate and are not presented as exhaustive.
