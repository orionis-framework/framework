from typing import TYPE_CHECKING
from orionis.database.exceptions import ConnectionNotFoundException
from orionis.database.migrations.context import migration_connection_scope
from orionis.database.transaction import Transaction
from orionis.orm.query_builder import QueryBuilder
from orionis.test import TestCase

if TYPE_CHECKING:
    from orionis.database.contracts.transaction import ITransaction

class _RecordingConnection:
    """Record gateway calls without replacing framework methods."""

    __slots__ = ("calls", "name")

    def __init__(self, name: str) -> None:
        """Initialize the named connection and its observations.

        Parameters
        ----------
        name : str
            Connection name reported in SELECT results.

        Returns
        -------
        None
            Initialize an independent call log.
        """
        self.name = name
        self.calls: list[tuple[object, ...]] = []

    async def select(
        self,
        sql: str,
        bindings: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        """Record a SELECT statement and return the connection identity.

        Parameters
        ----------
        sql : str
            Statement received from the gateway.
        bindings : dict of str to object or None, optional
            Original bound values received from the gateway.

        Returns
        -------
        list of dict
            One row identifying this connection.
        """
        self.calls.append(("select", sql, bindings))
        return [{"connection": self.name}]

    async def execute(
        self,
        sql: str,
        bindings: dict[str, object] | None = None,
    ) -> int:
        """Record a modifying statement and return its affected row count.

        Parameters
        ----------
        sql : str
            Statement received from the gateway.
        bindings : dict of str to object or None, optional
            Original bound values received from the gateway.

        Returns
        -------
        int
            Two affected rows.
        """
        self.calls.append(("execute", sql, bindings))
        return 2

    async def statement(
        self,
        sql: str,
        bindings: dict[str, object] | None = None,
    ) -> bool:
        """Record a statement executed without inspecting rows.

        Parameters
        ----------
        sql : str
            Statement received from the gateway.
        bindings : dict of str to object or None, optional
            Original bound values received from the gateway.

        Returns
        -------
        bool
            Confirm successful execution.
        """
        self.calls.append(("statement", sql, bindings))
        return True

    async def begin(self) -> None:
        """Record the start of a transaction.

        Returns
        -------
        None
            Append a transaction-start observation.
        """
        self.calls.append(("begin",))

    async def commit(self) -> None:
        """Record a transaction commit.

        Returns
        -------
        None
            Append a transaction-commit observation.
        """
        self.calls.append(("commit",))

    async def rollback(self) -> None:
        """Record a transaction rollback.

        Returns
        -------
        None
            Append a transaction-rollback observation.
        """
        self.calls.append(("rollback",))

    def transaction(self) -> ITransaction:
        """Build the framework's transaction context over this connection.

        Returns
        -------
        ITransaction
            Context committing or rolling back according to its outcome.
        """
        return Transaction(self)  # type: ignore[arg-type]

class _RecordingManager:
    """Resolve named connections and record the requested connection names."""

    __slots__ = ("connections", "default_name", "requests")

    def __init__(self) -> None:
        """Prepare two independent connections with SQLite as the default.

        Returns
        -------
        None
            Initialize named connection state and resolution observations.
        """
        self.default_name = "sqlite"
        self.connections = {
            name: _RecordingConnection(name) for name in ("sqlite", "reporting")
        }
        self.requests: list[str | None] = []

    def connection(self, name: str | None = None) -> _RecordingConnection:
        """Resolve a requested name or the current default connection.

        Parameters
        ----------
        name : str or None, optional
            Explicit name, or None to use the default.

        Returns
        -------
        _RecordingConnection
            Selected named connection.

        Raises
        ------
        ConnectionNotFoundException
            If the requested name is undeclared.
        """
        self.requests.append(name)
        target = name or self.default_name
        if target not in self.connections:
            error_msg = f"Unknown connection: {target}."
            raise ConnectionNotFoundException(error_msg)
        return self.connections[target]

    def getDefaultName(self) -> str:
        """Return the active default connection name.

        Returns
        -------
        str
            Current default connection name.
        """
        return self.default_name

    def setDefaultName(self, name: str) -> None:
        """Change the default to an existing named connection.

        Parameters
        ----------
        name : str
            Declared connection to select.

        Returns
        -------
        None
            Update the manager's default connection.

        Raises
        ------
        ConnectionNotFoundException
            If the requested connection is undeclared.
        """
        self.connection(name)
        self.default_name = name

class TestQueryBuilder(TestCase):
    """Verify gateway isolation, delegation, and connection precedence."""

    def setUp(self) -> None:
        """Create an independent gateway and recording manager.

        Returns
        -------
        None
            Initialize state owned exclusively by the current test.
        """
        self.manager = _RecordingManager()
        self.gateway = QueryBuilder(self.manager)  # type: ignore[arg-type]

    def testTableReturnsIndependentBuilders(self) -> None:
        """Keep table and predicate state independent between calls.

        Returns
        -------
        None
            Verify building a second query never retargets the first.
        """
        first = self.gateway.table("users", alias="u").where("id", 1)
        second = self.gateway.table("posts")
        self.assertIsNot(first, second)
        self.assertIsNot(first.toPlan(), second.toPlan())
        self.assertEqual(first.toPlan().table.name, "users")
        self.assertEqual(first.toPlan().alias, "u")
        self.assertEqual(second.toPlan().wheres, [])

    def testConnectionReturnsScopedGatewayWithoutMutating(self) -> None:
        """Select a connection without changing the shared gateway.

        Returns
        -------
        None
            Verify default, scoped, and explicit table connection precedence.
        """
        scoped = self.gateway.connection("reporting")
        self.assertIsNot(scoped, self.gateway)
        self.assertIsNone(self.gateway.table("users")._connection_name)
        self.assertEqual(scoped.table("users")._connection_name, "reporting")
        explicit = scoped.table("users", connection="sqlite")
        self.assertEqual(explicit._connection_name, "sqlite")
        self.assertIsNone(scoped.connection().table("users")._connection_name)

    def testDefaultConnectionChangesAreDelegated(self) -> None:
        """Read and update the default connection through the manager.

        Returns
        -------
        None
            Verify the gateway exposes manager state and preserves its errors.
        """
        self.assertEqual(self.gateway.getDefaultName(), "sqlite")
        self.gateway.setDefaultName("reporting")
        self.assertEqual(self.gateway.getDefaultName(), "reporting")
        with self.assertRaises(ConnectionNotFoundException):
            self.gateway.setDefaultName("missing")
        self.assertEqual(self.gateway.getDefaultName(), "reporting")

    async def testSqlOperationsPreserveArgumentsAndResults(self) -> None:
        """Delegate SQL and original bindings to the selected connection.

        Returns
        -------
        None
            Verify all three SQL entry points preserve results and arguments.
        """
        sql = "SELECT :value"
        bindings = {"value": 7}
        scoped = self.gateway.connection("reporting")
        self.assertEqual(
            await scoped.select(sql, bindings),
            [{"connection": "reporting"}],
        )
        self.assertEqual(await scoped.execute(sql, bindings), 2)
        self.assertTrue(await scoped.statement(sql, bindings))
        calls = self.manager.connections["reporting"].calls
        self.assertEqual(
            [call[0] for call in calls],
            ["select", "execute", "statement"],
        )
        for call in calls:
            self.assertEqual(call[1], sql)
            self.assertIs(call[2], bindings)

    async def testExplicitConnectionOverridesGatewayScope(self) -> None:
        """Resolve explicit SQL connection names before the gateway scope.

        Returns
        -------
        None
            Verify explicit names reach the manager and unknown names propagate.
        """
        scoped = self.gateway.connection("reporting")
        self.assertEqual(
            await scoped.select("SELECT 1", name="sqlite"),
            [{"connection": "sqlite"}],
        )
        with self.assertRaises(ConnectionNotFoundException):
            await scoped.select("SELECT 1", name="missing")

    async def testMigrationConnectionAppliesOnlyToUnqualifiedCalls(self) -> None:
        """Use the migration connection only when no name is selected.

        Returns
        -------
        None
            Verify ambient migration state never overrides explicit scopes.
        """
        migration = self.manager.connections["reporting"]
        with migration_connection_scope(migration):  # type: ignore[arg-type]
            self.assertEqual(
                await self.gateway.select("SELECT 1"),
                [{"connection": "reporting"}],
            )
            self.assertEqual(
                await self.gateway.connection("sqlite").select("SELECT 1"),
                [{"connection": "sqlite"}],
            )
        self.assertEqual(
            await self.gateway.select("SELECT 1"),
            [{"connection": "sqlite"}],
        )

    async def testTransactionCommandsUseTheSelectedConnection(self) -> None:
        """Forward transaction commands to the scoped or explicit connection.

        Returns
        -------
        None
            Verify begin, commit, and rollback preserve connection precedence.
        """
        scoped = self.gateway.connection("reporting")
        await scoped.beginTransaction()
        await scoped.commit()
        await scoped.rollback(name="sqlite")
        self.assertEqual(
            self.manager.connections["reporting"].calls,
            [("begin",), ("commit",)],
        )
        self.assertEqual(self.manager.connections["sqlite"].calls, [("rollback",)])

    async def testTransactionContextCommitsAndRollsBack(self) -> None:
        """Return a context that commits success and rolls back failures.

        Returns
        -------
        None
            Verify the gateway uses the framework transaction implementation.
        """
        async with self.gateway.transaction("reporting"):
            await self.gateway.select("SELECT 1", name="reporting")
        connection = self.manager.connections["reporting"]
        self.assertEqual(connection.calls[0], ("begin",))
        self.assertEqual(connection.calls[-1], ("commit",))
        with self.assertRaises(ValueError):
            async with self.gateway.transaction("reporting"):
                error_msg = "Abort the transaction."
                raise ValueError(error_msg)
        self.assertEqual(connection.calls[-2:], [("begin",), ("rollback",)])
