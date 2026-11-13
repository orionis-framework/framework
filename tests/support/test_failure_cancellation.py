# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Observe native work failures while preserving caller cancellation."""

import asyncio
from unittest.mock import AsyncMock, patch
from orionis.database.threaded.worker import _wait_for_completion
from orionis.failure.runtime import operation
from orionis.support.concurrency import complete_on_cancel
from orionis.test import TestCase
from tests.support.failure_runtime import activate_runtime


class TestCancelledFailureObservation(TestCase):
    """Collect errors that finish after their owning task was cancelled."""

    async def testDatabaseFailureAfterCancellationIsNotDiscarded(self) -> None:
        """Verify database failure after cancellation is not discarded."""
        app, _, handler = activate_runtime()
        error = OSError("late database failure")
        future = asyncio.get_running_loop().create_future()
        with operation(app, flow="http"):
            task = asyncio.create_task(_wait_for_completion(future))
            await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
            future.set_exception(error)
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(handler.reports, [error])
        self.assertEqual(handler.failures[0][1].phase, "cancelled_work")

    async def testCancellationCleanupFailureDoesNotReplaceCancellation(self) -> None:
        """Verify cancellation cleanup failure does not replace cancellation."""
        app, _, handler = activate_runtime()
        error = RuntimeError("late resource cleanup")
        future = asyncio.get_running_loop().create_future()
        cleanup = AsyncMock(side_effect=error)
        with operation(app):
            task = asyncio.create_task(_wait_for_completion(future, on_cancel=cleanup))
            await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
            future.set_result(object())
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(handler.reports, [error])
        self.assertEqual(handler.failures[0][1].phase, "cleanup")

    async def testOwnedFutureFailureAfterCancellationIsObserved(self) -> None:
        """Verify owned future failure after cancellation is observed."""
        app, _, handler = activate_runtime()
        error = RuntimeError("late owned work")
        future = asyncio.get_running_loop().create_future()
        with operation(app):
            task = asyncio.create_task(complete_on_cancel(future))
            await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
            future.set_exception(error)
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(handler.reports, [error])

    async def testFailingStopCallbackStillDrainsOwnedWork(self) -> None:
        """Verify failing stop callback still drains owned work."""
        app, _, handler = activate_runtime()
        error = RuntimeError("stop callback")
        future = asyncio.get_running_loop().create_future()

        def stop() -> None:
            """Raise the fixture error while stopping cancelled work."""
            raise error

        with operation(app):
            task = asyncio.create_task(complete_on_cancel(future, on_cancel=stop))
            await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            future.set_result(None)
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(handler.reports, [error])

    async def testRepeatedCancellationDuringStopReportingStillDrainsWork(self) -> None:
        """Finish owned work if cancellation interrupts stop-error reporting."""
        future = asyncio.get_running_loop().create_future()
        reporting = asyncio.Event()

        def stop() -> None:
            """Raise the fixture error while stopping cancelled work."""
            message = "stop callback failed"
            raise RuntimeError(message)

        async def observe(*_args: object, **_kwargs: object) -> None:
            """Suspend reporting so repeated cancellation can interrupt it."""
            reporting.set()
            await asyncio.Event().wait()

        with patch("orionis.failure.runtime.capture", side_effect=observe):
            task = asyncio.create_task(complete_on_cancel(future, on_cancel=stop))
            await asyncio.sleep(0)
            task.cancel()
            await reporting.wait()
            task.cancel()
            await asyncio.sleep(0)
            completed_early = task.done()
            future.set_result(None)
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertFalse(completed_early)
