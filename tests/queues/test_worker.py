import asyncio
from dataclasses import replace
from orionis.container.context.scope import ScopedContext
from orionis.queues.context import JobContext
from orionis.queues.entities.reserved_job import ReservedJob
from orionis.queues.exceptions import QueueConfigurationError, QueueLeaseError
from orionis.queues.functions import current_time
from orionis.queues.serializer import JobSerializer
from orionis.queues.worker import Worker, WorkerOptions
from orionis.test import TestCase
from tests.queues._worker_fakes import (
    FailJob, FailedRepository, FakeApp, GateJob, MemoryDriver, RecordJob,
    ReleaseJob, ScopedService, SlowApp, State, envelope,
)


class TestWorker(TestCase):
    """Verify scoped execution and resilient reservation completion."""

    def setUp(self) -> None:
        """Prepare real DI, wire serialization and isolated backend fakes."""
        self.app = FakeApp()
        self.state = State()
        token = ScopedContext.setCurrentScope(None)
        try:
            self.app.instance(State, self.state)
            self.app.scoped(None, ScopedService)
        finally:
            ScopedContext.reset(token)
        self.serializer = JobSerializer()
        self.driver = MemoryDriver(self.serializer)
        self.failed = FailedRepository()
        self.worker = Worker(self.app, self.driver, self.serializer,
                             WorkerOptions("database", sleep=0.001), self.failed)

    async def testSuccessUsesDistinctDependencyScopes(self) -> None:
        """Inject operational context and isolate each scoped service."""
        for value in range(3):
            await self.driver.push(envelope(self.serializer, RecordJob(value)))
        self.assertEqual(await self.worker.run(stop_when_empty=True), 3)
        self.assertEqual(len(self.state.events), 3)
        identities = {id(event[3]) for event in self.state.events}
        self.assertEqual(len(identities), 3)
        self.assertNotIn(JobContext, self.app.getCurrentScope())
        self.assertEqual(await self.driver.size("default"), 0)

    async def testRetryExhaustionPersistsOriginalFailure(self) -> None:
        """Apply backoff once per failed reservation and preserve the last error."""
        await self.driver.push(envelope(self.serializer, FailJob(1), options={
            "backoff": (0.0, 0.001, 0.1),
        }))
        with self.assertLogs("orionis.queues.worker", level="ERROR"):
            self.assertEqual(await self.worker.run(max_jobs=3), 3)
        self.assertEqual([event[2] for event in self.state.events], [1, 2, 3])
        self.assertEqual(self.driver.releases, [0.0, 0.001])
        failure = (await self.failed.all())[0]
        self.assertEqual(failure.attempts, 3)
        self.assertEqual(failure.exception_type, "ValueError")
        self.assertIn("Application job failure", failure.traceback)
        self.assertNotIn(JobContext, self.app.getCurrentScope())

    async def testExplicitReleaseSkipsAutomaticAcknowledgement(self) -> None:
        """Reserve an explicitly released job again with the next attempt."""
        await self.driver.push(envelope(self.serializer, ReleaseJob(2)))
        self.assertEqual(await self.worker.run(stop_when_empty=True), 2)
        self.assertEqual([event[2] for event in self.state.events], [1, 2])
        self.assertEqual(self.driver.releases, [0.0])

    async def testExceptionDoesNotStopOtherJobs(self) -> None:
        """Continue processing healthy work after an individual failure."""
        await self.driver.push(envelope(self.serializer, FailJob(1), tries=1))
        await self.driver.push(envelope(self.serializer, RecordJob(2)))
        with self.assertLogs("orionis.queues.worker", level="ERROR"):
            self.assertEqual(await self.worker.run(stop_when_empty=True), 2)
        self.assertEqual(len(await self.failed.all()), 1)
        self.assertEqual([event[0] for event in self.state.events], [1, 2])

    async def testTransitionFailureRetainsLeaseAndContinues(self) -> None:
        """Keep an unacknowledged retry when storage completion fails."""
        self.driver.broken = True
        await self.driver.push(envelope(self.serializer, FailJob(1)))
        await self.driver.push(envelope(self.serializer, RecordJob(2)))
        with self.assertLogs("orionis.queues.worker", level="ERROR") as logs:
            self.assertEqual(await self.worker.run(stop_when_empty=True), 2)
        self.assertTrue(any("Cannot complete" in log for log in logs.output))
        self.assertEqual(await self.driver.size("default"), 1)
        self.assertGreater(next(iter(self.driver.entries.values())).reserved_until,
                           current_time())

    async def testRepositoryFailureRetainsLeaseAndContinues(self) -> None:
        """Retain a terminal job until storage can preserve its failure."""
        self.failed.broken = True
        await self.driver.push(envelope(self.serializer, FailJob(1), tries=1))
        await self.driver.push(envelope(self.serializer, RecordJob(2)))
        with self.assertLogs("orionis.queues.worker", level="ERROR"):
            self.assertEqual(await self.worker.run(stop_when_empty=True), 2)
        self.assertEqual(await self.driver.size("default"), 1)

    async def testTimeoutClosesScopeAndPersistsFailure(self) -> None:
        """Cancel a suspended handler cooperatively and preserve TimeoutError."""
        await self.driver.push(envelope(self.serializer, GateJob(1), tries=1,
                                        timeout=0.01))
        with self.assertLogs("orionis.queues.worker", level="ERROR"):
            self.assertEqual(await self.worker.run(stop_when_empty=True), 1)
        self.assertEqual((await self.failed.all())[0].exception_type,
                         "TimeoutError")
        self.assertNotIn(JobContext, self.app.getCurrentScope())

    async def testNearExpiredLeaseBoundsExecutionTimeout(self) -> None:
        """Shorten a job timeout to the remaining reservation lifetime."""
        await self.driver.push(envelope(self.serializer, GateJob(1), tries=1))
        reserved = await self.driver.reserve(("default",), 0.04)
        started = current_time()
        with self.assertLogs("orionis.queues.worker", level="ERROR") as logs:
            await self.worker.execute(reserved)
        self.assertLess(current_time() - started, 0.3)
        self.assertIn("TimeoutError", "\n".join(logs.output))
        self.assertEqual(self.state.events, [])
        self.assertFalse(self.state.gate.is_set())

    async def testTimeoutIncludesAsyncDependencyResolution(self) -> None:
        """Bound service injection and close its scope when DI suspends too long."""
        app = SlowApp()
        token = ScopedContext.setCurrentScope(None)
        try:
            app.instance(State, self.state)
            app.scoped(None, ScopedService)
        finally:
            ScopedContext.reset(token)
        worker = Worker(app, self.driver, self.serializer,
                        WorkerOptions("database"), self.failed)
        await self.driver.push(envelope(self.serializer, RecordJob(1), tries=1,
                                        timeout=0.01))
        with self.assertLogs("orionis.queues.worker", level="ERROR"):
            await worker.run(stop_when_empty=True)
        self.assertEqual(self.state.events, [])
        self.assertEqual((await self.failed.all())[0].exception_type,
                         "TimeoutError")
        self.assertNotIn(JobContext, app.getCurrentScope())

    async def testExpiredLeaseNeverExecutesSideEffects(self) -> None:
        """Skip a stale claim before invoking the job handler."""
        await self.driver.push(envelope(self.serializer, RecordJob(1)))
        reserved = await self.driver.reserve(("default",), 1)
        expired = ReservedJob(**{
            field: getattr(reserved, field)
            for field in reserved.__struct_fields__
        } | {"reserved_until": current_time() - 1})
        with self.assertLogs("orionis.queues.worker", level="WARNING"):
            await self.worker.execute(expired)
        self.assertEqual(self.state.events, [])
        self.assertEqual(await self.failed.all(), ())

    async def testCrashExhaustionRejectsExtraExecution(self) -> None:
        """Fail a recovered claim whose attempt budget was already consumed."""
        await self.driver.push(envelope(self.serializer, RecordJob(1), tries=1))
        entry = next(iter(self.driver.entries.values()))
        entry.attempts = 1
        reserved = await self.driver.reserve(("default",), 1)
        with self.assertLogs("orionis.queues.worker", level="ERROR"):
            await self.worker.execute(reserved)
        self.assertEqual(self.state.events, [])
        self.assertEqual((await self.failed.all())[0].exception_type,
                         "QueueRetryError")

    async def testRetryDeadlineFailsBeforeInvocation(self) -> None:
        """Reject a job whose absolute retry deadline already expired."""
        await self.driver.push(envelope(self.serializer, RecordJob(1), options={
            "retry_until": current_time() - 1,
        }))
        with self.assertLogs("orionis.queues.worker", level="ERROR"):
            await self.worker.run(stop_when_empty=True)
        self.assertEqual(self.state.events, [])
        self.assertEqual(len(await self.failed.all()), 1)

    async def testConcurrencyLimitAndAttemptBudget(self) -> None:
        """Process many jobs without exceeding concurrency or max_jobs."""
        for value in range(20):
            await self.driver.push(envelope(self.serializer, RecordJob(value)))
        worker = Worker(self.app, self.driver, self.serializer,
                        WorkerOptions("database", concurrency=3), self.failed)
        self.assertEqual(await worker.run(max_jobs=5), 5)
        self.assertEqual(len(self.state.events), 5)
        self.assertGreater(self.state.maximum, 1)
        self.assertLessEqual(self.state.maximum, 3)
        self.assertEqual(await self.driver.size("default"), 15)

    async def testStopDrainsCurrentExecution(self) -> None:
        """Stop new reservations while allowing an active handler to finish."""
        await self.driver.push(envelope(self.serializer, GateJob(1)))
        await self.driver.push(envelope(self.serializer, RecordJob(2)))
        task = asyncio.create_task(self.worker.run())
        await self.state.entered.wait()
        self.worker.stop()
        self.assertFalse(task.done())
        self.state.gate.set()
        self.assertEqual(await task, 1)
        self.assertEqual(await self.driver.size("default"), 1)

    async def testCancellationDrainsCurrentExecution(self) -> None:
        """Drain handler tasks before propagating external cancellation."""
        await self.driver.push(envelope(self.serializer, GateJob(1)))
        task = asyncio.create_task(self.worker.run())
        await self.state.entered.wait()
        task.cancel()
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        self.state.gate.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(await self.driver.size("default"), 0)

    async def testIdleStopInterruptsPollingSleep(self) -> None:
        """Wake an idle worker immediately when graceful shutdown begins."""
        task = asyncio.create_task(self.worker.run())
        await asyncio.sleep(0)
        self.worker.stop()
        self.assertEqual(await asyncio.wait_for(task, 0.1), 0)

    async def testCancellationPreservesOriginalWhenReleaseFails(self) -> None:
        """Expose cancellation even when its backend release operation fails."""
        await self.driver.push(envelope(self.serializer, GateJob(1)))
        reserved = await self.driver.reserve(("default",), 90)
        task = asyncio.create_task(self.worker.execute(reserved))
        await self.state.entered.wait()
        self.driver.broken = True
        with self.assertLogs("orionis.queues.worker", level="ERROR"):
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(await self.driver.size("default"), 1)

    async def testExplicitContextFailurePersistsImmediately(self) -> None:
        """Preserve an explicitly reported failure without automatic retry."""
        await self.driver.push(envelope(self.serializer, RecordJob(1)))
        reserved = await self.driver.reserve(("default",), 90)
        context = JobContext(self.driver, reserved, "database", self.worker._fail)
        exception = ValueError("Explicit failure")
        await context.fail(exception)
        self.assertTrue(context.finished)
        self.assertIs(context.failure, exception)
        self.assertEqual(await self.driver.size("default"), 0)
        self.assertEqual(len(await self.failed.all()), 1)

    async def testCorruptEnvelopePersistsFailureWithoutInvocation(self) -> None:
        """Fail malformed persisted data without executing job side effects."""
        queued = envelope(self.serializer, RecordJob(1))
        await self.driver.push(queued)
        reserved = await self.driver.reserve(("default",), 90)
        corrupt = ReservedJob(**{
            field: getattr(reserved, field)
            for field in reserved.__struct_fields__
        } | {"payload": b"malformed"})
        with self.assertLogs("orionis.queues.worker", level="ERROR"):
            await self.worker.execute(corrupt)
        self.assertEqual(self.state.events, [])
        self.assertEqual(len(await self.failed.all()), 1)

    async def testContextPreventsRepeatedTransitions(self) -> None:
        """Expose reservation metadata and reject duplicate lifecycle actions."""
        payload = envelope(self.serializer, RecordJob(1))
        await self.driver.push(payload)
        reserved = await self.driver.reserve(("default",), 1)
        context = JobContext(self.driver, reserved, "database", self.worker._fail)
        self.assertEqual((context.id, context.queue, context.connection),
                         (payload.id, "default", "database"))
        await context.delete()
        with self.assertRaises(QueueLeaseError):
            await context.release()

    def testInvalidDirectWorkerSettingsFailEarly(self) -> None:
        """Reject invalid counts, finite durations and direct queue selections."""
        base = WorkerOptions("database")
        for changes in ({"concurrency": True}, {"retry_after": float("nan")},
                        {"sleep": -1}, {"queues": ()}, {"queues": ("bad key",)}):
            with self.subTest(changes=changes), self.assertRaises(
                    QueueConfigurationError):
                replace(base, **changes)
