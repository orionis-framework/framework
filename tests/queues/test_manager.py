import asyncio
import sys
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from unittest.mock import patch
from uuid import uuid4
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.context.scope import ScopedContext
from orionis.database.connection import Connection
from orionis.database.connection_manager import ConnectionManager
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.exceptions import QueryException
from orionis.foundation.config.queue import Redis as RedisConfig
from orionis.queues.context import JobContext
from orionis.foundation.enums.lifespan import Lifespan
from orionis.queues.contracts.manager import IQueueManager
from orionis.queues.drivers.sync import SyncQueueDriver
from orionis.queues.exceptions import (
    QueueConfigurationError, QueueDispatchError, QueueRetryError, QueueStorageError,
    UnknownJobError,
)
from orionis.queues.manager import QueueManager
from orionis.queues.provider import QueueProvider
from orionis.queues.schema import build_failed_jobs_table, build_jobs_table
from orionis.queues.serializer import JobSerializer
from orionis.queues.worker import Worker, WorkerOptions
from orionis.support.facades.queue import Queue
from orionis.test import TestCase
from tests.queues.drivers.test_database import make_envelope
from tests.queues.test_worker import (
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
        """
        Prepare a real container with isolated queue dependencies.

        Returns
        -------
        None
            Prepare a real container and isolated queue service dependencies.
        """
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
        """
        Execute a sync job only when its selected pending operation is awaited.

        Returns
        -------
        None
            Assert that synchronous dispatch remains deferred until awaited.
        """
        pending = self.manager.dispatch(RecordJob(8)).onQueue("emails")
        self.assertEqual(self.state.events, [])
        dispatch_id = await pending
        self.assertEqual(await pending, dispatch_id)
        self.assertEqual(len(self.state.events), 1)
        self.assertEqual(self.state.events[0][:3], (8, "emails", 1))
        self.assertNotIn(JobContext, self.app.getCurrentScope() or {})
        self.assertIsInstance(await self.manager.connection(), SyncQueueDriver)

    async def testSyncFailurePreservesAndPropagatesOriginalException(self) -> None:
        """
        Preserve terminal diagnostics and expose the application exception.

        Returns
        -------
        None
            Assert preservation of the original synchronous job exception.
        """
        with self.assertLogs("orionis.queues.worker", level="ERROR"), \
                self.assertRaisesRegex(ValueError, "Application job failure"):
            await self.manager.dispatch(FailJob(1))
        self.assertEqual(len(await self.failed.all()), 1)
        self.assertEqual((await self.failed.all())[0].attempts, 1)

    async def testSyncRejectsDelayAndPersistentWorker(self) -> None:
        """
        Reject durability-dependent behavior on immediate connections.

        Returns
        -------
        None
            Assert rejection of delayed dispatch and persistent sync workers.
        """
        with self.assertRaises(QueueDispatchError):
            await self.manager.dispatch(RecordJob(1)).delay(1)
        with self.assertRaises(QueueConfigurationError):
            await self.manager.worker("sync")

    async def testSyncCancellationPropagatesOriginalCancellation(self) -> None:
        """
        Preserve immediate cancellation when persistent release is unavailable.

        Returns
        -------
        None
            Assert preservation of the original synchronous cancellation.
        """
        task = asyncio.ensure_future(self.manager.dispatch(GateJob(1)))
        await self.state.entered.wait()
        with self.assertLogs("orionis.queues.worker", level="ERROR"):
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(await self.failed.all(), ())

    async def testConnectionAndQueueSelectionShareDriver(self) -> None:
        """
        Persist selected queues through one shared connection instance.

        Returns
        -------
        None
            Assert shared driver ownership across selected logical queues.
        """
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
        """
        Reject unknown connection selections with a module-specific error.

        Returns
        -------
        None
            Assert rejection of unknown connections before persistence.
        """
        with self.assertRaises(QueueConfigurationError):
            await self.manager.dispatch(RecordJob(1)).onConnection("missing")

    async def testRedisConnectionUsesStructuredSettingsWithoutConnecting(self) -> None:
        """
        Pass Redis fields directly to a lazy, manager-owned client.

        Returns
        -------
        None
            Assert lazy Redis client creation with structured connection fields.
        """
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
        """
        Normalize application defaults into dispatch and worker settings.

        Returns
        -------
        None
            Assert propagation of custom defaults into envelopes and workers.
        """
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
        """
        Preserve envelope identity while resetting backend attempt state.

        Returns
        -------
        None
            Assert reset attempts, preserved identity, and failure deletion.
        """
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
        """
        Forget only the old failure when a fast retry fails before push returns.

        Returns
        -------
        None
            Assert that retry cleanup preserves a newly recorded failure.
        """
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
        """
        Close initialized queue clients and preserve application services.

        Returns
        -------
        None
            Assert cleanup of owned clients without closing application services.
        """
        driver = MemoryDriver(self.serializer)
        self.manager._drivers["database"] = driver
        await self.manager.close()
        self.assertTrue(driver.closed)
        self.assertTrue(self.failed.closed)
        self.assertEqual(self.manager._drivers, {})

    async def testEagerProviderPinsImmediateFluentFacade(self) -> None:
        """
        Expose PendingDispatch directly after eager provider startup.

        Returns
        -------
        None
            Assert immediate fluent dispatch through the eagerly pinned facade.
        """
        previous = Queue._application
        previous_pin = Queue._pinned_instance
        Queue._application = self.app # NOSONAR
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
            Queue._pinned_instance = previous_pin # NOSONAR
            Queue._application = previous # NOSONAR

class TestQueueMigrations(TestCase):
    """Prepare real isolated databases without constructing queue clients."""

    async def asyncSetUp(self) -> None:
        """
        Configure separate prefixed databases for jobs, reports, and failures.

        Returns
        -------
        None
            Prepare isolated prefixed databases for queue migration tests.
        """
        self.directory = TemporaryDirectory()
        directory = Path(self.directory.name)
        self.databases = ConnectionManager(FakeApp({
            "default": "primary",
            "connections": {
                name: {
                    "driver": "sqlite",
                    "database": str(directory / f"{name}.sqlite"),
                    "prefix": prefix,
                }
                for name, prefix in (
                    ("primary", "q_"), ("reports", "r_"), ("failures", "f_"),
                )
            },
        }))
        self.app = FakeApp({
            "default": "sync",
            "connections": {
                "sync": {"driver": "sync"},
                "database": {
                    "driver": "database", "connection": None,
                    "table": "pending_jobs",
                },
                "reports": {
                    "driver": "database", "connection": "reports",
                    "table": "report_jobs",
                },
                "redis": {"driver": "redis", "endpoint": "redis.invalid"},
            },
            "failed": {"connection": "failures", "table": "queue_failures"},
        })
        token = ScopedContext.setCurrentScope(None)
        try:
            self.app.instance(IConnectionManager, self.databases)
        finally:
            ScopedContext.reset(token)
        self.manager = QueueManager(self.app, JobSerializer())

    async def asyncTearDown(self) -> None:
        """
        Release shared database handles before removing the temporary files.

        Returns
        -------
        None
            Close shared handles and remove the temporary database files.
        """
        await self.manager.close()
        await self.databases.disconnect()
        self.directory.cleanup()

    async def testMigrateCreatesAllConfiguredTablesAndIndexes(self) -> None:
        """
        Create complete prefixed schemas even when the default queue is sync.

        Returns
        -------
        None
            Assert creation of all configured tables and indexes.
        """
        await self.manager.migrate()
        expected = (
            ("primary", "q_pending_jobs", build_jobs_table("pending_jobs"),
             ("queue", "available_at", "reserved_until")),
            ("reports", "r_report_jobs", build_jobs_table("report_jobs"),
             ("queue", "available_at", "reserved_until")),
            ("failures", "f_queue_failures",
             build_failed_jobs_table("queue_failures"), ("failed_at",)),
        )
        for name, table, definition, index_columns in expected:
            with self.subTest(connection=name, table=table):
                connection = self.databases.connection(name)
                tables = await connection.select(
                    "SELECT name FROM sqlite_master WHERE type = 'table'",
                )
                self.assertEqual({row["name"] for row in tables}, {table})
                columns = await connection.select(
                    "SELECT name FROM pragma_table_info(:table)", {"table": table},
                )
                self.assertEqual(
                    {row["name"] for row in columns}, set(definition.columns),
                )
                indexes = await connection.select(
                    "SELECT name FROM pragma_index_list(:table) WHERE origin = 'c'",
                    {"table": table},
                )
                self.assertEqual(len(indexes), 1)
                indexed = await connection.select(
                    "SELECT name FROM pragma_index_info(:index_name)",
                    {"index_name": indexes[0]["name"]},
                )
                self.assertEqual(
                    tuple(row["name"] for row in indexed), index_columns,
                )
        self.assertEqual(self.manager._drivers, {})
        self.assertIsNone(self.manager._failed)

    async def testRepeatedMigrationsPreserveJobsAndFailures(self) -> None:
        """
        Keep pending reservations and failure records across repeated calls.

        Returns
        -------
        None
            Assert that repeated migrations preserve queued and failed jobs.
        """
        await self.manager.migrate()
        driver = await self.manager.connection("database")
        queued = make_envelope()
        await driver.push(queued)
        reserved = await driver.reserve(("default",), 90)
        repository = await self.manager.failed()
        failure = await repository.record(
            reserved, "database", ValueError("Preserved failure"),
        )
        await self.manager.migrate()
        await self.manager.migrate()
        self.assertEqual(await driver.size("default"), 1)
        self.assertTrue(await driver.delete(reserved))
        self.assertEqual(await repository.all(), (failure,))

    async def testMigratePreparesFailuresWithoutDatabaseQueueConnections(self) -> None:
        """
        Prepare failure storage without opening sync or Redis queue clients.

        Returns
        -------
        None
            Assert failure storage preparation without opening queue clients.
        """
        self.app.settings["connections"] = {
            "sync": {"driver": "sync"},
            "redis": {"driver": "redis", "endpoint": "redis.invalid"},
        }
        self.manager = QueueManager(self.app, JobSerializer())
        await self.manager.migrate()
        self.assertEqual(
            set(self.databases._cached_connections), {"failures"},
        )
        tables = await self.databases.connection("failures").select(
            "SELECT name FROM sqlite_master WHERE type = 'table'",
        )
        self.assertEqual(
            {row["name"] for row in tables}, {"f_queue_failures"},
        )
        self.assertEqual(self.manager._drivers, {})
        self.assertIsNone(self.manager._failed)

    async def testMigratePropagatesStorageErrors(self) -> None:
        """
        Preserve the database error when queue DDL cannot execute.

        Returns
        -------
        None
            Assert propagation of database errors during migration.
        """
        error = QueryException("Queue schema creation failed.")
        with patch.object(Connection, "createTable", side_effect=error), \
                self.assertRaises(QueryException) as raised:
            await self.manager.migrate()
        self.assertIs(raised.exception, error)

    async def testMigrateRejectsUnenforcedUniqueConstraints(self) -> None:
        """
        Reject database storage that cannot enforce unique job identifiers.

        Returns
        -------
        None
            Assert rejection of storage without enforced unique job identifiers.
        """
        with (
            patch.object(Connection, "supportsUniqueConstraints", return_value=False),
            self.assertRaisesRegex(QueueStorageError, "unique constraints"),
        ):
            await self.manager.migrate()

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
            "from tests.queues.test_worker import RecordJob\n"
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
        """
        Discover nested modules and preserve canonical job identities.

        Returns
        -------
        None
            Assert nested job discovery and canonical registered identities.
        """
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
        """
        Allow an application to start before its first job is generated.

        Returns
        -------
        None
            Assert startup without an application jobs directory.
        """
        app = FakeApp(base_path=self.base_path)
        self.assertEqual(app.path("app_jobs"), self.base_path / "app/jobs")
        manager = QueueManager(app, JobSerializer())
        await manager.boot()

    async def testMissingJobsPathReportsConfigurationError(self) -> None:
        """
        Reject a missing central path instead of inventing a queue default.

        Returns
        -------
        None
            Assert a configuration error for a missing central jobs path.
        """
        self.app._paths.clear()
        with self.assertRaises(QueueConfigurationError):
            await self.manager.boot()

    async def testUnimportableJobModulePreservesTheOriginalCause(self) -> None:
        """
        Report imports that fail inside the resolved application jobs path.

        Returns
        -------
        None
            Assert preservation of the original job-module import failure.
        """
        (self.jobs_path / "broken.py").write_text(
            "import orionis_queue_missing_dependency\n", encoding="utf-8",
        )
        with self.assertRaises(QueueConfigurationError) as raised:
            await self.manager.boot()
        self.assertIsInstance(raised.exception.__cause__, ModuleNotFoundError)
