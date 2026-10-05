import argparse
from unittest.mock import AsyncMock, Mock, patch
from orionis.console.commands.db.seed import DbSeedCommand
from orionis.console.commands.seed.seed import SeedCommand
from orionis.database.migrations.events import MigrationEvents
from orionis.test import TestCase

class TestDbSeedCommand(TestCase):
    """Verify the Laravel-style command shares the existing seeding path."""

    def testSignatureAndConnectionOption(self) -> None:
        """Expose the command signature and database connection option.

        Returns
        -------
        None
            Assertions verify the signature and parsed connection name.
        """
        self.assertEqual(DbSeedCommand.signature, "db:seed")
        self.assertEqual(SeedCommand.signature, "seed")

        parser = argparse.ArgumentParser()
        for argument in DbSeedCommand.arguments:
            argument.addToParser(parser)

        self.assertEqual(parser.parse_args(["-d", "reports"]).database, "reports")

    async def testUsesSelectedConnectionAndProgressCallbacks(self) -> None:
        """Forward the selected connection and lifecycle events to the runner.

        Returns
        -------
        None
            Assertions verify connection selection and progress reporting.
        """
        command = DbSeedCommand()
        command.setArguments({"database": "reports"})
        runner = Mock()
        runner.seed = AsyncMock(return_value=["admin"])

        with (
            patch.object(command, "newLine"),
            patch.object(command, "reportEmpty") as report_empty,
            patch("orionis.console.commands.migrate.base.Executor") as executor,
        ):
            await command.handle(runner)
            events = runner.seed.await_args.kwargs["events"]
            events.started("admin")
            events.succeeded("admin", 0.42)
            events.failed("roles", 0.5)

        runner.seed.assert_awaited_once()
        self.assertEqual(runner.seed.await_args.kwargs["connection"], "reports")
        self.assertIsInstance(events, MigrationEvents)
        executor.return_value.running.assert_called_once_with("admin")
        executor.return_value.done.assert_called_once_with("admin", "0.42s")
        executor.return_value.fail.assert_called_once_with("roles", "0.50s")
        report_empty.assert_not_called()

    async def testEmptyRunReportsAlreadyUpToDate(self) -> None:
        """Report the established message when no seeders are pending.

        Returns
        -------
        None
            Assertions verify the default connection and empty-run message.
        """
        command = DbSeedCommand()
        command.setArguments({})
        runner = Mock()
        runner.seed = AsyncMock(return_value=[])

        with (
            patch.object(command, "newLine"),
            patch.object(command, "reportEmpty") as report_empty,
        ):
            await command.handle(runner)

        self.assertIsNone(runner.seed.await_args.kwargs["connection"])
        report_empty.assert_called_once_with(
            "Nothing to seed. Database is already up to date.",
        )
