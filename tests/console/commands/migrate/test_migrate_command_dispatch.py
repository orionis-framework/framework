import io
from contextlib import redirect_stdout
from orionis.console.commands.migrate.fresh import MigrateFreshCommand
from orionis.console.commands.migrate.migrate import MigrateCommand
from orionis.console.commands.migrate.reset import MigrateResetCommand
from orionis.console.commands.migrate.status import MigrateStatusCommand
from orionis.database.migrations.events import MigrationEvents
from orionis.test import TestCase

class _RecordingMigrator:
    """Record migration service calls and return configured results."""

    __slots__ = ("calls", "migration_result", "status_result")

    def __init__(
        self,
        migration_result: list[str] | None = None,
        status_result: list[dict[str, object]] | None = None,
    ) -> None:
        """Initialize recorded calls and service results.

        Parameters
        ----------
        migration_result : list of str or None, optional
            Names returned by migration operations.
        status_result : list of dict or None, optional
            Rows returned by status inspection.

        Returns
        -------
        None
            Initialize call history and configured operation results.
        """
        self.calls: list[tuple[str, str | None, MigrationEvents | None]] = []
        self.migration_result = migration_result or []
        self.status_result = status_result or []

    async def migrate(
        self,
        *,
        connection: str | None,
        events: MigrationEvents,
    ) -> list[str]:
        """Record a migration run and return configured names.

        Parameters
        ----------
        connection : str or None
            Selected database connection.
        events : MigrationEvents
            Reporter passed by the command.

        Returns
        -------
        list of str
            Configured migration names.
        """
        self.calls.append(("migrate", connection, events))
        return self.migration_result

    async def fresh(
        self,
        *,
        connection: str | None,
        events: MigrationEvents,
    ) -> list[str]:
        """Record a fresh run and return configured names.

        Parameters
        ----------
        connection : str or None
            Selected database connection.
        events : MigrationEvents
            Reporter passed by the command.

        Returns
        -------
        list of str
            Configured migration names.
        """
        self.calls.append(("fresh", connection, events))
        return self.migration_result

    async def reset(
        self,
        *,
        connection: str | None,
        events: MigrationEvents,
    ) -> list[str]:
        """Record a reset run and return configured names.

        Parameters
        ----------
        connection : str or None
            Selected database connection.
        events : MigrationEvents
            Reporter passed by the command.

        Returns
        -------
        list of str
            Configured migration names.
        """
        self.calls.append(("reset", connection, events))
        return self.migration_result

    async def status(self, *, connection: str | None) -> list[dict[str, object]]:
        """Record a status lookup and return configured rows.

        Parameters
        ----------
        connection : str or None
            Selected database connection.

        Returns
        -------
        list of dict
            Configured migration status rows.
        """
        self.calls.append(("status", connection, None))
        return self.status_result

class _RecordingSeederRunner:
    """Record seeder service calls."""

    __slots__ = ("calls",)

    def __init__(self) -> None:
        """Initialize the seeder call record.

        Returns
        -------
        None
            Create an empty record of seeder calls.
        """
        self.calls: list[tuple[str | None, MigrationEvents]] = []

    async def seed(
        self,
        *,
        connection: str | None,
        events: MigrationEvents,
    ) -> list[str]:
        """Record the seeder call and return a completed seeder.

        Parameters
        ----------
        connection : str or None
            Selected database connection.
        events : MigrationEvents
            Reporter passed by the command.

        Returns
        -------
        list of str
            One completed seeder name.
        """
        self.calls.append((connection, events))
        return ["insert_reports"]

class _CountingMigrateCommand(MigrateCommand):
    """Count reads of the command's selected database connection."""

    __slots__ = ("target_calls",)

    def __init__(self) -> None:
        """Initialize the database selection counter.

        Returns
        -------
        None
            Start the target connection call count at zero.
        """
        super().__init__()
        self.target_calls = 0

    def targetConnection(self) -> str | None:
        """Count and return the selected database connection.

        Returns
        -------
        str or None
            Connection selected by the command argument.
        """
        self.target_calls += 1
        return super().targetConnection()

class TestMigrationCommandDispatch(TestCase):
    """Check the command contract with the migration services."""

    async def testMigrateAndSeedShareConnectionAndProgressEvents(self) -> None:
        """Use the same selected connection and reporter for both phases.

        Returns
        -------
        None
            Assertions verify the identity of shared state.
        """
        command = _CountingMigrateCommand()
        command.setArguments({"database": "reports", "seed": True})
        migrator = _RecordingMigrator(["create_reports"])
        runner = _RecordingSeederRunner()

        with redirect_stdout(io.StringIO()):
            await command.handle(migrator, runner)

        self.assertEqual(len(migrator.calls), 1)
        self.assertEqual(migrator.calls[0][:2], ("migrate", "reports"))
        self.assertEqual(len(runner.calls), 1)
        self.assertEqual(runner.calls[0][0], "reports")
        self.assertIs(migrator.calls[0][2], runner.calls[0][1])
        self.assertEqual(command.target_calls, 1)

    async def testFreshAndResetDispatchToSelectedConnection(self) -> None:
        """Forward the target connection and report an empty result.

        Returns
        -------
        None
            Assertions verify both commands' service and output calls.
        """
        for command_type, method_name, empty_message in (
            (MigrateFreshCommand, "fresh", "Nothing to migrate."),
            (MigrateResetCommand, "reset", "Nothing to reset."),
        ):
            with self.subTest(command=command_type.__name__):
                command = command_type()
                command.setArguments({"database": "reports"})
                migrator = _RecordingMigrator()
                output = io.StringIO()
                with redirect_stdout(output):
                    await command.handle(migrator)

                self.assertEqual(len(migrator.calls), 1)
                self.assertEqual(migrator.calls[0][:2], (method_name, "reports"))
                self.assertIsInstance(migrator.calls[0][2], MigrationEvents)
                self.assertIn(empty_message, output.getvalue())

    async def testStatusRendersAppliedAndPendingMigrations(self) -> None:
        """Render batches only for applied migrations.

        Returns
        -------
        None
            Assertions verify the status table and selected connection.
        """
        command = MigrateStatusCommand()
        command.setArguments({"database": "reports"})
        migrator = _RecordingMigrator(
            status_result=[
                {"migration": "create_users", "ran": True, "batch": 2},
                {"migration": "create_posts", "ran": False, "batch": None},
            ],
        )
        output = io.StringIO()
        with redirect_stdout(output):
            await command.handle(migrator)

        self.assertEqual(migrator.calls, [("status", "reports", None)])
        rendered = output.getvalue()
        for expected in ("create_users", "Ran", "2", "create_posts", "Pending"):
            self.assertIn(expected, rendered)

    async def testStatusReportsNoDiscoveredMigrations(self) -> None:
        """Report an empty catalog without attempting to render a table.

        Returns
        -------
        None
            Assertions verify the empty-state behavior.
        """
        command = MigrateStatusCommand()
        migrator = _RecordingMigrator()
        output = io.StringIO()
        with redirect_stdout(output):
            await command.handle(migrator)

        self.assertEqual(migrator.calls, [("status", None, None)])
        self.assertIn("No migrations were found.", output.getvalue())
