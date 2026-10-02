import asyncio
import sys
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from uuid import uuid4
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.context.scope import ScopedContext
from orionis.foundation.config.queue import Redis as RedisConfig
from orionis.queues.context import JobContext
from orionis.foundation.enums.lifespan import Lifespan
from orionis.queues.contracts.manager import IQueueManager
from orionis.queues.drivers.sync import SyncQueueDriver
from orionis.queues.exceptions import (
    QueueConfigurationError, QueueDispatchError, QueueRetryError, UnknownJobError,
)
from orionis.queues.manager import QueueManager
from orionis.queues.provider import QueueProvider
from orionis.queues.serializer import JobSerializer
from orionis.queues.worker import Worker, WorkerOptions
from orionis.support.facades.queue import Queue
from orionis.test import TestCase
from tests.queues._worker_fakes import (
    FailJob, FailedRepository, FakeApp, GateJob, MemoryDriver, RecordJob, ScopedService,
    State, envelope,
)

if TYPE_CHECKING:
    from orionis.queues.entities.envelope import JobEnvelope

_CREDENTIAL = "test:@/credential"


class FastFailureDriver(MemoryDriver):
    """Execute a requeued job before administrative retry finishes."""

    __slots__ = ("_worker",)

    def __init__(self, serializer: JobSerializer, app: FakeApp,
                 failed: FailedRepository) -> None:
        """Prepare a worker that immediately processes each pushed envelope.

        Parameters
        ----------
        serializer : JobSerializer
            Registered job codec.
        app : FakeApp
            Real test DI container.
        failed : FailedRepository
            Failure event repository.
        """
        super().__init__(serializer)
        self._worker = Worker(app, self, serializer, WorkerOptions("database"),
                              failed)

    async def push(self, envelope: JobEnvelope, delay: float = 0.0) -> str:
        """Process a new claim before the caller forgets its earlier failure.

        Parameters
        ----------
        envelope : JobEnvelope
            Job being retried.
        delay : float, optional
            Dispatch availability delay.

        Returns
        -------
        str
            Dispatch identifier.
        """
        dispatch_id = await super().push(envelope, delay)
        reserved = await self.reserve((envelope.queue,), 90)
        await self._worker.execute(reserved)
        return dispatch_id


class TestQueueManager(TestCase):
    """Verify lazy canonical dispatch, provider pinning and administration."""

    def setUp(self) -> None:
        """Prepare a real container with isolated queue dependencies."""
        self.app = FakeApp()
        self.state = State()
        token = ScopedContext.setCurrentScope(None)
        try:
            self.app.instance(State, self.state)
            self.app.scoped(None, ScopedService)
        finally:
            ScopedContext.reset(token)
        self.serializer = JobSerializer()
        self.manager = QueueManager(self.app, self.serializer)
        self.failed = FailedRepository()
        self.manager._failed = self.failed

    async def testDeferredSyncDispatchUsesQueueAndDi(self) -> None:
        """Execute a sync job only when its selected pending operation is awaited."""
        pending = self.manager.dispatch(RecordJob(8)).onQueue("emails")
        self.assertEqual(self.state.events, [])
        dispatch_id = await pending
        self.assertEqual(await pending, dispatch_id)
        self.assertEqual(len(self.state.events), 1)
        self.assertEqual(self.state.events[0][:3], (8, "emails", 1))
        self.assertNotIn(JobContext, self.app.getCurrentScope())
        self.assertIsInstance(await self.manager.connection(), SyncQueueDriver)

    async def testSyncFailurePreservesAndPropagatesOriginalException(self) -> None:
        """Preserve terminal diagnostics and expose the application exception."""
        with self.assertLogs("orionis.queues.worker", level="ERROR"), \
                self.assertRaisesRegex(ValueError, "Application job failure"):
            await self.manager.dispatch(FailJob(1))
        self.assertEqual(len(await self.failed.all()), 1)
        self.assertEqual((await self.failed.all())[0].attempts, 1)

    async def testSyncRejectsDelayAndPersistentWorker(self) -> None:
        """Reject durability-dependent behavior on immediate connections."""
        with self.assertRaises(QueueDispatchError):
            await self.manager.dispatch(RecordJob(1)).delay(1)
        with self.assertRaises(QueueConfigurationError):
            await self.manager.worker("sync")

    async def testSyncCancellationPropagatesOriginalCancellation(self) -> None:
        """Preserve immediate cancellation when persistent release is unavailable."""
        task = asyncio.ensure_future(self.manager.dispatch(GateJob(1)))
        await self.state.entered.wait()
        with self.assertLogs("orionis.queues.worker", level="ERROR"):
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(await self.failed.all(), ())

    async def testConnectionAndQueueSelectionShareDriver(self) -> None:
        """Persist selected queues through one shared connection instance."""
        driver = MemoryDriver(self.serializer)
        self.manager._drivers["database"] = driver
        await self.manager.dispatch(RecordJob(1)).onConnection("database").onQueue(
            "high",
        ).delay(0.1)
        await self.manager.dispatch(RecordJob(2)).onConnection("database")
        self.assertIs(await self.manager.connection("database"), driver)
        self.assertEqual(await driver.size("high"), 1)
        self.assertEqual(await driver.size("default"), 1)
        self.assertIsNone(await driver.reserve(("high",), 90))

    async def testUnknownConnectionFailsBeforePersistence(self) -> None:
        """Reject unknown connection selections with a module-specific error."""
        with self.assertRaises(QueueConfigurationError):
            await self.manager.dispatch(RecordJob(1)).onConnection("missing")

    async def testRedisConnectionUsesStructuredSettingsWithoutConnecting(self) -> None:
        """Pass Redis fields directly to a lazy, manager-owned client."""
        app = FakeApp({
            "default": "redis",
            "connections": {
                "redis": RedisConfig(
                    endpoint="redis.example.test", port=6380, db=2,
                    password=_CREDENTIAL, prefix="queues:structured",
                ),
            },
        })
        manager = QueueManager(app, self.serializer)
        try:
            driver = await manager.connection()
            pool = driver._client.connection_pool
            options = pool.connection_kwargs
            self.assertEqual(options["host"], "redis.example.test")
            self.assertEqual(options["port"], 6380)
            self.assertEqual(options["db"], 2)
            self.assertEqual(options["password"], _CREDENTIAL)
            self.assertEqual(driver._prefix, "queues:structured")
            self.assertEqual(pool._available_connections, [])
            self.assertEqual(pool._in_use_connections, set())
            self.assertTrue(driver._owns_client)
            self.assertIs(await manager.connection(), driver)
        finally:
            await manager.close()

    async def testCustomDefaultsFeedEnvelopeAndWorker(self) -> None:
        """Normalize application defaults into dispatch and worker settings."""
        app = FakeApp({"default": "database", "worker": {
            "concurrency": 3, "tries": 4, "timeout": 10.0, "backoff": (1.0, 2.0),
        }})
        manager = QueueManager(app, self.serializer)
        driver = MemoryDriver(self.serializer)
        manager._drivers["database"] = driver
        await manager.dispatch(RecordJob(1))
        queued = next(iter(driver.entries.values())).envelope
        self.assertEqual((queued.max_tries, queued.timeout, queued.backoff),
                         (4, 10.0, (1.0, 2.0)))
        worker = await manager.worker(queues=("high", "default"))
        self.assertEqual(worker._concurrency, 3)
        self.assertEqual(worker._queues, ("high", "default"))

    async def testManualRetryRestoresAttemptsAndForgetsFailure(self) -> None:
        """Preserve envelope identity while resetting backend attempt state."""
        driver = MemoryDriver(self.serializer)
        self.manager._drivers["database"] = driver
        queued = envelope(self.serializer, RecordJob(1))
        await driver.push(queued)
        reserved = await driver.reserve(("default",), 90)
        failure = await self.failed.record(reserved, "database", ValueError("Failed"))
        await driver.delete(reserved)
        self.assertEqual(await self.manager.retryFailed(failure.id), queued.id)
        self.assertEqual(next(iter(driver.entries.values())).attempts, 0)
        self.assertEqual(await self.failed.all(), ())
        with self.assertRaises(QueueRetryError):
            await self.manager.retryFailed("missing")

    async def testRetryKeepsAConcurrentNewFailureEvent(self) -> None:
        """Forget only the old failure when a fast retry fails before push returns."""
        original = MemoryDriver(self.serializer)
        queued = envelope(self.serializer, FailJob(1), tries=1)
        await original.push(queued)
        reserved = await original.reserve(("default",), 90)
        failure = await self.failed.record(reserved, "database", ValueError("Old"))
        self.manager._drivers["database"] = FastFailureDriver(
            self.serializer, self.app, self.failed,
        )
        with self.assertLogs("orionis.queues.worker", level="ERROR"):
            await self.manager.retryFailed(failure.id)
        remaining = await self.failed.all()
        self.assertEqual(len(remaining), 1)
        self.assertNotEqual(remaining[0].id, failure.id)
        self.assertEqual(remaining[0].job_id, queued.id)
        self.assertEqual(remaining[0].exception_message, "Application job failure")

    async def testCloseReleasesOwnedClients(self) -> None:
        """Close initialized queue clients and preserve application services."""
        driver = MemoryDriver(self.serializer)
        self.manager._drivers["database"] = driver
        await self.manager.close()
        self.assertTrue(driver.closed)
        self.assertTrue(self.failed.closed)
        self.assertEqual(self.manager._drivers, {})

    async def testEagerProviderPinsImmediateFluentFacade(self) -> None:
        """Expose PendingDispatch directly after eager provider startup."""
        previous = Queue._application
        previous_pin = Queue._pinned_instance
        Queue._application = self.app
        provider = QueueProvider(self.app)
        self.assertNotIsInstance(provider, DeferrableProvider)
        try:
            provider.register()
            await provider.boot()
            manager = await self.app.make(IQueueManager)
            self.assertIs(Queue._pinned_instance, manager)
            self.assertEqual(self.app.hooks[Lifespan.SHUTDOWN], {manager.close})
            pending = Queue.dispatch(RecordJob(4)).onQueue("high")
            self.assertEqual(self.state.events, [])
            await pending
            self.assertEqual(self.state.events[0][:2], (4, "high"))
            driver = MemoryDriver(self.serializer)
            manager._drivers["database"] = driver
            for callback in self.app.hooks[Lifespan.SHUTDOWN]:
                await callback()
            self.assertTrue(driver.closed)
        finally:
            Queue._pinned_instance = previous_pin
            Queue._application = previous


class TestQueueJobDiscovery(TestCase):
    """Discover jobs from resolved paths without queue module configuration."""

    def setUp(self) -> None:
        """Prepare importable jobs under an isolated custom application path.

        Returns
        -------
        None
            Create temporary modules and expose their application root.
        """
        self.directory = TemporaryDirectory()
        self.base_path = Path(self.directory.name)
        self.package_name = "queue_jobs_" + uuid4().hex
        self.jobs_path = self.base_path / self.package_name / "custom_jobs"
        nested = self.jobs_path / "nested"
        nested.mkdir(parents=True)
        (nested / "discovered.py").write_text(
            "from orionis.queues.job import BaseJob\n"
            "from tests.queues._worker_fakes import RecordJob\n"
            "\n"
            "class DiscoveredJob(RecordJob):\n"
            '    """Expose a job defined inside the custom jobs path."""\n'
            "    __slots__ = ()\n"
            "\n"
            "class AbstractJob(BaseJob):\n"
            '    """Keep an abstract job outside the serializer registry."""\n'
            "    __slots__ = ()\n",
            encoding="utf-8",
        )
        (self.jobs_path / "__init__.py").write_text(
            "from .nested.discovered import DiscoveredJob\n",
            encoding="utf-8",
        )
        self.original_sys_path = list(sys.path)
        sys.path.insert(0, str(self.base_path))
        self.app = FakeApp(base_path=self.base_path, jobs_path=self.jobs_path)
        self.serializer = JobSerializer()
        self.manager = QueueManager(self.app, self.serializer)

    def tearDown(self) -> None:
        """Restore imports and remove temporary jobs after every scenario.

        Returns
        -------
        None
            Restore the interpreter search path and remove fixture modules.
        """
        sys.path[:] = self.original_sys_path
        for name in tuple(sys.modules):
            if name == self.package_name or name.startswith(self.package_name + "."):
                del sys.modules[name]
        self.directory.cleanup()

    async def testCustomJobsPathRegistersNestedConcreteJobs(self) -> None:
        """Discover nested modules and preserve canonical job identities."""
        await self.manager.boot()
        module = import_module(self.package_name + ".custom_jobs.nested.discovered")
        source = JobSerializer()
        source.register(module.DiscoveredJob)
        identity, payload = source.encode(module.DiscoveredJob(42))
        restored = self.serializer.decode(identity, payload)
        self.assertIsInstance(restored, module.DiscoveredJob)
        self.assertEqual(restored.value, 42)
        identity, payload = source.encode(RecordJob(3))
        with self.assertRaises(UnknownJobError):
            self.serializer.decode(identity, payload)

    async def testMissingDefaultJobsDirectoryDoesNotBlockStartup(self) -> None:
        """Allow an application to start before its first job is generated."""
        app = FakeApp(base_path=self.base_path)
        self.assertEqual(app.path("app_jobs"), self.base_path / "app/jobs")
        manager = QueueManager(app, JobSerializer())
        await manager.boot()

    async def testMissingJobsPathReportsConfigurationError(self) -> None:
        """Reject a missing central path instead of inventing a queue default."""
        self.app._paths.clear()
        with self.assertRaises(QueueConfigurationError):
            await self.manager.boot()

    async def testUnimportableJobModulePreservesTheOriginalCause(self) -> None:
        """Report imports that fail inside the resolved application jobs path."""
        (self.jobs_path / "broken.py").write_text(
            "import orionis_queue_missing_dependency\n", encoding="utf-8",
        )
        with self.assertRaises(QueueConfigurationError) as raised:
            await self.manager.boot()
        self.assertIsInstance(raised.exception.__cause__, ModuleNotFoundError)
