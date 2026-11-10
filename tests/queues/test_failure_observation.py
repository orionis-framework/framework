"""Verify failure delivery without changing queue recovery decisions."""

import asyncio
from unittest.mock import patch
from orionis.failure.runtime import operation
from orionis.queues.context import JobContext
from orionis.queues.worker import Worker, WorkerOptions
from tests.queues.test_worker import (
    FailJob,
    FailedRepository,
    FakeApp,
    GateJob,
    JobSerializer,
    MemoryDriver,
    RecordJob,
    ScopedService,
    State,
    envelope,
)
from tests.support.failure_runtime import IsolatedFailureTestCase, activate_runtime


class TestQueueFailureObservation(IsolatedFailureTestCase):
    """Exercise the real worker, container, serializer and failure coordinator."""

    async def asyncSetUp(self) -> None:
        """Prepare an isolated runtime and collaborators."""
        self.app = FakeApp()
        self.app.instance(State, State())
        self.app.scoped(None, ScopedService)
        _, self.runtime, self.handler = activate_runtime(self.app)
        self.serializer = JobSerializer()
        self.driver = MemoryDriver(self.serializer)
        self.failed = FailedRepository()
        self.worker = Worker(
            self.app,
            self.driver,
            self.serializer,
            WorkerOptions("database", sleep=0.001),
            self.failed,
        )

    async def testRetryAttemptsRemainIndependentAndTerminalIsAResult(self) -> None:
        """Verify retry attempts remain independent and terminal is a result."""
        await self.driver.push(envelope(self.serializer, FailJob(1), tries=2))
        self.assertEqual(await self.worker.run(max_jobs=2), 2)
        self.assertEqual(len(self.handler.failures), 2)
        self.assertEqual(len(self.handler.reports), 2)
        self.assertEqual(
            [ctx.metadata["attempt"] for _, ctx in self.handler.failures], [1, 2],
        )
        self.assertEqual(self.driver.releases, [0.0])
        self.assertEqual(len(await self.failed.all()), 1)
        self.assertEqual([result for result, _ in self.handler.results], ["failed"])

    async def testBothConcurrentReservationFailuresReachTheHandler(self) -> None:
        """Verify both concurrent reservation failures reach the handler."""
        entered = 0
        barrier = asyncio.Event()
        errors = [RuntimeError("first reservation"), RuntimeError("second reservation")]

        async def reserve(*_args: object):
            nonlocal entered
            index = entered
            entered += 1
            if entered == 2:
                barrier.set()
            await barrier.wait()
            raise errors[index]

        self.worker = Worker(
            self.app,
            self.driver,
            self.serializer,
            WorkerOptions("database", concurrency=2),
            self.failed,
        )
        with (
            patch.object(MemoryDriver, "reserve", side_effect=reserve),
            self.assertRaises(RuntimeError),
        ):
            await self.worker.run(stop_when_empty=True)
        self.assertCountEqual([error for error, _ in self.handler.failures], errors)
        self.assertEqual(len(self.handler.reports), 2)

    async def testRecoveryFailureDoesNotHideTheJobError(self) -> None:
        """Verify recovery failure does not hide the job error."""
        await self.driver.push(envelope(self.serializer, FailJob(1)))
        reserved = await self.driver.reserve(("default",), 90)
        self.driver.broken = True
        await self.worker.execute(reserved)
        self.assertEqual(
            [context.phase for _, context in self.handler.failures],
            ["execution", "recovery"],
        )
        self.assertEqual(len(self.handler.reports), 2)
        self.assertEqual(await self.driver.size("default"), 1)

    async def testExplicitFailureIsDeliveredWithoutRaiseErrors(self) -> None:
        """Verify explicit failure is delivered without raise errors."""
        await self.driver.push(envelope(self.serializer, RecordJob(1)))
        reserved = await self.driver.reserve(("default",), 90)
        context = JobContext(self.driver, reserved, "database", self.worker._fail)
        error = ValueError("declared failure")
        with operation(self.app, flow="queue", isolated=True):
            await context.fail(error)
        self.assertIs(self.handler.failures[0][0], error)
        self.assertEqual(len(self.handler.failures), 1)
        self.assertEqual(await self.driver.size("default"), 0)
        self.assertTrue(context.finished)

    async def testReleaseFailurePreservesCancellationAndReportsTheBackend(self) -> None:
        """Verify release failure preserves cancellation and reports the backend."""
        await self.driver.push(envelope(self.serializer, GateJob(1)))
        reserved = await self.driver.reserve(("default",), 90)
        state = await self.app.make(State)
        task = asyncio.create_task(self.worker.execute(reserved))
        await state.entered.wait()
        self.driver.broken = True
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(len(self.handler.failures), 1)
        self.assertEqual(self.handler.failures[0][1].phase, "release")

    async def testBrokenLegacyLoggerCannotPreventRecovery(self) -> None:
        """Verify broken legacy logger cannot prevent recovery."""
        self.runtime._owners.clear()
        await self.driver.push(envelope(self.serializer, FailJob(1)))
        reserved = await self.driver.reserve(("default",), 90)
        with patch("orionis.queues.worker._LOGGER.error", side_effect=OSError("sink")):
            await self.worker.execute(reserved)
        self.assertEqual(self.driver.releases, [0.0])

    async def testCancellationDuringFailureHookReleasesReservation(self) -> None:
        """Release the lease when cancellation interrupts job-error observation.

        Returns
        -------
        None
            Preserve cancellation, the original incident, and immediate recovery.
        """
        await self.driver.push(envelope(self.serializer, FailJob(1)))
        reserved = await self.driver.reserve(("default",), 90)
        entered = asyncio.Event()
        original_hook = self.handler.handleFailure

        async def observe(exception, context):
            handling = await original_hook(exception, context)
            entered.set()
            await asyncio.Event().wait()
            return handling

        with patch.object(self.handler, "handleFailure", side_effect=observe):
            task = asyncio.create_task(self.worker.execute(reserved))
            await asyncio.wait_for(entered.wait(), 2)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(self.driver.releases, [0.0])
        self.assertEqual(len(self.handler.failures), 1)
        self.assertIsInstance(self.handler.failures[0][0], ValueError)
        self.assertEqual(self.handler.failures[0][1].correlation_id, reserved.id)
        self.assertEqual(self.handler.failures[0][1].metadata["attempt"], 1)
        self.assertEqual(self.handler.results, [])

    async def testRepeatedCancellationCannotAbandonReservationRelease(self) -> None:
        """Drain the owned lease release even after a second cancellation.

        Returns
        -------
        None
            Release once and propagate the caller's cancellation after cleanup.
        """
        await self.driver.push(envelope(self.serializer, GateJob(1)))
        reserved = await self.driver.reserve(("default",), 90)
        state = await self.app.make(State)
        entered, finish = asyncio.Event(), asyncio.Event()
        original_release = MemoryDriver.release

        async def release(driver, reservation, delay=0.0):
            entered.set()
            await finish.wait()
            return await original_release(driver, reservation, delay)

        with patch.object(MemoryDriver, "release", release):
            task = asyncio.create_task(self.worker.execute(reserved))
            await state.entered.wait()
            task.cancel()
            await asyncio.wait_for(entered.wait(), 2)
            task.cancel()
            finish.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(self.driver.releases, [0.0])
        self.assertEqual(self.handler.failures, [])
