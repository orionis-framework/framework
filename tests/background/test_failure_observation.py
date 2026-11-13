# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify background errors retain identity and do not depend on request scopes."""

import asyncio
import threading
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch
from orionis.background.task import BackgroundTask
from orionis.failure.runtime import capture_nowait, operation
from tests.support.failure_runtime import IsolatedFailureTestCase, activate_runtime

if TYPE_CHECKING:
    from collections.abc import Generator


class TestBackgroundFailureObservation(IsolatedFailureTestCase):
    """Exercise both execution styles with a real application handler."""

    async def testCancelledCleanupFailureRetainsCancellation(self) -> None:
        """Report a failed awaitable cleanup once without replacing cancellation."""
        loop = asyncio.get_running_loop()
        awaited = []

        class Result:
            """Expose a failing cleanup hook without running its await protocol."""

            def __await__(self) -> Generator[None]:
                """Record an unexpected execution of the abandoned awaitable.

                Yields
                ------
                None
                    Cooperative await checkpoint.
                """
                awaited.append(True)
                yield

            def close(self) -> None:
                """Raise the controlled cleanup failure.

                Raises
                ------
                OSError
                    Always raise the original cleanup failure.
                """
                raise error

        for kind in ("custom", "failed_future"):
            with self.subTest(kind=kind):
                app, runtime, handler = activate_runtime()
                self.addAsyncCleanup(runtime.shutdown)
                started, release = asyncio.Event(), threading.Event()
                error = OSError(f"abandoned {kind} failure")
                if kind == "custom":
                    result = Result()
                else:
                    result = loop.create_future()
                    result.set_exception(error)

                def work(
                    value: object = result,
                    entered: asyncio.Event = started,
                    gate: threading.Event = release,
                ) -> object:
                    """Return the selected awaitable once its worker is released.

                    Parameters
                    ----------
                    value : object
                        Awaitable selected by the current scenario.
                    entered : asyncio.Event
                        Notification that this worker has started.
                    gate : threading.Event
                        Release gate retained by this worker.

                    Returns
                    -------
                    object
                        Awaitable whose cleanup reports the original failure.
                    """
                    loop.call_soon_threadsafe(entered.set)
                    gate.wait()
                    return value

                with operation(app):
                    task = asyncio.create_task(BackgroundTask(work)())
                    try:
                        await asyncio.wait_for(started.wait(), timeout=5)
                        task.cancel()
                        release.set()
                        with self.assertRaises(asyncio.CancelledError):
                            await task
                        await runtime.drain()
                    finally:
                        release.set()
                        if not task.done():
                            task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
                        if kind == "failed_future":
                            result.exception()
                self.assertEqual(awaited, [])
                self.assertEqual(handler.reports, [error])
                self.assertEqual(len(handler.failures), 1)
                self.assertIs(handler.failures[0][0], error)
                self.assertEqual(handler.failures[0][1].phase, "cancelled_cleanup")

    async def testCancelledSyncTaskDrainsItsLateFailure(self) -> None:
        """Retain cancellation while observing a worker failure after cancellation."""
        app, runtime, handler = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)
        started, release = asyncio.Event(), threading.Event()
        loop = asyncio.get_running_loop()
        error = OSError("late worker failure")

        def fail() -> None:
            """Wait for release before raising the worker's controlled failure.

            Raises
            ------
            OSError
                Always raise the worker failure after release.
            """
            loop.call_soon_threadsafe(started.set)
            release.wait()
            raise error

        with operation(app):
            task = asyncio.create_task(BackgroundTask(fail)())
            try:
                await asyncio.wait_for(started.wait(), timeout=5)
                task.cancel()
                release.set()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            finally:
                release.set()
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        self.assertEqual(handler.reports, [error])

    async def testOriginalFailureReachesHandlerAndIsReraisedOnce(self) -> None:
        """Verify original failure reaches handler and is reraised once."""
        app, runtime, handler = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)
        error = ValueError("background original")

        async def fail() -> None:
            """Raise the original failure for identity and reporting assertions.

            Raises
            ------
            ValueError
                Always raise the controlled original failure.
            """
            raise error

        with (
            operation(app, flow="http"),
            patch("orionis.background.task.Log") as log,
            self.assertRaises(ValueError) as caught,
        ):
            await BackgroundTask(fail)()
        self.assertIs(caught.exception, error)
        self.assertEqual(handler.reports, [error])
        self.assertEqual(handler.failures[0][1].flow, "background")
        log.error.assert_not_called()

    async def testInactiveBrokenLoggerCannotReplaceTheOriginal(self) -> None:
        """Verify inactive broken logger cannot replace the original."""
        error = ValueError("background original")

        async def fail() -> None:
            """Raise the application failure while the fallback logger is broken.

            Raises
            ------
            ValueError
                Always raise the original application failure.
            """
            raise error

        with patch("orionis.background.task.Log") as log:
            log.error.side_effect = OSError("logging unavailable")
            with self.assertRaises(ValueError) as caught:
                await BackgroundTask(fail)()
            log.error.assert_called_once()
        self.assertIs(caught.exception, error)

    async def testSyncTaskCarriesRuntimeIntoRecoveredServiceErrors(self) -> None:
        """Verify sync task carries runtime into recovered service errors."""
        app, runtime, handler = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)
        error = OSError("recovered thread failure")

        def recovered() -> None:
            """Report a recovered service error from the inherited worker context."""
            capture_nowait(error, flow="storage", phase="read")

        with operation(app), patch("orionis.background.task.Log", MagicMock()):
            await BackgroundTask(recovered)()
            await runtime.drain()
        self.assertEqual(handler.reports, [error])

    async def testSuccessDoesNotInvokeTheFailureHandler(self) -> None:
        """Verify success does not invoke the failure handler."""
        app, runtime, handler = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)
        calls = []

        async def succeed() -> None:
            """Record successful execution without reporting a failure."""
            calls.append(1)

        with operation(app), patch("orionis.background.task.Log", MagicMock()):
            await BackgroundTask(succeed)()
        self.assertEqual(calls, [1])
        self.assertEqual(handler.failures, [])
        self.assertEqual(handler.results, [])
