# ruff: noqa: ARG001, ARG002, BLE001, PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Hook doubles intentionally keep the public keyword names even when unused.
# Worker failures must reach assertions rather than disappear in threads.

"""Exercise central failure delivery without booting a real application."""

from __future__ import annotations

import asyncio
import contextvars
import gc
import io
import logging
import threading
import weakref
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID
from contextlib import redirect_stderr
from functools import partial
from unittest.mock import AsyncMock, MagicMock, patch

from orionis.aio.loop import Loop
from orionis.container.container import Container
from orionis.failure import runtime as failure_runtime
from orionis.failure.base.handler import BaseExceptionHandler
from orionis.failure.catch import Catch
from orionis.failure.contracts.handler import IBaseExceptionHandler
from orionis.failure.entities.context import FailureContext
from orionis.failure.entities.handling import FailureHandling
from orionis.failure.enums.kernel_type import KernelContext
from orionis.failure.runtime import (
    FailureRuntime,
    capture,
    capture_nowait,
    capture_result,
    current_operation,
    get_runtime,
    handoff,
    operation,
    prepare,
)
from orionis.logging.contracts.logger import ILogger
from orionis.logging.handlers.queued import (
    BoundedQueueHandler,
    LoggingDeliveryError,
    observe_sink_error,
)
from tests.support.failure_runtime import IsolatedFailureTestCase


class _Handler(BaseExceptionHandler):
    def __init__(self, app: Container) -> None:
        """Initialize isolated state for this failure fixture.

        Parameters
        ----------
        app : Container
            Isolated application container.
        """
        super().__init__(MagicMock(), app)
        self.failures = []
        self.reports = []
        self.results = []

    async def handleFailure(
        self,
        exception: BaseException,
        context: FailureContext,
    ) -> FailureHandling:
        """Record the original and select deferred side effects."""
        self.failures.append((exception, context))
        return FailureHandling(
            logging=(
                partial(self.log, exception)
                if not context.expected and context.reporting_allowed
                else None
            ),
            presentation=self.present,
        )

    async def log(self, exception: BaseException) -> None:
        """Record logging performed by the returned plan."""
        self.reports.append(exception)

    async def handleResult(self, value: object, context: FailureContext) -> None:
        """Record a failed result separately from exceptions."""
        self.results.append((value, context))

    async def present(self, *, flow: str, request: object = None) -> object:
        """Preserve a caller-owned HTTP response in logger failure tests."""
        return request if flow == "http" else None


class _FailingContractHandler(IBaseExceptionHandler):
    """Exercise fallback construction for a handler that does not inherit Base."""

    def __init__(self) -> None:
        """Initialize isolated state for this failure fixture."""
        self.calls = []
        self.failure = ValueError("policy")

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

        Raises
        ------
        BaseException
            Propagate the fixture failure exercised by this scenario.
        """
        self.calls.append((exception, context))
        raise self.failure

    async def handleResult(
        self,
        value: object,
        context: FailureContext,
    ) -> FailureHandling | None:
        """Record the declared result and select its deferred effects.

        Parameters
        ----------
        value : object
            Declared failed result supplied by the owner.
        context : FailureContext
            Immutable failure metadata supplied by the runtime.
        """
        return None


class _App(Container):
    def __init__(self) -> None:
        """Initialize isolated state for this failure fixture."""
        super().__init__()
        self.handler = _Handler(self)
        self.resolved_scopes = []

    async def getExceptionHandler(self) -> _Handler:
        """Record resolution context without filesystem or application startup."""
        self.resolved_scopes.append(self.getCurrentScope())
        return self.handler


def _runtime(*, active: bool = True) -> tuple[_App, FailureRuntime, object]:
    """Create an isolated app and explicit runtime owner."""
    app = object.__new__(_App)
    app.__init__()
    runtime = FailureRuntime(app, app.handler)
    app._failure_runtime = runtime
    owner = object()
    if active:
        runtime.activate(owner)
    return app, runtime, owner


class TestFailureRuntime(IsolatedFailureTestCase):
    async def testInactiveRuntimeDoesNotReport(self) -> None:
        """Exclude failures before activation and after the last owner exits."""
        app, runtime, owner = _runtime(active=False)
        error = ValueError("before")
        self.assertIsNone(await capture(error, app=app))
        runtime.activate(owner)
        self.assertTrue((await capture(error, app=app)).delivered)
        runtime.deactivate(owner)
        self.assertIsNone(await capture(error, app=app))
        self.assertEqual(app.handler.reports, [error])

    async def testOwnersDoNotDeactivateEachOther(self) -> None:
        """Keep observation active until every independently started owner exits."""
        app, runtime, first = _runtime()
        second = object()
        runtime.activate(second)
        runtime.deactivate(first)
        self.assertTrue((await capture(ValueError(), app=app)).delivered)
        runtime.deactivate(second)
        self.assertFalse(runtime.active)

    async def testScopeFreeDeliveryPreservesOriginal(self) -> None:
        """Deliver cause, notes and traceback through real container invocation."""
        app, _, _ = _runtime()
        cause = KeyError("cause")
        error = ValueError("original")
        error.add_note("note")
        try:
            raise error from cause
        except ValueError:
            receipt = await capture(error, app=app, flow="queue", phase="reserve")
        self.assertTrue(receipt.delivered)
        self.assertIs(app.handler.failures[0][0], error)
        self.assertIs(error.__cause__, cause)
        self.assertEqual(error.__notes__, ["note"])
        self.assertIsNone(app.getCurrentScope())

    async def testExpectedFailureStillReachesHook(self) -> None:
        """Verify expected failure still reaches hook.

        Expected errors are observed without mandatory error logging.
        """
        app, _, _ = _runtime()
        error = ValueError("invalid input")
        receipt = await capture(error, app=app, expected=True)
        self.assertTrue(receipt.delivered)
        self.assertFalse(receipt.reported)
        self.assertEqual(app.handler.reports, [])
        self.assertIs(app.handler.failures[0][0], error)

    async def testDeclaredResultHasNoInventedException(self) -> None:
        """Retain nonzero outcomes as results without synthetic tracebacks."""
        app, _, _ = _runtime()
        receipt = await capture_result(1, app=app, flow="cli")
        self.assertTrue(receipt.delivered)
        self.assertEqual(app.handler.results[0][0], 1)
        self.assertEqual(app.handler.failures, [])
        self.assertEqual(app.handler.reports, [])

    async def testReportFailureDoesNotPreventHttpRendering(self) -> None:
        """Verify report failure does not prevent http rendering.

        A broken reporter must not replace the original or prevent a response.
        """
        app, _, _ = _runtime()
        error = ValueError("original")

        async def broken_report(exception: BaseException) -> None:
            """Raise a logging failure without exposing its sensitive message.

            Parameters
            ----------
            exception : BaseException
                Original exception supplied to the callback.

            Raises
            ------
            OSError
                Propagate the fixture failure exercised by this scenario.
            """
            message = "secret=do-not-print"
            raise OSError(message)

        app.handler.log = broken_report
        request = object()
        stderr = io.StringIO()
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.HTTP)
            with redirect_stderr(stderr):
                result = await Catch(app).exception(error, request)
        self.assertIs(result, request)
        self.assertIs(app.handler.failures[0][0], error)
        self.assertNotIn("do-not-print", stderr.getvalue())

    async def testHookFailureStillReportsOriginal(self) -> None:
        """Verify hook failure still reports original.

        A failed policy hook falls back to native logging for the original.
        """
        app, _, _ = _runtime()
        logger = MagicMock(spec=ILogger)
        app.instance(ILogger, logger)

        async def broken_hook(
            exception: BaseException,
            context: FailureContext,
        ) -> None:
            """Raise a policy failure while preserving the primary exception.

            Parameters
            ----------
            exception : BaseException
                Original exception supplied to the callback.
            context : FailureContext
                Immutable failure metadata supplied by the runtime.

            Raises
            ------
            RuntimeError
                Propagate the fixture failure exercised by this scenario.
            """
            message = "hook"
            raise RuntimeError(message)

        app.handler.handleFailure = broken_hook
        original = ValueError("original")
        with redirect_stderr(io.StringIO()):
            receipt = await capture(original, app=app)
        self.assertTrue(receipt.degraded)
        self.assertTrue(receipt.reported)
        self.assertFalse(receipt.delivered)
        logger.getLogger.return_value.error.assert_called_once_with(
            "[%s] %s",
            "ValueError",
            "original",
            exc_info=(ValueError, original, None),
        )

    async def testReporterRecursionIsBounded(self) -> None:
        """Verify reporter recursion is bounded.

        Recursive reporting uses emergency output without reentering the hook.
        """
        app, _, _ = _runtime()

        async def recursive(exception: BaseException) -> None:
            """Exercise capture reentry from a reporting callback.

            Parameters
            ----------
            exception : BaseException
                Original exception supplied to the callback.
            """
            await capture(RuntimeError("reporter"), app=app)

        app.handler.log = recursive
        with redirect_stderr(io.StringIO()):
            await capture(ValueError("original"), app=app)
        self.assertEqual(len(app.handler.failures), 1)

    async def testReporterTimeoutIsDegradedAndDrained(self) -> None:
        """Timeout a cooperative reporter without leaving a detached task."""
        app, runtime, _ = _runtime()
        runtime.timeout = 0.01
        finished = asyncio.Event()

        async def slow(exception: BaseException) -> None:
            """Hold reporting until timeout or caller cancellation.

            Parameters
            ----------
            exception : BaseException
                Original exception supplied to the callback.
            """
            try:
                await asyncio.Event().wait()
            finally:
                finished.set()

        app.handler.log = slow
        with redirect_stderr(io.StringIO()):
            receipt = await capture(ValueError(), app=app)
        self.assertTrue(receipt.degraded)
        self.assertTrue(finished.is_set())
        self.assertEqual(runtime._pending, set())

    async def testCallerCancellationPropagates(self) -> None:
        """Verify caller cancellation propagates.

        Cancellation of the caller is not converted to a reporting failure.
        """
        app, _, _ = _runtime()
        entered = asyncio.Event()

        async def slow(exception: BaseException) -> None:
            """Hold reporting until timeout or caller cancellation.

            Parameters
            ----------
            exception : BaseException
                Original exception supplied to the callback.
            """
            entered.set()
            await asyncio.Event().wait()

        app.handler.log = slow
        task = asyncio.create_task(capture(ValueError(), app=app))
        await entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

    async def testControlExceptionsAreNotServerErrors(self) -> None:
        """Verify control exceptions are not server errors.

        Normal control flow never invokes the failure hook or error logger.
        """
        app, _, _ = _runtime()
        for error in (
            asyncio.CancelledError(),
            SystemExit(),
            KeyboardInterrupt(),
            GeneratorExit(),
        ):
            self.assertIsNone(await capture(error, app=app))
        self.assertEqual(app.handler.failures, [])

    async def testNestedGroupIsDeliveredIntact(self) -> None:
        """Keep nested groups as original objects instead of flattening them."""
        app, _, _ = _runtime()
        group = ExceptionGroup(
            "outer",
            [ValueError(), ExceptionGroup("inner", [TypeError()])],
        )
        await capture(group, app=app)
        self.assertIs(app.handler.reports[0], group)

    async def testSameIncidentIsDeduplicatedWithinOperation(self) -> None:
        """Verify same incident is deduplicated within operation.

        Multiple boundaries for one propagation notify the handler once.
        """
        app, _, _ = _runtime()
        error = ValueError()
        with operation(app, flow="http", isolated=True):
            first = await capture(error)
            with operation():
                second = await capture(error)
        self.assertEqual(first.event_id, second.event_id)
        self.assertTrue(second.duplicate)
        self.assertEqual(app.handler.reports, [error])

    async def testDistinctAttemptsReuseExceptionWithoutHidingFailure(self) -> None:
        """Verify distinct attempts reuse exception without hiding failure.

        Per-attempt ledgers never deduplicate subsequent job attempts.
        """
        app, _, _ = _runtime()
        error = ValueError()
        for _ in range(2):
            with operation(app, isolated=True):
                await capture(error)
        self.assertEqual(app.handler.reports, [error, error])

    async def testNestedReraiseTransfersReceiptToParent(self) -> None:
        """Preserve identity when an isolated child propagates to its parent."""
        app, _, _ = _runtime()
        error = ValueError()
        with operation(app, isolated=True):
            try:
                with operation(isolated=True):
                    await capture(error)
                    raise error
            except ValueError as caught:
                self.assertTrue((await capture(caught)).duplicate)
        self.assertEqual(app.handler.reports, [error])

    async def testConcurrentOperationsRemainIndependent(self) -> None:
        """Verify concurrent operations remain independent.

        Concurrent invocations can reuse an error object without sharing state.
        """
        app, _, _ = _runtime()
        error = ValueError()

        async def invoke(identifier: str) -> None:
            """Capture the shared exception in an independent operation.

            Parameters
            ----------
            identifier : str
                Correlation identifier for this independent operation.
            """
            with operation(app, correlation_id=identifier, isolated=True):
                await asyncio.sleep(0)
                await capture(error)

        await asyncio.gather(invoke("a"), invoke("b"))
        self.assertEqual(len(app.handler.failures), 2)
        self.assertEqual(
            {ctx.correlation_id for _, ctx in app.handler.failures},
            {"a", "b"},
        )

    async def testNoLedgerAllocationOnSuccess(self) -> None:
        """Verify no ledger allocation on success.

        Successful operations allocate no event, traceback or dedup dictionary.
        """
        app, _, _ = _runtime()
        with operation(app) as boundary:
            self.assertIsNone(boundary.ledger)
        self.assertIsNone(boundary.ledger)

    async def testRuntimeIsolation(self) -> None:
        """Verify runtime isolation.

        Explicit application ownership wins over another current runtime.
        """
        first, _, _ = _runtime()
        second, _, _ = _runtime()
        with operation(first):
            await capture(ValueError("second"), app=second)
        self.assertEqual(first.handler.failures, [])
        self.assertEqual(len(second.handler.failures), 1)
        self.assertIsNone(get_runtime())

    async def testCallbackReportCanBeDrained(self) -> None:
        """Verify callback report can be drained.

        Callback reports are retained and awaitable by their owner.
        """
        app, runtime, _ = _runtime()
        error = ValueError()
        with operation(app):
            pending = capture_nowait(error)
            self.assertIsInstance(pending, asyncio.Task)
            await runtime.drain()
        self.assertEqual(app.handler.reports, [error])

    async def testDrainLetsCompletedReportCallbacksReleaseOwnership(self) -> None:
        """Drain completed tasks without starving their queued release callbacks."""
        _, runtime, _ = _runtime()
        completed = asyncio.create_task(asyncio.sleep(0))
        await completed
        runtime._pending.add(completed)
        completed.add_done_callback(runtime._pending.discard)
        gather = asyncio.gather
        iterations = 0

        async def bounded_gather(*tasks: object, **kwargs: object) -> list[object]:
            """Detect drain loops that starve task completion callbacks.

            Parameters
            ----------
            tasks : object
                Owned tasks to join.
            kwargs : object
                Keyword arguments forwarded to the native operation.

            Returns
            -------
            list[object]
                Results of the joined tasks.
            """
            nonlocal iterations
            iterations += 1
            # Fail deterministically instead of hanging the event loop on the
            # original busy loop, whose timeout callback cannot run either.
            self.assertLessEqual(iterations, 2, "drain starved release callbacks")
            return await gather(*tasks, **kwargs)

        with patch.object(asyncio, "gather", side_effect=bounded_gather):
            await runtime.drain()
        self.assertEqual(runtime._pending, set())
        self.assertIsNone(completed.result())

    async def testCallbackAndAwaitedCaptureDoNotDoubleReport(self) -> None:
        """Claim a callback incident before scheduling to prevent a racing report."""
        app, runtime, _ = _runtime()
        error = ValueError()
        with operation(app):
            capture_nowait(error)
            self.assertTrue((await capture(error)).duplicate)
            await runtime.drain()
        self.assertEqual(app.handler.reports, [error])

    async def testThreadReportUsesOwningLoop(self) -> None:
        """Verify thread report uses owning loop.

        Owned threads can notify without DI scopes or unsafe loop access.
        """
        app, runtime, _ = _runtime()
        error = ValueError()
        with operation(app):
            future = await asyncio.to_thread(capture_nowait, error)
            await asyncio.wrap_future(future)
            await runtime.drain()
        self.assertEqual(app.handler.reports, [error])

    async def testConcurrentThreadsClaimTheSameIncidentOnce(self) -> None:
        """Verify concurrent threads claim the same incident once.

        Copied operation contexts cannot allocate two events for one failure.
        """
        app, runtime, _ = _runtime()
        error = ValueError("shared worker failure")
        start = threading.Barrier(3)
        second_allocation = threading.Event()
        identifiers = []
        submitted = []
        worker_errors = []
        original_uuid = failure_runtime.uuid4

        def delayed_uuid() -> UUID:
            """Hold the first incident allocation while another worker competes.

            Returns
            -------
            UUID
                Allocated incident identifier.
            """
            identifier = original_uuid()
            identifiers.append(identifier)
            if len(identifiers) == 1:
                second_allocation.wait(0.2)
            else:
                second_allocation.set()
            return identifier

        def submit() -> None:
            """Submit the shared failure and retain worker errors for assertions."""
            try:
                start.wait(timeout=1)
                submitted.append(capture_nowait(error))
            except Exception as caught:
                worker_errors.append(caught)

        with operation(app, correlation_id="shared-worker-operation"):
            contexts = [contextvars.copy_context(), contextvars.copy_context()]
            workers = [
                threading.Thread(target=context.run, args=(submit,))
                for context in contexts
            ]
            with patch.object(failure_runtime, "uuid4", side_effect=delayed_uuid):
                for worker in workers:
                    worker.start()
                start.wait(timeout=1)
                for worker in workers:
                    worker.join(timeout=1)
            self.assertTrue(all(not worker.is_alive() for worker in workers))
            self.assertEqual(worker_errors, [])
            receipts = await asyncio.gather(
                *(asyncio.wrap_future(future) for future in submitted),
            )
            await runtime.drain()
        self.assertEqual(len(identifiers), 1)
        self.assertEqual(
            {receipt.event_id for receipt in receipts},
            {identifiers[0].hex},
        )
        self.assertEqual(sum(receipt.duplicate for receipt in receipts), 1)
        self.assertEqual(len(app.handler.failures), 1)
        self.assertEqual(app.handler.reports, [error])

    async def testPrepareResolvesOutsideRequestScope(self) -> None:
        """Verify prepare resolves outside request scope.

        Preparation cannot pin request-scoped constructor dependencies.
        """
        app = object.__new__(_App)
        app.__init__()
        runtime = FailureRuntime(app)
        app._failure_runtime = runtime
        async with app.beginScope() as scope:
            await prepare(app)
            self.assertIs(app.getCurrentScope(), scope)
        self.assertEqual(app.resolved_scopes, [None])
        self.assertFalse(runtime.active)

    async def testMetadataIsCopiedBoundedAndRedacted(self) -> None:
        """Verify metadata is copied bounded and redacted.

        Metadata snapshots never retain transport objects or credentials.
        """
        source = {"job": "42", "access_token": "sensitive", "request": object()}
        context = FailureContext(metadata=source)
        source["job"] = "changed"
        self.assertEqual(context.metadata["job"], "42")
        self.assertEqual(context.metadata["access_token"], "[REDACTED]")
        self.assertNotIn("request", context.metadata)
        with self.assertRaises(TypeError):
            context.metadata["job"] = "mutable"

    async def testDirectCatchCaptureNeedsNoScope(self) -> None:
        """Expose the same active coordinator through the compatible ICatch API."""
        app, _, _ = _runtime()
        error = ValueError()
        receipt = await Catch(app).capture(error, context=FailureContext(flow="queue"))
        self.assertTrue(receipt.delivered)
        self.assertEqual(app.handler.reports, [error])

    async def testExplicitAppDoesNotInheritAnotherAppsCorrelation(self) -> None:
        """Verify explicit app does not inherit another apps correlation.

        Context metadata is isolated as strictly as handler selection.
        """
        first, _, _ = _runtime()
        second, _, _ = _runtime()
        with operation(first, flow="http", correlation_id="private-first"):
            await capture(ValueError(), app=second)
        context = second.handler.failures[0][1]
        self.assertIsNone(context.correlation_id)
        self.assertEqual(context.flow, "runtime")

    async def testSecondaryFailureReferencesOriginalReceipt(self) -> None:
        """Verify secondary failure references original receipt.

        Cleanup failures are separate events related to their original cause.
        """
        app, _, _ = _runtime()
        primary = ValueError()
        secondary = OSError()
        secondary.__cause__ = primary
        with operation(app):
            first = await capture(primary)
            second = await capture(secondary)
        self.assertNotEqual(first.event_id, second.event_id)
        self.assertEqual(app.handler.failures[1][1].parent_event_id, first.event_id)

    async def testDuplicateCallbackReceiptIsAwaitable(self) -> None:
        """Verify duplicate callback receipt is awaitable.

        A duplicate scheduled capture remains awaitable on the owning loop.
        """
        app, runtime, _ = _runtime()
        error = ValueError()
        with operation(app):
            first = capture_nowait(error)
            second = capture_nowait(error)
            await asyncio.gather(first, second)
            await runtime.drain()
        self.assertEqual(app.handler.reports, [error])

    async def testLoopTaskFailureReachesHandlerAndRemainsAwaitable(self) -> None:
        """Verify loop task failure reaches handler and remains awaitable.

        Supervised tasks retain their normal await and exception semantics.
        """
        app, runtime, _ = _runtime()
        error = ValueError("task")

        async def fail() -> None:
            """Raise the original exception from a supervised task.

            Raises
            ------
            BaseException
                Propagate the fixture failure exercised by this scenario.
            """
            raise error

        with operation(app):
            task = Loop.createTask(fail(), name="owned-task")
            with self.assertRaises(ValueError):
                await task
            duplicate = await capture(error)
        await runtime.drain()
        self.assertTrue(duplicate.duplicate)
        self.assertEqual(app.handler.reports, [error])
        self.assertEqual(task.get_name(), "owned-task")

    async def testShutdownReportsCleanupOfSupervisedTask(self) -> None:
        """Verify shutdown reports cleanup of supervised task.

        Stopping an owned detached task observes a failing finally block.
        """
        app, runtime, _ = _runtime()
        entered = asyncio.Event()
        error = OSError("cleanup")

        async def wait() -> None:
            """Raise the cleanup error when the supervised task is cancelled.

            Raises
            ------
            BaseException
                Propagate the fixture failure exercised by this scenario.
            """
            try:
                entered.set()
                await asyncio.Event().wait()
            finally:
                raise error

        with operation(app):
            task = Loop.createTask(wait())
            await entered.wait()
            await runtime.shutdown()
        self.assertTrue(task.done())
        self.assertEqual(app.handler.reports, [error])
        self.assertEqual(runtime._tasks, set())

    async def testQueuedLoggerReportsEverySinkFailure(self) -> None:
        """Verify queued logger reports every sink failure.

        Background logging failures are observed without reusing that sink.
        """
        app, runtime, _ = _runtime()
        release = threading.Event()
        errors = []

        class Sink(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                """Inject the configured failure into native logging delivery.

                Parameters
                ----------
                record : logging.LogRecord
                    Native log record delivered to the sink.

                Raises
                ------
                BaseException
                    Propagate the fixture failure exercised by this scenario.
                """
                release.wait(2)
                error = OSError(record.getMessage())
                errors.append(error)
                raise error

        handler = BoundedQueueHandler(Sink(), 2, app=app)
        try:
            for message in ("one", "two"):
                handler.handle(logging.LogRecord("test", 40, "", 1, message, (), None))
        finally:
            release.set()
            with self.assertRaises(LoggingDeliveryError):
                await asyncio.to_thread(handler.close)
        await runtime.drain()
        self.assertEqual(len(errors), 2)
        self.assertCountEqual(app.handler.reports, errors)

    async def testDefaultHandlerHookPreservesLegacyLogging(self) -> None:
        """Verify default handler hook preserves legacy logging.

        Optional inherited hooks work through the real dependency injector.
        """
        app, runtime, _ = _runtime()
        log = MagicMock(spec=ILogger)
        app.instance(ILogger, log)
        runtime.handler = BaseExceptionHandler(MagicMock(), app)
        receipt = await capture(ValueError("default"), app=app)
        self.assertTrue(receipt.delivered)
        self.assertFalse(receipt.degraded)
        log.getLogger.return_value.error.assert_called_once()

    async def testCallbackHandoffDeduplicatesAnAwaitingOwner(self) -> None:
        """Verify callback handoff deduplicates an awaiting owner.

        A consumed child error can explicitly wake its owner without duplication.
        """
        app, runtime, _ = _runtime()
        error = OSError("write failed")
        with operation(app, isolated=True):
            connection = current_operation()
            with operation(isolated=True):
                pending = capture_nowait(error)
                self.assertTrue(handoff(error, target=connection))
                await pending
            self.assertTrue((await capture(error)).duplicate)
        await runtime.drain()
        self.assertEqual(app.handler.reports, [error])

    async def testClosedOwnerDoesNotRetainLateReceipts(self) -> None:
        """Verify closed owner does not retain late receipts.

        A stale callback cannot repopulate a completed operation's ledger.
        """
        app, _, _ = _runtime()
        error = ValueError()
        with operation(app) as boundary:
            receipt = await capture(error)
        self.assertFalse(handoff(error, target=boundary, receipt=receipt))
        self.assertEqual(boundary.ledger, {})

    async def testGroupHandoffRetainsNativePresentationWithoutRelogging(self) -> None:
        """Verify group handoff retains native presentation without relogging.

        A group of reported leaves still obtains native HTTP presentation.
        """
        app, runtime, _ = _runtime()
        leaves = [ValueError("first"), OSError("second")]
        group = ExceptionGroup("combined", leaves)
        with operation(app, flow="http", isolated=True) as owner:
            with operation(isolated=True):
                for error in leaves:
                    await capture(error)
                self.assertTrue(handoff(group, target=owner))
            plan = await runtime.handlingFor(
                group,
                context=FailureContext(flow="http"),
            )
            self.assertIsNotNone(plan)
            self.assertIsNone(plan.logging)
            self.assertIsNotNone(plan.presentation)
            self.assertIs(
                await runtime.handlingFor(group, context=FailureContext(flow="http")),
                plan,
            )
        self.assertEqual(app.handler.reports, leaves)
        self.assertEqual(len(app.handler.failures), len(leaves))

    async def testConcurrentGroupOwnersShareFallbackSelection(self) -> None:
        """Verify concurrent group owners share fallback selection.

        Only one owner constructs a fallback for an already reported group.
        """
        app, runtime, _ = _runtime()
        error = ValueError("reported")
        group = ExceptionGroup("combined", [error])
        entered = asyncio.Event()
        release = asyncio.Event()
        selected = FailureHandling()

        async def select(
            exception: BaseException,
            context: FailureContext,
        ) -> FailureHandling:
            """Select the fixture plan through the configured fallback path.

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
            return selected

        runtime._defaultHandling = AsyncMock(side_effect=select)
        with operation(app, flow="http"):
            await capture(error)
            first = asyncio.create_task(
                runtime.handlingFor(
                    group,
                    context=FailureContext(flow="http"),
                ),
            )
            try:
                await entered.wait()
                second = asyncio.create_task(
                    runtime.handlingFor(
                        group,
                        context=FailureContext(flow="http"),
                    ),
                )
                await asyncio.sleep(0)
                release.set()
                plans = await asyncio.gather(first, second)
            finally:
                release.set()
                await first
        self.assertTrue(all(plan is selected for plan in plans))
        runtime._defaultHandling.assert_awaited_once()
        self.assertEqual(app.handler.reports, [error])

    async def testTransferredFallbackCannotAwaitItsOwnIncident(self) -> None:
        """Keep fallback construction inside the same reporter reentry guard."""
        app, runtime, _ = _runtime()
        original = ValueError("reported")
        group = ExceptionGroup("combined", [original])
        selected = FailureHandling()
        nested = []

        async def select(
            exception: BaseException,
            context: FailureContext,
        ) -> FailureHandling:
            """Select the fixture plan through the configured fallback path.

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
            nested.append(await runtime.handlingFor(exception, context=context))
            return selected

        runtime._defaultHandling = AsyncMock(side_effect=select)
        with operation(app, flow="http"):
            await capture(original)
            async with asyncio.timeout(1):
                plan = await runtime.handlingFor(
                    group,
                    context=FailureContext(flow="http"),
                )
        self.assertIs(plan, selected)
        self.assertEqual(nested, [None])
        self.assertEqual(app.handler.reports, [original])
        runtime._defaultHandling.assert_awaited_once()

    async def testCorrelationIsAllocatedOnlyAfterFirstError(self) -> None:
        """Verify correlation is allocated only after first error.

        Uncorrelated requests gain a stable identifier on their error path.
        """
        app, _, _ = _runtime()
        with operation(app) as boundary:
            self.assertIsNone(boundary.correlation_id)
            await capture(ValueError())
            await capture(OSError())
        contexts = [context for _, context in app.handler.failures]
        self.assertIsNotNone(contexts[0].correlation_id)
        self.assertEqual(contexts[0].correlation_id, contexts[1].correlation_id)

    async def testClosingLoggerKeepsHookWithoutReopeningReporter(self) -> None:
        """Verify closing logger keeps hook without reopening reporter.

        Final logging cleanup remains observable without resolving a new sink.
        """
        app, runtime, owner = _runtime()
        self.assertTrue(runtime.hasOwner(owner))
        runtime.stopReporting()
        error = OSError("closed sink")
        with redirect_stderr(io.StringIO()):
            receipt = await capture(error, app=app)
        self.assertTrue(receipt.delivered)
        self.assertTrue(receipt.degraded)
        self.assertEqual(app.handler.failures[0][0], error)
        self.assertEqual(app.handler.reports, [])
        await runtime.start(object())
        await capture(ValueError("next owner"), app=app)
        self.assertEqual(len(app.handler.reports), 1)

    async def testStartWaitsForPhysicalLoggerClose(self) -> None:
        """Verify start waits for physical logger close.

        A new owner cannot publish while the previous logger is closing.
        """
        _, runtime, _ = _runtime()
        owner = object()
        async with runtime.lifecycle_lock:
            start = asyncio.create_task(runtime.start(owner))
            await asyncio.sleep(0)
            self.assertFalse(runtime.hasOwner(owner))
        await start
        self.assertTrue(runtime.hasOwner(owner))

    async def testEquivalentNestedContextPreservesParentLifetime(self) -> None:
        """Verify equivalent nested context preserves parent lifetime.

        Reused metadata must not clear receipts or close the parent boundary.
        """
        app, _, _ = _runtime()
        error = ValueError("same")
        with operation(app, flow="mcp", operation="tools/list") as outer:
            with operation(app, flow="mcp", operation="tools/list") as inner:
                self.assertIs(inner, outer)
                await capture(error)
            self.assertFalse(outer.closed)
            self.assertTrue((await capture(error)).duplicate)
        self.assertTrue(outer.closed)
        self.assertEqual(app.handler.reports, [error])

    async def testInactiveApplicationDoesNotInheritAnotherOwner(self) -> None:
        """Verify inactive application does not inherit another owner.

        An explicitly inactive app must not report to an active neighbour.
        """
        active, _, _ = _runtime()
        inactive, _, _ = _runtime(active=False)
        with operation(active), operation(inactive):
            self.assertIsNone(get_runtime())
            self.assertIsNone(await capture(ValueError()))
        self.assertEqual(active.handler.failures, [])
        self.assertEqual(inactive.handler.failures, [])

    async def testInactiveRuntimeDoesNotInheritAnotherOwner(self) -> None:
        """Verify inactive runtime does not inherit another owner.

        An explicit inactive runtime suppresses its neighbour's observation.
        """
        active, _, _ = _runtime()
        inactive, runtime, _ = _runtime(active=False)
        with operation(active), operation(runtime=runtime):
            self.assertIsNone(get_runtime())
            self.assertIsNone(await capture(ValueError()))
        self.assertEqual(active.handler.failures, [])
        self.assertEqual(inactive.handler.failures, [])

    async def testNowaitRecursionDoesNotQueueMoreReports(self) -> None:
        """Verify nowait recursion does not queue more reports.

        Recursive callbacks settle immediately and cannot grow the drain set.
        """
        app, runtime, _ = _runtime()
        receipts = []

        async def log(exception: BaseException) -> None:
            """Execute the fixture reporting effect for the current incident.

            Parameters
            ----------
            exception : BaseException
                Original exception supplied to the callback.
            """
            receipts.append(await capture_nowait(OSError(), app=app))

        app.handler.log = log
        with redirect_stderr(io.StringIO()):
            await capture(ValueError(), app=app)
            await runtime.drain()
        self.assertTrue(receipts[0].degraded)
        self.assertEqual(runtime._pending, set())
        self.assertEqual(len(app.handler.failures), 1)

    async def testQueuedReportingRetainsRecursionGuardAcrossThread(self) -> None:
        """Verify queued reporting retains recursion guard across thread.

        A recovered rotation failure cannot repeatedly enqueue itself.
        """
        app, runtime, _ = _runtime()
        errors = []

        class Sink(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                """Inject the configured failure into native logging delivery.

                Parameters
                ----------
                record : logging.LogRecord
                    Native log record delivered to the sink.
                """
                error = OSError("rotation")
                errors.append(error)
                capture_nowait(error, app=app, flow="logging")

        handler = BoundedQueueHandler(Sink(), 2, app=app)

        async def log(exception: BaseException) -> None:
            """Execute the fixture reporting effect for the current incident.

            Parameters
            ----------
            exception : BaseException
                Original exception supplied to the callback.
            """
            handler.handle(logging.LogRecord("test", 40, "", 1, "error", (), None))

        app.handler.log = log
        try:
            with redirect_stderr(io.StringIO()):
                await capture(ValueError(), app=app)
                await asyncio.to_thread(handler.flush)
                await runtime.drain()
        finally:
            await asyncio.to_thread(handler.close)
        self.assertEqual(len(errors), 1)
        self.assertEqual(len(app.handler.failures), 1)
        self.assertEqual(runtime._thread_pending, set())

    async def testSynchronousSinkFailureDegradesWithoutReplacingOriginal(self) -> None:
        """Verify synchronous sink failure degrades without replacing original.

        An emit implementation that swallows OSError still fails reporting.
        """
        app, _, _ = _runtime()
        original = ValueError("application")

        class Sink(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                """Inject the configured failure into native logging delivery.

                Parameters
                ----------
                record : logging.LogRecord
                    Native log record delivered to the sink.

                Raises
                ------
                OSError
                    Propagate the fixture failure exercised by this scenario.
                """
                try:
                    message = "sink"
                    raise OSError(message)
                except OSError:
                    self.handleError(record)

        handler = Sink()
        handler.handleError = partial(
            observe_sink_error,
            app=app,
            original=lambda _: None,
        )

        async def log(exception: BaseException) -> None:
            """Execute the fixture reporting effect for the current incident.

            Parameters
            ----------
            exception : BaseException
                Original exception supplied to the callback.
            """
            handler.handle(logging.LogRecord("test", 40, "", 1, "error", (), None))

        app.handler.log = log
        with redirect_stderr(io.StringIO()):
            receipt = await capture(original, app=app)
        self.assertTrue(receipt.degraded)
        self.assertFalse(receipt.reported)
        self.assertIs(app.handler.failures[0][0], original)

    async def testReporterCannotJoinOrCancelItsOwnSupervisor(self) -> None:
        """Verify reporter cannot join or cancel its own supervisor.

        Reentrant shutdown/drain defer to the external owner without deadlock.
        """
        app, runtime, _ = _runtime()
        error = ValueError("owned task")

        async def log(exception: BaseException) -> None:
            """Execute the fixture reporting effect for the current incident.

            Parameters
            ----------
            exception : BaseException
                Original exception supplied to the callback.
            """
            await runtime.drain()
            await runtime.shutdown()

        async def fail() -> None:
            """Raise the original exception from a supervised task.

            Raises
            ------
            BaseException
                Propagate the fixture failure exercised by this scenario.
            """
            raise error

        app.handler.log = log
        async with asyncio.timeout(1):
            await capture_nowait(OSError("callback"), app=app)
            with operation(app):
                task = Loop.createTask(fail())
                with self.assertRaises(ValueError):
                    await task
            await runtime.drain()
        self.assertFalse(task.cancelled())
        self.assertEqual(len(app.handler.failures), 2)

    async def testQueuedClosePreservesBothFlushAndCloseErrors(self) -> None:
        """Verify queued close preserves both flush and close errors.

        The public first error can remain unchanged without losing cleanup.
        """
        app, runtime, _ = _runtime()
        flush_error = OSError("flush")
        close_error = OSError("close")

        class Sink(logging.Handler):
            broken = True

            def flush(self) -> None:
                """Raise the configured flush error while the sink is broken.

                Raises
                ------
                BaseException
                    Propagate the fixture failure exercised by this scenario.
                """
                if self.broken:
                    raise flush_error

            def close(self) -> None:
                """Close the sink and raise its configured cleanup error once.

                Raises
                ------
                BaseException
                    Propagate the fixture failure exercised by this scenario.
                """
                if self.broken:
                    self.broken = False
                    super().close()
                    raise close_error

        handler = BoundedQueueHandler(Sink(), 2, app=app)
        with self.assertRaises(LoggingDeliveryError):
            await asyncio.to_thread(handler.close)
        await runtime.drain()
        self.assertCountEqual(app.handler.reports, [flush_error, close_error])

    async def testRetiredOwnerStillObservesCleanupWithoutOwningNewResources(
        self,
    ) -> None:
        """Verify retired owner still observes cleanup without owning new resources.

        Pending cleanup does not prevent the next generation closing its logger.
        """
        app, runtime, owner = _runtime()
        runtime.beginClosing(owner)
        self.assertEqual(runtime.ownerCount, 0)
        self.assertTrue(runtime.active)
        self.assertTrue(runtime.hasOwner(owner))
        next_owner = object()
        await runtime.start(next_owner)
        self.assertEqual(runtime.ownerCount, 1)
        await capture(OSError("old cleanup"), app=app)
        runtime.deactivate(owner)
        self.assertTrue(runtime.hasOwner(next_owner))
        self.assertEqual(len(app.handler.failures), 1)

    async def testQueuedStreamFailureDeliversTheOriginalObject(self) -> None:
        """Verify queued stream failure delivers the original object.

        Standard logging's handleError translation keeps original identity.
        """
        app, runtime, _ = _runtime()
        error = OSError("write")
        stream = MagicMock()
        stream.write.side_effect = error
        handler = BoundedQueueHandler(logging.StreamHandler(stream), 2, app=app)
        handler.handle(logging.LogRecord("test", 40, "", 1, "error", (), None))
        with self.assertRaises(LoggingDeliveryError):
            await asyncio.to_thread(handler.close)
        await runtime.drain()
        self.assertEqual(app.handler.reports, [error])

    async def testDrainCannotOvertakeAnOwnedThreadSubmission(self) -> None:
        """Verify drain cannot overtake an owned thread submission.

        Shutdown waits for submission publication before deactivating its app.
        """
        app, runtime, owner = _runtime()
        entered = threading.Event()
        release = threading.Event()
        loop = asyncio.get_running_loop()
        submit = loop.call_soon_threadsafe
        released = []
        error = OSError("thread")

        def delayed(
            callback: object,
            *args: object,
            **kwargs: object,
        ) -> asyncio.Handle:
            """Pause the reporting worker before it enqueues its admission.

            Parameters
            ----------
            callback : object
                Callback submitted to the owning event loop.
            *args : object
                Positional callback arguments forwarded unchanged.
            **kwargs : object
                Scheduling options forwarded unchanged.

            Returns
            -------
            asyncio.Handle
                Scheduled callback handle after the worker is released.
            """
            if threading.current_thread() is thread:
                entered.set()
                released.append(release.wait(2))
            return submit(callback, *args, **kwargs)

        thread = threading.Thread(
            target=capture_nowait,
            args=(error,),
            kwargs={"app": app},
        )
        draining = None
        try:
            with patch.object(loop, "call_soon_threadsafe", delayed):
                thread.start()
                self.assertTrue(await asyncio.to_thread(entered.wait, 2))
                draining = asyncio.create_task(runtime.drain())
                await asyncio.sleep(0)
                self.assertFalse(draining.done())
                release.set()
                await asyncio.wait_for(draining, 2)
                runtime.deactivate(owner)
                self.assertEqual(app.handler.reports, [error])
        finally:
            release.set()
            await asyncio.to_thread(thread.join, 2)
            self.assertFalse(thread.is_alive())
            if draining is not None:
                await asyncio.wait_for(draining, 2)
        self.assertEqual(released, [True])

    async def testHookRaisingAfterSuperLogsOriginalOnlyOnce(self) -> None:
        """Verify hook raising after super logs original only once.

        Default effects remain deferred when a custom hook later fails.
        """
        app, runtime, _ = _runtime()
        logger = MagicMock(spec=ILogger)
        app.instance(ILogger, logger)
        responses = MagicMock()
        response = object()
        responses.exception = AsyncMock(return_value=response)
        app.config = MagicMock(return_value=True)
        request = MagicMock()
        request.wantsJson.return_value = True
        calls = []

        class Handler(BaseExceptionHandler):
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

                Raises
                ------
                RuntimeError
                    Propagate the fixture failure exercised by this scenario.
                """
                calls.append(exception)
                await super().handleFailure(exception, context)
                message = "custom hook"
                raise RuntimeError(message)

        runtime.handler = Handler(responses, app)
        error = ValueError("original")
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.HTTP)
            with operation(app, flow="http"), redirect_stderr(io.StringIO()):
                receipt = await capture(error)
                self.assertIs(await Catch(app).exception(error, request), response)
        responses.exception.assert_awaited_once()
        self.assertEqual(calls, [error])
        self.assertTrue(receipt.degraded)
        self.assertTrue(receipt.reported)
        logger.getLogger.return_value.error.assert_called_once_with(
            "[%s] %s",
            "ValueError",
            "original",
            exc_info=(ValueError, error, None),
        )

    async def testNativeLoggerFailureStillProducesHttpResponse(self) -> None:
        """Verify native logger failure still produces http response.

        Failed native logging cannot consume the plan's HTTP presentation.
        """
        app, runtime, _ = _runtime()
        logger = MagicMock(spec=ILogger)
        logger.getLogger.return_value.error.side_effect = OSError("private-log-detail")
        app.instance(ILogger, logger)
        app.config = MagicMock(return_value=True)
        response = object()
        responses = MagicMock()
        responses.exception = AsyncMock(return_value=response)
        runtime.handler = BaseExceptionHandler(responses, app)
        error = ValueError("original")
        request = MagicMock()
        request.wantsJson.return_value = True
        output = io.StringIO()
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.HTTP)
            with operation(app, flow="http"), redirect_stderr(output):
                receipt = await capture(error)
                result = await Catch(app).exception(error, request)
        self.assertIs(result, response)
        self.assertTrue(receipt.degraded)
        self.assertFalse(receipt.reported)
        logger.getLogger.return_value.error.assert_called_once()
        responses.exception.assert_awaited_once()
        self.assertIs(responses.exception.call_args.kwargs["exception"], error)
        self.assertNotIn("private-log-detail", output.getvalue())

    async def testCompletedOperationReleasesPlanAndLiveRequest(self) -> None:
        """Verify completed operation releases plan and live request.

        Retained receipts and contexts cannot retain plans or request state.
        """
        app, runtime, _ = _runtime()
        contexts = []

        class Payload:
            pass

        payload = Payload()
        reference = weakref.ref(payload)
        error = ValueError("original")
        error.payload = payload

        async def hook(
            exception: BaseException,
            context: FailureContext,
        ) -> FailureHandling:
            """Capture incident-local state in the returned handling plan.

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
            contexts.append(context)
            selected = exception.payload

            async def log() -> None:
                """Execute the fixture reporting effect for the current incident."""
                self.assertIsNotNone(selected)

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
                return request

            return FailureHandling(logging=log, presentation=present)

        runtime.handler.handleFailure = hook
        async with app.beginScope() as scope:
            scope.set("kernel", KernelContext.HTTP)
            with operation(app, flow="http") as boundary:
                receipt = await capture(error)
                await Catch(app).exception(error, payload)
            self.assertEqual(boundary.ledger, {})
        del error, payload
        gc.collect()
        self.assertIsNone(reference())
        self.assertTrue(receipt.delivered)
        self.assertEqual(contexts[0].flow, "http")

    async def testDirectContractImplementationCompletesBothHookPlans(self) -> None:
        """Verify direct contract implementation completes both hook plans.

        The runtime needs only the unified exception and result entry points.
        """
        app, runtime, _ = _runtime()
        events = []
        logs = []

        class Handler(IBaseExceptionHandler):
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
                events.append((exception, context))

                async def write() -> None:
                    """Execute the deferred logging effect for this scenario."""
                    logs.append(exception)

                return FailureHandling(logging=write)

            async def handleResult(
                self,
                value: object,
                context: FailureContext,
            ) -> FailureHandling | None:
                """Record the declared result and select its deferred effects.

                Parameters
                ----------
                value : object
                    Declared failed result supplied by the owner.
                context : FailureContext
                    Immutable failure metadata supplied by the runtime.

                Returns
                -------
                FailureHandling | None
                    Selected deferred handling plan.
                """
                events.append((value, context))

                async def write() -> None:
                    """Execute the deferred logging effect for this scenario."""
                    logs.append(value)

                return FailureHandling(logging=write)

        runtime.handler = Handler()
        error = ValueError("original")
        failure = await capture(error, app=app, flow="queue")
        result = await capture_result(9, app=app, flow="cli")
        self.assertEqual([value for value, _ in events], [error, 9])
        self.assertEqual(logs, [error, 9])
        self.assertTrue(failure.reported)
        self.assertTrue(result.reported)

    async def testScheduledHandoffOutlivesClosedChildOperation(self) -> None:
        """Verify scheduled handoff outlives closed child operation.

        A parent's presentation awaits the child callback's original plan.
        """
        app, runtime, _ = _runtime()
        error = ValueError("late child callback")
        request = object()
        with operation(app, flow="http", isolated=True) as owner:
            with operation(isolated=True):
                pending = capture_nowait(error)
                self.assertTrue(handoff(error, target=owner))
            receipt = await asyncio.wait_for(pending, 0.5)
            self.assertTrue(receipt.delivered)
            plan = await asyncio.wait_for(
                runtime.handlingFor(error, context=FailureContext(flow="http")),
                0.5,
            )
            self.assertIs(await plan.present(flow="http", request=request), request)
            duplicate = await capture(error)
            self.assertEqual(duplicate.event_id, receipt.event_id)
            self.assertTrue(duplicate.delivered)
        self.assertEqual(app.handler.reports, [error])
        self.assertEqual(len(app.handler.failures), 1)

    async def testCancelledUnstartedCaptureCanBeReclaimedByItsOwner(self) -> None:
        """Verify cancelled unstarted capture can be reclaimed by its owner.

        A task cancelled before entering capture must not leave a stuck claim.
        """
        app, runtime, _ = _runtime()
        error = ValueError("cancelled callback")
        with operation(app, flow="http"):
            pending = capture_nowait(error)
            pending.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await pending
            self.assertEqual(app.handler.failures, [])
            plan = await asyncio.wait_for(
                runtime.handlingFor(error, context=FailureContext(flow="http")),
                0.5,
            )
            self.assertIsNotNone(plan)
            receipt = await capture(error)
            self.assertTrue(receipt.delivered)
            self.assertTrue(receipt.reported)
        await runtime.drain()
        self.assertEqual(app.handler.reports, [error])
        self.assertEqual(len(app.handler.failures), 1)
        self.assertEqual(runtime._pending, set())

    async def testCancelledUnstartedThreadCaptureCanBeReclaimed(self) -> None:
        """Verify cancelled unstarted thread capture can be reclaimed.

        A cancelled worker future cannot strand presentation on the owner loop.
        """
        app, runtime, _ = _runtime()
        error = ValueError("cancelled worker callback")
        submitted = []

        def submit_and_cancel() -> None:
            """Cancel a worker submission before the owning loop starts it."""
            future = capture_nowait(error)
            future.cancel()
            submitted.append(future)

        with operation(app, flow="http"):
            context = contextvars.copy_context()
            worker = threading.Thread(target=context.run, args=(submit_and_cancel,))
            worker.start()
            # Keep the loop paused until cancellation precedes its first task step.
            worker.join(timeout=1)
            self.assertFalse(worker.is_alive())
            self.assertTrue(submitted[0].cancelled())
            await runtime.drain()
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            self.assertEqual(app.handler.failures, [])
            plan = await asyncio.wait_for(
                runtime.handlingFor(error, context=FailureContext(flow="http")),
                0.5,
            )
            self.assertIsNotNone(plan)
            receipt = await capture(error)
            self.assertTrue(receipt.delivered)
            self.assertTrue(receipt.reported)
        await runtime.drain()
        self.assertEqual(app.handler.reports, [error])
        self.assertEqual(len(app.handler.failures), 1)
        self.assertEqual(runtime._thread_pending, set())

    async def testFallbackConstructionHasTheReportingTimeout(self) -> None:
        """Verify fallback construction has the reporting timeout.

        Fallback dependency construction cannot hang after the policy fails.
        """
        app, runtime, _ = _runtime()
        runtime.timeout = 0.01
        finished = asyncio.Event()
        runtime.handler = _FailingContractHandler()

        async def build(_type: type[BaseExceptionHandler]) -> BaseExceptionHandler:
            """Exercise handler construction with the scenario-specific lifecycle.

            Parameters
            ----------
            _type : type[BaseExceptionHandler]
                Requested handler implementation.
            """
            try:
                await asyncio.Event().wait()
            finally:
                finished.set()

        app.build = AsyncMock(side_effect=build)
        with redirect_stderr(io.StringIO()):
            receipt = await asyncio.wait_for(capture(ValueError(), app=app), 0.5)
        self.assertTrue(receipt.degraded)
        self.assertFalse(receipt.delivered)
        self.assertFalse(receipt.reported)
        self.assertTrue(finished.is_set())
        app.build.assert_awaited_once_with(BaseExceptionHandler)
        self.assertEqual(len(runtime.handler.calls), 1)

    async def testFallbackConstructionDoesNotRetainRequestState(self) -> None:
        """Verify fallback construction does not retain request state.

        A cached native fallback is constructed outside the failing request.
        """
        app, runtime, _ = _runtime()
        runtime.handler = _FailingContractHandler()
        logger = MagicMock(spec=ILogger)
        app.instance(ILogger, logger)
        resolved_scopes = []

        async def build(_type: type[BaseExceptionHandler]) -> BaseExceptionHandler:
            """Exercise handler construction with the scenario-specific lifecycle.

            Parameters
            ----------
            _type : type[BaseExceptionHandler]
                Requested handler implementation.

            Returns
            -------
            BaseExceptionHandler
                Value returned by the configured fixture operation.
            """
            resolved_scopes.append((app.getCurrentScope(), current_operation()))
            return BaseExceptionHandler(MagicMock(), app)

        app.build = AsyncMock(side_effect=build)
        async with app.beginScope() as scope:
            with operation(app) as boundary, redirect_stderr(io.StringIO()):
                receipt = await capture(ValueError())
                self.assertIs(app.getCurrentScope(), scope)
                self.assertIs(current_operation(), boundary)
        self.assertEqual(resolved_scopes, [(None, None)])
        self.assertTrue(receipt.reported)

    async def testLazyResolutionHasTheReportingTimeout(self) -> None:
        """Verify lazy resolution has the reporting timeout.

        An embedder's unresolved handler cannot hang either incident hook.
        """
        for capture_function, value in ((capture, ValueError()), (capture_result, 1)):
            with self.subTest(hook=capture_function.__name__):
                app, runtime, _ = _runtime()
                runtime.handler = None
                runtime.timeout = 0.01
                finished = asyncio.Event()
                logger = MagicMock(spec=ILogger)
                app.instance(ILogger, logger)
                app.build = AsyncMock(
                    return_value=BaseExceptionHandler(MagicMock(), app),
                )

                async def resolve(completed: asyncio.Event = finished) -> None:
                    """Resolve or suspend the handler according to the fixture scenario.

                    Parameters
                    ----------
                    completed : asyncio.Event
                        Event set when handler resolution exits.
                    """
                    try:
                        await asyncio.Event().wait()
                    finally:
                        completed.set()

                app.getExceptionHandler = AsyncMock(side_effect=resolve)
                with redirect_stderr(io.StringIO()):
                    receipt = await asyncio.wait_for(
                        capture_function(value, app=app),
                        0.5,
                    )
                self.assertTrue(receipt.degraded)
                self.assertFalse(receipt.delivered)
                self.assertTrue(finished.is_set())
                app.getExceptionHandler.assert_awaited_once()

    async def testInternalResolutionCancellationPreservesTheOriginal(self) -> None:
        """Verify internal resolution cancellation preserves the original.

        An embedder's CancelledError is protected like a failed handler hook.
        """
        app, runtime, _ = _runtime()
        runtime.handler = None
        logger = MagicMock(spec=ILogger)
        app.instance(ILogger, logger)
        app.build = AsyncMock(return_value=BaseExceptionHandler(MagicMock(), app))
        app.getExceptionHandler = AsyncMock(side_effect=asyncio.CancelledError())
        error = ValueError("original")
        with redirect_stderr(io.StringIO()):
            receipt = await capture(error, app=app)
        self.assertTrue(receipt.degraded)
        self.assertFalse(receipt.delivered)
        self.assertTrue(receipt.reported)
        self.assertEqual(asyncio.current_task().cancelling(), 0)
        logger.getLogger.return_value.error.assert_called_once_with(
            "[%s] %s",
            "ValueError",
            "original",
            exc_info=(ValueError, error, None),
        )

    async def testFallbackInternalCancellationDegradesOriginalFailure(self) -> None:
        """Verify fallback internal cancellation degrades original failure.

        A dependency's own CancelledError does not cancel the reporting owner.
        """
        app, runtime, _ = _runtime()
        runtime.handler = _FailingContractHandler()
        app.build = AsyncMock(side_effect=asyncio.CancelledError())
        with redirect_stderr(io.StringIO()):
            receipt = await capture(ValueError("original"), app=app)
        self.assertTrue(receipt.degraded)
        self.assertFalse(receipt.delivered)
        self.assertFalse(receipt.reported)
        self.assertEqual(asyncio.current_task().cancelling(), 0)
        app.build.assert_awaited_once_with(BaseExceptionHandler)

    async def testCallerCancellationDuringFallbackStillPropagates(self) -> None:
        """Protect fallback failures while retaining caller cancellation semantics."""
        app, runtime, _ = _runtime()
        runtime.handler = _FailingContractHandler()
        entered = asyncio.Event()
        finished = asyncio.Event()

        async def build(_type: type[BaseExceptionHandler]) -> BaseExceptionHandler:
            """Exercise handler construction with the scenario-specific lifecycle.

            Parameters
            ----------
            _type : type[BaseExceptionHandler]
                Requested handler implementation.
            """
            try:
                entered.set()
                await asyncio.Event().wait()
            finally:
                finished.set()

        app.build = AsyncMock(side_effect=build)
        with redirect_stderr(io.StringIO()):
            task = asyncio.create_task(capture(ValueError(), app=app))
            await asyncio.wait_for(entered.wait(), 0.5)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(finished.is_set())
        app.build.assert_awaited_once_with(BaseExceptionHandler)

    async def testConsumedCallerCancellationDoesNotHideInternalReportingFailure(
        self,
    ) -> None:
        """Distinguish old cancellation counts from fresh reporter cancellation."""
        for stage in ("hook", "resolution", "fallback", "logging", "presentation"):
            with self.subTest(stage=stage):
                app, runtime, _ = _runtime()
                error = ValueError("primary")
                logger = MagicMock(spec=ILogger)
                app.instance(ILogger, logger)
                cancelled = AsyncMock(side_effect=asyncio.CancelledError("internal"))
                if stage == "hook":
                    app.handler.handleFailure = cancelled
                elif stage == "resolution":
                    runtime.handler = None
                    app.getExceptionHandler = cancelled
                elif stage == "fallback":
                    runtime.handler = _FailingContractHandler()
                    app.build = cancelled
                elif stage == "logging":
                    app.handler.log = cancelled

                async def observe(
                    current_stage: str = stage,
                    owner: FailureRuntime = runtime,
                    failure: BaseException = error,
                    presenter: AsyncMock = cancelled,
                ) -> None:
                    """Exercise cancellation while observing the original failure.

                    Parameters
                    ----------
                    current_stage : str
                        Reporting stage receiving an internal cancellation.
                    owner : FailureRuntime
                        Runtime owning this incident.
                    failure : BaseException
                        Primary exception that must remain unchanged.
                    presenter : AsyncMock
                        Callback injecting the internal cancellation.
                    """
                    task = asyncio.current_task()
                    task.cancel("previous")
                    with self.assertRaises(asyncio.CancelledError):
                        await asyncio.sleep(0)
                    try:
                        if current_stage == "presentation":
                            with self.assertRaises(ValueError) as raised:
                                await owner.presentHandling(
                                    FailureHandling(presentation=presenter),
                                    failure,
                                    context=FailureContext(flow="http"),
                                )
                            self.assertIs(raised.exception, failure)
                        else:
                            receipt = await owner.capture(
                                failure,
                                context=FailureContext(),
                            )
                            self.assertTrue(receipt.degraded)
                        self.assertEqual(task.cancelling(), 1)
                    finally:
                        task.uncancel()

                with redirect_stderr(io.StringIO()):
                    await asyncio.create_task(observe())
                cancelled.assert_awaited_once()

    async def testPendingCallerCancellationPrecedesReportingEffects(self) -> None:
        """Deliver cancellation already requested before starting the hook."""
        app, runtime, _ = _runtime()
        app.handler.handleFailure = AsyncMock(return_value=None)

        async def observe() -> None:
            """Exercise cancellation while observing the original failure."""
            task = asyncio.current_task()
            task.cancel("pending")
            try:
                with self.assertRaises(asyncio.CancelledError):
                    await runtime.capture(ValueError(), context=FailureContext())
            finally:
                task.uncancel()

        await asyncio.create_task(observe())
        app.handler.handleFailure.assert_not_awaited()
