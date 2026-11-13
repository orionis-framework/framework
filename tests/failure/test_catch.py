# ruff: noqa: PT009, PT027, SLF001, TC001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# The real container inspects these handler callback annotations at runtime.
"""Exercise one failure hook followed by deferred transport presentation."""

import asyncio
import inspect
import io
from contextlib import redirect_stderr
from typing import get_args
from unittest.mock import AsyncMock

from orionis.container.container import Container
from orionis.failure.catch import Catch
from orionis.failure.contracts.catch import ICatch
from orionis.failure.entities.context import FailureContext
from orionis.failure.entities.handling import FailureHandling
from orionis.failure.enums.kernel_type import KernelContext
from orionis.failure.runtime import FailureRuntime, capture, operation
from orionis.http.adapters.request.contracts.transport import TransportAdapter
from tests.support.failure_runtime import IsolatedFailureTestCase


class _Handler:
    """Select logging and presentation while recording their execution order."""

    def __init__(self) -> None:
        """Initialize isolated state for this failure fixture."""
        self.effects = []
        self.failures = []
        self.presentations = []

    async def handleFailure(
        self,
        exception: BaseException,
        context: FailureContext,
    ) -> FailureHandling | None:
        """Select or fail the configured exception policy for this scenario.

        Parameters
        ----------
        exception : BaseException
            Original exception supplied to the callback.
        context : FailureContext
            Immutable failure metadata supplied by the runtime.

        Returns
        -------
        FailureHandling | None
            Selected deferred handling plan.
        """
        self.effects.append("hook")
        self.failures.append((exception, context))

        async def log() -> None:
            """Execute the fixture reporting effect for the current incident."""
            self.effects.append("logging")

        async def present(*, flow: str, request: object | None = None) -> object:
            """Execute the scenario-specific presentation effect.

            Parameters
            ----------
            flow : str
                Presentation flow selected by the execution owner.
            request : object | None
                Live presentation payload supplied by the owner.

            Returns
            -------
            object
                Value returned by the configured fixture operation.
            """
            self.effects.append("presentation")
            self.presentations.append((exception, flow, request))
            return request if flow == "http" else None

        return FailureHandling(logging=log, presentation=present)

    async def handleResult(
        self,
        _value: object,
        _context: FailureContext,
    ) -> FailureHandling | None:
        """Record the declared result and select the configured deferred effects.

        Parameters
        ----------
        _value : object
            Declared failed result supplied by the owner.
        _context : FailureContext
            Immutable failure metadata supplied by the runtime.
        """
        return None


def _application(*, active: bool = False) -> tuple[Container, _Handler]:
    """Use real DI invocation without any application bootstrap or services."""
    app = object.__new__(Container)
    Container.__init__(app)
    handler = _Handler()
    app.getExceptionHandler = AsyncMock(return_value=handler)
    if active:
        app._failure_runtime = FailureRuntime(app, handler)
        app._failure_runtime.activate(object())
    return app, handler


class TestCatch(IsolatedFailureTestCase):
    """Verify native transport ownership and one observation per incident."""

    def testContractAndTransportRequestAnnotation(self) -> None:
        """Preserve transport adapter typing and the injectable Catch contract."""
        self.assertTrue(issubclass(Catch, ICatch))
        annotation = inspect.signature(Catch.exception).parameters["request"].annotation
        self.assertIn(TransportAdapter, get_args(annotation))

    async def testNoActiveScopeRaises(self) -> None:
        """Reject presentation without a scope that owns transport state."""
        app, _ = _application()
        with self.assertRaises(RuntimeError):
            await Catch(app).exception(RuntimeError("no scope"))
        app.getExceptionHandler.assert_not_awaited()

    async def testNoKernelRaises(self) -> None:
        """Reject presentation when the active scope has no transport kernel."""
        app, _ = _application()
        async with app.beginScope():
            with self.assertRaises(RuntimeError):
                await Catch(app).exception(RuntimeError("no kernel"))
        app.getExceptionHandler.assert_not_awaited()

    async def testStandaloneConsoleCompletesPlanBeforeRendering(self) -> None:
        """Verify standalone console completes plan before rendering.

        A standalone Catch preserves CLI output and logging order.
        """
        app, handler = _application()
        error = ValueError("console")
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.CONSOLE)
            self.assertIsNone(await Catch(app).exception(error))
        self.assertEqual(handler.effects, ["hook", "logging", "presentation"])
        self.assertEqual(handler.presentations, [(error, "cli", None)])
        self.assertEqual(handler.failures[0][1].flow, "cli")

    async def testStandaloneHttpPassesRequestAndReturnsResponse(self) -> None:
        """Verify standalone http passes request and returns response.

        A unified plan retains the caller's HTTP response and live request.
        """
        app, handler = _application()
        request = object()
        error = ValueError("http")
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.HTTP)
            response = await Catch(app).exception(error, request)
        self.assertIs(response, request)
        self.assertEqual(handler.effects, ["hook", "logging", "presentation"])
        self.assertEqual(handler.presentations, [(error, "http", request)])
        self.assertEqual(handler.failures[0][1].flow, "http")

    async def testUnknownKernelHasNoPresentation(self) -> None:
        """Verify unknown kernel has no presentation.

        Unknown kernels may observe failures without formatting a response.
        """
        app, handler = _application()
        async with app.beginScope() as scope:
            scope.set("kernel", "unknown")
            self.assertIsNone(await Catch(app).exception(ValueError("unknown")))
        self.assertEqual(handler.effects, ["hook", "logging"])
        self.assertEqual(handler.presentations, [])

    async def testHandlerIsResolvedOnceForSequentialCalls(self) -> None:
        """Verify handler is resolved once for sequential calls.

        A standalone Catch shares the resolved handler across incidents.
        """
        app, handler = _application()
        catch = Catch(app)
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.CONSOLE)
            await catch.exception(ValueError("first"))
            await catch.exception(ValueError("second"))
        app.getExceptionHandler.assert_awaited_once()
        self.assertEqual(len(handler.failures), 2)

    async def testHandlerResolutionIsSharedAcrossConcurrentCalls(self) -> None:
        """Verify handler resolution is shared across concurrent calls.

        Overlapping first use resolves one handler and handles each incident.
        """
        app, handler = _application()

        async def resolve() -> _Handler:
            """Resolve or suspend the handler according to the fixture scenario.

            Returns
            -------
            _Handler
                Value returned by the configured fixture operation.
            """
            await asyncio.sleep(0)
            return handler

        app.getExceptionHandler.side_effect = resolve
        catch = Catch(app)
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.CONSOLE)
            await asyncio.gather(*(catch.exception(ValueError()) for _ in range(8)))
        app.getExceptionHandler.assert_awaited_once()
        self.assertEqual(len(handler.failures), 8)

    async def testStandaloneResolutionDoesNotRetainTheRequestScope(self) -> None:
        """Verify standalone resolution does not retain the request scope.

        Standalone handling uses the same scope-free preparation as runtime.
        """
        app, handler = _application()
        resolved_scopes = []

        async def resolve() -> _Handler:
            """Resolve or suspend the handler according to the fixture scenario.

            Returns
            -------
            _Handler
                Value returned by the configured fixture operation.
            """
            resolved_scopes.append(app.getCurrentScope())
            return handler

        app.getExceptionHandler.side_effect = resolve
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.CONSOLE)
            await Catch(app).exception(ValueError("standalone"))
            self.assertIs(app.getCurrentScope(), scope)
        self.assertEqual(resolved_scopes, [None])

    async def testCaptureThenCatchUsesOnePlan(self) -> None:
        """Verify capture then catch uses one plan.

        An already observed error renders without a second hook or log.
        """
        app, handler = _application(active=True)
        error = ValueError("original")
        request = object()
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.HTTP)
            with operation(app, flow="http"):
                await capture(error, flow="http", phase="execution")
                catch = Catch(app)
                self.assertIs(await catch.exception(error, request), request)
                self.assertIs(await catch.exception(error, request), request)
        self.assertEqual(handler.effects, ["hook", "logging", "presentation"])
        self.assertEqual(handler.failures[0][1].phase, "execution")

    async def testDirectCatchRetainsTheOwningOperationContext(self) -> None:
        """Verify direct catch retains the owning operation context.

        Pass the original operation name and correlation to direct handling.
        """
        app, handler = _application(active=True)
        error = ValueError("original")
        request = object()
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.HTTP)
            with operation(
                app,
                flow="http",
                operation="orders.create",
                correlation_id="request-17",
            ):
                self.assertIs(await Catch(app).exception(error, request), request)
        self.assertEqual(len(handler.failures), 1)
        self.assertIs(handler.failures[0][0], error)
        context = handler.failures[0][1]
        self.assertEqual(context.operation, "orders.create")
        self.assertEqual(context.correlation_id, "request-17")
        self.assertEqual(handler.effects, ["hook", "logging", "presentation"])

    async def testConcurrentCaptureAndCatchWaitForOriginalPlan(self) -> None:
        """Verify concurrent capture and catch wait for original plan.

        Presentation waits for an in-flight hook and reuses its only plan.
        """
        app, handler = _application(active=True)
        entered = asyncio.Event()
        release = asyncio.Event()
        original_hook = handler.handleFailure

        async def delayed(
            exception: BaseException,
            context: FailureContext,
        ) -> FailureHandling:
            """Delay the delegated operation until the test releases it.

            Parameters
            ----------
            exception : BaseException
                Original exception supplied to the callback.
            context : FailureContext
                Immutable failure metadata supplied by the runtime.

            Returns
            -------
            FailureHandling
                Selected deferred handling plan.
            """
            entered.set()
            await release.wait()
            return await original_hook(exception, context)

        handler.handleFailure = delayed
        error = ValueError("original")
        request = object()
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.HTTP)
            with operation(app, flow="http"):
                capturing = asyncio.create_task(capture(error))
                await entered.wait()
                presenting = asyncio.create_task(Catch(app).exception(error, request))
                try:
                    await asyncio.sleep(0)
                    self.assertFalse(presenting.done())
                    release.set()
                    await capturing
                    self.assertIs(await presenting, request)
                finally:
                    release.set()
                    await asyncio.gather(capturing, presenting, return_exceptions=True)
        self.assertEqual(handler.effects, ["hook", "logging", "presentation"])

    async def testNestedPropagationKeepsTheOriginallySelectedPlan(self) -> None:
        """Verify nested propagation keeps the originally selected plan.

        An isolated child transfers its existing plan to the HTTP owner.
        """
        app, handler = _application(active=True)
        error = ValueError("original")
        request = object()
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.HTTP)
            with operation(app, flow="http"):
                try:
                    with operation(isolated=True):
                        await capture(error)
                        raise error
                except ValueError:
                    self.assertIs(await Catch(app).exception(error, request), request)
        self.assertEqual(handler.effects, ["hook", "logging", "presentation"])

    async def testNonePlanSuppressesDefaultEffects(self) -> None:
        """Verify none plan suppresses default effects.

        A deliberate policy result must not trigger a second default handler.
        """
        app, handler = _application(active=True)
        handler.handleFailure = AsyncMock(return_value=None)
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.HTTP)
            with operation(app, flow="http"):
                result = await Catch(app).exception(ValueError("silent"), object())
        self.assertIsNone(result)
        handler.handleFailure.assert_awaited_once()
        self.assertEqual(handler.effects, [])

    async def testCancelledPresentationWaiterDoesNotCancelCapture(self) -> None:
        """Verify cancelled presentation waiter does not cancel capture.

        A cancelled HTTP waiter leaves the original delivery available.
        """
        app, handler = _application(active=True)
        entered = asyncio.Event()
        release = asyncio.Event()
        original_hook = handler.handleFailure

        async def delayed(
            exception: BaseException,
            context: FailureContext,
        ) -> FailureHandling:
            """Delay the delegated operation until the test releases it.

            Parameters
            ----------
            exception : BaseException
                Original exception supplied to the callback.
            context : FailureContext
                Immutable failure metadata supplied by the runtime.

            Returns
            -------
            FailureHandling
                Selected deferred handling plan.
            """
            entered.set()
            await release.wait()
            return await original_hook(exception, context)

        handler.handleFailure = delayed
        error = ValueError("original")
        request = object()
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.HTTP)
            with operation(app, flow="http"):
                capturing = asyncio.create_task(capture(error))
                await entered.wait()
                presenting = asyncio.create_task(Catch(app).exception(error, request))
                try:
                    await asyncio.sleep(0)
                    presenting.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await presenting
                    self.assertFalse(capturing.done())
                    release.set()
                    await capturing
                    self.assertIs(await Catch(app).exception(error, request), request)
                finally:
                    release.set()
                    await asyncio.gather(capturing, presenting, return_exceptions=True)
        self.assertEqual(handler.effects, ["hook", "logging", "presentation"])

    async def testPresentationFailurePreservesPrimaryAndDoesNotRetry(self) -> None:
        """Retain the primary cause and diagnose a failing presenter once."""
        app, handler = _application(active=True)
        error = ValueError("private primary")
        cause = LookupError("private cause")
        error.__cause__ = cause
        secondary = OSError("private presentation")
        presentation = AsyncMock(side_effect=secondary)
        handler.handleFailure = AsyncMock(
            return_value=FailureHandling(
                presentation=presentation,
            ),
        )
        diagnostics = io.StringIO()
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.HTTP)
            with operation(app, flow="http"), redirect_stderr(diagnostics):
                for _ in range(2):
                    with self.assertRaises(ValueError) as raised:
                        await Catch(app).exception(error, object())
                    self.assertIs(raised.exception, error)
        self.assertIs(error.__cause__, cause)
        handler.handleFailure.assert_awaited_once()
        presentation.assert_awaited_once()
        self.assertEqual(diagnostics.getvalue().count("OSError"), 1)
        self.assertNotIn("private", diagnostics.getvalue())

    async def testPresentationTimeoutPreservesThePrimary(self) -> None:
        """Bound a cooperative presenter and retain its failed plan."""
        app, handler = _application(active=True)
        app._failure_runtime.timeout = 0.01
        entered = asyncio.Event()

        async def present(**_kwargs: object) -> object:
            """Execute the scenario-specific presentation effect.

            Parameters
            ----------
            _kwargs : object
                Keyword arguments forwarded to the native operation.
            """
            entered.set()
            await asyncio.Event().wait()

        presentation = AsyncMock(side_effect=present)
        handler.handleFailure = AsyncMock(
            return_value=FailureHandling(
                presentation=presentation,
            ),
        )
        error = ValueError("original")
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.HTTP)
            with operation(app, flow="http"), redirect_stderr(io.StringIO()):
                async with asyncio.timeout(1):
                    with self.assertRaises(ValueError) as raised:
                        await Catch(app).exception(error, object())
                self.assertIs(raised.exception, error)
        self.assertTrue(entered.is_set())
        presentation.assert_awaited_once()

    async def testPresentationReentryDoesNotWaitForItsOwnPlan(self) -> None:
        """Verify presentation reentry does not wait for its own plan.

        A presenter can encounter Catch without deadlocking or reporting again.
        """
        app, handler = _application(active=True)
        error = ValueError("original")
        request = object()
        nested = []

        async def present(**_kwargs: object) -> object:
            """Execute the scenario-specific presentation effect.

            Parameters
            ----------
            _kwargs : object
                Keyword arguments forwarded to the native operation.

            Returns
            -------
            object
                Value returned by the configured fixture operation.
            """
            nested.append(await Catch(app).exception(error, request))
            return request

        presentation = AsyncMock(side_effect=present)
        handler.handleFailure = AsyncMock(
            return_value=FailureHandling(
                presentation=presentation,
            ),
        )
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.HTTP)
            with operation(app, flow="http"):
                async with asyncio.timeout(1):
                    self.assertIs(await Catch(app).exception(error, request), request)
        self.assertEqual(nested, [None])
        handler.handleFailure.assert_awaited_once()
        presentation.assert_awaited_once()

    async def testInternalPresentationCancellationPreservesThePrimary(self) -> None:
        """Verify internal presentation cancellation preserves the primary.

        An internally cancelled presenter does not cancel the HTTP owner.
        """
        app, handler = _application(active=True)
        handler.handleFailure = AsyncMock(
            return_value=FailureHandling(
                presentation=AsyncMock(side_effect=asyncio.CancelledError()),
            ),
        )
        error = ValueError("original")
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.HTTP)
            with (
                redirect_stderr(io.StringIO()),
                self.assertRaises(ValueError) as raised,
            ):
                await Catch(app).exception(error, object())
        self.assertIs(raised.exception, error)

    async def testCallerCancellationDuringPresentationStillPropagates(self) -> None:
        """Keep genuine cancellation and never retry partially executed output."""
        app, handler = _application(active=True)
        entered = asyncio.Event()

        async def present(**_kwargs: object) -> object:
            """Execute the scenario-specific presentation effect.

            Parameters
            ----------
            _kwargs : object
                Keyword arguments forwarded to the native operation.
            """
            entered.set()
            await asyncio.Event().wait()

        presentation = AsyncMock(side_effect=present)
        handler.handleFailure = AsyncMock(
            return_value=FailureHandling(
                presentation=presentation,
            ),
        )
        error = ValueError("original")
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.HTTP)
            with operation(app, flow="http"), redirect_stderr(io.StringIO()):
                task = asyncio.create_task(Catch(app).exception(error, object()))
                await entered.wait()
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                with self.assertRaises(ValueError) as raised:
                    await Catch(app).exception(error, object())
        self.assertIs(raised.exception, error)
        presentation.assert_awaited_once()
