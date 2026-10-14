# Error policies and reference

## Public API

### `Catch(app)`

The only symbol exported by `orionis.failure`. Its async `exception(exception, request=None)` resolves and caches the application handler, reads the current scope's `kernel`, reports, and dispatches. Direct construction is primarily framework/testing infrastructure; applications normally use the support facade or receive `ICatch` through injection.

### `BaseExceptionHandler`

- `toThrowable(exception)` stringifies every exception argument and preserves the native traceback.
- `isExceptionIgnored(exception)` tests exact exception-class membership in `dont_catch`.
- `report(exception, log)` logs `[ClassName] message` and returns `Throwable`, or `None` when ignored.
- `handleCLI(exception, console)` delegates display to `console.exception` unless ignored.
- `handleHTTP(exception, request)` builds mapped, production, or debug responses.

### `Throwable`

A frozen, keyword-only, slotted dataclass with `classtype`, `message`, stringified `args`, and optional native `traceback`. It does not serialize or format itself.

### Contracts and facade

`ICatch` is exported from `orionis.failure.contracts`; `IBaseExceptionHandler` remains available from its defining module. The application facade is `orionis.support.facades.Catch`, distinct from the concrete package export.

## Configuration

This module has no dedicated config file. The default handler reads `app.debug`:

| Value | Unknown HTTP exception behavior |
|---|---|
| `False` | Sanitized status 500 with `Internal Server Error`. |
| `True` | Detailed exception response with request path/method. |

The exception handler class is registered through the application API. `dont_catch` is code-level handler policy, not an environment setting.

## Errors and edge cases

- Missing active scope or missing `kernel` raises `RuntimeError`; reporting cannot proceed safely.
- HTTP context with no usable request fails when the handler asks `wantsJson()`; always pass the request/adapter.
- `isExceptionIgnored` requires a `BaseException` instance and rejects other objects with `TypeError`.
- Ignore matching is exact by `type(exception)`, while HTTP mapping walks the exception MRO and therefore includes subclasses.
- If reporting itself raises, renderer dispatch does not occur.
- `KeyboardInterrupt`, `SystemExit`, and other `BaseException` subclasses can reach the API; ignore/handle them deliberately.

Mapped statuses are 401 authentication, 403 authorization, 404 route not found, 405 method not allowed, 413 payload too large, 415 unsupported media type, and 419 CSRF mismatch.

## Performance and concurrency

The first concurrent call resolves the exception handler behind an `asyncio.Lock`; later calls reuse it without locking. Scope and kernel are still fetched for every exception because they are context-local. `Throwable` conversion and mapping are small in-memory operations; logging and response rendering dominate cost.

The singleton keeps only the resolved handler, while request and exception state stay local to each coroutine. Custom handlers must follow the same rule to remain safe under concurrent HTTP requests.

## Compatibility

Orionis declares Python 3.14+. The module relies on Orionis HTTP, auth, logging, console, and container contracts and introduces no separate third-party dependency.


## Module structure

| Path | Responsibility |
|---|---|
| `catch.py` | Handler resolution, reporting, and kernel-context dispatch. |
| `base/handler.py` | Default reporting, CLI output, HTTP mapping, debug policy. |
| `entities/throwable.py` | Frozen, slotted structured exception record. |
| `enums/kernel_type.py` | `CONSOLE` and `HTTP` scope markers. |
| `contracts/` | Catch and exception-handler abstract interfaces. |
| `provider.py` | Singleton binding and facade pinning. |

## Evidence and next steps

[handler.py](../../base/handler.py) · [throwable.py](../../entities/throwable.py) · [handler.py](../../contracts/handler.py)

[Return to the module index](README.md).
