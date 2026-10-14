# Reporting and handling exceptions

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

## Core concepts

### Reporting before rendering

`Catch.exception()` always invokes `report` after it resolves the current kernel, then invokes the matching renderer. The application's container-aware `call()` performs parameter injection, supplying services such as `ILogger` and `Console` to default handler methods.

### Context dispatch

`KernelContext.CONSOLE` renders to console and returns `None`. `KernelContext.HTTP` returns a `Response` or `None`. Any other scope value still reports the exception but performs no rendering. Missing scope or missing `kernel` is a runtime configuration error.

### Public HTTP policy

Known framework exceptions map to stable public status/message pairs. Unknown errors expose details only when `app.debug` is true; production returns a generic `500 Internal Server Error`. Content negotiation is taken from `request.wantsJson()`.

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


### Use the facade in a booted application

```python
from orionis.support.facades import Catch

async def handle_failure(exception: BaseException, request):
    return await Catch.exception(exception, request)
```

## Integration with Orionis

`CatchProvider` is a core provider. It binds `ICatch` to the concrete `Catch` singleton under alias `x-orionis-ICatch`, then pins the support facade. HTTP kernel, console reactor, scheduler, and session middleware inject `ICatch` to funnel failures through one policy.

The application resolves its configured handler (defaulting to `BaseExceptionHandler`). Container method calls inject logging, console, and response collaborators. Token authentication failures also receive `WWW-Authenticate: Bearer` when the current auth guard is `token`.

## Turn a domain conflict into a response

Save this module as `app/exceptions/handler.py` and register `ExceptionHandler` with `app.withExceptionHandler(ExceptionHandler)` before `create()`. The handler retains native policy for other errors. Each error's state stays in local variables, not singleton attributes.

`Catch` calls `report` before rendering. This conflict therefore still uses inherited reporting. Do not add `OrderConflict` to `dont_catch` when you need the 409 response: that collection also suppresses rendering. To adjust logging policy, explicitly override `report` while retaining required injected dependencies. A logger failure interrupts the flow before rendering.

```python
from orionis.failure.base import BaseExceptionHandler
from orionis.http import JSONResponse, Response, Request
from orionis.http.adapters.request.contracts.transport import TransportAdapter

class OrderConflict(Exception):
    pass

class ExceptionHandler(BaseExceptionHandler):
    async def handleHTTP(
        self,
        exception: BaseException,
        request: Request | TransportAdapter,
    ) -> Response | None:
        if isinstance(exception, OrderConflict):
            return JSONResponse({"message": "Order already processed"}, status_code=409)
        return await super().handleHTTP(exception, request)
```

## Evidence and next steps

[catch.py](../../catch.py) · [handler.py](../../base/handler.py) · [provider.py](../../provider.py)

[Return to the module index](README.md).
