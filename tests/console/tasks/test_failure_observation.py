"""Exercise scheduler failure delivery without external scheduler services."""

import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from orionis.console.enums.events import TaskEvent
from orionis.console.tasks.schedule import Schedule
from orionis.failure.runtime import capture, operation
from orionis.test import TestCase
from tests.support.failure_runtime import activate_runtime


class TestSchedulerFailureObservation(TestCase):
    """Observe jobs, listeners and shutdown through the configured handler."""

    async def asyncSetUp(self) -> None:
        """Prepare an isolated runtime and collaborators."""
        self.app, self.runtime, self.handler = activate_runtime()
        stores = MagicMock()
        stores.config.store = "memory"
        self.schedule = Schedule(MagicMock(), MagicMock(), stores)
        self.schedule._Schedule__failure_runtime = self.runtime

    async def _drain(self) -> None:
        pending = self.schedule._Schedule__pending_listener_tasks
        while pending:
            await asyncio.gather(*tuple(pending), return_exceptions=True)
            await asyncio.sleep(0)

    async def testJobErrorIsObservedWithoutAnyUserListener(self) -> None:
        """Verify job error is observed without any user listener."""
        error = ValueError("scheduler backend")
        event = SimpleNamespace(
            code=TaskEvent.ERROR, job_id="test:job", exception=error,
        )
        self.schedule._dispatchTaskEventListener(event)
        await self._drain()
        self.assertEqual(len(self.handler.failures), 1)
        self.assertIs(self.handler.failures[0][0], error)
        self.assertEqual(self.handler.failures[0][1].phase, "job")

    async def testJobAndListenerFailuresRemainDistinct(self) -> None:
        """Verify job and listener failures remain distinct."""
        original = ValueError("job")
        listener = OSError("listener")
        self.schedule._Schedule__tasks_listeners["test:job"] = {
            TaskEvent.ERROR: AsyncMock(side_effect=listener),
        }
        event = SimpleNamespace(
            code=TaskEvent.ERROR, job_id="test:job", exception=original,
        )
        self.schedule._dispatchTaskEventListener(event)
        await self._drain()
        self.assertCountEqual(
            [error for error, _ in self.handler.failures], [original, listener],
        )

    async def testManagedTaskFailureIsCollectedBeforeItIsDiscarded(self) -> None:
        """Verify managed task failure is collected before it is discarded."""
        error = RuntimeError("managed task")

        async def fail():
            raise error

        self.schedule._Schedule__createManagedTask(fail())
        await self._drain()
        self.assertEqual(len(self.handler.failures), 1)
        self.assertIs(self.handler.failures[0][0], error)

    async def testShutdownFailureUnblocksWaitAndPreservesItsException(self) -> None:
        """Verify shutdown failure unblocks wait and preserves its exception."""
        error = RuntimeError("shutdown backend")
        self.schedule._Schedule__scheduler = SimpleNamespace(
            shutdown=MagicMock(side_effect=error),
        )
        with operation(self.app, flow="scheduler"):
            self.schedule.shutdown(wait=0)
            with self.assertRaises(RuntimeError) as caught:
                await asyncio.wait_for(self.schedule.wait(), 1)
            await self._drain()
        self.assertIs(caught.exception, error)
        self.assertEqual(len(self.handler.failures), 1)
        self.assertEqual(self.handler.failures[0][1].phase, "shutdown")

    async def testCancelledTaskClosesAnUnstartedCoroutine(self) -> None:
        """Verify cancelled task closes an unstarted coroutine."""

        async def never_started():
            await asyncio.sleep(1)

        coroutine = never_started()
        self.schedule._Schedule__createManagedTask(coroutine)
        task = next(iter(self.schedule._Schedule__pending_listener_tasks))
        task.cancel()
        await self._drain()
        self.assertIsNone(coroutine.cr_frame)
        self.assertEqual(self.handler.failures, [])

    async def testShutdownCancellationBeforeStartingReleasesWaiters(self) -> None:
        """Expose cancellation even if shutdown never reaches its finally block."""
        self.schedule.shutdown(wait=0)
        task = next(iter(self.schedule._Schedule__pending_listener_tasks))
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(self.schedule.wait(), 1)
        await self._drain()
        self.assertEqual(self.handler.failures, [])

    async def testRepeatedShutdownDrainsAndStopsTheSchedulerOnce(self) -> None:
        """Avoid sibling shutdown tasks waiting on one another during draining."""
        shutdown = MagicMock()
        self.schedule._Schedule__scheduler = SimpleNamespace(shutdown=shutdown)
        self.schedule.shutdown(wait=0)
        self.schedule.shutdown(wait=0)
        await asyncio.wait_for(self.schedule.wait(), 1)
        await self._drain()
        shutdown.assert_called_once_with(wait=True)
        self.assertEqual(self.handler.failures, [])

    async def testConsumedControlFailureReachesHandlerWithoutLocalLogging(self) -> None:
        """Observe the public wrapper even if application code consumes it."""
        original = OSError("scheduler backend")
        self.schedule._Schedule__scheduler = SimpleNamespace(
            remove_all_jobs=MagicMock(side_effect=original),
        )
        with patch("orionis.console.tasks.schedule.Log") as log:
            with self.assertRaises(RuntimeError) as caught:
                self.schedule.removeAllTasks()
            await self.runtime.drain()
        self.assertIs(caught.exception.__cause__, original)
        self.assertEqual(self.handler.reports, [caught.exception])
        log.error.assert_not_called()

    async def testControlFailureReportsOnceAcrossTheOuterBoundary(self) -> None:
        """Reuse the scheduled incident when the same wrapper propagates outward."""
        original = OSError("scheduler backend")
        self.schedule._Schedule__scheduler = SimpleNamespace(
            remove_all_jobs=MagicMock(side_effect=original),
        )
        with operation(self.app), patch("orionis.console.tasks.schedule.Log") as log:
            with self.assertRaises(RuntimeError) as caught:
                self.schedule.removeAllTasks()
            await capture(caught.exception, app=self.app, flow="console")
            await self.runtime.drain()
        self.assertIs(caught.exception.__cause__, original)
        self.assertEqual(self.handler.reports, [caught.exception])
        self.assertEqual(len(self.handler.failures), 1)
        log.error.assert_not_called()

    async def testInactiveControlFailureKeepsItsLegacyLogging(self) -> None:
        """Preserve standalone logging and exception chaining before activation."""
        self.runtime._owners.clear()
        original = OSError("scheduler backend")
        self.schedule._Schedule__scheduler = SimpleNamespace(
            remove_all_jobs=MagicMock(side_effect=original),
        )
        with patch("orionis.console.tasks.schedule.Log") as log:
            with self.assertRaises(RuntimeError) as caught:
                self.schedule.removeAllTasks()
            log.error.assert_called_once()
        self.assertIs(caught.exception.__cause__, original)
        self.assertEqual(self.handler.failures, [])

    async def testSeparateListenersMayRaiseTheSameExceptionInstance(self) -> None:
        """Keep independent listener invocations independently observable."""
        error = OSError("reused listener failure")
        with operation(self.app):
            await self.schedule._Schedule__handleListenerException(error)
            await self.schedule._Schedule__handleListenerException(error)
        self.assertEqual(self.handler.reports, [error, error])

    async def testCancelledShutdownRetainsWorkerFailureWithoutCallerScope(self) -> None:
        """Keep the saved scheduler runtime available to a cancelled worker drain."""
        started, release = asyncio.Event(), threading.Event()
        loop = asyncio.get_running_loop()
        error = OSError("shutdown worker failure")

        def shutdown(**_kwargs: object):
            loop.call_soon_threadsafe(started.set)
            release.wait()
            raise error

        self.schedule._Schedule__scheduler = SimpleNamespace(shutdown=shutdown)
        self.schedule.shutdown(wait=0)
        await started.wait()
        task = next(iter(self.schedule._Schedule__pending_listener_tasks))
        task.cancel()
        release.set()
        with self.assertRaises(asyncio.CancelledError):
            await self.schedule.wait()
        await self._drain()
        self.assertEqual(self.handler.reports, [error])
