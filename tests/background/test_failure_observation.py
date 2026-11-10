"""Verify background errors retain identity and do not depend on request scopes."""

import asyncio
import threading
from unittest.mock import MagicMock, patch
from orionis.background.task import BackgroundTask
from orionis.failure.runtime import operation
from orionis.test import TestCase
from tests.support.failure_runtime import activate_runtime


class TestBackgroundFailureObservation(TestCase):
    """Exercise both execution styles with a real application handler."""

    async def testCancelledSyncTaskDrainsItsLateFailure(self) -> None:
        """Retain cancellation while observing a worker failure after cancellation."""
        app, _, handler = activate_runtime()
        started, release = asyncio.Event(), threading.Event()
        loop = asyncio.get_running_loop()
        error = OSError("late worker failure")

        def fail():
            loop.call_soon_threadsafe(started.set)
            release.wait()
            raise error

        with operation(app):
            task = asyncio.create_task(BackgroundTask(fail)())
            await started.wait()
            task.cancel()
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(handler.reports, [error])

    async def testOriginalFailureReachesHandlerAndIsReraisedOnce(self) -> None:
        """Verify original failure reaches handler and is reraised once."""
        app, _, handler = activate_runtime()
        error = ValueError("background original")

        async def fail():
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

        async def fail():
            raise error

        with patch("orionis.background.task.Log") as log:
            log.error.side_effect = OSError("logging unavailable")
            with self.assertRaises(ValueError) as caught:
                await BackgroundTask(fail)()
        self.assertIs(caught.exception, error)

    async def testSyncTaskCarriesRuntimeIntoRecoveredServiceErrors(self) -> None:
        """Verify sync task carries runtime into recovered service errors."""
        from orionis.failure.runtime import capture_nowait

        app, runtime, handler = activate_runtime()
        error = OSError("recovered thread failure")

        def recovered():
            capture_nowait(error, flow="storage", phase="read")

        with operation(app), patch("orionis.background.task.Log", MagicMock()):
            await BackgroundTask(recovered)()
            await runtime.drain()
        self.assertEqual(handler.reports, [error])

    async def testSuccessDoesNotInvokeTheFailureHandler(self) -> None:
        """Verify success does not invoke the failure handler."""
        app, _, handler = activate_runtime()
        calls = []

        async def succeed():
            calls.append(1)

        with operation(app), patch("orionis.background.task.Log", MagicMock()):
            await BackgroundTask(succeed)()
        self.assertEqual(calls, [1])
        self.assertEqual(handler.failures, [])
        self.assertEqual(handler.results, [])
