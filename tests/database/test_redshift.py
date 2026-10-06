import asyncio
import os
import subprocess
import sys
import threading
from contextvars import ContextVar
from dataclasses import FrozenInstanceError
from importlib.util import find_spec
from pathlib import Path
from tempfile import TemporaryDirectory
from sqlalchemy import create_engine, event, text
from config.database import BootstrapDatabase
from orionis.database.compiler import SQLCompiler
from orionis.database.connection import Connection
from orionis.database.dialect import build_engine_url, engine_options
from orionis.database.exceptions import QueryException, TransactionException
from orionis.database.threaded.engine import ThreadedEngine
from orionis.foundation.config.database import (
    ConnectionName,
    Connections,
    Database,
    Redshift,
    RedshiftSSLMode,
)
from orionis.orm.query.expressions import DeletePlan, InsertPlan, SelectPlan, UpdatePlan
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, Integer, String
from orionis.test import TestCase
from tests.foundation.config.test_environment import ConfigurationTestCase

class TestRedshiftConfiguration(ConfigurationTestCase):
    """Verify lazy Redshift configuration without optional driver imports."""

    def testDefaultsUseTheOfficialConnectorTlsPolicy(self) -> None:
        """Keep a secure TLS policy and the native Redshift port.

        Returns
        -------
        None
            Defaults serialize into connector-compatible scalar values.
        """
        settings = Redshift().toDict()
        self.assertEqual(settings["driver"], "redshift")
        self.assertEqual(settings["port"], 5439)
        self.assertEqual(settings["database"], "dev")
        self.assertTrue(settings["ssl"])
        self.assertEqual(settings["sslmode"], "verify-full")
        self.assertEqual(settings["timeout"], 30)
        self.assertFalse(settings["iam"])
        self.assertFalse(settings["is_serverless"])

    def testBothConfigurationLayersReadCurrentEnvironment(self) -> None:
        """Read the shared endpoint and Redshift-specific authentication options.

        Returns
        -------
        None
            Core and application settings retain independent snapshots.
        """
        self.environment.values.update(
            DB_CONNECTION=ConnectionName.REDSHIFT,
            DB_HOST="warehouse.example.com",
            DB_PORT=5439,
            DB_DATABASE="analytics",
            DB_REDSHIFT_IAM=True,
            DB_REDSHIFT_REGION="us-east-1",
            DB_REDSHIFT_CLUSTER_IDENTIFIER="warehouse",
            DB_REDSHIFT_DB_USER="analyst",
            DB_REDSHIFT_PROFILE="development",
        )
        for config_type in (Database, BootstrapDatabase):
            config = config_type()
            self.assertEqual(config.default, "redshift")
            settings = config.connections.redshift
            self.assertEqual(settings.host, "warehouse.example.com")
            self.assertEqual(settings.database, "analytics")
            self.assertTrue(settings.iam)
            self.assertEqual(settings.region, "us-east-1")
            self.assertEqual(settings.cluster_identifier, "warehouse")
            self.assertEqual(settings.db_user, "analyst")
            self.assertEqual(settings.profile, "development")
        before = Redshift()
        self.environment.values["DB_REDSHIFT_REGION"] = "eu-west-1"
        self.assertEqual(before.region, "us-east-1")
        self.assertEqual(Redshift().region, "eu-west-1")

    def testPostgresqlSslModeDoesNotInvalidateRedshiftDefaults(self) -> None:
        """Keep libpq's SSL policy separate from the AWS connector policy.

        Returns
        -------
        None
            PostgreSQL prefer mode never leaks into Redshift settings.
        """
        self.environment.values.update(DB_CONNECTION="pgsql", DB_SSLMODE="prefer")
        for config_type in (Database, BootstrapDatabase):
            config = config_type()
            self.assertEqual(config.connections.pgsql.sslmode, "prefer")
            self.assertEqual(config.connections.redshift.sslmode, "verify-full")

    def testNamedDefaultAndDictionaryConnectionNormalize(self) -> None:
        """Normalize the new built-in name and its dictionary configuration.

        Returns
        -------
        None
            Dictionaries become validated Redshift entities.
        """
        config = Database(
            default=" REDSHIFT ",
            connections={"redshift": {"port": "5439", "sslmode": " VERIFY_CA "}},
        )
        self.assertEqual(config.default, "redshift")
        self.assertIsInstance(config.connections.redshift, Redshift)
        self.assertEqual(config.connections.redshift.sslmode, "verify-ca")
        self.assertEqual(RedshiftSSLMode.VERIFY_FULL.value, "verify-full")

    def testServerlessSettingsRemainConnectorFields(self) -> None:
        """Preserve IAM Serverless options and nullable endpoint credentials.

        Returns
        -------
        None
            No URLs or AWS clients are constructed by the entity.
        """
        settings = Redshift(
            host=None, username=None, password=None, iam=True,
            is_serverless=True, serverless_work_group="analytics",
            serverless_acct_id="123456789012", timeout=None,
        ).toDict()
        self.assertIsNone(settings["host"])
        self.assertIsNone(settings["timeout"])
        self.assertTrue(settings["is_serverless"])
        self.assertEqual(settings["serverless_work_group"], "analytics")
        self.assertEqual(settings["serverless_acct_id"], "123456789012")

    def testInvalidSettingsFailBeforeNetworkAccess(self) -> None:
        """Reject values the connector cannot safely interpret.

        Returns
        -------
        None
            Each invalid scalar produces an explicit validation exception.
        """
        for options in (
            {"driver": "pgsql"}, {"port": 0}, {"port": 65536}, {"port": True},
            {"port": "invalid"}, {"database": ""}, {"username": 10},
            {"ssl": "true"}, {"sslmode": "prefer"}, {"iam": 1},
            {"timeout": 0}, {"timeout": True}, {"region": ""},
            {"is_serverless": "false"},
        ):
            with self.subTest(options=options), self.assertRaises(
                (TypeError, ValueError),
            ):
                Redshift(**options)
        with self.assertRaises(TypeError):
            Connections(redshift=object())

    def testConfigurationIsFrozen(self) -> None:
        """Keep Redshift settings immutable after validation.

        Returns
        -------
        None
            Mutation is rejected by the existing configuration contract.
        """
        settings = Redshift()
        with self.assertRaises(FrozenInstanceError):
            settings.port = 5432

class TestRedshiftDialect(TestCase):
    """Compile real connector statements without reaching an AWS endpoint."""

    def setUp(self) -> None:
        """Skip only the optional driver checks when the extra is not installed.

        Returns
        -------
        None
            Configuration and thread-adapter tests remain independently available.
        """
        if any(
            find_spec(package) is None
            for package in ("redshift_connector", "sqlalchemy_redshift")
        ):
            self.skipTest("Install orionis[redshift] to inspect the official driver.")

    def testSyncEngineUsesTheOfficialConnectorWithoutOpeningSockets(self) -> None:
        """Build the actual dialect with no implicit network or PostgreSQL fallback.

        Returns
        -------
        None
            The registered DBAPI is the AWS connector and RETURNING is disabled.
        """
        import redshift_connector
        settings = {"driver": "redshift", "host": "warehouse.example.com"}
        engine = create_engine(
            build_engine_url(settings, sync=True),
            **engine_options(settings, sync=True),
        )
        try:
            self.assertIs(engine.dialect.dbapi, redshift_connector)
            self.assertEqual(engine.dialect.name, "redshift")
            self.assertFalse(engine.dialect.is_async)
            self.assertFalse(engine.dialect.insert_returning)
            self.assertFalse(engine.dialect.update_returning)
            self.assertFalse(engine.dialect.delete_returning)
            self.assertEqual(engine.pool.checkedout(), 0)
        finally:
            engine.dispose()

    async def testAsyncConnectionUsesALazyThreadedOfficialEngine(self) -> None:
        """Keep the asynchronous API while using the real blocking AWS DBAPI.

        Returns
        -------
        None
            First engine construction neither opens sockets nor checks out handles.
        """
        import redshift_connector
        connection = Connection(
            "warehouse", {"driver": "redshift", "host": "warehouse.example.com"},
        )
        self.assertIsNone(connection._engine)
        try:
            engine = connection._getEngine()
            self.assertIsInstance(engine, ThreadedEngine)
            self.assertIs(engine.sync_engine.dialect.dbapi, redshift_connector)
            self.assertEqual(engine.sync_engine.pool.checkedout(), 0)
        finally:
            await connection.disconnect()

    def testIdentityDdlAndInsertDoNotUsePostgresqlSequences(self) -> None:
        """Generate native IDENTITY and omit unavailable sequence and RETURNING SQL.

        Returns
        -------
        None
            Auto-generated columns remain server-owned during an insert.
        """
        settings = {"driver": "redshift"}
        engine = create_engine(build_engine_url(settings), **engine_options(settings))
        try:
            table = TableDefinition(
                name="items", primary_key="id",
                columns={
                    "id": BigInteger().primary().autoIncrement(), "name": String(),
                },
            )
            compiler = SQLCompiler(driver="redshift")
            ddl = str(compiler.compileCreateTable(table).compile(
                dialect=engine.dialect,
            ))
            self.assertIn("BIGINT IDENTITY(1,1)", ddl)
            self.assertNotIn("SERIAL", ddl)
            insert = compiler.compileInsert(InsertPlan(
                table=table, values=[{"name": "alpha"}],
            )).compile(dialect=engine.dialect)
            self.assertNotIn("RETURNING", str(insert))
            self.assertNotIn("nextval", str(insert))
            self.assertNotIn("id", insert.params)
        finally:
            engine.dispose()

class _BlockingQuery:
    """Pause real DBAPI work until the asynchronous test releases it."""

    __slots__ = ("entered", "fail", "release")

    def __init__(self, *, fail: bool = False) -> None:
        """Prepare independent start and release notifications.

        Parameters
        ----------
        fail : bool, optional
            Raise after release to exercise exception collection during cancellation.

        Returns
        -------
        None
            Initialize a deterministic blocking query gate.
        """
        self.entered = threading.Event()
        self.release = threading.Event()
        self.fail = fail

    def wait(self) -> int:
        """Block the worker and return or fail only after an explicit release.

        Returns
        -------
        int
            Fixed query value after release.

        Raises
        ------
        TimeoutError
            If the test fails to release the worker within its safety deadline.
        RuntimeError
            If this gate represents a failing driver operation.
        """
        self.entered.set()
        if not self.release.wait(5):
            message = "The test did not release its blocking query."
            raise TimeoutError(message)
        if self.fail:
            message = "The blocked query failed."
            raise RuntimeError(message)
        return 7

class TestThreadedRedshiftConnection(TestCase):
    """Exercise the async adapter with real SQLite Core I/O instead of AWS services."""

    async def asyncSetUp(self) -> None:
        """Create an isolated blocking engine and run schema work through the adapter.

        Returns
        -------
        None
            Each test owns its database file, checkouts and worker threads.
        """
        self._directory = TemporaryDirectory()
        self._engine = ThreadedEngine(create_engine(
            "sqlite:///" + (Path(self._directory.name) / "warehouse.sqlite").as_posix(),
            connect_args={"check_same_thread": False},
        ), "warehouse")
        self._connection = Connection("warehouse", {"driver": "redshift"})
        self._connection._engine = self._engine
        self._table = TableDefinition(
            name="items", primary_key="id",
            columns={"id": Integer().primary(), "name": String()},
        )
        await self._connection.createTable(self._table)

    async def asyncTearDown(self) -> None:
        """Dispose the pool before deleting the test-owned database.

        Returns
        -------
        None
            No driver handles or adapter threads retain the temporary database.
        """
        await self._connection.disconnect()
        self._directory.cleanup()

    async def testCoreCrudAndBatchResultsUseTheSameConnectionApi(self) -> None:
        """Run compiled plans, batch bindings and scalar reads through blocking Core.

        Returns
        -------
        None
            Row counts, generated-key metadata and dictionaries match the native API.
        """
        inserted = await self._connection.insert(InsertPlan(
            table=self._table, values=[{"name": "first"}],
        ))
        self.assertEqual(inserted.last_insert_id, 1)
        self.assertEqual(inserted.row_count, 1)
        batch = await self._connection.insert(InsertPlan(
            table=self._table, values=[{"name": "second"}, {"name": "third"}],
        ))
        self.assertEqual(batch.row_count, 2)
        self.assertIsNone(batch.last_insert_id)
        rows = await self._connection.select(SelectPlan(table=self._table))
        self.assertEqual([row["name"] for row in rows], ["first", "second", "third"])
        self.assertEqual(await self._connection.scalar(SelectPlan(
            table=self._table, columns=("name",),
        )), "first")
        self.assertEqual(await self._connection.update(UpdatePlan(
            table=self._table, values={"name": "updated"},
        )), 3)
        deleted = await self._connection.delete(DeletePlan(table=self._table))
        self.assertEqual(deleted, 3)
        self.assertIsNone(await self._connection.scalar(SelectPlan(table=self._table)))

    async def testRawBindingsAndSanitizedErrorsSurviveThreadExecution(self) -> None:
        """Retain named bindings and exclude driver payloads from query failures.

        Returns
        -------
        None
            Blocking Core does not expose raw driver exceptions or credentials.
        """
        self.assertTrue(await self._connection.statement(
            "INSERT INTO items (name) VALUES (:name)", {"name": "bound"},
        ))
        self.assertEqual(await self._connection.select(
            "SELECT name FROM items WHERE name = :value", {"value": "bound"},
        ), [{"name": "bound"}])
        self.assertEqual(await self._connection.execute(
            "UPDATE items SET name = :name", {"name": "changed"},
        ), 1)
        credential = "private-bound-value"
        with self.assertRaises(QueryException) as caught:
            await self._connection.execute(
                "INSERT INTO missing_table (name) VALUES (:name)",
                {"name": credential},
            )
        self.assertNotIn(credential, str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)

    async def testRootTransactionsCommitAndRollBackOnTheirReservedWorker(self) -> None:
        """Persist successful work and discard a failed root transaction.

        Returns
        -------
        None
            Transaction state and pool ownership settle after either outcome.
        """
        async with self._connection.transaction():
            self.assertTrue(self._connection.inTransaction())
            await self._connection.execute(
                "INSERT INTO items (name) VALUES (:name)", {"name": "kept"},
            )
        with self.assertRaises(RuntimeError):
            async with self._connection.transaction():
                await self._connection.execute(
                    "INSERT INTO items (name) VALUES (:name)", {"name": "discarded"},
                )
                message = "Roll back this transaction."
                raise RuntimeError(message)
        self.assertFalse(self._connection.inTransaction())
        self.assertEqual(await self._connection.select("SELECT name FROM items"), [
            {"name": "kept"},
        ])
        self.assertEqual(self._engine.sync_engine.pool.checkedout(), 0)

    async def testNestedTransactionsFailWithoutLosingTheOuterTransaction(self) -> None:
        """Reject Redshift savepoints explicitly before sending unsupported SQL.

        Returns
        -------
        None
            The outer transaction remains usable and commits normally.
        """
        async with self._connection.transaction():
            with self.assertRaisesRegex(TransactionException, "nested transactions"):
                await self._connection.begin()
            self.assertTrue(self._connection.inTransaction())
            await self._connection.execute(
                "INSERT INTO items (name) VALUES (:name)", {"name": "outer"},
            )
        self.assertEqual(await self._connection.select("SELECT name FROM items"), [
            {"name": "outer"},
        ])

    async def testCheckoutKeepsItsThreadAndResultsOutliveTheCursor(self) -> None:
        """Keep worker affinity through a checkout and materialize rows before close.

        Returns
        -------
        None
            Results remain readable after the cursor and its worker are closed.
        """
        raw = await self._engine.connect()
        try:
            first = await raw.runSync(lambda _connection: threading.get_ident())
            second = await raw.runSync(lambda _connection: threading.get_ident())
            self.assertEqual(first, second)
            self.assertNotEqual(first, threading.get_ident())
            result = await raw.execute(text("SELECT :value AS value"), {"value": "row"})
        finally:
            await raw.close()
        self.assertEqual([dict(row) for row in result.mappings()], [{"value": "row"}])
        self.assertNotIn(first, {thread.ident for thread in threading.enumerate()})

    async def testCheckoutPropagatesTheAsyncContext(self) -> None:
        """Preserve caller context for defaults and Core callbacks on the worker.

        Returns
        -------
        None
            A context-local value is visible without mutating the caller's context.
        """
        marker = ContextVar("orionis_threaded_test_marker", default="missing")
        context = marker.set("request-value")
        raw = await self._engine.connect()
        try:
            value = await raw.runSync(lambda _raw: marker.get())
            self.assertEqual(value, "request-value")
        finally:
            await raw.close()
            marker.reset(context)

    async def testParallelQueriesOwnIndependentCheckouts(self) -> None:
        """Allow concurrent callers without sharing transaction or worker state.

        Returns
        -------
        None
            Every query returns its own bindings and all checkouts return to the pool.
        """
        rows = await asyncio.gather(*(
            self._connection.select("SELECT :value AS value", {"value": value})
            for value in range(12)
        ))
        self.assertEqual(rows, [[{"value": value}] for value in range(12)])
        self.assertEqual(self._engine.sync_engine.pool.checkedout(), 0)

    async def testCancellationDrainsQueriesWithoutUnhandledWorkerFailures(self) -> None:
        """Keep the loop responsive and collect failures after repeated cancellation.

        Returns
        -------
        None
            Cancelled work completes before cleanup with no lost future exceptions.
        """
        loop = asyncio.get_running_loop()
        original_handler = loop.get_exception_handler()
        errors = []
        loop.set_exception_handler(lambda _loop, context: errors.append(context))
        try:
            for fail in (False, True):
                gate = _BlockingQuery(fail=fail)
                raw = await self._engine.connect()
                try:
                    await raw.runSync(lambda connection, callback=gate.wait: (
                        connection.connection.driver_connection.create_function(
                            "wait_for_release", 0, callback,
                        )
                    ))
                    task = asyncio.create_task(raw.execute(
                        text("SELECT wait_for_release() AS value"),
                    ))
                    self.assertTrue(await asyncio.to_thread(gate.entered.wait, 2))
                    self.assertFalse(task.done())
                    task.cancel()
                    await asyncio.sleep(0)
                    self.assertFalse(task.done())
                    task.cancel()
                    gate.release.set()
                    with self.assertRaises(asyncio.CancelledError):
                        await task
                finally:
                    gate.release.set()
                    await raw.close()
            await asyncio.sleep(0)
            self.assertEqual(errors, [])
            self.assertEqual(self._engine.sync_engine.pool.checkedout(), 0)
        finally:
            loop.set_exception_handler(original_handler)

    async def testCancelledOpeningReturnsItsLateCheckoutToThePool(self) -> None:
        """Clean up a blocking connection that finishes opening after cancellation.

        Returns
        -------
        None
            The caller waits for opening to settle and no checkout leaks.
        """
        await self._engine.dispose()
        gate = _BlockingQuery()
        event.listen(
            self._engine.sync_engine, "connect", lambda _dbapi, _record: gate.wait(),
        )
        task = asyncio.create_task(self._engine.connect())
        try:
            self.assertTrue(await asyncio.to_thread(gate.entered.wait, 2))
            task.cancel()
            await asyncio.sleep(0)
            self.assertFalse(task.done())
        finally:
            gate.release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self._engine.sync_engine.pool.checkedout(), 0)

    async def testSchemaDropAndRepeatedDisconnectReleaseTheBlockingPool(self) -> None:
        """Run schema helpers and allow repeated disconnects without live resources.

        Returns
        -------
        None
            DDL and lifecycle operations use the same worker cleanup path.
        """
        self.assertTrue(await self._connection.dropTable("items"))
        with self.assertRaises(QueryException):
            await self._connection.select("SELECT * FROM items")
        await self._connection.disconnect()
        await self._connection.disconnect()

class TestRedshiftOptionalDependencies(TestCase):
    """Keep ordinary framework imports independent of the optional AWS packages."""

    def testMissingExtraFailsOnlyWhenTheRedshiftEngineIsRequested(self) -> None:
        """Reject missing dialect or driver lazily with the official extra hint.

        Returns
        -------
        None
            Fresh interpreters prove both optional-package failures remain isolated.
        """
        root = Path(__file__).resolve().parents[2]
        script = """import asyncio
import importlib.abc
import sys

class BlockPackage(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] == sys.argv[1]:
            raise ModuleNotFoundError('Optional package unavailable', name=fullname)
        return None

sys.meta_path.insert(0, BlockPackage())
from orionis.database.connection import Connection
from orionis.database.exceptions import MissingDatabaseDependencyException
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Integer

sqlite = Connection('default', {'driver': 'sqlite', 'database': ':memory:'})
assert sqlite._engine is None
assert sys.argv[1] not in sys.modules
redshift = Connection('warehouse', {'driver': 'redshift'})
assert redshift._engine is None
try:
    redshift._getEngine()
except MissingDatabaseDependencyException as error:
    assert "uv add 'orionis[redshift]'" in str(error)
else:
    raise AssertionError('The missing optional dependency was not reported')

async def check_schema():
    table = TableDefinition(
        name='items', columns={'id': Integer().primary().autoIncrement()},
    )
    try:
        await redshift.createTable(table)
    except MissingDatabaseDependencyException as error:
        assert "uv add 'orionis[redshift]'" in str(error)
    else:
        raise AssertionError('Schema creation did not report the optional extra')
    finally:
        await redshift.disconnect()

asyncio.run(check_schema())
print('Optional dependency isolation passed')
"""
        for package in ("sqlalchemy_redshift", "redshift_connector"):
            with self.subTest(package=package), TemporaryDirectory() as directory:
                result = subprocess.run(  # noqa: S603
                    [sys.executable, "-B", "-c", script, package],
                    cwd=directory, env={**os.environ, "PYTHONPATH": str(root)},
                    capture_output=True, text=True, encoding="utf-8",
                    timeout=30, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("Optional dependency isolation passed", result.stdout)



