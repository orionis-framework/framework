"""Verify that failure observation begins after successful runtime startup."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from orionis.aio.loop import Loop
from orionis.container.context.manager import ScopeManager
from orionis.failure.entities.handling import FailureHandling
from orionis.failure.runtime import (
    FailureRuntime, capture, capture_nowait, current_operation, operation,
)
from orionis.foundation.application import _await_http_tasks
from orionis.foundation.enums.lifespan import Lifespan
from orionis.foundation.enums.runtimes import Runtime
from orionis.test import TestCase
from tests.foundation.test_application_lifecycle import make_application


class RecordingHandler:
    """Record the original exception and context without external services."""

    def __init__(self) -> None:
        self.events = []
        self.reports = []
        self.results = []

    async def handleFailure(self, exception, context) -> FailureHandling:
        """Retain the original incident and its transport context."""
        self.events.append((exception, context))

        async def log() -> None:
            self.reports.append(exception)

        return FailureHandling(
            logging=log if not context.expected and context.reporting_allowed else None,
        )

    async def handleResult(self, value, context) -> None:
        """Record a failed result without creating an exception."""
        self.results.append((value, context))


def reporting_application():
    """Create an isolated application with a prepared, inactive reporter."""
    app = make_application()
    handler = RecordingHandler()
    app._failure_runtime = FailureRuntime(app, handler)
    return app, handler


class TestFailureLifecycle(TestCase):
    async def testFailedStartupDoesNotActivateReporting(self) -> None:
        """Keep failed initialization outside runtime observation."""
        app, handler = reporting_application()
        error = RuntimeError("startup failed")
        app._Application__onStartup = AsyncMock(side_effect=error)
        send = AsyncMock()
        await app(
            {"type": "lifespan"},
            AsyncMock(return_value={"type": "lifespan.startup"}),
            send,
        )
        self.assertFalse(app._failure_runtime.active)
        self.assertEqual(handler.events, [])
        self.assertEqual(send.call_args.args[0]["type"], "lifespan.startup.failed")

    async def testReadinessSendFailureIsStillBeforeActivation(self) -> None:
        """Treat failed readiness delivery as incomplete startup."""
        app, handler = reporting_application()
        app._Application__onStartup = AsyncMock()
        send = AsyncMock(side_effect=[RuntimeError("readiness failed"), None])
        await app(
            {"type": "lifespan"},
            AsyncMock(return_value={"type": "lifespan.startup"}),
            send,
        )
        self.assertFalse(app._failure_runtime.active)
        self.assertEqual(handler.events, [])

    async def testShutdownFailureIsObservedOnceBeforeDeactivation(self) -> None:
        """Retain observation through the final shutdown callback."""
        app, handler = reporting_application()
        failure = RuntimeError("shutdown failed")
        app._Application__onStartup = AsyncMock()

        async def shutdown(**_kwargs: object):
            self.assertTrue(app._failure_runtime.active)
            await capture(failure, app=app, flow="lifecycle", phase="shutdown")
            raise failure

        app._Application__onShutdown = shutdown
        receive = AsyncMock(
            side_effect=[
                {"type": "lifespan.startup"},
                {"type": "lifespan.shutdown"},
            ],
        )
        send = AsyncMock()
        await app({"type": "lifespan"}, receive, send)
        self.assertEqual([error for error, _ in handler.events], [failure])
        self.assertEqual(handler.reports, [failure])
        self.assertFalse(app._failure_runtime.active)
        self.assertEqual(send.call_args.args[0]["type"], "lifespan.shutdown.failed")

    async def testFailedLifespanFailureSendPreservesShutdownException(self) -> None:
        """Observe failed protocol delivery without replacing shutdown's error."""
        app, handler = reporting_application()
        primary = ValueError("shutdown")
        secondary = OSError("send")
        app._Application__onStartup = AsyncMock()
        app._Application__onShutdown = AsyncMock(side_effect=primary)
        receive = AsyncMock(side_effect=[
            {"type": "lifespan.startup"}, {"type": "lifespan.shutdown"},
        ])
        send = AsyncMock(side_effect=[None, secondary])
        with self.assertRaises(ValueError) as caught:
            await app({"type": "lifespan"}, receive, send)
        self.assertIs(caught.exception, primary)
        self.assertEqual([error for error, _ in handler.events], [primary, secondary])
        self.assertEqual(handler.reports, [primary, secondary])
        self.assertEqual(
            handler.events[1][1].parent_event_id, handler.events[0][1].event_id,
        )
        self.assertEqual(send.await_count, 2)
        self.assertFalse(app._failure_runtime.active)

    async def testConcurrentCommandsRetainIndependentRuntimeOwners(self) -> None:
        """Keep reporting active until the final concurrent command exits."""
        app, handler = reporting_application()
        entered = asyncio.Event()
        release = asyncio.Event()
        failure = ValueError("second command failed")
        app._Application__onStartup = AsyncMock()
        app._Application__onShutdown = AsyncMock()

        async def command(args):
            if args == ["second"]:
                entered.set()
                await release.wait()
                raise failure
            await entered.wait()
            return 0

        app._Application__kernel_cli = command
        first = asyncio.create_task(app.handleCommand(["first"]))
        second = asyncio.create_task(app.handleCommand(["second"]))
        try:
            self.assertEqual(await first, 0)
            self.assertTrue(app._failure_runtime.active)
            release.set()
            with self.assertRaises(ValueError):
                await second
        finally:
            release.set()
            await asyncio.gather(first, second, return_exceptions=True)
        self.assertEqual([error for error, _ in handler.events], [failure])
        self.assertFalse(app._failure_runtime.active)

    async def testLazyHttpInitializationActivatesOnlyAfterSuccess(self) -> None:
        """Exclude failed lazy startup and observe the successful retry."""
        app, handler = reporting_application()
        startup_error = RuntimeError("kernel startup")
        request_error = ValueError("request execution")

        async def request(*_args: object):
            raise request_error

        app.config = lambda *_args: None
        app._Application__loadHTTPKernel = AsyncMock(side_effect=startup_error)
        with self.assertRaises(RuntimeError):
            await app({"type": "http"}, AsyncMock(), AsyncMock())
        self.assertEqual(handler.events, [])
        self.assertFalse(app._failure_runtime.active)
        app._Application__loadHTTPKernel = AsyncMock(
            return_value=SimpleNamespace(
                disconnectPaths=frozenset,
                handleASGI=request,
                handleRSGI=request,
            ),
        )
        with self.assertRaises(ValueError):
            await app({"type": "http"}, AsyncMock(), AsyncMock())
        self.assertEqual([error for error, _ in handler.events], [request_error])

    async def testRequestAndMonitorFailuresBothReachTheHandler(self) -> None:
        """Preserve each failure when request and disconnect monitor fail."""
        app, handler = reporting_application()
        app._failure_runtime.activate(object())
        primary = ValueError("request failed")
        secondary = OSError("monitor failed")

        async def fail(error):
            raise error

        async def dispatch(*_args: object):
            request = asyncio.create_task(fail(primary))
            monitor = asyncio.create_task(fail(secondary))
            await asyncio.sleep(0)
            await _await_http_tasks(request, monitor)

        app._Application__kernel_http_asgi = dispatch
        with self.assertRaises(ValueError) as caught:
            await app({"type": "http"}, AsyncMock(), AsyncMock())
        self.assertIs(caught.exception, primary)
        self.assertIs(secondary.__context__, primary)
        self.assertEqual([error for error, _ in handler.events], [primary, secondary])
        self.assertEqual(
            handler.events[1][1].parent_event_id, handler.events[0][1].event_id,
        )

    async def testConcurrentFirstRequestsWaitForHandlerPreparation(self) -> None:
        """Avoid exposing a kernel while its global handler is still resolving."""
        app, handler = reporting_application()
        app._failure_runtime.handler = None
        preparing = asyncio.Event()
        release = asyncio.Event()
        failures = [ValueError("first request"), ValueError("second request")]
        calls = []

        async def resolve_handler():
            preparing.set()
            await release.wait()
            return handler

        async def request(*_args: object):
            calls.append(True)
            raise failures[len(calls) - 1]

        app.getExceptionHandler = resolve_handler
        app.config = lambda *_args: None
        app._Application__loadHTTPKernel = AsyncMock(
            return_value=SimpleNamespace(
                disconnectPaths=frozenset,
                handleASGI=request,
                handleRSGI=request,
            ),
        )
        first = asyncio.create_task(app({"type": "http"}, AsyncMock(), AsyncMock()))
        await preparing.wait()
        second = asyncio.create_task(app({"type": "http"}, AsyncMock(), AsyncMock()))
        await asyncio.sleep(0)
        self.assertEqual(calls, [])
        release.set()
        results = await asyncio.gather(first, second, return_exceptions=True)
        self.assertEqual(results, failures)
        self.assertEqual([error for error, _ in handler.events], failures)

    async def testKernelMetadataFailureDoesNotActivateLazyHttp(self) -> None:
        """Finish kernel metadata resolution before activating lazy serving."""
        app, handler = reporting_application()
        app.config = lambda *_args: None
        failure = RuntimeError("disconnect policy startup failed")

        def disconnect_paths():
            raise failure

        app._Application__loadHTTPKernel = AsyncMock(
            return_value=SimpleNamespace(
                disconnectPaths=disconnect_paths,
                handleASGI=AsyncMock(),
                handleRSGI=AsyncMock(),
            ),
        )
        with self.assertRaises(RuntimeError):
            await app({"type": "http"}, AsyncMock(), AsyncMock())
        self.assertFalse(app._failure_runtime.active)
        self.assertIsNone(app._Application__kernel_http_asgi)
        self.assertIsNone(app._Application__kernel_http_rsgi)
        self.assertEqual(handler.events, [])

    async def testShutdownHookAndLoggerErrorsRemainVisible(self) -> None:
        """Deliver hook and logging cleanup failures independently."""
        app, handler = reporting_application()
        app._failure_runtime.activate(object())
        app._Application__configured = True
        app.bound = lambda _contract: True
        app._Application__bootstrap = {"config": {"logging": {"queue_capacity": 1}}}
        primary = RuntimeError("hook failed")
        secondary = OSError("logger close failed")

        async def hook():
            raise primary

        app.on(Lifespan.SHUTDOWN, hook, runtime=Runtime.CLI)
        app.make = AsyncMock(
            return_value=SimpleNamespace(aclose=AsyncMock(side_effect=secondary)),
        )
        with operation(app), self.assertRaises(RuntimeError) as caught:
            await app._Application__onShutdown(runtime=Runtime.CLI)
        self.assertIs(caught.exception, primary)
        self.assertEqual([error for error, _ in handler.events], [primary, secondary])
        self.assertEqual(
            handler.events[1][1].parent_event_id, handler.events[0][1].event_id,
        )

    async def testCommandFailureSurvivesShutdownFailure(self) -> None:
        """Observe cleanup without replacing the command's original failure."""
        app, handler = reporting_application()
        primary = ValueError("command failed")
        secondary = OSError("shutdown failed")
        app._Application__onStartup = AsyncMock()
        app._Application__kernel_cli = AsyncMock(side_effect=primary)

        async def close():
            raise secondary

        app.on(Lifespan.SHUTDOWN, close, runtime=Runtime.CLI)
        with self.assertRaises(ValueError) as caught:
            await app.handleCommand([])
        self.assertIs(caught.exception, primary)
        self.assertEqual([error for error, _ in handler.events], [primary, secondary])
        self.assertEqual(handler.reports, [primary, secondary])
        self.assertEqual(
            handler.events[1][1].parent_event_id, handler.events[0][1].event_id,
        )
        self.assertFalse(app._failure_runtime.active)

    async def testShutdownAttemptsAllCallbacksAfterFailure(self) -> None:
        """Close independent resources even when an earlier hook fails."""
        app, handler = reporting_application()
        app._failure_runtime.activate(object())
        calls = []
        failure = ValueError("resource close failed")

        async def first():
            calls.append("first")
            if len(calls) == 1:
                raise failure

        async def second():
            calls.append("second")
            if len(calls) == 1:
                raise failure

        app.on(Lifespan.SHUTDOWN, first, second, runtime=Runtime.CLI)
        with self.assertRaises(ValueError) as caught:
            await app._Application__onShutdown(runtime=Runtime.CLI)
        self.assertIs(caught.exception, failure)
        self.assertCountEqual(calls, ["first", "second"])
        self.assertEqual([error for error, _ in handler.events], [failure])

    async def testDirectHandlerResolutionDetachesRequestScope(self) -> None:
        """A shared handler cannot capture a caller's request-scoped objects."""
        app, _ = reporting_application()
        app._Application__booted = True
        app._Application__exception_handler_resolved = RecordingHandler
        app._failure_runtime.activate(object())
        scopes = []

        async def build(_handler):
            scopes.append((app.getCurrentScope(), current_operation()))
            return RecordingHandler()

        with patch.object(app, "build", build), operation(app) as active:
            async with ScopeManager() as scope:
                resolved = await app.getExceptionHandler()
                self.assertIs(app.getCurrentScope(), scope)
                self.assertIs(current_operation(), active)
        self.assertEqual(scopes, [(None, None)])
        self.assertIs(await app.getExceptionHandler(), resolved)

    async def testExplicitCausalHandoffPreservesTheOriginalPythonChain(self) -> None:
        """Link a child incident without manufacturing a Python exception cause."""
        app, handler = reporting_application()
        app._failure_runtime.activate(object())
        primary = ValueError("execution")
        secondary = OSError("cleanup")
        with operation(app, flow="worker", operation="import", isolated=True):
            receipt = await capture(primary)
            await asyncio.create_task(capture(
                secondary, phase="cleanup", parent_event_id=receipt.event_id,
            ))
        self.assertIsNone(secondary.__cause__)
        self.assertIsNone(secondary.__context__)
        self.assertEqual([error for error, _ in handler.events], [primary, secondary])
        self.assertEqual(handler.reports, [primary, secondary])
        context = handler.events[1][1]
        self.assertEqual(context.parent_event_id, receipt.event_id)
        self.assertEqual(context.flow, "worker")
        self.assertEqual(context.operation, "import")
        self.assertEqual(context.phase, "cleanup")
        self.assertEqual(context.correlation_id, handler.events[0][1].correlation_id)

    async def testRepeatedCommandCancellationDrainsShutdownBeforeRelease(self) -> None:
        """Retain runtime ownership until a cancelled command finishes cleanup."""
        app, _ = reporting_application()
        app._Application__onStartup = AsyncMock()
        app._Application__kernel_cli = AsyncMock(return_value=0)
        entered = asyncio.Event()
        release = asyncio.Event()
        finished = asyncio.Event()

        async def close():
            entered.set()
            await release.wait()
            finished.set()

        app.on(Lifespan.SHUTDOWN, close, runtime=Runtime.CLI)
        task = asyncio.create_task(app.handleCommand([]))
        await entered.wait()
        try:
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            self.assertTrue(app._failure_runtime.active)
        finally:
            release.set()
            await asyncio.gather(task, return_exceptions=True)
        self.assertTrue(task.cancelled())
        self.assertTrue(finished.is_set())
        self.assertFalse(app._failure_runtime.active)

    async def testSupervisedOwnerCanCloseItsOwnHeadlessRuntime(self) -> None:
        """Protected cleanup cannot wait on the supervised task awaiting it."""
        app, _ = reporting_application()
        app.create = lambda: app
        app._Application__bootEagerProviders = AsyncMock()
        await app.boot()
        with operation(app):
            task = Loop.createTask(app.aclose())
        await asyncio.wait_for(task, timeout=1)
        self.assertFalse(task.cancelled())
        self.assertFalse(app._failure_runtime.active)

    async def testReportingHookDoesNotReenterHeadlessCloseLock(self) -> None:
        """A pending hook cannot wait on the shutdown already draining it."""
        app, handler = reporting_application()
        app.create = lambda: app
        app._Application__bootEagerProviders = AsyncMock()
        await app.boot()
        entered = asyncio.Event()
        draining = asyncio.Event()
        release = asyncio.Event()
        original_hook = handler.handleFailure
        original_drain = app._failure_runtime.drain
        failure = ValueError("pending report")

        async def hook(exception, context):
            entered.set()
            await release.wait()
            await app.aclose()
            return await original_hook(exception, context)

        async def drain():
            draining.set()
            await original_drain()

        handler.handleFailure = hook
        with operation(app):
            reporting = capture_nowait(failure)
        await entered.wait()
        with patch.object(app._failure_runtime, "drain", drain):
            closing = asyncio.create_task(app.aclose())
            await draining.wait()
            release.set()
            try:
                done, _ = await asyncio.wait([closing], timeout=1)
                self.assertIn(closing, done)
                await closing
            finally:
                reporting.cancel()
                await asyncio.gather(reporting, closing, return_exceptions=True)
        self.assertEqual([error for error, _ in handler.events], [failure])
        self.assertEqual(handler.reports, [failure])
        self.assertFalse(app._failure_runtime.active)

    async def testExceptionHandlerInstanceIsSharedAcrossConcurrentResolution(
        self,
    ) -> None:
        """Resolve the global handler once under concurrent access."""
        app, _ = reporting_application()
        app._Application__booted = True
        app._Application__exception_handler_resolved = RecordingHandler
        with patch.object(
            app, "build", AsyncMock(return_value=RecordingHandler()),
        ) as build:
            resolved = await asyncio.gather(
                *(app.getExceptionHandler() for _ in range(8)),
            )
        self.assertTrue(all(handler is resolved[0] for handler in resolved))
        build.assert_awaited_once()

    async def testRsgiStartupActivatesAfterItsCallbackCompletes(self) -> None:
        """Publish RSGI reporting after startup rather than during its hook."""
        app, handler = reporting_application()

        async def startup(**_kwargs: object):
            self.assertFalse(app._failure_runtime.active)

        app._Application__onStartup = startup
        await app._Application__startRsgi()
        self.assertTrue(app._failure_runtime.active)
        failure = ValueError("rsgi request")
        app._Application__kernel_http_rsgi = AsyncMock(side_effect=failure)
        with self.assertRaises(ValueError):
            await app.__rsgi__(SimpleNamespace(proto="http"), object())
        self.assertEqual([error for error, _ in handler.events], [failure])
        app._Application__onShutdown = AsyncMock()
        await app._Application__stopRsgi()
        self.assertFalse(app._failure_runtime.active)

    async def testHeadlessBootActivatesAfterProvidersFinish(self) -> None:
        """Prepare headless reporting only after eager providers complete."""
        app, _ = reporting_application()
        app.create = lambda: app

        async def boot_providers():
            self.assertFalse(app._failure_runtime.active)

        app._Application__bootEagerProviders = boot_providers
        self.assertIs(await app.boot(), app)
        self.assertTrue(app._failure_runtime.active)
        app._Application__bootEagerProviders = AsyncMock()
        self.assertIs(await app.boot(), app)
        self.assertEqual(app._failure_runtime.ownerCount, 1)

    async def testShutdownDoesNotCloseLoggerOwnedByAnotherRuntime(self) -> None:
        """Keep the shared sink available while another command is active."""
        app, _ = reporting_application()
        app._failure_runtime.activate(object())
        app._failure_runtime.activate(object())
        app._Application__configured = True
        app.bound = lambda _contract: True
        app._Application__bootstrap = {"config": {"logging": {"queue_capacity": 1}}}
        logger = SimpleNamespace(aclose=AsyncMock())
        app.make = AsyncMock(return_value=logger)
        await app._Application__onShutdown(runtime=Runtime.CLI)
        logger.aclose.assert_not_called()

    async def testHeadlessCloseDrainsOwnedTasksBeforeLoggerWithoutCallbacks(
        self,
    ) -> None:
        """Release the headless lifetime and its resources exactly once."""
        app, _ = reporting_application()
        app.create = lambda: app
        app._Application__bootEagerProviders = AsyncMock()
        await app.boot()
        app._Application__configured = True
        app.bound = lambda _contract: True
        app._Application__bootstrap = {"config": {"logging": {"queue_capacity": 1}}}
        closed = []
        entered = asyncio.Event()

        async def background():
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                closed.append("task")

        async def close_logger():
            self.assertTrue(app._failure_runtime.active)
            closed.append("logger")

        logger = SimpleNamespace(aclose=AsyncMock(side_effect=close_logger))
        app.make = AsyncMock(return_value=logger)
        callback = AsyncMock()
        app.on(Lifespan.SHUTDOWN, callback)
        with operation(app):
            task = Loop.createTask(background())
        await entered.wait()
        await asyncio.gather(app.aclose(), app.aclose())
        self.assertTrue(task.cancelled())
        self.assertFalse(app._failure_runtime.active)
        self.assertEqual(closed, ["task", "logger"])
        callback.assert_not_called()
        await app.aclose()
        logger.aclose.assert_awaited_once()

    async def testHeadlessClosePreservesOtherRuntimeOwner(self) -> None:
        """Releasing headless ownership cannot close a running HTTP server."""
        app, _ = reporting_application()
        app.create = lambda: app
        app._Application__bootEagerProviders = AsyncMock()
        await app.boot()
        other_owner = object()
        app._failure_runtime.activate(other_owner)
        with patch.object(app._failure_runtime, "shutdown", AsyncMock()) as shutdown:
            await app.aclose()
            self.assertEqual(app._failure_runtime.ownerCount, 1)
            self.assertTrue(app._failure_runtime.hasOwner(other_owner))
            await app.aclose()
            shutdown.assert_not_called()

    async def testNewCommandWaitsUntilThePreviousLoggerCloseFinishes(self) -> None:
        """Coordinate a new owner with physical closure of the shared sink."""
        app, handler = reporting_application()
        app._Application__onStartup = AsyncMock()
        app._Application__configured = True
        app.bound = lambda _contract: True
        app._Application__bootstrap = {"config": {"logging": {"queue_capacity": 1}}}
        closing = asyncio.Event()
        release = asyncio.Event()
        executed = []
        failure = ValueError("second command")

        async def command(args):
            executed.append(args[0])
            if args == ["second"]:
                raise failure
            return 0

        async def close_logger():
            closing.set()
            await release.wait()

        app._Application__kernel_cli = command
        app.make = AsyncMock(return_value=SimpleNamespace(aclose=close_logger))
        first = asyncio.create_task(app.handleCommand(["first"]))
        await closing.wait()
        second = asyncio.create_task(app.handleCommand(["second"]))
        try:
            await asyncio.sleep(0)
            self.assertEqual(executed, ["first"])
        finally:
            release.set()
            results = await asyncio.gather(first, second, return_exceptions=True)
        self.assertEqual(results, [0, failure])
        self.assertEqual([error for error, _ in handler.events], [failure])
        self.assertEqual(handler.reports, [failure])
        self.assertFalse(app._failure_runtime.active)

    async def testSynchronousLoggerClosesDuringActiveRuntime(self) -> None:
        """Observe synchronous sink cleanup even when queue capacity is zero."""
        app, handler = reporting_application()
        app._failure_runtime.activate(object())
        app._Application__configured = True
        app._Application__bootstrap = {"config": {"logging": {"queue_capacity": 0}}}
        app.bound = lambda _contract: True
        failure = OSError("synchronous sink close failed")

        async def close_logger():
            self.assertTrue(app._failure_runtime.active)
            raise failure

        app.make = AsyncMock(return_value=SimpleNamespace(aclose=close_logger))
        with self.assertRaises(OSError):
            await app._Application__onShutdown(runtime=Runtime.CLI)
        app.make.assert_awaited_once()
        self.assertEqual([error for error, _ in handler.events], [failure])

    async def testShutdownWithoutLoggerBindingDoesNotConstructOne(self) -> None:
        """Leave custom applications without a logger binding unchanged."""
        app, _ = reporting_application()
        app._failure_runtime.activate(object())
        app._Application__configured = True
        app.bound = lambda _contract: False
        app.make = AsyncMock()
        await app._Application__onShutdown(runtime=Runtime.CLI)
        app.make.assert_not_called()

    async def testConcurrentCommandShutdownClosesTheFinalLoggerOnce(self) -> None:
        """Retire concurrent owners atomically so one closes shared resources."""
        app, _ = reporting_application()
        app._Application__onStartup = AsyncMock()
        app._Application__configured = True
        app.bound = lambda _contract: True
        logger = SimpleNamespace(aclose=AsyncMock())
        app.make = AsyncMock(return_value=logger)
        entered = []
        ready = asyncio.Event()

        async def command(args):
            entered.append(args)
            if len(entered) == 2:
                ready.set()
            await ready.wait()
            return 0

        async def drain():
            await asyncio.sleep(0)

        app._Application__kernel_cli = command
        with patch.object(app._failure_runtime, "drain", drain):
            results = await asyncio.gather(
                app.handleCommand(["first"]), app.handleCommand(["second"]),
            )
        self.assertEqual(results, [0, 0])
        logger.aclose.assert_awaited_once()
        self.assertEqual(app._failure_runtime.ownerCount, 0)
        self.assertFalse(app._failure_runtime.active)

    async def testNewOwnerClosesItsLoggerWhileAnEarlierOwnerDrains(self) -> None:
        """Exclude closing owners from the new lifetime's resource ownership."""
        app, _ = reporting_application()
        app._Application__onStartup = AsyncMock()
        app._Application__configured = True
        app.bound = lambda _contract: True
        app._Application__kernel_cli = AsyncMock(return_value=0)
        logger = SimpleNamespace(aclose=AsyncMock())
        app.make = AsyncMock(return_value=logger)
        first_draining = asyncio.Event()
        release = asyncio.Event()

        async def drain():
            if logger.aclose.await_count == 1 and not first_draining.is_set():
                first_draining.set()
                await release.wait()
            else:
                await asyncio.sleep(0)

        with patch.object(app._failure_runtime, "drain", drain):
            first = asyncio.create_task(app.handleCommand(["first"]))
            try:
                await first_draining.wait()
                self.assertTrue(app._failure_runtime.active)
                self.assertEqual(app._failure_runtime.ownerCount, 0)
                self.assertEqual(await app.handleCommand(["second"]), 0)
                self.assertEqual(logger.aclose.await_count, 2)
                self.assertTrue(app._failure_runtime.active)
            finally:
                release.set()
                await first
        self.assertFalse(app._failure_runtime.active)
