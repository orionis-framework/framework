# orionis.failure

> `orionis.failure` centralizes exception reporting and renders context-aware CLI or HTTP failures for Orionis.

## Overview

`Catch` is the package-level service that receives an exception, lazily resolves the application's exception handler, reports the exception, and dispatches rendering according to the active kernel scope. Console contexts use `handleCLI`; HTTP contexts use `handleHTTP`; unknown contexts report only.

`BaseExceptionHandler` supplies the default policy: structured `Throwable` conversion, logging, CLI rendering, known HTTP status mapping, sanitized production 500 responses, and detailed debug responses. Applications can register another handler through the application API as long as it satisfies `IBaseExceptionHandler`.

## Requirements

- Python 3.14 or newer.
- A booted Orionis application/container for `Catch.exception()` or the `Catch` facade.
- An active application scope containing the `kernel` context.
- A request or transport adapter when handling an HTTP exception.
- Logging, console, and default-response services resolvable for the selected handler method.

## Quick start

```python
from orionis.failure.base import BaseExceptionHandler

handler = BaseExceptionHandler(object(), object())
error = ValueError("invalid value", 7)
throwable = handler.toThrowable(error)

assert throwable.classtype is ValueError
assert throwable.message == "invalid value"
assert throwable.args == ("invalid value", "7")
print(throwable.classtype.__name__, throwable.message)
```

Validation: **Executed successfully** on CPython 3.14.6; only the dependency-free conversion path was exercised.

## Core concepts

### Reporting before rendering

`Catch.exception()` always invokes `report` after it resolves the current kernel, then invokes the matching renderer. The application's container-aware `call()` performs parameter injection, supplying services such as `ILogger` and `Console` to default handler methods.

### Context dispatch

`KernelContext.CONSOLE` renders to console and returns `None`. `KernelContext.HTTP` returns a `Response` or `None`. Any other scope value still reports the exception but performs no rendering. Missing scope or missing `kernel` is a runtime configuration error.

### Public HTTP policy

Known framework exceptions map to stable public status/message pairs. Unknown errors expose details only when `app.debug` is true; production returns a generic `500 Internal Server Error`. Content negotiation is taken from `request.wantsJson()`.

## Module structure

| Path | Responsibility |
|---|---|
| `catch.py` | Handler resolution, reporting, and kernel-context dispatch. |
| `base/handler.py` | Default reporting, CLI output, HTTP mapping, debug policy. |
| `entities/throwable.py` | Frozen, slotted structured exception record. |
| `enums/kernel_type.py` | `CONSOLE` and `HTTP` scope markers. |
| `contracts/` | Catch and exception-handler abstract interfaces. |
| `provider.py` | Singleton binding and facade pinning. |

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

## Common workflows

### Customize ignored exceptions

Set a handler subclass's class-level `dont_catch` to a `frozenset` of exact classes. Matching exceptions skip logging and rendering. Subclasses are not implicitly ignored, which prevents unexpectedly suppressing broader error families.

### Install a custom handler

Subclass or implement `IBaseExceptionHandler`, preserve the injectable method signatures, then register it through the application's exception-handler configuration API. `Catch` resolves it once and reuses it.

### Return safe API failures

Raise the framework's authentication, authorization, routing, payload, media-type, or CSRF exceptions. The default handler maps them independently of debug mode and asks `DefaultResponses` for JSON or HTML according to the request.

## Examples

### Ignore one exact exception class

```python
from orionis.failure.base import BaseExceptionHandler


class QuietError(Exception):
    pass


class ChildError(QuietError):
    pass


handler = BaseExceptionHandler(object(), object())
BaseExceptionHandler.dont_catch = frozenset({QuietError})
assert handler.isExceptionIgnored(QuietError("quiet"))
assert not handler.isExceptionIgnored(ChildError("child"))
BaseExceptionHandler.dont_catch = frozenset()
print("exact matching ok")
```

Validation: **Executed successfully** on CPython 3.14.6; shared class state was restored.

### Report through a logger

```python
import asyncio
from orionis.failure.base import BaseExceptionHandler


class Log:
    def __init__(self) -> None:
        self.messages = []

    def error(self, message: str) -> None:
        self.messages.append(message)


handler = BaseExceptionHandler(object(), object())
log = Log()
result = asyncio.run(handler.report(RuntimeError("boom"), log))
assert result is not None
assert log.messages == ["[RuntimeError] boom"]
print(log.messages[0])
```

Validation: **Executed successfully** on CPython 3.14.6.

### Dispatch a console failure

```python
import asyncio
from orionis.failure import Catch
from orionis.failure.enums import KernelContext


class Scope:
    async def get(self, name: str):
        assert name == "kernel"
        return KernelContext.CONSOLE


class Handler:
    def __init__(self) -> None:
        self.calls = []

    async def report(self, exception: BaseException) -> None:
        self.calls.append(("report", str(exception)))

    async def handleCLI(self, exception: BaseException) -> None:
        self.calls.append(("cli", str(exception)))


class App:
    def __init__(self) -> None:
        self.handler = Handler()

    async def getExceptionHandler(self):
        return self.handler

    def getCurrentScope(self):
        return Scope()

    async def call(self, target, method: str, **kwargs):
        return await getattr(target, method)(**kwargs)


app = App()
assert asyncio.run(Catch(app).exception(RuntimeError("boom"))) is None
assert app.handler.calls == [("report", "boom"), ("cli", "boom")]
print(app.handler.calls)
```

Validation: **Executed successfully** on CPython 3.14.6 with an isolated application double.

### Map a route failure to HTTP 404

```python
import asyncio
from orionis.failure.base import BaseExceptionHandler
from orionis.http.routes.exceptions.route_not_found import RouteNotFound


class Responses:
    async def error(self, **kwargs):
        return kwargs

    async def exception(self, **kwargs):
        return kwargs


class App:
    def config(self, name: str):
        assert name == "app.debug"
        return False


class Request:
    path = "/missing"
    method = "GET"

    def wantsJson(self) -> bool:
        return True


handler = BaseExceptionHandler(Responses(), App())
response = asyncio.run(handler.handleHTTP(RouteNotFound("missing"), Request()))
assert response == {
    "status_code": 404,
    "content": "Route not found",
    "expects_json": True,
}
print(response["status_code"], response["content"])
```

Validation: **Executed successfully** on CPython 3.14.6; output was `404 Route not found`.

### Use the facade in a booted application

```python
from orionis.support.facades import Catch

response = await Catch.exception(exception, request)
```

Validation: **Import-only** on CPython 3.14.6; the illustrative variables and active scope come from a running kernel.

## Configuration

This module has no dedicated config file. The default handler reads `app.debug`:

| Value | Unknown HTTP exception behavior |
|---|---|
| `False` | Sanitized status 500 with `Internal Server Error`. |
| `True` | Detailed exception response with request path/method. |

The exception handler class is registered through the application API. `dont_catch` is code-level handler policy, not an environment setting.

## Integration with Orionis

`CatchProvider` is a core provider. It binds `ICatch` to the concrete `Catch` singleton under alias `x-orionis-ICatch`, then pins the support facade. HTTP kernel, console reactor, scheduler, and session middleware inject `ICatch` to funnel failures through one policy.

The application resolves its configured handler (defaulting to `BaseExceptionHandler`). Container method calls inject logging, console, and response collaborators. Token authentication failures also receive `WWW-Authenticate: Bearer` when the current auth guard is `token`.

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

Orionis declares Python 3.14+. The module relies on Orionis HTTP, auth, logging, console, and container contracts and introduces no separate third-party dependency. Validation used CPython 3.14.6 on Windows.

## Verification notes

Validation used CPython 3.14.6. Exports, contracts, catch dispatcher, base handler, HTTP mappings, entity, enum, provider, facade, kernels, and `tests/failure` were inspected. All 91 failure tests passed through the Orionis runner. Five direct programs executed successfully; the facade snippet was import-validated only.
