import argparse
from unittest.mock import AsyncMock, Mock, patch
from orionis.console.commands.migrate.migrate import MigrateCommand
from orionis.console.commands.seed.seed import SeedCommand
from orionis.console.core.commands import CORE_COMMANDS
from orionis.database.migrations.events import MigrationEvents
from orionis.test import TestCase

class TestSeederCommands(TestCase):
    """Verify seeding is exposed through the existing console conventions."""

    def testSeedAndMigrateArgumentsAreRegistered(self) -> None:
        """Expose seed commands and parse connection and flag options.

        Returns
        -------
        None
            Assertions verify the registered signatures and CLI options.
        """
        signatures = {command.signature for command in CORE_COMMANDS}
        self.assertIn("seed", signatures)
        self.assertIn("migrate", signatures)

        seed_parser = argparse.ArgumentParser()
        for argument in SeedCommand.arguments:
            argument.addToParser(seed_parser)
        self.assertEqual(
            seed_parser.parse_args(["--database", "reports"]).database,
            "reports",
        )

        migrate_parser = argparse.ArgumentParser()
        for argument in MigrateCommand.arguments:
            argument.addToParser(migrate_parser)
        self.assertFalse(migrate_parser.parse_args([]).seed)
        parsed = migrate_parser.parse_args(["-d", "reports", "--seed"])
        self.assertEqual(parsed.database, "reports")
        self.assertTrue(parsed.seed)

    async def testSeedUsesSelectedConnectionAndReportsEmptyRun(self) -> None:
        """Pass the target connection and progress callbacks to the runner.

        Returns
        -------
        None
            The runner receives the selected connection and empty output.
        """
        command = SeedCommand()
        command.setArguments({"database": "reports"})
        runner = Mock()
        runner.seed = AsyncMock(return_value=[])

        with (
            patch.object(command, "newLine"),
            patch.object(command, "reportEmpty") as report_empty,
        ):
            await command.handle(runner)

        self.assertEqual(runner.seed.await_count, 1)
        self.assertEqual(runner.seed.await_args.kwargs["connection"], "reports")
        self.assertIsInstance(
            runner.seed.await_args.kwargs["events"],
            MigrationEvents,
        )
        report_empty.assert_called_once_with(
            "Nothing to seed. Database is already up to date.",
        )

    async def testSeedProgressReportsRunningDoneAndFail(self) -> None:
        """Render seeder progress with the existing console executor.

        Returns
        -------
        None
            Every progress callback reaches the matching executor method.
        """
        command = SeedCommand()
        with patch("orionis.console.commands.migrate.base.Executor") as executor:
            events = command.progressEvents()
            events.started("users")
            events.succeeded("users", 0.42)
            events.failed("roles", 0.5)

        executor.return_value.running.assert_called_once_with("users")
        executor.return_value.done.assert_called_once_with("users", "0.42s")
        executor.return_value.fail.assert_called_once_with("roles", "0.50s")

    async def testMigrateWithoutSeedDoesNotRunSeeders(self) -> None:
        """Keep ordinary migration behavior when the flag is absent.

        Returns
        -------
        None
            The migrator runs and the seeder runner is not invoked.
        """
        command = MigrateCommand()
        command.setArguments({})
        migrator = Mock()
        migrator.migrate = AsyncMock(return_value=["create_users"])
        runner = Mock()
        runner.seed = AsyncMock()

        with patch.object(command, "newLine"):
            await command.handle(migrator, runner)

        self.assertEqual(migrator.migrate.await_count, 1)
        self.assertIsNone(migrator.migrate.await_args.kwargs["connection"])
        runner.seed.assert_not_awaited()

    async def testMigrateWithSeedRunsAfterSuccessfulMigrations(self) -> None:
        """Seed the same connection after migrations have finished.

        Returns
        -------
        None
            Recorded calls prove the ordering and connection propagation.
        """
        command = MigrateCommand()
        command.setArguments({"database": "reports", "seed": True})
        calls: list[str] = []

        async def migrate(*, connection: str, events: object) -> list[str]:
            """Record migration dispatch and return one applied migration.

            Parameters
            ----------
            connection : str
                Selected database connection.
            events : object
                Progress callbacks supplied to the migrator.

            Returns
            -------
            list[str]
                Applied migration names.
            """
            calls.append("migrate")
            self.assertEqual(connection, "reports")
            self.assertIsInstance(events, MigrationEvents)
            return ["create_users"]

        async def seed(*, connection: str, events: object) -> list[str]:
            """Record seeder dispatch and return one completed seeder.

            Parameters
            ----------
            connection : str
                Selected database connection.
            events : object
                Progress callbacks supplied to the seeder runner.

            Returns
            -------
            list[str]
                Completed seeder names.
            """
            calls.append("seed")
            self.assertEqual(connection, "reports")
            self.assertIsInstance(events, MigrationEvents)
            return ["admin"]

        migrator = Mock()
        migrator.migrate = AsyncMock(side_effect=migrate)
        runner = Mock()
        runner.seed = AsyncMock(side_effect=seed)

        with patch.object(command, "newLine"):
            await command.handle(migrator, runner)

        self.assertEqual(calls, ["migrate", "seed"])

    async def testMigrateWithSeedRunsWhenNoMigrationsArePending(self) -> None:
        """Continue to pending seeders even on an empty migration run.

        Returns
        -------
        None
            The seed runner executes once after the empty migration result.
        """
        command = MigrateCommand()
        command.setArguments({"seed": True})
        migrator = Mock()
        migrator.migrate = AsyncMock(return_value=[])
        runner = Mock()
        runner.seed = AsyncMock(return_value=["admin"])

        with (
            patch.object(command, "newLine"),
            patch.object(command, "reportEmpty") as report_empty,
        ):
            await command.handle(migrator, runner)

        runner.seed.assert_awaited_once()
        report_empty.assert_called_once_with(
            "Nothing to migrate. Database is already up to date.",
        )

    async def testMigrationFailurePreventsSeeding(self) -> None:
        """Do not start seeders when a migration raises an error.

        Returns
        -------
        None
            The exception propagates and no seeder run begins.
        """
        command = MigrateCommand()
        command.setArguments({"seed": True})
        migrator = Mock()
        migrator.migrate = AsyncMock(side_effect=RuntimeError("migration failed"))
        runner = Mock()
        runner.seed = AsyncMock()

        with (
            patch.object(command, "newLine"),
            self.assertRaisesRegex(RuntimeError, "migration failed"),
        ):
            await command.handle(migrator, runner)

        runner.seed.assert_not_awaited()
