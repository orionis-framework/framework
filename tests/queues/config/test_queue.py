from dataclasses import FrozenInstanceError, asdict, fields, is_dataclass
import msgspec

from config.queue import BootstrapQueue
from orionis.foundation.config.queue import (
    Connections, Database, Drivers, Failed, Queue, Redis, Sync, Worker,
)
from tests.foundation.config.test_environment import ConfigurationTestCase

_CREDENTIAL = "queue-test-credential"


class TestQueueConfiguration(ConfigurationTestCase):
    """Exercise defaults, ownership, and invalid configuration boundaries."""

    __slots__ = ()

    def testQueueTuningReadsEnvironmentInBothLayers(self) -> None:
        """Read worker limits and backend tuning from dedicated environment keys."""
        self.environment.values.update(
            QUEUE_SYNC_QUEUE="inline",
            QUEUE_SYNC_RETRY_AFTER=30.0,
            QUEUE_DB_QUEUE="reports",
            QUEUE_DB_RETRY_AFTER=45.0,
            QUEUE_REDIS_PREFIX="application:queues",
            QUEUE_REDIS_QUEUE="emails",
            QUEUE_REDIS_RETRY_AFTER=60.0,
            QUEUE_WORKER_CONCURRENCY=8,
            QUEUE_WORKER_SLEEP=0.25,
            QUEUE_WORKER_TIMEOUT=20.0,
            QUEUE_WORKER_TRIES=5,
            QUEUE_WORKER_BACKOFF=[0.5, 2.0],
        )
        for entity_type in (Queue, BootstrapQueue):
            config = entity_type()
            self.assertEqual(config.connections.sync.queue, "inline")
            self.assertEqual(config.connections.sync.retry_after, 30.0)
            self.assertEqual(config.connections.database.queue, "reports")
            self.assertEqual(config.connections.database.retry_after, 45.0)
            self.assertEqual(config.connections.redis.prefix, "application:queues")
            self.assertEqual(config.connections.redis.queue, "emails")
            self.assertEqual(config.connections.redis.retry_after, 60.0)
            self.assertEqual(config.worker.concurrency, 8)
            self.assertEqual(config.worker.sleep, 0.25)
            self.assertEqual(config.worker.timeout, 20.0)
            self.assertEqual(config.worker.tries, 5)
            self.assertEqual(config.worker.backoff, (0.5, 2.0))
        self.assertEqual(Sync().queue, "inline")
        self.assertEqual(Database().retry_after, 45.0)
        self.assertEqual(Redis().prefix, "application:queues")
        self.assertEqual(Worker().concurrency, 8)

    def testQueueTuningEnvironmentRemainsStrict(self) -> None:
        """Reject invalid environment values without coercing configuration."""
        for name, value in (
            ("QUEUE_SYNC_QUEUE", False), ("QUEUE_SYNC_RETRY_AFTER", True),
            ("QUEUE_DB_QUEUE", "../escape"), ("QUEUE_DB_RETRY_AFTER", 0.0),
            ("QUEUE_REDIS_PREFIX", " "), ("QUEUE_REDIS_QUEUE", None),
            ("QUEUE_REDIS_RETRY_AFTER", float("inf")),
            ("QUEUE_WORKER_CONCURRENCY", True), ("QUEUE_WORKER_SLEEP", 0.0),
            ("QUEUE_WORKER_TIMEOUT", None), ("QUEUE_WORKER_TRIES", False),
            ("QUEUE_WORKER_BACKOFF", (True,)),
        ):
            self.environment.values.clear()
            self.environment.values[name] = value
            for entity_type in (Queue, BootstrapQueue):
                with self.assertRaises((TypeError, ValueError)):
                    entity_type()

    def testExplicitSettingsOverrideEnvironmentAndOwnRetryLists(self) -> None:
        """Prefer developer overrides and isolate environment-provided retries."""
        delays = [0.0, 1.0]
        self.environment.values.update(
            QUEUE_SYNC_QUEUE="environment",
            QUEUE_REDIS_PREFIX="environment:queues",
            QUEUE_WORKER_CONCURRENCY=8,
            QUEUE_WORKER_BACKOFF=delays,
        )
        self.assertEqual(Sync(queue="explicit").queue, "explicit")
        self.assertEqual(Redis(prefix="explicit:queues").prefix, "explicit:queues")
        self.assertEqual(Worker(concurrency=2).concurrency, 2)
        self.assertEqual(Worker(backoff=(3.0,)).backoff, (3.0,))
        first = Worker()
        second = Worker()
        delays.append(2.0)
        self.assertEqual(first.backoff, (0.0, 1.0))
        self.assertEqual(second.backoff, (0.0, 1.0))

    def testJobDiscoveryIsNotQueueConfiguration(self) -> None:
        """Keep the application jobs path out of queue connection settings."""
        for entity_type in (Queue, BootstrapQueue):
            self.assertNotIn("job_modules", {item.name for item in fields(entity_type)})
            self.assertNotIn("job_modules", entity_type().toDict())
        with self.assertRaises(TypeError):
            Queue(job_modules=("app.jobs",))

    def testRedisUsesStructuredSettingsInBothLayers(self) -> None:
        """Read Redis host, port, database, and credentials without a URL field."""
        self.assertEqual(
            {item.name for item in fields(Redis)},
            {
                "driver", "endpoint", "port", "db", "password", "prefix",
                "queue", "retry_after",
            },
        )
        self.environment.values.update(
            REDIS_HOST="redis.example.test", REDIS_PORT=6380, REDIS_DB=2,
            REDIS_PASSWORD=_CREDENTIAL,
        )
        for config in (
            Redis(), Queue().connections.redis, BootstrapQueue().connections.redis,
        ):
            self.assertEqual(config.endpoint, "redis.example.test")
            self.assertEqual(config.port, 6380)
            self.assertEqual(config.db, 2)
            self.assertEqual(config.password, _CREDENTIAL)
            self.assertNotIn("url", config.toDict())

    def testNestedSettingsAreDataclasses(self) -> None:
        """Keep backend, failure, and worker settings in validated dataclasses."""
        config = Queue()
        self.assertTrue(is_dataclass(config.connections))
        self.assertTrue(is_dataclass(config.failed))
        self.assertTrue(is_dataclass(config.worker))
        for backend in fields(config.connections):
            self.assertTrue(is_dataclass(getattr(config.connections, backend.name)))

    def testDefaultsAndBootstrapMatch(self) -> None:
        """Produce independent canonical defaults in core and application config."""
        config = Queue()
        self.assertEqual(config.toDict(), BootstrapQueue().toDict())
        self.assertEqual(config.default, "sync")
        self.assertEqual(
            set(config.connections.toDict()), {"sync", "database", "redis"},
        )
        self.assertLess(
            config.worker.timeout, config.connections.database.retry_after,
        )
        with self.assertRaises(FrozenInstanceError):
            config.default = "redis"

    def testEnvironmentValuesReachConnections(self) -> None:
        """Read backend selection and credentials through the real Env contract."""
        self.environment.values.update(
            QUEUE_CONNECTION="redis",
            REDIS_HOST="redis.example.test", REDIS_PORT=6380, REDIS_DB=2,
            REDIS_PASSWORD=_CREDENTIAL,
            QUEUE_DB_CONNECTION="archive",
            QUEUE_FAILED_DB_CONNECTION="audit",
            QUEUE_TABLE="pending_jobs",
            QUEUE_FAILED_TABLE="queue_failures",
        )
        config = BootstrapQueue()
        self.assertEqual(config.default, "redis")
        self.assertEqual(config.connections.redis.endpoint, "redis.example.test")
        self.assertEqual(config.connections.redis.port, 6380)
        self.assertEqual(config.connections.redis.db, 2)
        self.assertEqual(config.connections.redis.password, _CREDENTIAL)
        self.assertEqual(config.connections.database.connection, "archive")
        self.assertEqual(config.connections.database.table, "pending_jobs")
        self.assertEqual(
            config.failed.toDict(), {"connection": "audit", "table": "queue_failures"},
        )

    def testCustomConnectionsAndPartialDefaults(self) -> None:
        """Normalize named backends while preserving explicit worker values."""
        config = Queue(
            default="reports",
            connections={"reports": {"driver": "database", "queue": "high"}},
            worker={"concurrency": 8, "timeout": 20.0, "backoff": [0.1, 0.5]},
            failed={"table": "report_failures"},
        )
        self.assertIsInstance(config.connections["reports"], Database)
        self.assertEqual(config.connections["reports"].table, "jobs")
        self.assertEqual(config.connections["reports"].retry_after, 90.0)
        self.assertEqual(config.worker.backoff, (0.1, 0.5))
        self.assertEqual(config.worker.tries, 3)
        self.assertIsNone(config.failed.connection)

    def testSettingsDoNotShareCallerState(self) -> None:
        """Copy caller mappings and keep separate configuration instances."""
        connections = {"local": {"driver": "sync", "queue": "emails"}}
        worker = {"backoff": [1.0]}
        failed = {"table": "failures"}
        first = Queue(
            default="local", connections=connections, worker=worker, failed=failed,
        )
        second = Queue(
            default="local", connections=connections, worker=worker, failed=failed,
        )
        connections["local"]["queue"] = "changed"
        worker["backoff"].append(2.0)
        failed["table"] = "changed"
        first.connections["local"] = Sync(queue="private")
        self.assertEqual(second.connections["local"].queue, "emails")
        self.assertEqual(second.worker.backoff, (1.0,))
        self.assertEqual(second.failed.table, "failures")
        with self.assertRaises(FrozenInstanceError):
            second.connections["local"].queue = "changed"

    def testRejectsInvalidRoutingAndUnsupportedSettings(self) -> None:
        """Reject unknown backends, unsafe names, and dead configuration keys."""
        cases = (
            {"default": "missing"},
            {"connections": []},
            {"connections": {"sync": {"driver": "rabbitmq"}}},
            {"connections": {"sync": {"queue": "../escape"}}},
            {"connections": {"sync": {"strategy": "fifo"}}},
            {"connections": {"sync": {"retry_after": True}}},
            {"connections": {"sync": None}},
            {"default": "database", "connections": {
                "database": {"table": "jobs;DROP"},
            }},
            {"default": "redis", "connections": {"redis": {"url": "http://example.test"}}},
            {"failed": {"table": "failed.jobs"}},
            {"failed": {"driver": "memory"}},
            {"failed": None},
            {"worker": {"unknown": 1}},
            {"worker": None},
        )
        for settings in cases:
            with (
                self.subTest(settings=settings),
                self.assertRaises((TypeError, ValueError)),
            ):
                Queue(**settings)

    def testRejectsUnsafeLeaseAndRetryValues(self) -> None:
        """Fail configuration before a worker can outlive its reservation."""
        cases = (
            {"timeout": 90.0},
            {"timeout": 0.0},
            {"timeout": float("inf")},
            {"timeout": float("nan")},
            {"timeout": None},
            {"tries": 0},
            {"tries": True},
            {"concurrency": -1},
            {"concurrency": False},
            {"sleep": 0.0},
            {"sleep": -0.1},
            {"backoff": (-1.0,)},
            {"backoff": (float("inf"),)},
            {"backoff": (True,)},
            {"backoff": ()},
        )
        for worker in cases:
            with (
                self.subTest(worker=worker),
                self.assertRaises((TypeError, ValueError)),
            ):
                Queue(worker=worker)

    def testCompiledConfigurationWireRoundTrip(self) -> None:
        """Restore msgspec retry lists to normalized tuple settings."""
        original = Queue().toDict()
        restored = msgspec.msgpack.decode(msgspec.msgpack.encode(original))
        self.assertIsInstance(restored["worker"]["backoff"], list)
        normalized = Queue(**restored)
        self.assertEqual(normalized.toDict(), original)
        self.assertEqual(asdict(normalized), original)
        self.assertIsInstance(normalized.worker, Worker)
        self.assertIsInstance(normalized.failed, Failed)
        self.assertIsInstance(normalized.connections["database"], Database)

    def testRejectsSharedDurableStorageNamespaces(self) -> None:
        """Prevent named backend aliases from consuming another connection's jobs."""
        for driver in ("database", "redis"):
            with self.subTest(driver=driver), self.assertRaises(ValueError):
                Queue(default="first", connections={
                    "first": {"driver": driver}, "second": {"driver": driver},
                })
        config = Queue(default="first", connections={
            "first": {"driver": "database", "table": "first_jobs"},
            "second": {"driver": "database", "table": "second_jobs"},
        })
        self.assertEqual(len(config.connections), 2)

    def testRejectsFailureStorageSharingJobsTable(self) -> None:
        """Reject incompatible job and failure schemas on the same database table."""
        with self.assertRaises(ValueError):
            Queue(failed={"table": "jobs"})
        config = Queue(failed={"connection": "audit", "table": "jobs"})
        self.assertEqual(config.failed.connection, "audit")

    def testBootstrapExposesEveryCustomizableField(self) -> None:
        """Keep all queue settings explicitly editable in application config."""
        self.assertEqual(
            set(BootstrapQueue.__annotations__),
            {"default", "connections", "failed", "worker"},
        )
        config = BootstrapQueue(
            default="redis",
            connections=Connections(redis=Redis(queue="high", retry_after=120.0)),
            worker=Worker(concurrency=8, timeout=20.0, backoff=[0.1, 0.5]),
            failed=Failed(connection="audit", table="queue_failures"),
        )
        self.assertEqual(config.connections.redis.queue, "high")
        self.assertEqual(config.worker.concurrency, 8)
        self.assertEqual(config.worker.backoff, (0.1, 0.5))
        self.assertEqual(config.failed.connection, "audit")
        with self.assertRaises(ValueError):
            BootstrapQueue(worker=Worker(timeout=90.0))

    def testConventionalConnectionsConvertNestedMappings(self) -> None:
        """Convert conventional backend mappings to their declared entities."""
        connections = Connections(
            sync={"queue": "inline"},
            database={"table": "pending_jobs"},
            redis={"endpoint": "redis.example.test", "port": 6380, "db": 2},
        )
        self.assertIsInstance(connections.sync, Sync)
        self.assertIsInstance(connections.database, Database)
        self.assertIsInstance(connections.redis, Redis)
        self.assertEqual(connections.sync.queue, "inline")
        self.assertEqual(connections.database.table, "pending_jobs")
        self.assertEqual(connections.redis.endpoint, "redis.example.test")
        self.assertEqual(connections.redis.port, 6380)
        self.assertEqual(connections.redis.db, 2)
        for name, value in (
            ("sync", None), ("database", Redis()), ("redis", Database()),
        ):
            with self.assertRaises(TypeError):
                Connections(**{name: value})

    def testNamedConnectionsAcceptTypedEntities(self) -> None:
        """Preserve custom names without requiring untyped backend dictionaries."""
        connection = Database(table="report_jobs", queue="high")
        config = Queue(
            default="reports", connections={"reports": connection},
        )
        self.assertIs(config.connections["reports"], connection)
        self.assertEqual(
            config.toDict()["connections"]["reports"], connection.toDict(),
        )
        with self.assertRaises(ValueError):
            Queue(
                default="reports",
                connections={"reports": connection, "alias": connection},
            )

    def testConnectionEntitiesValidateWithoutQueue(self) -> None:
        """Reject invalid driver, channel, and lease settings at entity creation."""
        for entity_type in (Sync, Database, Redis):
            for settings in (
                {"driver": 1}, {"driver": "unsupported"},
                {"queue": None}, {"queue": "../escape"},
                {"retry_after": True}, {"retry_after": "90"},
                {"retry_after": 0.0}, {"retry_after": float("nan")},
                {"retry_after": float("inf")},
            ):
                with self.assertRaises((TypeError, ValueError)):
                    entity_type(**settings)
        with self.assertRaises(ValueError):
            Database(driver=Drivers.REDIS)
        with self.assertRaises(ValueError):
            Redis(driver=Drivers.DATABASE)

    def testBackendAndFailureEntitiesValidateStorage(self) -> None:
        """Reject malformed storage identifiers and Redis settings directly."""
        for entity_type in (Database, Failed):
            for settings in (
                {"connection": 1}, {"connection": "../escape"},
                {"table": "jobs.invalid"}, {"table": "j\u00f6bs"},
                {"table": None},
            ):
                with self.assertRaises((TypeError, ValueError)):
                    entity_type(**settings)
        for settings in (
            {"endpoint": None}, {"endpoint": " "},
            {"prefix": " "}, {"prefix": 1},
        ):
            with self.assertRaises((TypeError, ValueError)):
                Redis(**settings)

    def testWorkerEntityOwnsBackoffAndRejectsInvalidValues(self) -> None:
        """Validate worker values independently and freeze caller retry lists."""
        delays = [0.0, 1.0]
        worker = Worker(backoff=delays)
        delays.append(2.0)
        self.assertEqual(worker.backoff, (0.0, 1.0))
        for settings in (
            {"concurrency": True}, {"concurrency": 1.5}, {"tries": 0},
            {"sleep": False}, {"sleep": 0.0}, {"timeout": None},
            {"timeout": float("inf")}, {"backoff": []},
            {"backoff": (True,)}, {"backoff": (-1.0,)},
        ):
            with self.assertRaises((TypeError, ValueError)):
                Worker(**settings)
        with self.assertRaises(FrozenInstanceError):
            worker.timeout = 1.0

    def testEnvironmentValuesRemainStrictInBothLayers(self) -> None:
        """Reject invalid environment settings in core and bootstrap factories."""
        for name, value in (
            ("QUEUE_CONNECTION", False), ("QUEUE_TABLE", "jobs.invalid"),
            ("REDIS_HOST", 1), ("QUEUE_DB_CONNECTION", False),
            ("REDIS_PORT", True), ("REDIS_DB", -1), ("REDIS_PASSWORD", 1),
            ("QUEUE_FAILED_TABLE", "failures.invalid"),
        ):
            self.environment.values.clear()
            self.environment.values[name] = value
            for entity_type in (Queue, BootstrapQueue):
                with self.assertRaises((TypeError, ValueError)):
                    entity_type()

    def testRedisRejectsInvalidStructuredSettings(self) -> None:
        """Enforce host, TCP port, database, and optional password types."""
        for settings in (
            {"endpoint": 1}, {"endpoint": None}, {"endpoint": " "},
            {"port": True}, {"port": "6379"}, {"port": 1.5},
            {"port": 0}, {"port": 65536}, {"db": False},
            {"db": "0"}, {"db": -1}, {"password": 1},
        ):
            with self.assertRaises((TypeError, ValueError)):
                Redis(**settings)
        for password in (None, ""):
            config = Redis(port=65535, db=0, password=password)
            self.assertEqual(config.port, 65535)
            self.assertEqual(config.password, password)
        with self.assertRaises(TypeError):
            Redis(url="redis://127.0.0.1:6379/0")

    def testRedisStorageNamespacesExcludeCredentials(self) -> None:
        """Isolate storage by host, port, database, and prefix, not credentials."""
        first = Redis(password=_CREDENTIAL)
        with self.assertRaises(ValueError):
            Queue(default="first", connections={
                "first": first, "second": Redis(password=None),
            })
        for settings in (
            {"endpoint": "redis.example.test"}, {"port": 6380},
            {"db": 1}, {"prefix": "queues:other"},
        ):
            config = Queue(default="first", connections={
                "first": first, "second": Redis(**settings),
            })
            self.assertEqual(len(config.connections), 2)
