from __future__ import annotations
import traceback
from orionis.database.connection import Connection
from orionis.database.contracts.transaction import ITransaction
from orionis.database.exceptions import (
    QueryException,
    TransactionException,
    UnsupportedDriverException,
)
from orionis.orm.query.expressions import (
    DeletePlan,
    InsertPlan,
    SelectPlan,
    UpdatePlan,
    WhereClause,
)
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Integer, String
from orionis.test import TestCase

def _makeTable() -> TableDefinition:
    """Build the table definition shared by the connection tests."""
    columns = {
        "id": Integer().primary().autoIncrement(),
        "name": String(),
    }
    for key, column in columns.items():
        column.name = key
    return TableDefinition(name="items", columns=columns, primary_key="id")

class TestConnection(TestCase):

    async def asyncSetUp(self) -> None:
        """
        Create an in-memory connection with a fresh table per test.

        Guarantees complete isolation between tests.
        """
        self._table = _makeTable()
        self._connection = Connection(
            "sqlite",
            {"driver": "sqlite", "database": ":memory:", "prefix": ""},
        )
        await self._connection.createTable(self._table)

    async def asyncTearDown(self) -> None:
        """
        Dispose the engine after each test.

        Releases the pooled in-memory database.
        """
        await self._connection.disconnect()

    async def _insert(self, name: str):
        """Insert a row and return the insert result."""
        plan = InsertPlan(table=self._table, values=[{"name": name}])
        return await self._connection.insert(plan)

    # ── CRUD plans ────────────────────────────────────────────────────────────

    async def testInsertReportsGeneratedKey(self) -> None:
        """
        Report the generated primary key for single-row inserts.

        Validates the InsertResult contract.
        """
        result = await self._insert("alpha")
        self.assertEqual(result.last_insert_id, 1)
        self.assertEqual(result.row_count, 1)

    async def testMultiRowInsertOmitsGeneratedKey(self) -> None:
        """
        Omit the generated key when inserting several rows at once.

        Validates the multi-row InsertResult contract.
        """
        plan = InsertPlan(
            table=self._table,
            values=[{"name": "a"}, {"name": "b"}],
        )
        result = await self._connection.insert(plan)
        self.assertIsNone(result.last_insert_id)
        self.assertEqual(result.row_count, 2)

    async def testSelectReturnsPlainDictionaries(self) -> None:
        """
        Return rows as plain dictionaries keyed by column name.

        Validates that no engine objects leak through select.
        """
        await self._insert("alpha")
        rows = await self._connection.select(SelectPlan(table=self._table))
        self.assertEqual(rows, [{"id": 1, "name": "alpha"}])
        self.assertIsInstance(rows[0], dict)

    async def testSelectProjectsOnlyRequestedColumns(self) -> None:
        """
        Return only the projected columns in each row.

        Validates the column projection path.
        """
        await self._insert("alpha")
        plan = SelectPlan(table=self._table, columns=("name",))
        rows = await self._connection.select(plan)
        self.assertEqual(rows, [{"name": "alpha"}])

    async def testUpdateReturnsAffectedRowCount(self) -> None:
        """
        Report the number of rows touched by an update.

        Validates the update row count contract.
        """
        await self._insert("alpha")
        await self._insert("beta")
        plan = UpdatePlan(
            table=self._table,
            values={"name": "renamed"},
            wheres=[WhereClause(column="id", value=1)],
        )
        self.assertEqual(await self._connection.update(plan), 1)

    async def testDeleteReturnsAffectedRowCount(self) -> None:
        """
        Report the number of rows removed by a delete.

        Validates the delete row count contract.
        """
        await self._insert("alpha")
        await self._insert("beta")
        plan = DeletePlan(table=self._table)
        self.assertEqual(await self._connection.delete(plan), 2)

    async def testScalarReturnsFirstColumn(self) -> None:
        """
        Return the first column of the first row for scalar plans.

        Validates the scalar execution path used by aggregates.
        """
        await self._insert("alpha")
        plan = SelectPlan(table=self._table, columns=("name",))
        self.assertEqual(await self._connection.scalar(plan), "alpha")

    async def testScalarReturnsNoneWithoutRows(self) -> None:
        """
        Return None when the scalar query yields no rows.

        Validates the empty scalar contract.
        """
        plan = SelectPlan(table=self._table, columns=("name",))
        self.assertIsNone(await self._connection.scalar(plan))

    # ── Raw SQL ───────────────────────────────────────────────────────────────

    async def testRawSelectWithNamedBindings(self) -> None:
        """
        Run raw SQL with named parameter bindings.

        Validates the textual query path.
        """
        await self._insert("alpha")
        rows = await self._connection.select(
            "SELECT name FROM items WHERE id = :id",
            {"id": 1},
        )
        self.assertEqual(rows, [{"name": "alpha"}])

    async def testExecuteReturnsRowCount(self) -> None:
        """
        Report affected rows for raw data-modifying statements.

        Validates the execute contract.
        """
        await self._insert("alpha")
        affected = await self._connection.execute(
            "UPDATE items SET name = :name",
            {"name": "x"},
        )
        self.assertEqual(affected, 1)

    async def testStatementRunsDdl(self) -> None:
        """
        Run DDL statements through the statement helper.

        Validates the DDL execution path.
        """
        done = await self._connection.statement(
            "CREATE TABLE extra (id INTEGER PRIMARY KEY)",
        )
        self.assertTrue(done)

    async def testQueryFailureRaisesQueryException(self) -> None:
        """
        Translate engine errors into QueryException.

        Validates that engine exceptions never escape raw.
        """
        with self.assertRaises(QueryException):
            await self._connection.select("SELECT * FROM missing_table")

    async def testQueryErrorsDoNotExposeBoundCredentials(self) -> None:
        """Keep credentials out of SQL errors and their formatted exception chain."""
        credential = "private-value-that-must-not-be-logged"
        with self.assertRaises(QueryException) as caught:
            await self._connection.execute(
                "INSERT INTO missing_table (credential) VALUES (:value)",
                {"value": credential},
            )
        self.assertNotIn(credential, str(caught.exception))
        formatted = "".join(traceback.format_exception(caught.exception))
        self.assertNotIn(credential, formatted)
        self.assertIn("OperationalError", str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)

    # ── Transactions ──────────────────────────────────────────────────────────

    async def testTransactionCommitPersistsChanges(self) -> None:
        """
        Persist rows written inside a committed transaction.

        Validates the commit path of the context manager.
        """
        async with self._connection.transaction():
            await self._insert("kept")
        rows = await self._connection.select(SelectPlan(table=self._table))
        self.assertEqual(len(rows), 1)

    async def testTransactionRollbackDiscardsChanges(self) -> None:
        """
        Discard rows written inside a failed transaction.

        Validates the rollback path of the context manager.
        """
        with self.assertRaises(RuntimeError):
            async with self._connection.transaction():
                await self._insert("ghost")
                error_msg = "boom"
                raise RuntimeError(error_msg)
        rows = await self._connection.select(SelectPlan(table=self._table))
        self.assertEqual(rows, [])

    async def testNestedTransactionUsesSavepoints(self) -> None:
        """
        Roll back only the inner savepoint on nested failures.

        Validates savepoint-based nesting semantics.
        """
        async with self._connection.transaction():
            await self._insert("outer")
            with self.assertRaises(RuntimeError):
                async with self._connection.transaction():
                    await self._insert("inner")
                    error_msg = "inner boom"
                    raise RuntimeError(error_msg)
        rows = await self._connection.select(SelectPlan(table=self._table))
        self.assertEqual([row["name"] for row in rows], ["outer"])

    async def testExplicitBeginCommitRollback(self) -> None:
        """
        Drive the transaction through the explicit control methods.

        Validates begin, commit, rollback, and state reporting.
        """
        self.assertFalse(self._connection.inTransaction())
        await self._connection.begin()
        self.assertTrue(self._connection.inTransaction())
        await self._insert("explicit")
        await self._connection.commit()
        self.assertFalse(self._connection.inTransaction())

        await self._connection.begin()
        await self._insert("undone")
        await self._connection.rollback()
        rows = await self._connection.select(SelectPlan(table=self._table))
        self.assertEqual([row["name"] for row in rows], ["explicit"])

    async def testCommitWithoutTransactionRaises(self) -> None:
        """
        Raise TransactionException for commits without a transaction.

        Validates the transaction state guard.
        """
        with self.assertRaises(TransactionException):
            await self._connection.commit()

    async def testRollbackWithoutTransactionRaises(self) -> None:
        """
        Raise TransactionException for rollbacks without a transaction.

        Validates the transaction state guard.
        """
        with self.assertRaises(TransactionException):
            await self._connection.rollback()

    # ── Schema helpers ────────────────────────────────────────────────────────

    async def testDropTableRemovesTable(self) -> None:
        """
        Drop the physical table through the schema helper.

        Validates the drop DDL execution.
        """
        await self._connection.dropTable("items")
        with self.assertRaises(QueryException):
            await self._connection.select(SelectPlan(table=self._table))

    async def testCreateTableIfNotExistsFalseFailsOnDuplicate(self) -> None:
        """
        Fail to recreate an existing table without the IF NOT EXISTS guard.

        Validates that disabling if_not_exists surfaces the engine error.
        """
        with self.assertRaises(QueryException):
            await self._connection.createTable(self._table, if_not_exists=False)

    async def testDropTableIfExistsFalseFailsOnMissingTable(self) -> None:
        """
        Fail to drop a missing table without the IF EXISTS guard.

        Validates that disabling if_exists surfaces the engine error.
        """
        await self._connection.dropTable("items")
        with self.assertRaises(QueryException):
            await self._connection.dropTable("items", if_exists=False)
    # ── Configuration and lifecycle ────────────────────────────────────────────────

    async def testUnsupportedDriverFailsAtConstruction(self) -> None:
        """
        Reject unsupported drivers when the connection is created.

        Validates the fail-fast configuration guard.
        """
        with self.assertRaises(UnsupportedDriverException):
            Connection("bad", {"driver": "mssql-legacy"})

    async def testConnectionExposesItsName(self) -> None:
        """
        Expose the registered connection name.

        Validates the getName accessor.
        """
        self.assertEqual(self._connection.getName(), "sqlite")

    async def testTransactionFactoryReturnsContract(self) -> None:
        """
        Build transaction objects honoring the ITransaction contract.

        Validates the transaction factory return type.
        """
        self.assertIsInstance(self._connection.transaction(), ITransaction)

    async def testDisconnectIsIdempotent(self) -> None:
        """
        Allow disconnecting an already disposed connection.

        Validates the idempotent lifecycle contract.
        """
        await self._connection.disconnect()
        await self._connection.disconnect()

    async def testSqlitePragmasAreApplied(self) -> None:
        """
        Apply the configured PRAGMA settings on new connections.

        Validates the connect-hook configuration path.
        """
        connection = Connection(
            "tuned",
            {
                "driver": "sqlite",
                "database": ":memory:",
                "foreign_key_constraints": True,
                "busy_timeout": 2500,
                "journal_mode": "MEMORY",
                "synchronous": "NORMAL",
            },
        )
        try:
            fk = await connection.select("PRAGMA foreign_keys")
            self.assertEqual(fk[0]["foreign_keys"], 1)
            timeout = await connection.select("PRAGMA busy_timeout")
            self.assertEqual(timeout[0]["timeout"], 2500)
        finally:
            await connection.disconnect()
