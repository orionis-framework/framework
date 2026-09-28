from __future__ import annotations
import asyncio
import unittest
from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import event, literal
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import AsyncAdaptedQueuePool, QueuePool
from orionis.database.compiler import SQLCompiler
from orionis.database.connection import Connection
from orionis.database.dialect import engine_options
from orionis.database.exceptions import QueryException, TransactionException
from orionis.orm.query.expressions import (
    InsertPlan,
    RawExpression,
    SelectPlan,
    SubQueryColumn,
    WhereClause,
    WhereType,
)
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Integer


class TestRuntimeRegressions(unittest.IsolatedAsyncioTestCase):
    """Exercise connection isolation and compiler behavior without application DI."""

    async def asyncSetUp(self) -> None:
        """Create a private in-memory database for each test."""
        self.connection = Connection(
            "runtime", {"driver": "sqlite", "database": ":memory:"},
        )
        await self.connection.statement(
            "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)",
        )

    async def asyncTearDown(self) -> None:
        """Dispose the private database after each test."""
        if self.connection.inTransaction():
            await self.connection.rollback()
        await self.connection.disconnect()

    async def testChildCannotUseInheritedTransaction(self) -> None:
        """Reject transaction use from a child without changing the owner state."""
        await self.connection.begin()
        operations = (
            self.connection.begin,
            self.connection.commit,
            self.connection.rollback,
        )
        for operation in operations:
            with self.assertRaisesRegex(TransactionException, "child task"):
                await asyncio.create_task(operation())
            self.assertTrue(self.connection.inTransaction())

        with self.assertRaisesRegex(TransactionException, "child task"):
            await asyncio.create_task(self.connection.select("SELECT 1"))
        self.assertFalse(await asyncio.create_task(self._childInTransaction()))
        await self.connection.rollback()

    async def _childInTransaction(self) -> bool:
        """Read transaction ownership from the calling task."""
        return self.connection.inTransaction()

    async def testChildDiscardsSettledInheritedState(self) -> None:
        """Allow a child to query after its inherited transaction has settled."""
        ready = asyncio.Event()

        async def query_after_commit() -> list[dict]:
            await ready.wait()
            return await self.connection.select("SELECT 1 AS value")

        await self.connection.begin()
        task = asyncio.create_task(query_after_commit())
        await self.connection.commit()
        ready.set()
        self.assertEqual(await task, [{"value": 1}])

    async def testTransactionReusesItsContext(self) -> None:
        """Return the same connection context throughout a transaction."""
        await self.connection.begin()
        self.assertIs(self.connection._acquire(), self.connection._acquire())
        await self.connection.rollback()

    async def testRootRollbackIncludesFirstSavepoint(self) -> None:
        """Keep a first-write savepoint inside its enclosing root transaction."""
        await self.connection.begin()
        await self.connection.begin()
        await self.connection.execute("INSERT INTO items (name) VALUES ('nested')")
        await self.connection.commit()
        await self.connection.rollback()
        self.assertEqual(await self.connection.select("SELECT * FROM items"), [])

    async def testRootRollbackUndoesDdl(self) -> None:
        """Keep table creation inside the active root transaction."""
        await self.connection.begin()
        await self.connection.statement("CREATE TABLE rolled_back (id INTEGER)")
        await self.connection.rollback()
        rows = await self.connection.select(
            "SELECT name FROM sqlite_master WHERE name = 'rolled_back'",
        )
        self.assertEqual(rows, [])

    async def testMemoryDatabaseSerializesIndependentTransactions(self) -> None:
        """Keep another task's commit outside a transaction being rolled back."""
        started = asyncio.Event()
        release = asyncio.Event()

        async def rollback_owner() -> None:
            await self.connection.begin()
            await self.connection.execute(
                "INSERT INTO items (name) VALUES ('rolled back')",
            )
            started.set()
            await release.wait()
            await self.connection.rollback()

        async with asyncio.TaskGroup() as group:
            owner = group.create_task(rollback_owner())
            await started.wait()
            writer = group.create_task(self.connection.execute(
                "INSERT INTO items (name) VALUES ('committed')",
            ))
            try:
                with self.assertRaises(TimeoutError):
                    await asyncio.wait_for(asyncio.shield(writer), 0.05)
            finally:
                release.set()
            await owner
        rows = await self.connection.select("SELECT name FROM items")
        self.assertEqual(rows, [{"name": "committed"}])

    async def testRawBindingsRemainIndependent(self) -> None:
        """Reuse SQL text while preserving each immutable parameter mapping."""
        query = "SELECT :value AS value"
        first = MappingProxyType({"value": 1})
        second = MappingProxyType({"value": 2})
        self.assertEqual(await self.connection.select(query, first), [{"value": 1}])
        self.assertEqual(await self.connection.select(query, second), [{"value": 2}])
        self.assertEqual(dict(first), {"value": 1})

    async def testBatchInsertUsesExecutemany(self) -> None:
        """Execute homogeneous rows using one reusable insert statement."""
        executions = []

        def capture_insert(
            _connection,
            _cursor,
            statement,
            _parameters,
            _context,
            executemany,
        ) -> None:
            if statement.startswith("INSERT"):
                executions.append((statement, executemany))

        event.listen(
            self.connection._getEngine().sync_engine,
            "before_cursor_execute",
            capture_insert,
        )
        rows = [{"name": str(value)} for value in range(1000)]
        result = await self.connection.insert(InsertPlan(
            table=TableDefinition("items"), values=rows,
        ))
        self.assertEqual(result.row_count, 1000)
        self.assertIsNone(result.last_insert_id)
        self.assertEqual(executions, [("INSERT INTO items (name) VALUES (?)", True)])
        count = await self.connection.select("SELECT COUNT(*) AS n FROM items")
        self.assertEqual(count, [{"n": 1000}])

    async def testBatchInsertFailureRollsBackEveryRow(self) -> None:
        """Roll back the entire batch after a later row violates a constraint."""
        plan = InsertPlan(
            table=TableDefinition("items"),
            values=[{"id": 1, "name": "first"}, {"id": 1, "name": "duplicate"}],
        )
        with self.assertRaises(QueryException):
            await self.connection.insert(plan)
        self.assertEqual(await self.connection.select("SELECT * FROM items"), [])

    async def testBatchInsertPreservesColumnDefaults(self) -> None:
        """Apply client defaults for every parameter group in a batch."""
        definition = TableDefinition("defaults", {
            "id": Integer().primary().autoIncrement(),
            "value": Integer().default(7),
        })
        await self.connection.createTable(definition)
        result = await self.connection.insert(InsertPlan(
            table=definition, values=[{}, {}, {}],
        ))
        self.assertEqual(result.row_count, 3)
        rows = await self.connection.select(SelectPlan(table=definition))
        self.assertEqual([row["value"] for row in rows], [7, 7, 7])

    async def testInsertExpressionsKeepTheirSqlSemantics(self) -> None:
        """Keep per-row SQL expressions on the explicit VALUES path."""
        result = await self.connection.insert(InsertPlan(
            table=TableDefinition("items"),
            values=[{"name": literal("one")}, {"name": literal("two")}],
        ))
        self.assertEqual(result.row_count, 2)
        rows = await self.connection.select("SELECT name FROM items ORDER BY id")
        self.assertEqual(rows, [{"name": "one"}, {"name": "two"}])

    async def testAliasedRawProjectionKeepsBindings(self) -> None:
        """Bind special characters in a raw projection carrying an alias."""
        await self.connection.execute("INSERT INTO items (name) VALUES ('sample')")
        value = "x'); DROP TABLE items; --"
        plan = SelectPlan(
            table=TableDefinition("items"),
            columns=(RawExpression(":value", {"value": value}, "label"),),
        )
        self.assertEqual(await self.connection.select(plan), [{"label": value}])
        rows = await self.connection.select("SELECT name FROM items")
        self.assertEqual(rows, [{"name": "sample"}])

    async def testAliasedBoundAggregatePreservesGrouping(self) -> None:
        """Keep bound aggregate fragments in the surrounding GROUP BY query."""
        await self.connection.statement(
            "CREATE TABLE metrics (category INTEGER, amount INTEGER)",
        )
        await self.connection.execute(
            "INSERT INTO metrics VALUES (1, 5), (1, 7), (2, 20)",
        )
        plan = SelectPlan(
            table=TableDefinition("metrics"),
            columns=(
                "category",
                RawExpression("SUM(amount) + :offset", {"offset": 3}, "total"),
            ),
            groups=["category"],
        )
        rows = await self.connection.select(plan)
        self.assertEqual(
            rows, [{"category": 1, "total": 15}, {"category": 2, "total": 23}],
        )

    async def testAliasedBoundFragmentPreservesCorrelation(self) -> None:
        """Resolve an outer column inside a bound raw scalar projection."""
        await self.connection.execute("INSERT INTO items (name) VALUES ('a'), ('b')")
        table = TableDefinition("items")
        nested = SelectPlan(
            table=table,
            alias="inner_items",
            columns=(RawExpression(
                "inner_items.id + outer_items.id + :offset",
                {"offset": 10},
                "computed",
            ),),
            wheres=[WhereClause(
                column="inner_items.id",
                where_type=WhereType.COLUMN,
                value="outer_items.id",
            )],
        )
        plan = SelectPlan(
            table=table,
            alias="outer_items",
            columns=("id", SubQueryColumn(nested, "calculated")),
        )
        rows = await self.connection.select(plan)
        self.assertEqual(
            rows, [{"id": 1, "calculated": 12}, {"id": 2, "calculated": 14}],
        )

    async def testMixedBooleanConnectorsPreserveGrouping(self) -> None:
        """Preserve left-to-right AND/OR semantics while combining runs."""
        await self.connection.statement(
            "CREATE TABLE flags (id INTEGER, a INTEGER, b INTEGER, c INTEGER)",
        )
        for value in range(8):
            await self.connection.execute(
                "INSERT INTO flags VALUES (:id, :a, :b, :c)",
                {"id": value, "a": value & 1, "b": value & 2, "c": value & 4},
            )
        plan = SelectPlan(
            table=TableDefinition("flags"),
            columns=("id",),
            wheres=[
                WhereClause(column="a", value=1),
                WhereClause(column="b", value=2, boolean="or"),
                WhereClause(column="c", value=4, boolean="and"),
                WhereClause(column="id", value=0, boolean="or"),
            ],
        )
        rows = await self.connection.select(plan)
        self.assertEqual([row["id"] for row in rows], [0, 5, 6, 7])

    def testRawMetadataCanBecomeDeclaredMetadata(self) -> None:
        """Apply real types when a declared table follows a schemaless query."""
        compiler = SQLCompiler()
        compiler.compileSelect(SelectPlan(
            table=TableDefinition("entries"), columns=("id",),
        ))
        column = Integer().primary()
        column.name = "id"
        definition = TableDefinition("entries", {"id": column})
        ddl = str(compiler.compileCreateTable(definition))
        self.assertIn("id INTEGER NOT NULL", ddl)
        self.assertIn("PRIMARY KEY (id)", ddl)

    def testMemoryPoolUsesExclusiveCheckout(self) -> None:
        """Select single-connection queue pools for both engine variants."""
        config = {"driver": "sqlite", "database": ":memory:"}
        options = engine_options(config)
        self.assertIs(options["poolclass"], AsyncAdaptedQueuePool)
        self.assertEqual(options["pool_size"], 1)
        self.assertEqual(options["max_overflow"], 0)
        self.assertIs(engine_options(config, sync=True)["poolclass"], QueuePool)

    def testDefinitionKeysProvideUnboundColumnNames(self) -> None:
        """Use table mapping names without mutating shared column definitions."""
        column = Integer().primary()
        definition = TableDefinition("named", {"key": column})
        ddl = str(SQLCompiler().compileCreateTable(definition))
        self.assertIn("key INTEGER NOT NULL", ddl)
        self.assertEqual(column.name, "")

    def testConnectionHasNoInstanceDictionary(self) -> None:
        """Keep connection instances constrained to their declared slots."""
        self.assertFalse(hasattr(self.connection, "__dict__"))


class TestTransactionStartFailures(unittest.IsolatedAsyncioTestCase):
    """Verify acquired resources are released when a transaction cannot begin."""

    async def testBeginFailureClosesRawConnection(self) -> None:
        """Close a connection whose root transaction failed to start."""
        raw = MagicMock()
        raw.begin = AsyncMock(side_effect=SQLAlchemyError("failed"))
        raw.close = AsyncMock()
        connection = Connection("failure", {"driver": "sqlite"})
        engine = MagicMock()
        engine.connect = AsyncMock(return_value=raw)
        connection._engine = engine
        with self.assertRaises(TransactionException):
            await connection.begin()
        raw.close.assert_awaited_once()
        self.assertFalse(connection.inTransaction())

    async def testBeginCancellationClosesRawConnection(self) -> None:
        """Close a connection when cancellation interrupts transaction start."""
        raw = MagicMock()
        raw.begin = AsyncMock(side_effect=asyncio.CancelledError)
        raw.close = AsyncMock()
        connection = Connection("cancelled", {"driver": "sqlite"})
        engine = MagicMock()
        engine.connect = AsyncMock(return_value=raw)
        connection._engine = engine
        with self.assertRaises(asyncio.CancelledError):
            await connection.begin()
        raw.close.assert_awaited_once()
        self.assertFalse(connection.inTransaction())
