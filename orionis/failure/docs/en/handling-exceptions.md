# Handling exceptions

## Application entry points

Register an application subclass with `app.withExceptionHandler(ExceptionHandler)` before `create()`. Both methods return the inherited result so the runtime receives the selected plan:

```python
from orionis.failure.base import BaseExceptionHandler
from orionis.failure.entities import FailureContext, FailureHandling


class ExceptionHandler(BaseExceptionHandler):
    async def handleFailure(
        self,
        exception: BaseException,
        context: FailureContext,
    ) -> FailureHandling | None:
        return await super().handleFailure(exception, context)

    async def handleResult(
        self,
        value: object,
        context: FailureContext,
    ) -> FailureHandling | None:
        return await super().handleResult(value, context)
```

`IBaseExceptionHandler` declares exactly these two abstract hooks. Extending `BaseExceptionHandler` supplies both defaults. Implementing the contract directly requires both methods. The application prepares and reuses one handler outside request scopes; constructor dependencies must have compatible lifetimes.

Returning `None` selects no deferred effects. Merely awaiting `super().handleFailure(...)` and discarding its return therefore drops default logging and presentation. Do not call capture again from a hook or store per-incident state on the shared handler.

## One incident, one deferred plan

1. An execution boundary supplies the original exception and immutable `FailureContext` to the runtime.
2. The runtime deduplicates propagation within the operation and invokes `handleFailure` once for that incident.
3. `BaseExceptionHandler` constructs a `FailureHandling` plan without logging or rendering. The runtime calls its `complete()` under recursion, timeout, and fallback safeguards.
4. When an HTTP or CLI owner needs output, `Catch.exception()` uses the same plan's `present(flow=..., request=...)`. It does not invoke another application hook. Other owners retain their own recovery, protocol response, or propagation behavior.

The plan belongs to the incident, not the shared handler. `complete()` executes its optional asynchronous `logging()` callback once. `present()` executes its optional asynchronous `presentation(*, flow, request=None)` callback once and caches the result. A failed callback is retained and is not retried by repeated calls. Do not execute these methods inside the application hook.

The default logging action resolves `ILogger` and writes one exception record using `Throwable` and the original traceback. `context.expected=True` skips this logging action. Exact classes in `dont_catch` skip logging and presentation, while the hook still receives the original exception. During final shutdown, `context.reporting_allowed=False` also prevents the base plan from scheduling logging; custom logging policy must honor that flag.

`handleResult` receives a declared failed result without constructing an exception or traceback. Its base implementation returns `None`. A custom implementation can return a plan for deferred logging; capturing that result does not replace the original value or automatically present an HTTP/CLI response.

## Customize an HTTP response

This application handler turns a domain conflict into HTTP 409 while retaining inherited logging and CLI output. It uses local variables so concurrent incidents cannot overwrite one another. The inherited presentation callback is kept before replacing it; calling the plan's own `present()` inside that callback would recurse.

```python
from orionis.failure.base import BaseExceptionHandler
from orionis.failure.entities import FailureContext, FailureHandling
from orionis.http import JSONResponse


class OrderConflict(Exception):
    pass


class ExceptionHandler(BaseExceptionHandler):
    async def handleFailure(
        self,
        exception: BaseException,
        context: FailureContext,
    ) -> FailureHandling | None:
        plan = await super().handleFailure(exception, context)
        if not isinstance(exception, OrderConflict) or self.isExceptionIgnored(
            exception
        ):
            return plan

        inherited_presentation = plan.presentation

        async def present(*, flow: str, request: object | None = None) -> object:
            if flow == "http":
                return JSONResponse(
                    {"message": "Order already processed"},
                    status_code=409,
                )
            if inherited_presentation is not None:
                return await inherited_presentation(flow=flow, request=request)
            return None

        plan.presentation = present
        return plan
```

Register this class before startup. Do not add `OrderConflict` to `dont_catch` if its 409 response is required, since that policy suppresses presentation too. To suppress only logging for a selected business exception, set the returned plan's `logging` to `None`. To replace logging, supply an async callback that honors `context.reporting_allowed`; leave execution to the runtime.

## Default HTTP and CLI policy

`Catch.exception()` reads the active scope's `kernel`. `KernelContext.CONSOLE` requests `flow="cli"` and the base plan calls `Console.exception`. `KernelContext.HTTP` requests `flow="http"` with the request or adapter. Other kernel values request no presentation. Missing scope or `kernel` raises `RuntimeError`.

Known HTTP exceptions map to stable public status/message pairs, including subclasses. Unknown errors expose detail only when `app.debug` is true; production returns a generic `500 Internal Server Error`. JSON or HTML follows `request.wantsJson()`. Token authentication failures also receive `WWW-Authenticate: Bearer` when the current auth guard is `token`.

Inside an existing booted HTTP execution boundary, use the facade when that boundary owns the response:

```python
from orionis.support.facades import Catch


async def handle_failure(exception: BaseException, request):
    return await Catch.exception(exception, request)
```

A logging failure does not itself prevent presentation. The runtime contains hook/logging failures and writes bounded emergency diagnostics to stderr using incident identity and exception types. It avoids sensitive exception messages and protocol stdout. Cancellation and process-control exceptions retain their control-flow behavior.

## Capture after startup

HTTP and CLI activate observation after successful startup; HTTP without lifespan activates it after lazy kernel initialization. `create()` alone does not activate this guarantee. For headless execution, finish `await app.boot()` and own an explicit execution boundary:

```python
from orionis.failure.runtime import capture, operation

await app.boot()
try:
    with operation(app, flow="worker", operation="import", isolated=True):
        try:
            await service.run()
        except Exception as error:
            await capture(error, phase="execution")
            raise
finally:
    await app.aclose()
```

`operation()` establishes context and deduplication; it does not automatically catch errors. Its owner notifies and preserves propagation, response, or recovery. Keep stream consumption inside the boundary. `Loop.createTask` tasks created there are supervised; arbitrary external `asyncio.create_task` calls require their own explicit owner.

`aclose()` releases the headless owner, cancels and drains supervised tasks when the last owner finishes, then closes logging. It does not run HTTP lifecycle callbacks. Observation remains available during cleanup, with logging disabled as reporting resources close.

The injected service also supports `await catch.capture(error, context=FailureContext(flow="worker", phase="execution"))`. `FailureReceipt` distinguishes delivery, reporting, duplication, and degradation; `None` means no active runtime or an excluded control-flow exception. Repeated propagation within one operation shares the incident; independent attempts and operations remain distinct.

Context contains origin, phase, correlation, `expected`, `reporting_allowed`, and bounded scalar metadata. It contains no request, socket, or scope. Keep the live request in the execution owner and pass it only when presentation is needed. No global Python exception hooks observe arbitrary external code, and failures before startup remain outside the runtime guarantee.

## Sources and next steps

[Catch](../../catch.py) · [Base handler](../../base/handler.py) · [Handling plan](../../entities/handling.py) · [Runtime](../../runtime.py)

[Return to the module index](README.md).
