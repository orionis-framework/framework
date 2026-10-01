import tempfile
from pathlib import Path
from orionis.database.connection_manager import ConnectionManager
from orionis.database.contracts.migration import Migration
from orionis.database.migrations.migrator import Migrator
from orionis.database.seeders.runner import SeederRunner
from orionis.database.seeders.seeder import Seeder
from orionis.orm.resolver import ConnectionResolver
from orionis.test import TestCase

class _StubApp:
    """Provide two SQLite databases to both runners."""

    def __init__(self, database: str) -> None:
        """Store the SQLite database path for both test connections.

        Parameters
        ----------
        database : str
            Path used by the default SQLite connection.

        Returns
        -------
        None
            Store the app paths and database configuration.
        """
        self.basePath = Path.cwd()
        self._database = database

    async def build(self, target: type[Migration | Seeder]) -> Migration | Seeder:
        """Build test migrations and seeders without dependencies.

        Parameters
        ----------
        target : type[Migration | Seeder]
            Migration or seeder class requested by the runner.

        Returns
        -------
        Migration or Seeder
            Constructed test migration or seeder.
        """
        return target()

    def config(self, key: str) -> dict:  # noqa: ARG002
        """Return isolated default and secondary connections.

        Parameters
        ----------
        key : str
            Configuration key requested by the connection manager.

        Returns
        -------
        dict
            Default connection name and both SQLite configurations.
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

class _CreateEntries(Migration):
    """Own the application table populated by the test seeder."""

    async def up(self) -> None:
        """Create the seeded application table.

        Returns
        -------
        None
            Create the entries table on the selected connection.
        """
        await ConnectionResolver.connection().statement(
            "CREATE TABLE entries (id INTEGER PRIMARY KEY, label VARCHAR(50))",
        )

    async def down(self) -> None:
        """Remove the seeded application table and its rows.

        Returns
        -------
        None
            Drop the entries table from the selected connection.
        """
        await ConnectionResolver.connection().statement("DROP TABLE entries")

class _CreateAudit(Migration):
    """Create a separate table that does not hold seeded data."""

    async def up(self) -> None:
        """Create an unrelated application table.

        Returns
        -------
        None
            Create the audit table on the selected connection.
        """
        await ConnectionResolver.connection().statement(
            "CREATE TABLE audit (id INTEGER PRIMARY KEY)",
        )

    async def down(self) -> None:
        """Remove the unrelated application table.

        Returns
        -------
        None
            Drop the audit table from the selected connection.
        """
        await ConnectionResolver.connection().statement("DROP TABLE audit")

class _SeedEntry(Seeder):
    """Insert one record into the migrated application table."""

    async def run(self) -> None:
        """Write one row to the selected connection.

        Returns
        -------
        None
            Insert the seeded label into the entries table.
        """
        await ConnectionResolver.connection().execute(
            "INSERT INTO entries (label) VALUES (:label)",
            {"label": "seeded"},
        )

class TestMigrationSeederLifecycle(TestCase):
    """Keep seeder history consistent with the migrated schema."""

    async def asyncSetUp(self) -> None:
        """Create isolated databases and runners for each test.

        Returns
        -------
        None
            Prepare the connections, migration runner, and seeder runner.
        """
        self._workspace = tempfile.TemporaryDirectory()
        app = _StubApp(str(Path(self._workspace.name) / "lifecycle.sqlite"))
        self._manager = ConnectionManager(app)
        ConnectionResolver.setManager(self._manager)
        self._migrator = Migrator(app, self._manager)
        self._migrator._Migrator__discovered_cache = {
            "m01_entries": _CreateEntries,
        }
        self._seeders = SeederRunner(app, self._manager)
        self._seeders._SeederRunner__discovered_cache = {
            "s01_entry": _SeedEntry,
        }

    async def asyncTearDown(self) -> None:
        """Close both connections and remove their files.

        Returns
        -------
        None
            Disconnect the manager and clean the temporary workspace.
        """
        await self._manager.disconnect()
        ConnectionResolver.clear()
        self._workspace.cleanup()

    async def _tableExists(self, table: str, connection: str = "sqlite") -> bool:
        """Check the selected SQLite catalog for a table.

        Parameters
        ----------
        table : str
            Table name to find.
        connection : str, optional
            Connection name whose catalog is queried.

        Returns
        -------
        bool
            Whether the table exists on the selected connection.
        """
        rows = await self._manager.connection(connection).select(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = :name",
            {"name": table},
        )
        return bool(rows)

    async def _entries(self, connection: str = "sqlite") -> list[str]:
        """Read the seeded application rows from one connection.

        Parameters
        ----------
        connection : str, optional
            Connection name from which to read entries.

        Returns
        -------
        list[str]
            Entry labels ordered by their database identifiers.
        """
        rows = await self._manager.connection(connection).select(
            "SELECT label FROM entries ORDER BY id",
        )
        return [row["label"] for row in rows]

    async def _trackedSeeders(self, connection: str = "sqlite") -> list[str]:
        """Read seeder history, including when its table was removed.

        Parameters
        ----------
        connection : str, optional
            Connection name from which to read seeder history.

        Returns
        -------
        list[str]
            Tracked seeder names, or an empty list if the table is absent.
        """
        if not await self._tableExists("seeders", connection):
            return []
        rows = await self._manager.connection(connection).select(
            "SELECT seeder FROM seeders ORDER BY id",
        )
        return [row["seeder"] for row in rows]

    async def testRollbackAllowsSeedingNewlyRecreatedTables(self) -> None:
        """Re-run a seeder after migration rollback removes its data.

        Returns
        -------
        None
            Verify rollback clears history and reseeding succeeds after migration.
        """
        self.assertEqual(await self._migrator.migrate(), ["m01_entries"])
        self.assertEqual(await self._seeders.seed(), ["s01_entry"])
        self.assertEqual(await self._entries(), ["seeded"])
        self.assertEqual(await self._trackedSeeders(), ["s01_entry"])

        self.assertEqual(await self._migrator.rollback(), ["m01_entries"])
        self.assertFalse(await self._tableExists("entries"))
        self.assertEqual(await self._trackedSeeders(), [])

        self.assertEqual(await self._migrator.migrate(), ["m01_entries"])
        self.assertEqual(await self._seeders.seed(), ["s01_entry"])
        self.assertEqual(await self._entries(), ["seeded"])
        self.assertEqual(await self._trackedSeeders(), ["s01_entry"])
        self.assertEqual(await self._seeders.seed(), [])

    async def testRollbackClearsOnlySelectedConnectionsSeederHistory(self) -> None:
        """Preserve the default database when rolling back a named one.

        Returns
        -------
        None
            Verify rollback and reseeding affect only the selected connection.
        """
        await self._migrator.migrate()
        await self._seeders.seed()
        await self._migrator.migrate(connection="secondary")
        await self._seeders.seed(connection="secondary")

        self.assertEqual(
            await self._migrator.rollback(connection="secondary"),
            ["m01_entries"],
        )
        self.assertFalse(await self._tableExists("entries", "secondary"))
        self.assertEqual(await self._trackedSeeders("secondary"), [])
        self.assertEqual(await self._entries(), ["seeded"])
        self.assertEqual(await self._trackedSeeders(), ["s01_entry"])

        self.assertEqual(
            await self._migrator.migrate(connection="secondary"),
            ["m01_entries"],
        )
        self.assertEqual(
            await self._seeders.seed(connection="secondary"),
            ["s01_entry"],
        )
        self.assertEqual(await self._entries("secondary"), ["seeded"])
        self.assertEqual(await self._seeders.seed(), [])
        self.assertEqual(await self._entries(), ["seeded"])

    async def testPartialRollbackPreservesHistoryUntilSchemaIsFullyReset(self) -> None:
        """Keep seeder claims while their seeded table remains intact.

        Returns
        -------
        None
            Verify partial rollback preserves valid seeder history.
        """
        await self._migrator.migrate()
        await self._seeders.seed()
        self._migrator._Migrator__discovered_cache = {
            "m01_entries": _CreateEntries,
            "m02_audit": _CreateAudit,
        }
        self.assertEqual(await self._migrator.migrate(), ["m02_audit"])

        self.assertEqual(await self._migrator.rollback(), ["m02_audit"])
        self.assertTrue(await self._tableExists("entries"))
        self.assertFalse(await self._tableExists("audit"))
        self.assertEqual(await self._trackedSeeders(), ["s01_entry"])
        self.assertEqual(await self._seeders.seed(), [])
        self.assertEqual(await self._entries(), ["seeded"])

        self.assertEqual(await self._migrator.rollback(), ["m01_entries"])
        self.assertEqual(await self._trackedSeeders(), [])
        self.assertEqual(await self._migrator.migrate(), ["m01_entries", "m02_audit"])
        self.assertEqual(await self._seeders.seed(), ["s01_entry"])
        self.assertEqual(await self._entries(), ["seeded"])

    async def testFreshClearsLegacySeederHistoryWithoutMigrationRows(self) -> None:
        """Recover when an earlier rollback leaves only seeder history.

        Returns
        -------
        None
            Verify fresh migration clears stale history and allows reseeding.
        """
        await self._migrator.migrate()
        await self._seeders.seed()
        connection = self._manager.connection()
        await connection.statement("DELETE FROM migrations")
        await connection.statement("DROP TABLE entries")
        self.assertFalse(await self._tableExists("entries"))
        self.assertEqual(await self._trackedSeeders(), ["s01_entry"])

        self.assertEqual(await self._migrator.fresh(), ["m01_entries"])
        self.assertEqual(await self._trackedSeeders(), [])
        self.assertEqual(await self._seeders.seed(), ["s01_entry"])
        self.assertEqual(await self._entries(), ["seeded"])
        self.assertEqual(await self._trackedSeeders(), ["s01_entry"])
