import sys
import tempfile
from asyncio import gather
from pathlib import Path
from types import ModuleType
from typing import ClassVar
from unittest.mock import patch
from orionis.container.container import Container
from orionis.database.connection_manager import ConnectionManager
from orionis.database.contracts.connection import IConnection  # noqa: TC001
from orionis.database.contracts.migration import Migration
from orionis.database.exceptions import (
    ConnectionNotFoundException,
    MigrationNotFoundException,
)
from orionis.database.migrations.context import current_migration_connection
from orionis.database.migrations.events import MigrationEvents
from orionis.database.migrations.migrator import Migrator
from orionis.orm.resolver import ConnectionResolver
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Integer, String
from orionis.test import TestCase

# File-backed database created per test so every connection sees the same
# schema; ``:memory:`` would give each engine its own private one, and a
# ``file:...?uri=true`` DSN is not URI-decoded by the driver, which leaves a
# stray file in the working directory.
_DATABASE_FILE: str = "migrator.sqlite"

class _StubApp:
    """Application stub exposing the paths and configuration used."""

    def __init__(self, database: str) -> None:
        """Initialize the test double.

        Parameters
        ----------
        database : str
            Value supplied for ``database``.

        Returns
        -------
        None
            Store the working directory and database path.
        """
        self.basePath = Path.cwd()
        self._database = database

        class _IsolatedContainer(Container):
            """Keep constructor bindings private to this migration test."""

        self._container = _IsolatedContainer()

    async def build(self, target: type[Migration]) -> Migration:
        """Resolve migration constructors with the application's container.

        Parameters
        ----------
        target : type of Migration
            Discovered migration class to instantiate.

        Returns
        -------
        Migration
            Fresh migration with constructor dependencies resolved.
        """
        return await self._container.build(target)

    def path(self, key: str) -> Path:  # noqa: ARG002
        """Resolve the requested application path.

        Parameters
        ----------
        key : str
            Application path key requested by the runner.

        Returns
        -------
        Path
            Database migrations directory.
        """
        return Path.cwd() / "database"

    def config(self, key: str) -> dict:  # noqa: ARG002
        """Return the requested database configuration.

        Parameters
        ----------
        key : str
            Configuration key requested by the connection manager.

        Returns
        -------
        dict
            Default connection name and SQLite connection settings.
        """
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {
                    "driver": "sqlite",
                    "database": self._database,
                    "prefix": "",
                },
                "secondary": {
                    "driver": "sqlite",
                    "database": f"{self._database}.secondary",
                    "prefix": "",
                },
            },
        }

def _definition(name: str) -> TableDefinition:
    """
    Build a one-column table definition.

    Parameters
    ----------
    name : str
        Logical table name.

    Returns
    -------
    TableDefinition
        Definition with a single primary key column.
    """
    column = Integer().primary().autoIncrement()
    column.name = "id"
    label = String()
    label.name = "label"
    return TableDefinition(
        name=name,
        columns={"id": column, "label": label},
        primary_key="id",
    )

class _CreateAlpha(Migration):
    """Migration creating and dropping the ``alpha`` table."""

    async def up(self) -> None:
        """Apply the test migration.

        Returns
        -------
        None
            Create the alpha table on the selected connection.
        """
        await ConnectionResolver.connection().createTable(_definition("alpha"))

    async def down(self) -> None:
        """Revert the test migration.

        Returns
        -------
        None
            Drop the alpha table from the selected connection.
        """
        await ConnectionResolver.connection().dropTable("alpha")

class _CreateBeta(Migration):
    """Migration creating and dropping the ``beta`` table."""

    async def up(self) -> None:
        """Apply the test migration.

        Returns
        -------
        None
            Create the beta table on the selected connection.
        """
        await ConnectionResolver.connection().createTable(_definition("beta"))

    async def down(self) -> None:
        """Revert the test migration.

        Returns
        -------
        None
            Drop the beta table from the selected connection.
        """
        await ConnectionResolver.connection().dropTable("beta")

class _Broken(Migration):
    """Migration whose ``up`` always fails."""

    async def up(self) -> None:
        """Apply the test migration.

        Returns
        -------
        None
            Raise the configured failure during migration execution.

        Raises
        ------
        RuntimeError
            Raised by this helper to exercise the failure path.
        """
        error_msg = "boom"
        raise RuntimeError(error_msg)

    async def down(self) -> None:
        """Do nothing; this migration never applies.

        Returns
        -------
        None
            Leave the database unchanged because this migration never applies.
        """

class _MigrationDependency:
    """Capture the connection and transaction active during DI resolution."""

    __slots__ = ("connection", "transaction_active")

    def __init__(self) -> None:
        """Record the active migration connection and transaction state.

        Returns
        -------
        None
            Capture the migration context available during construction.
        """
        self.connection: IConnection | None = current_migration_connection()
        self.transaction_active = (
            self.connection.inTransaction()
            if self.connection is not None
            else False
        )

class _InjectedMigration(Migration):
    """Require constructor injection for both apply and rollback."""

    observations: ClassVar[list[tuple[str, IConnection | None, bool]]] = []

    def __init__(self, dependency: _MigrationDependency) -> None:
        """Store the dependency resolved by the application container.

        Parameters
        ----------
        dependency : _MigrationDependency
            Service built inside the selected migration transaction.

        Returns
        -------
        None
            Store the dependency for the migration steps.
        """
        self._dependency = dependency

    async def up(self) -> None:
        """Create a table on the connection captured during construction.

        Returns
        -------
        None
            Record the active transaction and create the injected table.
        """
        type(self).observations.append((
            "up", self._dependency.connection,
            self._dependency.transaction_active,
        ))
        await ConnectionResolver.connection().createTable(_definition("injected"))

    async def down(self) -> None:
        """Drop the injected table with a newly resolved dependency.

        Returns
        -------
        None
            Record the active transaction and drop the injected table.
        """
        type(self).observations.append((
            "down", self._dependency.connection,
            self._dependency.transaction_active,
        ))
        await ConnectionResolver.connection().dropTable("injected")

class TestMigrator(TestCase):
    """Behaviour of the migration runner against a real sqlite database."""

    async def asyncSetUp(self) -> None:
        """Wire an isolated manager and a migrator with fixed migrations.

        Returns
        -------
        None
            Prepare the manager and runners with fixed migration mappings.
        """
        self._workspace = tempfile.TemporaryDirectory()
        app = _StubApp(str(Path(self._workspace.name) / _DATABASE_FILE))
        self._app = app
        self._manager = ConnectionManager(app)
        ConnectionResolver.setManager(self._manager)
        self._migrator = Migrator(app, self._manager)
        self.useMigrations({"m01_alpha": _CreateAlpha, "m02_beta": _CreateBeta})

    async def asyncTearDown(self) -> None:
        """Release the manager and drop the temporary database.

        Returns
        -------
        None
            Disconnect the databases and remove temporary files.
        """
        await self._manager.disconnect()
        ConnectionResolver.clear()
        self._workspace.cleanup()

    def useMigrations(self, migrations: dict) -> None:
        """
        Replace the discovered migrations with a fixed mapping.

        Parameters
        ----------
        migrations : dict
            Migration classes keyed by their tracked name.

        Returns
        -------
        None
            Replace the runner's cached migration mapping.
        """
        # Discovery is filesystem-based; seeding its cache keeps the test
        # focused on the runner instead of on module importing.
        self._migrator._Migrator__discovered_cache = migrations

    async def tableExists(self, name: str) -> bool:
        """
        Report whether a table exists in the sqlite catalog.

        Parameters
        ----------
        name : str
            Table name to look up.

        Returns
        -------
        bool
            ``True`` when the table exists.
        """
        rows = await self._manager.connection().select(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = :name",
            {"name": name},
        )
        return bool(rows)

    async def testMigrateAppliesEveryPendingMigration(self) -> None:
        """Apply pending migrations in chronological order.

        Returns
        -------
        None
            Verify both migrations run and create their tables.
        """
        applied = await self._migrator.migrate()
        self.assertEqual(applied, ["m01_alpha", "m02_beta"])
        self.assertTrue(await self.tableExists("alpha"))
        self.assertTrue(await self.tableExists("beta"))

    async def testMigrateIsIdempotent(self) -> None:
        """Skip migrations that already ran.

        Returns
        -------
        None
            Verify a repeated migration run returns no applied migrations.
        """
        await self._migrator.migrate()
        self.assertEqual(await self._migrator.migrate(), [])

    async def testMigrationsShareASingleBatch(self) -> None:
        """Record every migration of one run under the same batch.

        Returns
        -------
        None
            Verify migrations from one run share a batch number.
        """
        await self._migrator.migrate()
        rows = await self._migrator.status()
        self.assertEqual([row["batch"] for row in rows], [1, 1])

    async def testStatusReportsPendingMigrations(self) -> None:
        """Report applied and pending migrations separately.

        Returns
        -------
        None
            Verify status changes from pending to applied after migration.
        """
        rows = await self._migrator.status()
        self.assertEqual([row["ran"] for row in rows], [False, False])
        await self._migrator.migrate()
        rows = await self._migrator.status()
        self.assertEqual([row["ran"] for row in rows], [True, True])

    async def testRollbackRevertsTheLastBatchOnly(self) -> None:
        """Revert only the most recent batch.

        Returns
        -------
        None
            Verify older batches remain applied after rollback.
        """
        await self._migrator.migrate()
        self.useMigrations({
            "m01_alpha": _CreateAlpha,
            "m02_beta": _CreateBeta,
            "m03_gamma": _CreateAlpha,
        })
        # The third migration lands in its own batch.
        await self._migrator.migrate()
        reverted = await self._migrator.rollback()
        self.assertEqual(reverted, ["m03_gamma"])
        self.assertTrue(await self.tableExists("beta"))

    async def testRollbackRevertsInReverseOrder(self) -> None:
        """Revert the migrations of a batch newest first.

        Returns
        -------
        None
            Verify rollback removes the batch in reverse migration order.
        """
        await self._migrator.migrate()
        self.assertEqual(
            await self._migrator.rollback(),
            ["m02_beta", "m01_alpha"],
        )
        self.assertFalse(await self.tableExists("alpha"))

    async def testRollbackRejectsNonPositiveSteps(self) -> None:
        """Reject a non-positive step count.

        Returns
        -------
        None
            Verify zero steps raise the validation error.
        """
        with self.assertRaises(ValueError):
            await self._migrator.rollback(0)

    async def testResetRevertsEverything(self) -> None:
        """Revert every recorded migration regardless of batches.

        Returns
        -------
        None
            Verify reset reverts all migrations and clears their status.
        """
        await self._migrator.migrate()
        reverted = await self._migrator.reset()
        self.assertEqual(reverted, ["m02_beta", "m01_alpha"])
        self.assertEqual(await self._migrator.status(), [
            {"migration": "m01_alpha", "ran": False, "batch": None},
            {"migration": "m02_beta", "ran": False, "batch": None},
        ])

    async def testRefreshRollsBackAndMigratesAgain(self) -> None:
        """Rebuild the schema in a single operation.

        Returns
        -------
        None
            Verify refresh reapplies the migrations after rollback.
        """
        await self._migrator.migrate()
        applied = await self._migrator.refresh()
        self.assertEqual(applied, ["m01_alpha", "m02_beta"])
        self.assertTrue(await self.tableExists("alpha"))

    async def testFreshRestartsTheHistory(self) -> None:
        """Drop the tracking table and rebuild from the first batch.

        Returns
        -------
        None
            Verify fresh restarts migration history at batch one.
        """
        await self._migrator.migrate()
        await self._migrator.rollback()
        await self._migrator.migrate()
        await self._migrator.fresh()
        rows = await self._migrator.status()
        self.assertEqual([row["batch"] for row in rows], [1, 1])

    async def testFailedMigrationIsNotRecorded(self) -> None:
        """Leave no tracking record behind when a migration fails.

        Returns
        -------
        None
            Verify a failed migration remains unapplied in status.
        """
        self.useMigrations({"m01_alpha": _CreateAlpha, "m02_broken": _Broken})
        with self.assertRaises(RuntimeError):
            await self._migrator.migrate()
        rows = await self._migrator.status()
        self.assertEqual([row["ran"] for row in rows], [True, False])

    async def testMissingMigrationFileIsReported(self) -> None:
        """Report a recorded migration whose file disappeared.

        Returns
        -------
        None
            Verify reset raises when a recorded migration cannot be discovered.
        """
        await self._migrator.migrate()
        self.useMigrations({"m01_alpha": _CreateAlpha})
        with self.assertRaises(MigrationNotFoundException):
            await self._migrator.reset()

    async def testMissingHistoricalMigrationDoesNotPartiallyRevert(self) -> None:
        """Check the full rollback plan before changing the schema.

        Returns
        -------
        None
            Every operation leaves the schema and history intact.
        """
        await self._migrator.migrate()
        self.useMigrations({"m02_beta": _CreateBeta})

        for operation in (
            self._migrator.reset,
            self._migrator.refresh,
            self._migrator.fresh,
        ):
            with self.assertRaises(MigrationNotFoundException):
                await operation()
            self.assertTrue(await self.tableExists("alpha"))
            self.assertTrue(await self.tableExists("beta"))
            rows = await self._manager.connection().select(
                "SELECT migration FROM migrations ORDER BY id ASC",
            )
            self.assertEqual(
                [row["migration"] for row in rows],
                ["m01_alpha", "m02_beta"],
            )

    async def testDiscoveryIgnoresImportedClassesAndPackageInitializers(self) -> None:
        """Run only the migration defined by its source file.

        Returns
        -------
        None
            Imported and reexported migration classes are ignored.
        """
        module_name = "migration_fixture.m01_alpha"
        init_name = "migration_fixture.__init__"
        own_migration = type(
            "OwnMigration", (_CreateAlpha,), {"__module__": module_name},
        )
        source_module = ModuleType(module_name)
        source_module.OwnMigration = own_migration
        source_module.ImportedMigration = _CreateBeta
        init_module = ModuleType(init_name)
        init_module.OwnMigration = own_migration
        self._migrator._Migrator__discovered_cache = None

        with (
            patch.object(self._app, "path", return_value=Path.cwd()),
            patch(
                "orionis.database.migrations.migrator.ModuleInspector.discoverModules",
                return_value={module_name, init_name},
            ),
            patch.dict(
                sys.modules,
                {module_name: source_module, init_name: init_module},
            ),
        ):
            applied = await self._migrator.migrate()

        self.assertEqual(applied, ["m01_alpha"])
        self.assertTrue(await self.tableExists("alpha"))
        self.assertFalse(await self.tableExists("beta"))

    async def testDiscoveryRejectsDuplicateMigrationNames(self) -> None:
        """Reject files that would share one persisted migration name.

        Returns
        -------
        None
            The ambiguous migrations do not run.
        """
        first_name = "migration_fixture.alpha.m01_create"
        second_name = "migration_fixture.beta.m01_create"
        first_module = ModuleType(first_name)
        second_module = ModuleType(second_name)
        first_module.AlphaMigration = type(
            "AlphaMigration", (_CreateAlpha,), {"__module__": first_name},
        )
        second_module.BetaMigration = type(
            "BetaMigration", (_CreateBeta,), {"__module__": second_name},
        )
        self._migrator._Migrator__discovered_cache = None

        with (
            patch.object(self._app, "path", return_value=Path.cwd()),
            patch(
                "orionis.database.migrations.migrator.ModuleInspector.discoverModules",
                return_value={first_name, second_name},
            ),
            patch.dict(
                sys.modules,
                {first_name: first_module, second_name: second_module},
            ),
            self.assertRaisesRegex(ValueError, "Ambiguous migration 'm01_create'"),
        ):
            await self._migrator.migrate()

        self.assertFalse(await self.tableExists("alpha"))
        self.assertFalse(await self.tableExists("beta"))

    async def testProgressEventsAreReported(self) -> None:
        """Report progress for every migration through the callbacks.

        Returns
        -------
        None
            Verify callbacks receive each migration in execution order.
        """
        started: list[str] = []
        finished: list[str] = []
        await self._migrator.migrate(
            events=MigrationEvents(
                on_start=started.append,
                on_success=lambda name, _elapsed: finished.append(name),
            ),
        )
        self.assertEqual(started, ["m01_alpha", "m02_beta"])
        self.assertEqual(finished, ["m01_alpha", "m02_beta"])

    async def testUnknownConnectionIsRejected(self) -> None:
        """Reject a connection name that is not configured.

        Returns
        -------
        None
            Verify migration execution raises for an unknown connection.
        """
        with self.assertRaises(ConnectionNotFoundException):
            await self._migrator.migrate(connection="ghost")

    async def testNamedMigrationUsesItsTrackingConnection(self) -> None:
        """Apply and revert unqualified migration operations on the target.

        Returns
        -------
        None
            Verify schema changes and resolver scope stay on the named connection.
        """
        await self._migrator.migrate(connection="secondary")
        self.assertFalse(await self.tableExists("alpha"))
        target = self._manager.connection("secondary")
        rows = await target.select(
            "SELECT name FROM sqlite_master WHERE name = 'alpha'",
        )
        self.assertEqual(len(rows), 1)
        self.assertIsNone(current_migration_connection())
        self.assertIs(ConnectionResolver.connection(), self._manager.connection())
        self.assertEqual(
            await self._migrator.rollback(connection="secondary"),
            ["m02_beta", "m01_alpha"],
        )
        rows = await target.select(
            "SELECT name FROM sqlite_master WHERE name = 'alpha'",
        )
        self.assertEqual(rows, [])

    async def testConstructorInjectionSharesNamedTransactionForBothSteps(
        self,
    ) -> None:
        """Build migrations with DI inside the selected transaction.

        Returns
        -------
        None
            Verify apply and rollback resolve dependencies in the target transaction.
        """
        self._app._container.transient(None, _MigrationDependency)
        self.useMigrations({"m01_injected": _InjectedMigration})
        _InjectedMigration.observations.clear()
        target = self._manager.connection("secondary")

        self.assertEqual(
            await self._migrator.migrate(connection="secondary"),
            ["m01_injected"],
        )
        self.assertEqual(
            _InjectedMigration.observations, [("up", target, True)],
        )
        self.assertFalse(await self.tableExists("injected"))
        rows = await target.select(
            "SELECT name FROM sqlite_master WHERE name = 'injected'",
        )
        self.assertEqual(len(rows), 1)

        self.assertEqual(
            await self._migrator.rollback(connection="secondary"),
            ["m01_injected"],
        )
        self.assertEqual(_InjectedMigration.observations, [
            ("up", target, True), ("down", target, True),
        ])
        self.assertIsNone(current_migration_connection())
        rows = await target.select(
            "SELECT name FROM sqlite_master WHERE name = 'injected'",
        )
        self.assertEqual(rows, [])

    async def testConcurrentMigrationsKeepTheirConnectionsSeparate(self) -> None:
        """Isolate selected connections while two migration runs overlap.

        Returns
        -------
        None
            Verify concurrent runs create separate schemas without leaking scope.
        """
        results = await gather(
            self._migrator.migrate(),
            self._migrator.migrate(connection="secondary"),
        )
        self.assertEqual(results, [
            ["m01_alpha", "m02_beta"],
            ["m01_alpha", "m02_beta"],
        ])
        for name in (None, "secondary"):
            rows = await self._manager.connection(name).select(
                "SELECT name FROM sqlite_master WHERE name = 'alpha'",
            )
            self.assertEqual(len(rows), 1)
        self.assertIsNone(current_migration_connection())

    async def testFailedMigrationRestoresTheConnectionScope(self) -> None:
        """Restore the caller's connection after a named migration raises.

        Returns
        -------
        None
            Verify the previous connection scope is restored after failure.
        """
        self.useMigrations({"m01_broken": _Broken})
        with self.assertRaises(RuntimeError):
            await self._migrator.migrate(connection="secondary")
        self.assertIsNone(current_migration_connection())
        self.assertIs(ConnectionResolver.connection(), self._manager.connection())
