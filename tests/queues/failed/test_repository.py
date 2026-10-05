import asyncio
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from orionis.database.connection import Connection
from orionis.queues.drivers.database import DatabaseQueueDriver
from orionis.queues.failed.repository import DatabaseFailedJobRepository
from orionis.queues.exceptions import QueueConfigurationError
from orionis.test import TestCase
from tests.queues.drivers.test_database import make_envelope

if TYPE_CHECKING:
    from orionis.queues.entities.failed_job import FailedJob

class TestDatabaseFailedJobRepository(TestCase):
    """Verify durable failure diagnostics and idempotent failure persistence."""

    __slots__ = (
        "_connection", "_driver", "_path", "_repository", "_temporary",
    )

    async def asyncSetUp(self) -> None:
        """Create isolated file-backed queue and failed-job storage.

        Returns
        -------
        None
            Prepare real storage shared by the queue and failure repository.
        """
        self._temporary = tempfile.TemporaryDirectory()
        self._path = str(Path(self._temporary.name) / "failures.sqlite")
        self._connection = Connection("failures", {
            "driver": "sqlite", "database": self._path, "prefix": "f_",
        })
        self._driver = DatabaseQueueDriver(self._connection)
        self._repository = DatabaseFailedJobRepository(self._connection)
        await self._repository.all()

    async def asyncTearDown(self) -> None:
        """Close file handles before removing isolated failure storage.

        Returns
        -------
        None
            Release the database file and temporary directory.
        """
        await self._connection.disconnect()
        self._temporary.cleanup()

    async def _recordFailure(self) -> FailedJob:
        """Reserve and record one real failed queue job.

        Returns
        -------
        FailedJob
            Failure with retained envelope and original diagnostics.
        """
        await self._driver.push(make_envelope())
        reserved = await self._driver.reserve(("default",), 60.0)
        return await self._repository.record(
            reserved, "database", RuntimeError("delivery failed"),
        )

    async def testRecordFindAndList(self) -> None:
        """Preserve complete diagnostics and retryable envelope bytes.

        Returns
        -------
        None
            Assert the repository can inspect and enumerate one failure.
        """
        failure = await self._recordFailure()
        self.assertNotEqual(failure.id, failure.job_id)
        self.assertEqual(failure.connection, "database")
        self.assertEqual(failure.queue, "default")
        self.assertEqual(failure.attempts, 1)
        self.assertIsInstance(failure.payload, bytes)
        self.assertEqual(failure.exception_type, "builtins.RuntimeError")
        self.assertEqual(failure.exception_message, "delivery failed")
        self.assertIn("RuntimeError: delivery failed", failure.traceback)
        self.assertIsInstance(failure.failed_at, float)
        self.assertEqual(await self._repository.find(failure.id), failure)
        self.assertEqual(await self._repository.all(), (failure,))

    async def testForgetAndMissingFailure(self) -> None:
        """Remove a failure and report absent identifiers consistently.

        Returns
        -------
        None
            Assert existing and missing failure behavior.
        """
        failure = await self._recordFailure()
        self.assertTrue(await self._repository.forget(failure.id))
        self.assertFalse(await self._repository.forget(failure.id))
        self.assertIsNone(await self._repository.find(failure.id))
        self.assertEqual(await self._repository.all(), ())

    async def testConcurrentRecordsAreIdempotent(self) -> None:
        """Persist one stable failure even when multiple workers report its id.

        Returns
        -------
        None
            Assert concurrent inserts retain one complete failure record.
        """
        await self._driver.push(make_envelope())
        reserved = await self._driver.reserve(("default",), 60.0)
        failures = await asyncio.gather(*(
            self._repository.record(reserved, "database", RuntimeError("failed"))
            for _ in range(20)
        ))
        persisted = await self._repository.all()
        self.assertEqual(len(persisted), 1)
        self.assertTrue(all(item == persisted[0] for item in failures))

    async def testListUsesChronologicalOrder(self) -> None:
        """List failures in their original chronological order.

        Returns
        -------
        None
            Assert stable time ordering across several distinct failures.
        """
        first = await self._recordFailure()
        second = await self._recordFailure()
        self.assertEqual(await self._repository.all(), (first, second))

    async def testPersistenceAcrossRecreation(self) -> None:
        """Recover failure records after recreating repository and connection.

        Returns
        -------
        None
            Assert diagnostics and envelope survive process-equivalent recreation.
        """
        failure = await self._recordFailure()
        await self._connection.disconnect()
        self._connection = Connection("failures", {
            "driver": "sqlite", "database": self._path, "prefix": "f_",
        })
        self._repository = DatabaseFailedJobRepository(self._connection)
        self.assertEqual(await self._repository.find(failure.id), failure)

    async def testClosePreservesConnection(self) -> None:
        """Preserve shared framework connection ownership on repository closure.

        Returns
        -------
        None
            Assert storage remains usable through its original manager lifecycle.
        """
        failure = await self._recordFailure()
        engine = self._connection._engine
        await self._repository.close()
        self.assertIs(self._connection._engine, engine)
        self.assertEqual(await self._repository.find(failure.id), failure)

    async def testRejectInvalidTableIdentifier(self) -> None:
        """Reject failure table identifiers containing SQL fragments.

        Returns
        -------
        None
            Assert validation precedes database use.
        """
        with self.assertRaises(QueueConfigurationError):
            DatabaseFailedJobRepository(self._connection, "failed jobs")

    async def testFirstUseSchemaRollbackIsRecoverable(self) -> None:
        """Recreate a failed-job table after its first transaction rolls back.

        Returns
        -------
        None
            Assert failure storage readiness tracks committed schema creation.
        """
        await self._driver.push(make_envelope())
        reserved = await self._driver.reserve(("default",), 60.0)
        repository = DatabaseFailedJobRepository(self._connection, "tx_failed_jobs")
        with self.assertRaisesRegex(RuntimeError, "rollback"):
            async with self._connection.transaction():
                await repository.record(reserved, "database", ValueError("failed"))
                message = "rollback"
                raise RuntimeError(message)
        self.assertEqual(await repository.all(), ())

    async def testNewFailureSurvivesForgettingPreviousAttempt(self) -> None:
        """Preserve a fast retried failure when its preceding record is forgotten.

        Returns
        -------
        None
            Assert event identities differ across reservation attempts.
        """
        await self._driver.push(make_envelope())
        first = await self._driver.reserve(("default",), 60.0)
        previous = await self._repository.record(first, "database", ValueError("old"))
        await self._driver.release(first)
        second = await self._driver.reserve(("default",), 60.0)
        current = await self._repository.record(second, "database", ValueError("new"))
        self.assertNotEqual(previous.id, current.id)
        self.assertEqual(previous.job_id, current.job_id)
        await self._repository.forget(previous.id)
        self.assertEqual(await self._repository.find(current.id), current)
        self.assertEqual(await self._repository.all(), (current,))
