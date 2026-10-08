import tempfile
import traceback
from pathlib import Path
from sqlalchemy import event
from orionis.database.connection import Connection
from orionis.database.exceptions import QueryException
from orionis.test import TestCase

_BOUND_MARKER = "context-control-private-marker"
_FAULT_SQL = "SELECT ? FROM missing_context_control_table"

class TestNativeContextControlErrors(TestCase):
    async def asyncSetUp(self):
        """
        Initialize an isolated SQLite connection for each test.

        Returns
        -------
        None
            Create the entries table and register connection and file cleanup.
        """
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.connection = Connection(
            "context_errors",
            {"driver": "sqlite", "database": str(Path(directory.name) / "db.sqlite")},
        )
        self.addAsyncCleanup(self.connection.disconnect)
        await self.connection.statement("CREATE TABLE entries (value TEXT)")

    async def _checkFault(self, boundary):
        """
        Verify error redaction and recovery at an implicit control boundary.

        Parameters
        ----------
        boundary : {"begin", "commit", "rollback"}
            Engine event at which to trigger the bound driver error.

        Returns
        -------
        None
            Assert sanitized errors, released checkouts, and rollback of writes.
        """
        engine = self.connection._getEngine().sync_engine

        def fault(raw):
            """
            Trigger a bound SQL error at the selected transaction boundary.

            Parameters
            ----------
            raw : sqlalchemy.engine.Connection
                Synchronous connection supplied by the engine event.

            Raises
            ------
            sqlalchemy.exc.OperationalError
                Raised by executing the bound query against a missing table.
            """
            raw.exec_driver_sql(_FAULT_SQL, (_BOUND_MARKER,))

        event.listen(engine, boundary, fault)
        try:
            with self.assertRaises(QueryException) as caught:
                if boundary == "rollback":
                    # DML succeeds; SELECT result materialization then raises a
                    # real ResourceClosedError, entering context rollback.
                    await self.connection.select(
                        "INSERT INTO entries (value) VALUES (:value)",
                        {"value": _BOUND_MARKER},
                    )
                else:
                    await self.connection.select("SELECT 1 AS value")
        finally:
            event.remove(engine, boundary, fault)
        error = caught.exception
        rendered = "".join(traceback.format_exception(error))
        self.assertIn("context_errors", str(error))
        self.assertIn("OperationalError", str(error))
        self.assertNotIn(_BOUND_MARKER, rendered)
        self.assertNotIn(_FAULT_SQL, rendered)
        self.assertNotIn("missing_context_control_table", rendered)
        self.assertIsNone(error.__cause__)
        self.assertTrue(error.__suppress_context__)
        self.assertEqual(engine.pool.checkedout(), 0)
        self.assertFalse(self.connection.inTransaction())
        self.assertEqual(
            await self.connection.select("SELECT 9 AS value"), [{"value": 9}],
        )
        self.assertEqual(await self.connection.select("SELECT value FROM entries"), [])

    async def testImplicitBeginFaultHidesDriverSqlAndBindingsAndRecovers(self):
        """
        Verify that implicit BEGIN failures hide driver details and recover.

        Returns
        -------
        None
            Confirm SQL and binding redaction, released resources, and reuse.
        """
        await self._checkFault("begin")

    async def testImplicitCommitFaultHidesDriverSqlAndBindingsAndRecovers(self):
        """
        Verify that implicit COMMIT failures hide driver details and recover.

        Returns
        -------
        None
            Confirm SQL and binding redaction, released resources, and reuse.
        """
        await self._checkFault("commit")

    async def testImplicitRollbackFaultHidesDriverSqlAndBindingsAndRecovers(self):
        """
        Verify that failed implicit rollback hides driver details and recovers.

        Returns
        -------
        None
            Confirm redaction, connection reuse, and removal of pending rows.
        """
        await self._checkFault("rollback")
