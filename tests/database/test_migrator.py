from __future__ import annotations
import tempfile
from pathlib import Path
from orionis.database.connection_manager import ConnectionManager
from orionis.database.contracts.migration import Migration
from orionis.database.exceptions import (
    ConnectionNotFoundException,
    MigrationNotFoundException,
)
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
        self.basePath = Path.cwd()
        self._database = database

    def path(self, key: str) -> Path:  # noqa: ARG002
        return Path.cwd() / "database"

    def config(self, key: str) -> dict:  # noqa: ARG002
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {
                    "driver": "sqlite",
                    "database": self._database,
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
        await ConnectionResolver.connection().createTable(_definition("alpha"))

    async def down(self) -> None:
        await ConnectionResolver.connection().dropTable("alpha")


class _CreateBeta(Migration):
    """Migration creating and dropping the ``beta`` table."""

    async def up(self) -> None:
        await ConnectionResolver.connection().createTable(_definition("beta"))

    async def down(self) -> None:
        await ConnectionResolver.connection().dropTable("beta")


class _Broken(Migration):
    """Migration whose ``up`` always fails."""

    async def up(self) -> None:
        error_msg = "boom"
        raise RuntimeError(error_msg)

    async def down(self) -> None:
        """Do nothing; this migration never applies."""


class TestMigrator(TestCase):
    """Behaviour of the migration runner against a real sqlite database."""

    async def asyncSetUp(self) -> None:
        """Wire an isolated manager and a migrator with fixed migrations."""
        self._workspace = tempfile.TemporaryDirectory()
        app = _StubApp(str(Path(self._workspace.name) / _DATABASE_FILE))
        self._manager = ConnectionManager(app)
        ConnectionResolver.setManager(self._manager)
        self._migrator = Migrator(app, self._manager)
        self.useMigrations({"m01_alpha": _CreateAlpha, "m02_beta": _CreateBeta})

    async def asyncTearDown(self) -> None:
        """Release the manager and drop the temporary database."""
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
            This method does not return a value.
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
        """
        Apply pending migrations in chronological order.

        Validates the happy path of the runner.
        """
        applied = await self._migrator.migrate()
        self.assertEqual(applied, ["m01_alpha", "m02_beta"])
        self.assertTrue(await self.tableExists("alpha"))
        self.assertTrue(await self.tableExists("beta"))

    async def testMigrateIsIdempotent(self) -> None:
        """
        Skip migrations that already ran.

        Validates that a second run is a no-op.
        """
        await self._migrator.migrate()
        self.assertEqual(await self._migrator.migrate(), [])

    async def testMigrationsShareASingleBatch(self) -> None:
        """
        Record every migration of one run under the same batch.

        Validates the batch numbering used by rollbacks.
        """
        await self._migrator.migrate()
        rows = await self._migrator.status()
        self.assertEqual([row["batch"] for row in rows], [1, 1])

    async def testStatusReportsPendingMigrations(self) -> None:
        """
        Report applied and pending migrations separately.

        Validates the status projection.
        """
        rows = await self._migrator.status()
        self.assertEqual([row["ran"] for row in rows], [False, False])
        await self._migrator.migrate()
        rows = await self._migrator.status()
        self.assertEqual([row["ran"] for row in rows], [True, True])

    async def testRollbackRevertsTheLastBatchOnly(self) -> None:
        """
        Revert only the most recent batch.

        Validates batch-scoped rollbacks.
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
        """
        Revert the migrations of a batch newest first.

        Validates the ordering guarantee of a rollback.
        """
        await self._migrator.migrate()
        self.assertEqual(
            await self._migrator.rollback(),
            ["m02_beta", "m01_alpha"],
        )
        self.assertFalse(await self.tableExists("alpha"))

    async def testRollbackRejectsNonPositiveSteps(self) -> None:
        """
        Reject a non-positive step count.

        Validates the argument guard.
        """
        with self.assertRaises(ValueError):
            await self._migrator.rollback(0)

    async def testResetRevertsEverything(self) -> None:
        """
        Revert every recorded migration regardless of batches.

        Validates ``reset``.
        """
        await self._migrator.migrate()
        reverted = await self._migrator.reset()
        self.assertEqual(reverted, ["m02_beta", "m01_alpha"])
        self.assertEqual(await self._migrator.status(), [
            {"migration": "m01_alpha", "ran": False, "batch": None},
            {"migration": "m02_beta", "ran": False, "batch": None},
        ])

    async def testRefreshRollsBackAndMigratesAgain(self) -> None:
        """
        Rebuild the schema in a single operation.

        Validates ``refresh``.
        """
        await self._migrator.migrate()
        applied = await self._migrator.refresh()
        self.assertEqual(applied, ["m01_alpha", "m02_beta"])
        self.assertTrue(await self.tableExists("alpha"))

    async def testFreshRestartsTheHistory(self) -> None:
        """
        Drop the tracking table and rebuild from the first batch.

        Validates ``fresh``.
        """
        await self._migrator.migrate()
        await self._migrator.rollback()
        await self._migrator.migrate()
        await self._migrator.fresh()
        rows = await self._migrator.status()
        self.assertEqual([row["batch"] for row in rows], [1, 1])

    async def testFailedMigrationIsNotRecorded(self) -> None:
        """
        Leave no tracking record behind when a migration fails.

        Validates the atomicity of each migration step.
        """
        self.useMigrations({"m01_alpha": _CreateAlpha, "m02_broken": _Broken})
        with self.assertRaises(RuntimeError):
            await self._migrator.migrate()
        rows = await self._migrator.status()
        self.assertEqual([row["ran"] for row in rows], [True, False])

    async def testMissingMigrationFileIsReported(self) -> None:
        """
        Report a recorded migration whose file disappeared.

        Validates the rollback guard.
        """
        await self._migrator.migrate()
        self.useMigrations({"m01_alpha": _CreateAlpha})
        with self.assertRaises(MigrationNotFoundException):
            await self._migrator.reset()

    async def testProgressEventsAreReported(self) -> None:
        """
        Report progress for every migration through the callbacks.

        Validates the console-agnostic reporting hooks.
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
        """
        Reject a connection name that is not configured.

        Validates the multi-connection entry point.
        """
        with self.assertRaises(ConnectionNotFoundException):
            await self._migrator.migrate(connection="ghost")
