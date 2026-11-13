# ruff: noqa: PT009, PT027, S603, SLF001, TC001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Keep runtime contract types available to reflection in these fixtures.
# Run this interpreter with fixed probes and the inherited isolated environment.
"""Exercise schema and migration failures against an isolated SQLite database."""

import asyncio
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import get_type_hints
from unittest.mock import AsyncMock, patch
from orionis.database.connection_manager import ConnectionManager
from orionis.database.contracts.connection import IConnection
from orionis.database.contracts.migration import Migration
from orionis.database.contracts.migrator import IMigrator
from orionis.database.contracts.schema import ISchema
from orionis.database.migrations.context import (
    current_migration_connection,
    migration_connection_scope,
)
from orionis.database.migrations.events import MigrationEvents
from orionis.database.migrations.migrator import Migrator
from orionis.database.schema.blueprint import Blueprint
from orionis.database.schema.column import Column
from orionis.database.schema.primary import PrimaryKey
from orionis.database.schema.schema import Schema
from orionis.database.schema.table_creation import TableCreation
from orionis.database.seeders.runner import SeederRunner
from orionis.database.seeders.seeder import Seeder
from orionis.test import TestCase


class _Application:
    """Expose only application dependencies needed by the schema runners."""

    def __init__(self, root: Path) -> None:
        """Retain an owned application root.

        Parameters
        ----------
        root : pathlib.Path
            Temporary root owned by the test.

        Returns
        -------
        None
            No return value.
        """
        self.basePath = root

    def config(self, key: str) -> dict:
        """Return private SQLite connection settings.

        Parameters
        ----------
        key : str
            Requested configuration group.

        Returns
        -------
        dict
            Database settings for this fixture.
        """
        if key != "database":
            raise KeyError(key)
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {"driver": "sqlite", "database": ":memory:"},
            },
        }

    def path(self, key: str) -> Path:
        """Resolve a discovery directory within the owned root.

        Parameters
        ----------
        key : str
            Requested application path.

        Returns
        -------
        pathlib.Path
            Configured discovery directory.
        """
        return self.basePath / key

    async def build(self, target: type[Migration | Seeder]) -> Migration | Seeder:
        """Construct a dependency-free migration or seeder.

        Parameters
        ----------
        target : type[Migration | Seeder]
            Fixture class requested by discovery.

        Returns
        -------
        Migration or Seeder
            Fresh fixture instance.
        """
        return target()


class _BrokenMigration(Migration):
    """Raise a stable failure without changing the temporary schema."""

    async def up(self) -> None:
        """Fail the migration body.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            Always, to exercise failure propagation.
        """
        message = "migration body failed"
        raise ValueError(message)

    async def down(self) -> None:
        """Leave the temporary schema unchanged.

        Returns
        -------
        None
            No return value.
        """


class _BrokenSeeder(Seeder):
    """Fail after the runner acquires its real transactional claim."""

    async def run(self) -> None:
        """Raise an application seeding error.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            Always, to exercise failure propagation.
        """
        message = "seeder body failed"
        raise ValueError(message)


class TestSchemaRegressions(TestCase):
    """Keep invalid declarations and stale migration state observable."""

    async def asyncSetUp(self) -> None:
        """Create an owned root and register cleanup before using connections.

        Returns
        -------
        None
            No return value.
        """
        workspace = TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.app = _Application(Path(workspace.name))
        self.manager = ConnectionManager(self.app)
        self.addAsyncCleanup(self.manager.disconnect)
        self.connection = self.manager.connection()

    async def testDuplicateColumnsNeverReachTheDatabase(self) -> None:
        """Reject duplicate definitions before silently replacing a column.

        Returns
        -------
        None
            No return value.
        """
        for duplicate in ("plain", "primary", "timestamp"):
            with self.subTest(duplicate=duplicate):
                schema = Schema(self.manager)
                with self.assertRaisesRegex(ValueError, "already|duplicate"):
                    async with schema.create("invalid_" + duplicate) as table:
                        if duplicate == "timestamp":
                            table.string("created_at")
                            table.timestamps()
                        else:
                            if duplicate == "primary":
                                table.id()
                            else:
                                table.string("id")
                            table.string("id")
                rows = await self.connection.select(
                    "SELECT name FROM sqlite_master WHERE name = :name",
                    {"name": "invalid_" + duplicate},
                )
                self.assertEqual(rows, [])

    def testEmptyPrimaryKeysRaiseADeclarationError(self) -> None:
        """Reject a primary key without columns at its declaration boundary.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(ValueError):
            PrimaryKey()

    def testBlueprintExposesOnlyColumnFactories(self) -> None:
        """Reject inherited type utilities masquerading as column factories.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(AttributeError):
            _ = Blueprint().mro

    async def testTableCreationRejectsOverlappingEntries(self) -> None:
        """Keep an active declaration intact when its context is entered twice.

        Returns
        -------
        None
            No return value.
        """
        creation = Schema(self.manager).create("entries")
        async with creation as table:
            table.id()
            with self.assertRaises(RuntimeError):
                await creation.__aenter__()
        self.assertEqual(await self.connection.select("SELECT * FROM entries"), [])

    async def testTableCreationConsumesEachSuccessfulDeclarationOnce(self) -> None:
        """Prevent a settled context from issuing its create operation again.

        Returns
        -------
        None
            No return value.
        """
        schema = Schema(self.manager)
        original = schema._createTable
        with patch.object(
            Schema,
            "_createTable",
            new=AsyncMock(wraps=original),
        ) as create:
            creation = schema.create("once_only")
            async with creation as table:
                table.id()
            await creation.__aexit__(None, None, None)
            self.assertEqual(create.await_count, 1)

    async def testChildDiscardsACompletedMigrationScope(self) -> None:
        """Release inherited connection selection when its owner leaves scope.

        Returns
        -------
        None
            No return value.
        """
        ready = asyncio.Event()

        async def resolve_after_scope() -> IConnection | None:
            """Resolve the inherited binding after the parent finishes.

            Returns
            -------
            IConnection or None
                Remaining active migration connection.
            """
            await ready.wait()
            return current_migration_connection()

        with migration_connection_scope(self.connection):
            self.assertIs(current_migration_connection(), self.connection)
            child = asyncio.create_task(resolve_after_scope())
        ready.set()
        self.assertIsNone(await child)
        self.assertIsNone(current_migration_connection())

    async def testDiscoveryPreservesFilesystemErrors(self) -> None:
        """Propagate unreadable discovery roots instead of caching an empty run.

        Returns
        -------
        None
            No return value.
        """
        for runner in (
            Migrator(self.app, self.manager),
            SeederRunner(self.app, self.manager),
        ):
            with self.subTest(runner=type(runner).__name__):
                # Prepare tables first so only directory discovery encounters stat.
                if isinstance(runner, Migrator):
                    await runner.status()
                    runner._Migrator__discovered_cache = None
                    operation = runner.status
                else:
                    await runner.seed()
                    runner._SeederRunner__discovered_cache = None
                    operation = runner.seed
                error = PermissionError("discovery denied")
                with (
                    patch.object(Path, "stat", side_effect=error),
                    self.assertRaises(PermissionError) as raised,
                ):
                    await operation()
                self.assertIs(raised.exception, error)

    def testSchemaRuntimeAnnotationsResolve(self) -> None:
        """Resolve reflection metadata for schema factories and migration events.

        Returns
        -------
        None
            No return value.
        """
        targets = (
            Column.strictArray,
            Blueprint.__getattr__,
            Blueprint.columns,
            Blueprint.definitions,
            MigrationEvents,
            current_migration_connection,
            migration_connection_scope.__wrapped__,
            TableCreation.__init__,
            TableCreation.__aexit__,
            Schema.createFromModel,
            Schema._createTable,
            ISchema.create,
            ISchema.createFromDefinition,
            ISchema.createFromModel,
            IMigrator.migrate,
        )
        for target in targets:
            with self.subTest(target=target.__qualname__):
                self.assertTrue(get_type_hints(target))

    async def testRunnerReportFailuresKeepTheBodyError(self) -> None:
        """Preserve the migration or seeder error when progress reporting fails.

        Returns
        -------
        None
            No return value.
        """
        reporting_error = OSError("progress output unavailable")

        def report_failure(name: str, elapsed: float) -> None:
            """Fail only while reporting a runner failure.

            Parameters
            ----------
            name : str
                Failed step name.
            elapsed : float
                Duration reported by the runner.

            Returns
            -------
            None
                No return value.

            Raises
            ------
            OSError
                Always, after recording the progress callback inputs.
            """
            self.assertEqual(name, "broken")
            self.assertGreaterEqual(elapsed, 0)
            raise reporting_error

        migrator = Migrator(self.app, self.manager)
        migrator._Migrator__discovered_cache = {"broken": _BrokenMigration}
        seeder = SeederRunner(self.app, self.manager)
        seeder._SeederRunner__discovered_cache = {"broken": _BrokenSeeder}
        for operation in (migrator.migrate, seeder.seed):
            with (
                self.subTest(operation=operation.__qualname__),
                self.assertRaisesRegex(ValueError, "body failed"),
            ):
                await operation(events=MigrationEvents(on_error=report_failure))

    async def testDiscoveryIgnoresRealPackageInitializers(self) -> None:
        """Exclude classes defined by package initializers during real discovery.

        Returns
        -------
        None
            No return value.
        """
        await self._exerciseDiscovery(include_alias=False, include_initializer=True)

    async def testDiscoveryDeduplicatesAliasesOfTheSameClass(self) -> None:
        """Persist one step when its own module also exports a class alias.

        Returns
        -------
        None
            No return value.
        """
        await self._exerciseDiscovery(include_alias=True, include_initializer=False)

    async def _exerciseDiscovery(
        self,
        *,
        include_alias: bool,
        include_initializer: bool,
    ) -> None:
        """Import owned fixture packages through the actual directory walker.

        Parameters
        ----------
        include_alias : bool
            Export the leaf class twice from its own module.
        include_initializer : bool
            Declare a step in the package initializer as well as the leaf module.

        Returns
        -------
        None
            No return value.
        """
        for base, runner_type, method in (
            (Migration, Migrator, "migrate"),
            (Seeder, SeederRunner, "seed"),
        ):
            package = "discovery_" + self.app.basePath.name + base.__name__
            folder = self.app.basePath / package
            folder.mkdir()
            body = (
                "from " + base.__module__ + " import " + base.__name__ + "\n"
                "class Step(" + base.__name__ + "):\n"
                '    """Define an owned discovery fixture."""\n'
            )
            methods = ("up", "down") if base is Migration else ("run",)
            for name in methods:
                body += (
                    "    async def " + name + "(self) -> None:\n"
                    '        """Leave the fixture database unchanged."""\n'
                )
            initializer = body if include_initializer else '"""Hold fixture steps."""\n'
            (folder / "__init__.py").write_text(initializer, encoding="utf-8")
            (folder / "step.py").write_text(
                body + ("Alias = Step\n" if include_alias else ""),
                encoding="utf-8",
            )
            runner = runner_type(self.app, self.manager)
            try:
                with (
                    patch.object(sys, "path", [str(self.app.basePath), *sys.path]),
                    patch.object(self.app, "path", return_value=folder),
                    self.subTest(runner=runner_type.__name__),
                ):
                    self.assertEqual(await getattr(runner, method)(), ["step"])
            finally:
                for module in tuple(sys.modules):
                    if module == package or module.startswith(package + "."):
                        sys.modules.pop(module, None)

    def testPublicSchemaImportsInEveryOrder(self) -> None:
        """Resolve cyclic public schema annotations from each fresh import entry.

        Returns
        -------
        None
            No return value.
        """
        for entry in (
            "orionis.database.contracts.schema",
            "orionis.database.schema.schema",
            "orionis.database.schema.table_creation",
        ):
            script = (
                "import importlib; from typing import get_type_hints; "
                f"importlib.import_module({entry!r}); "
                "from orionis.database.contracts.schema import ISchema; "
                "from orionis.database.schema.schema import Schema; "
                "from orionis.database.schema.table_creation import TableCreation; "
                "assert get_type_hints(TableCreation.__init__)['schema'] is Schema; "
                "assert get_type_hints(ISchema.create)['return'] is TableCreation"
            )
            with self.subTest(entry=entry):
                result = subprocess.run(
                    [sys.executable, "-B", "-c", script],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
