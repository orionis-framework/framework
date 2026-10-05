import tempfile
import asyncio
from pathlib import Path
from uuid import uuid4
import msgspec
from orionis.database.connection import Connection
from orionis.queues.drivers import database as database_module
from orionis.queues.drivers.database import DatabaseQueueDriver
from orionis.queues.entities.envelope import JobEnvelope
from orionis.queues.exceptions import QueueConfigurationError, QueueStorageError
from orionis.test import TestCase

def make_envelope(queue: str = "default") -> JobEnvelope:
    """Build a valid envelope for driver contract tests.

    Parameters
    ----------
    queue : str, optional
        Logical queue used by the test envelope.

    Returns
    -------
    JobEnvelope
        Unique envelope independent of application job registration.
    """
    return JobEnvelope(
        id=str(uuid4()), job="tests.queues.drivers.test_database:ContractJob",
        payload=b"{}", connection="database", queue=queue,
        max_tries=3, timeout=1.0, backoff=(0.0,),
    )

class DurableDriverContract:
    """Exercise identical persistence and lease behavior for durable drivers."""

    __slots__ = ()

    async def _advanceTime(self, seconds: float) -> None:
        """Wait for a real backend deadline unless a controlled clock is used.

        Parameters
        ----------
        seconds : float
            Duration added to the backend's notion of current time.

        Returns
        -------
        None
            Make delayed work or leases eligible for the next assertion.
        """
        await asyncio.sleep(seconds)

    async def testPushReserveDelete(self) -> None:
        """Round-trip one envelope through a complete reservation.

        Returns
        -------
        None
            Assert stable payload, first attempt, and acknowledged removal.
        """
        envelope = make_envelope()
        self.assertEqual(await self._driver.push(envelope), envelope.id)
        reserved = await self._driver.reserve(("default",), 60.0)
        self.assertIsNotNone(reserved)
        self.assertEqual(reserved.id, envelope.id)
        self.assertEqual(reserved.attempts, 1)
        self.assertEqual(
            msgspec.json.decode(reserved.payload, type=JobEnvelope), envelope,
        )
        self.assertEqual(await self._driver.size("default"), 1)
        self.assertIsNone(await self._driver.reserve(("default",), 60.0))
        self.assertTrue(await self._driver.delete(reserved))
        self.assertFalse(await self._driver.delete(reserved))
        self.assertEqual(await self._driver.size("default"), 0)

    async def testDelayedJob(self) -> None:
        """Keep a delayed job unavailable until its deadline.

        Returns
        -------
        None
            Assert delayed visibility and eventual reservation.
        """
        envelope = make_envelope()
        await self._driver.push(envelope, delay=0.08)
        self.assertIsNone(await self._driver.reserve(("default",), 60.0))
        self.assertEqual(await self._driver.size("default"), 1)
        await self._advanceTime(0.12)
        self.assertEqual(
            (await self._driver.reserve(("default",), 60.0)).id, envelope.id,
        )

    async def testReleaseDelayAndAttempts(self) -> None:
        """Preserve attempts when releasing a job with delayed availability.

        Returns
        -------
        None
            Assert one increment per successful reservation.
        """
        await self._driver.push(make_envelope())
        reserved = await self._driver.reserve(("default",), 60.0)
        self.assertTrue(await self._driver.release(reserved, delay=0.08))
        self.assertFalse(await self._driver.release(reserved))
        self.assertIsNone(await self._driver.reserve(("default",), 60.0))
        await self._advanceTime(0.12)
        next_reservation = await self._driver.reserve(("default",), 60.0)
        self.assertEqual(next_reservation.attempts, 2)
        self.assertNotEqual(next_reservation.token, reserved.token)
        self.assertFalse(await self._driver.delete(reserved))
        self.assertTrue(await self._driver.delete(next_reservation))

    async def testExpiredLeaseRecoveryAndFencing(self) -> None:
        """Recover expired reservations while rejecting their stale owners.

        Returns
        -------
        None
            Assert fencing before and after another worker reclaims the job.
        """
        envelope = make_envelope()
        await self._driver.push(envelope)
        expired = await self._driver.reserve(("default",), 0.05)
        await self._advanceTime(0.08)
        self.assertFalse(await self._driver.delete(expired))
        self.assertFalse(await self._driver.release(expired))
        reserved = await self._driver.reserve(("default",), 60.0)
        self.assertEqual(reserved.id, envelope.id)
        self.assertEqual(reserved.attempts, 2)
        self.assertNotEqual(expired.token, reserved.token)
        self.assertFalse(await self._driver.delete(expired))
        self.assertFalse(await self._driver.release(expired))
        self.assertTrue(await self._driver.delete(reserved))

    async def testQueueIsolationAndPriority(self) -> None:
        """Consume multiple logical queues in explicit priority order.

        Returns
        -------
        None
            Assert isolation and higher-priority consumption.
        """
        low = make_envelope("default")
        high = make_envelope("high")
        await self._driver.push(low)
        await self._driver.push(high)
        self.assertIsNone(await self._driver.reserve(("emails",), 60.0))
        first = await self._driver.reserve(("high", "default"), 60.0)
        second = await self._driver.reserve(("high", "default"), 60.0)
        self.assertEqual(first.id, high.id)
        self.assertEqual(second.id, low.id)

    async def testClearFencesActiveReservations(self) -> None:
        """Remove ready, delayed, and reserved jobs only from the named queue.

        Returns
        -------
        None
            Assert clear counts and stale acknowledgements.
        """
        await self._driver.push(make_envelope())
        reserved = await self._driver.reserve(("default",), 60.0)
        await self._driver.push(make_envelope(), delay=60)
        await self._driver.push(make_envelope())
        await self._driver.push(make_envelope("other"))
        self.assertEqual(await self._driver.clear("default"), 3)
        self.assertEqual(await self._driver.clear("default"), 0)
        self.assertFalse(await self._driver.delete(reserved))
        self.assertEqual(await self._driver.size("default"), 0)
        self.assertEqual(await self._driver.size("other"), 1)

    async def testConcurrentClaimSingleWinner(self) -> None:
        """Grant exactly one of one hundred simultaneous reservation attempts.

        Returns
        -------
        None
            Assert single ownership repeatedly against a durable backend.
        """
        for _ in range(3):
            envelope = make_envelope()
            await self._driver.push(envelope)
            reservations = await asyncio.gather(*(
                self._driver.reserve(("default",), 60.0) for _ in range(100)
            ), return_exceptions=True)
            errors = [item for item in reservations if isinstance(item, BaseException)]
            self.assertEqual(errors, [])
            winners = [item for item in reservations if item is not None]
            self.assertEqual(len(winners), 1)
            self.assertEqual(winners[0].id, envelope.id)
            self.assertEqual(winners[0].attempts, 1)
            self.assertTrue(await self._driver.delete(winners[0]))

    async def _consumeJobs(self) -> list[str]:
        """Reserve and acknowledge jobs until the backend has no ready work.

        Returns
        -------
        list of str
            Identifiers processed by this consumer.
        """
        processed = []
        while (reserved := await self._driver.reserve(("default",), 60.0)):
            processed.append(reserved.id)
            self.assertTrue(await self._driver.delete(reserved))
        return processed

    async def testManyJobsManyWorkers(self) -> None:
        """Process every job without loss across many competing consumers.

        Returns
        -------
        None
            Assert complete, unique acknowledged processing.
        """
        envelopes = [make_envelope() for _ in range(40)]
        for envelope in envelopes:
            await self._driver.push(envelope)
        async with asyncio.TaskGroup() as group:
            consumers = [group.create_task(self._consumeJobs()) for _ in range(20)]
        results = [task.result() for task in consumers]
        processed = [job_id for group in results for job_id in group]
        self.assertEqual(len(processed), len(envelopes))
        self.assertEqual(set(processed), {item.id for item in envelopes})
        self.assertEqual(await self._driver.size("default"), 0)

    async def testRejectInvalidDurations(self) -> None:
        """Reject invalid persistence and lease durations before writing jobs.

        Returns
        -------
        None
            Assert negative delays and nonpositive leases fail explicitly.
        """
        with self.assertRaises(QueueConfigurationError):
            await self._driver.push(make_envelope(), delay=-1)
        with self.assertRaises(QueueConfigurationError):
            await self._driver.reserve(("default",), 0)
        self.assertEqual(await self._driver.size("default"), 0)

class _Clock:
    """Expose a controlled wall clock without assuming SQLite operation speed."""

    __slots__ = ("now",)

    def __init__(self) -> None:
        """Start with an exactly representable epoch timestamp.

        Returns
        -------
        None
            Set the current time for queue storage operations.
        """
        self.now = 1000.0

    def __call__(self) -> float:
        """Return the controlled timestamp.

        Returns
        -------
        float
            Timestamp advanced only by the contract's explicit time hook.
        """
        return self.now

class TestDatabaseQueueDriver(DurableDriverContract, TestCase):
    """Run the durable driver contract against a prefixed SQLite file."""

    __slots__ = (
        "_clock", "_connection", "_driver", "_original_time", "_path", "_temporary",
    )

    async def asyncSetUp(self) -> None:
        """Create independent pooled connections backed by a temporary file.

        Returns
        -------
        None
            Prepare real database arbitration for concurrent reservations.
        """
        self._original_time = database_module.current_time
        self.addCleanup(setattr, database_module, "current_time", self._original_time)
        self._clock = _Clock()
        database_module.current_time = self._clock
        self._temporary = tempfile.TemporaryDirectory()
        self._path = str(Path(self._temporary.name) / "queues.sqlite")
        self._connection = Connection("queues", {
            "driver": "sqlite", "database": self._path, "prefix": "q_",
            "journal_mode": "WAL", "busy_timeout": 30000,
        })
        self._driver = DatabaseQueueDriver(self._connection)
        await self._driver.size("default")

    async def asyncTearDown(self) -> None:
        """Close database handles before removing the temporary directory.

        Returns
        -------
        None
            Release the SQLite file and its containing directory.
        """
        try:
            await self._connection.disconnect()
            self._temporary.cleanup()
        finally:
            database_module.current_time = self._original_time

    async def _advanceTime(self, seconds: float) -> None:
        """Advance queue deadlines deterministically, independent of I/O speed.

        Parameters
        ----------
        seconds : float
            Duration added to the controlled queue clock.

        Returns
        -------
        None
            Yield once after changing the backend's current timestamp.
        """
        self._clock.now += seconds
        await asyncio.sleep(0)

    async def testPersistenceAcrossConnectionRecreation(self) -> None:
        """Retain queued state after rebuilding the driver and connection.

        Returns
        -------
        None
            Assert persisted attempts and delayed reservation state survive.
        """
        envelope = make_envelope()
        await self._driver.push(envelope)
        reserved = await self._driver.reserve(("default",), 60.0)
        await self._driver.release(reserved)
        await self._driver.close()
        await self._connection.disconnect()
        self._connection = Connection("queues", {
            "driver": "sqlite", "database": self._path, "prefix": "q_",
            "journal_mode": "WAL", "busy_timeout": 30000,
        })
        self._driver = DatabaseQueueDriver(self._connection)
        next_reservation = await self._driver.reserve(("default",), 60.0)
        self.assertEqual(next_reservation.id, envelope.id)
        self.assertEqual(next_reservation.attempts, 2)

    async def testClosePreservesSharedConnection(self) -> None:
        """Preserve framework connection ownership when closing the driver.

        Returns
        -------
        None
            Assert the shared engine remains usable after queue closure.
        """
        await self._driver.push(make_envelope())
        engine = self._connection._engine
        await self._driver.close()
        self.assertIs(self._connection._engine, engine)
        self.assertEqual(await self._driver.size("default"), 1)

    async def testSchemaUsesIndexesAndFractionalTimestamps(self) -> None:
        """Create useful claim indexes and preserve subsecond deadlines.

        Returns
        -------
        None
            Assert prefixed table indexes and floating timestamp storage.
        """
        envelope = make_envelope()
        await self._driver.push(envelope, delay=0.125)
        rows = await self._connection.select(
            "SELECT available_at, created_at FROM q_jobs WHERE id=:id",
            {"id": envelope.id},
        )
        self.assertIsInstance(rows[0]["available_at"], float)
        self.assertAlmostEqual(
            rows[0]["available_at"] - rows[0]["created_at"], 0.125,
        )
        indexes = await self._connection.select("PRAGMA index_list(q_jobs)")
        self.assertTrue(any("available_at" in item["name"] for item in indexes))

    async def testRejectUnsafeTableName(self) -> None:
        """Reject invalid SQL identifiers in queue table configuration.

        Returns
        -------
        None
            Assert unsafe table names fail before database access.
        """
        with self.assertRaises(QueueConfigurationError):
            DatabaseQueueDriver(self._connection, "jobs;DROP TABLE jobs")

    async def testFirstUseSchemaRollbackIsRecoverable(self) -> None:
        """Rebuild a lazily created queue table after its transaction rolls back.

        Returns
        -------
        None
            Assert schema readiness never outlives uncommitted creation.
        """
        driver = DatabaseQueueDriver(self._connection, "transaction_jobs")
        with self.assertRaisesRegex(RuntimeError, "rollback"):
            async with self._connection.transaction():
                await driver.push(make_envelope())
                self.assertEqual(await driver.size("default"), 1)
                message = "rollback"
                raise RuntimeError(message)
        self.assertEqual(await driver.size("default"), 0)
        self.assertIsNone(await driver.reserve(("default",), 60.0))

    async def testPushJoinsCurrentTransaction(self) -> None:
        """Keep database queue pushes subject to the caller's transaction.

        Returns
        -------
        None
            Assert a push is removed by rollback on an existing queue table.
        """
        with self.assertRaisesRegex(RuntimeError, "rollback"):
            async with self._connection.transaction():
                await self._driver.push(make_envelope())
                self.assertEqual(await self._driver.size("default"), 1)
                message = "rollback"
                raise RuntimeError(message)
        self.assertEqual(await self._driver.size("default"), 0)

    async def testReserveRejectsAmbientTransaction(self) -> None:
        """Reject reservations that could return an uncommitted lease.

        Returns
        -------
        None
            Assert queue claims cannot join a caller's open transaction.
        """
        await self._driver.push(make_envelope())
        async with self._connection.transaction():
            with self.assertRaisesRegex(QueueStorageError, "committed"):
                await self._driver.reserve(("default",), 60.0)
        self.assertIsNotNone(await self._driver.reserve(("default",), 60.0))

    async def testCommittedPushVisibleToIndependentConnection(self) -> None:
        """Expose a queued job to other connections only after its commit.

        Returns
        -------
        None
            Assert independent consumers cannot reserve uncommitted queue rows.
        """
        independent = Connection("consumer", {
            "driver": "sqlite", "database": self._path, "prefix": "q_",
            "journal_mode": "WAL", "busy_timeout": 30000,
        })
        consumer = DatabaseQueueDriver(independent)
        try:
            await consumer.size("default")
            envelope = make_envelope()
            async with self._connection.transaction():
                await self._driver.push(envelope)
                self.assertIsNone(await consumer.reserve(("default",), 60.0))
            reserved = await consumer.reserve(("default",), 60.0)
            self.assertEqual(reserved.id, envelope.id)
        finally:
            await independent.disconnect()

    async def testIndependentDriversBootstrapAndClaimAtomically(self) -> None:
        """Arbitrate cold schema creation and claims across independent engines.

        Returns
        -------
        None
            Assert one owner across one hundred calls using twenty connections.
        """
        connections = tuple(Connection(f"worker_{index}", {
            "driver": "sqlite", "database": self._path, "prefix": "q_",
            "journal_mode": "WAL", "busy_timeout": 30000,
        }) for index in range(20))
        drivers = tuple(
            DatabaseQueueDriver(connection, "independent_jobs")
            for connection in connections
        )
        try:
            sizes = await asyncio.gather(*(
                driver.size("default") for driver in drivers
            ), return_exceptions=True)
            self.assertEqual(sizes, [0] * len(drivers))
            for _ in range(3):
                envelope = make_envelope()
                await drivers[0].push(envelope)
                reserved = await asyncio.gather(*(
                    drivers[index % len(drivers)].reserve(("default",), 60.0)
                    for index in range(100)
                ), return_exceptions=True)
                errors = [item for item in reserved if isinstance(item, BaseException)]
                self.assertEqual(errors, [])
                winners = [item for item in reserved if item is not None]
                self.assertEqual(len(winners), 1)
                self.assertEqual(winners[0].id, envelope.id)
                self.assertTrue(await drivers[0].delete(winners[0]))
        finally:
            await asyncio.gather(*(
                connection.disconnect() for connection in connections
            ))
