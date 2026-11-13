# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Exercise runtime ownership, original exception identity and shutdown cleanup."""

import asyncio
import inspect
from typing import TYPE_CHECKING, get_type_hints

from orionis.failure.entities.context import FailureContext
from orionis.failure.runtime import (
    capture,
    capture_nowait,
    capture_result,
    FailureRuntime,
    operation,
    reporting_from,
)
from tests.support.failure_runtime import IsolatedFailureTestCase, activate_runtime


if TYPE_CHECKING:
    from collections.abc import Iterator


class _FalsyCause(Exception):
    """Provide a legitimate exception whose truth value is false."""

    def __bool__(self) -> bool:
        """Return false without changing exception identity."""
        return False


class _UnbooleanableCause(Exception):
    """Reject truth-value inspection of an exception."""

    def __bool__(self) -> bool:
        """Fail if runtime bookkeeping evaluates exception truthiness."""
        message = "Exception truthiness must not be evaluated."
        raise AssertionError(message)


class _CustomInterrupt(KeyboardInterrupt):
    """Preserve control-signal semantics for application-defined subclasses."""


class _ClosingAwaitable:
    """Raise an original cleanup error when discarded before execution."""

    def __init__(self, error: Exception) -> None:
        """Store one original cleanup exception."""
        self.error = error

    def __await__(self) -> Iterator[object]:
        """Complete immediately if the work is ever started."""
        return iter(())

    def close(self) -> None:
        """Raise the stored error during abandoned-work cleanup."""
        raise self.error


class TestRuntimeRegressions(IsolatedFailureTestCase):
    """Keep failure observation bounded and isolated from retired contexts."""

    async def testShutdownRejectsNewWorkUntilExplicitRestart(self) -> None:
        """Cancel new work before entry under ordinary and eager task factories."""
        _, runtime, _ = activate_runtime()
        loop = asyncio.get_running_loop()
        previous = loop.get_task_factory()
        entered = []

        async def work() -> int:
            """Record execution so rejected coroutine bodies remain observable."""
            entered.append(True)
            return 7

        await runtime.shutdown()
        try:
            for factory in (None, asyncio.eager_task_factory):
                with self.subTest(factory=factory):
                    loop.set_task_factory(factory)
                    coroutine = work()
                    task = runtime.createTask(coroutine)
                    with self.assertRaises(asyncio.CancelledError):
                        await task
                    await runtime.shutdown()
                    self.assertEqual(
                        inspect.getcoroutinestate(coroutine),
                        inspect.CORO_CLOSED,
                    )
            self.assertEqual(entered, [])
            await runtime.start(object())
            self.assertEqual(await runtime.createTask(work()), 7)
        finally:
            loop.set_task_factory(previous)
            await runtime.shutdown()

    async def testExternalRestartWaitsAndCleanupRestartFailsPromptly(self) -> None:
        """Wait for a shared shutdown without allowing its own work to reenter."""
        _, runtime, _ = activate_runtime()
        started = asyncio.Event()
        cleanup_started = asyncio.Event()
        release = asyncio.Event()
        rejected = []

        async def work() -> None:
            """Attempt a forbidden restart while shutdown drains this task."""
            try:
                started.set()
                await asyncio.Event().wait()
            finally:
                try:
                    await runtime.start(object())
                except RuntimeError:
                    rejected.append(True)
                cleanup_started.set()
                await release.wait()

        task = runtime.createTask(work())
        closing = None
        restarting = None
        try:
            await started.wait()
            closing = asyncio.create_task(runtime.shutdown())
            await asyncio.wait_for(cleanup_started.wait(), timeout=2)
            restarting = asyncio.create_task(runtime.start(object()))
            await asyncio.sleep(0)
            self.assertFalse(restarting.done())
            self.assertEqual(rejected, [True])
            with self.assertRaises(RuntimeError):
                runtime.activate(object())
        finally:
            release.set()
            pending = [item for item in (closing, restarting, task) if item is not None]
            await asyncio.gather(*pending, return_exceptions=True)
            await runtime.shutdown()

    async def testConcurrentShutdownWaitersDoNotRecancelSharedCleanup(self) -> None:
        """Keep cleanup alive when a second waiter joins or another is cancelled."""
        _, runtime, _ = activate_runtime()
        started = asyncio.Event()
        cleanup_started = asyncio.Event()
        cleanup_finished = asyncio.Event()
        release = asyncio.Event()

        async def work() -> None:
            """Retain a cleanup operation until its explicit release."""
            try:
                started.set()
                await asyncio.Event().wait()
            finally:
                cleanup_started.set()
                try:
                    await release.wait()
                finally:
                    cleanup_finished.set()

        task = runtime.createTask(work())
        first = None
        second = None
        try:
            await started.wait()
            first = asyncio.create_task(runtime.shutdown())
            await asyncio.wait_for(cleanup_started.wait(), timeout=2)
            second = asyncio.create_task(runtime.shutdown())
            await asyncio.sleep(0)
            self.assertFalse(cleanup_finished.is_set())
            first.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await first
            self.assertFalse(cleanup_finished.is_set())
            self.assertFalse(second.done())
            release.set()
            await second
            self.assertTrue(cleanup_finished.is_set())
        finally:
            release.set()
            pending = [item for item in (first, second, task) if item is not None]
            await asyncio.gather(*pending, return_exceptions=True)
            await runtime.shutdown()

    async def testControlSignalsDoNotEnterStandaloneOrCallbackReporting(self) -> None:
        """Skip control signals consistently while retaining mixed groups intact."""
        app, runtime, handler = activate_runtime()
        standalone = FailureRuntime(app, handler)
        context = FailureContext(flow="worker", phase="execution")
        for signal in (
            asyncio.CancelledError(),
            KeyboardInterrupt(),
            _CustomInterrupt(),
            SystemExit(),
            GeneratorExit(),
        ):
            with self.subTest(signal=type(signal).__name__, entry="standalone"):
                receipt, handling = await standalone.dispatchFailure(
                    signal,
                    context=context,
                )
                self.assertFalse(receipt.delivered)
                self.assertIsNone(handling)
            with self.subTest(signal=type(signal).__name__, entry="callback"):
                pending = capture_nowait(signal, runtime=runtime)
                try:
                    self.assertIsNone(pending)
                finally:
                    if pending is not None:
                        await pending
        self.assertEqual(handler.failures, [])
        mixed = BaseExceptionGroup(
            "mixed",
            [KeyboardInterrupt(), ValueError("failure")],
        )
        await capture(mixed, runtime=runtime)
        self.assertIs(handler.failures[-1][0], mixed)

    async def testCausalLinkDoesNotEvaluateExceptionTruthiness(self) -> None:
        """Link the explicit cause by identity even when its bool is unusual."""
        for kind in (_FalsyCause, _UnbooleanableCause):
            with self.subTest(kind=kind.__name__):
                _, runtime, handler = activate_runtime()
                cause = kind("original")
                secondary = RuntimeError("secondary")
                secondary.__cause__ = cause
                with operation(runtime=runtime, isolated=True):
                    first = await capture(cause, runtime=runtime)
                    await capture(secondary, runtime=runtime)
                self.assertIs(handler.failures[-1][0], secondary)
                self.assertEqual(
                    handler.failures[-1][1].parent_event_id,
                    first.event_id,
                )

    async def testClosedOperationDoesNotSupplyLateTaskMetadata(self) -> None:
        """Use fresh defaults after the inherited operation owner has closed."""
        _, runtime, handler = activate_runtime()
        ready = asyncio.Event()

        async def report_later() -> None:
            """Capture explicitly after the creating operation exits."""
            await ready.wait()
            await capture(ValueError("late"), runtime=runtime)

        with operation(
            runtime=runtime,
            operation="retired",
            correlation_id="retired-correlation",
            isolated=True,
        ):
            pending = asyncio.create_task(report_later())
        try:
            ready.set()
            await pending
            context = handler.failures[-1][1]
            self.assertIsNone(context.operation)
            self.assertIsNone(context.correlation_id)
        finally:
            ready.set()
            await pending

    async def testShutdownSettlesTasksCreatedDuringCleanup(self) -> None:
        """Retain and settle children created by a cancelled owner's finally."""
        _, runtime, _ = activate_runtime()
        started = asyncio.Event()
        children = []

        async def child_work() -> None:
            """Wait until shutdown takes ownership of this child."""
            await asyncio.Event().wait()

        async def work() -> None:
            """Create a supervised child while cancellation unwinds."""
            try:
                started.set()
                await asyncio.Event().wait()
            finally:
                children.append(runtime.createTask(child_work()))

        parent = runtime.createTask(work())
        try:
            await started.wait()
            await runtime.shutdown()
            self.assertTrue(parent.done())
            self.assertEqual(len(children), 1)
            self.assertTrue(children[0].done())
        finally:
            for task in (parent, *children):
                task.cancel()
            await asyncio.gather(parent, *children, return_exceptions=True)
            await runtime.drain()

    async def testCancelledWorkCleanupUsesTheCentralObserver(self) -> None:
        """Capture close errors once instead of leaking a callback exception."""
        _, runtime, handler = activate_runtime()
        loop = asyncio.get_running_loop()
        previous = loop.get_exception_handler()
        loop_errors = []

        def record_loop_error(_loop: object, context: dict) -> None:
            """Retain unexpected callback errors for an explicit assertion."""
            loop_errors.append(context)

        loop.set_exception_handler(record_loop_error)
        error = ValueError("cleanup")
        try:
            pending = runtime.createTask(_ClosingAwaitable(error))
            pending.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await pending
            await runtime.drain()
            self.assertEqual(handler.reports, [error])
            self.assertIs(handler.failures[0][0], error)
            self.assertEqual(handler.failures[0][1].phase, "cancelled_cleanup")
            self.assertEqual(loop_errors, [])
        finally:
            loop.set_exception_handler(previous)
            await runtime.shutdown()

    async def testDeepObservedGroupDoesNotOverflowTheLedgerLookup(self) -> None:
        """Deduplicate an intact nested group without recursive Python calls."""
        _, runtime, handler = activate_runtime()
        error = ValueError("original")
        group = error
        for _ in range(1100):
            group = ExceptionGroup("nested", [group])
        with operation(runtime=runtime, isolated=True):
            first = await capture(error, runtime=runtime)
            receipt = await capture(group, runtime=runtime)
        self.assertTrue(receipt.duplicate)
        self.assertEqual(receipt.event_id, first.event_id)
        self.assertEqual(handler.reports, [error])

    def testPublicRuntimeAnnotationsResolve(self) -> None:
        """Resolve exported runtime helper annotations without caller namespaces."""
        for function in (capture, capture_nowait, capture_result, reporting_from):
            with self.subTest(function=function.__name__):
                self.assertIn("return", get_type_hints(function))
