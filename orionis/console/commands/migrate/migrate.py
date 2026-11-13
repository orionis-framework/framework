# ruff: noqa: TC001
# Keep runtime reflection annotations and intentionally deferred imports.
"""Apply every migration that has not been run yet."""

from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.commands.migrate.base import MigrationCommand
from orionis.database.migrations.migrator import Migrator
from orionis.database.seeders.runner import SeederRunner


class MigrateCommand(MigrationCommand):
    """Apply every migration that has not been run yet."""

    signature: str = "migrate"
    """Signature identifier: ``migrate``."""
    description: str = "Runs all pending database migrations."
    """Description identifier: ``Runs all pending database migrations.``."""

    arguments: ClassVar[list[Argument]] = [
        *MigrationCommand.arguments,
        Argument(
            name_or_flags="--seed",
            action="store_true",
            default=False,
            help="Run pending database seeders after successful migrations.",
            dest="seed",
        ),
    ]
    """Command-line argument declarations accepted by this command."""

    async def handle(
        self,
        migrator: Migrator,
        seeder_runner: SeederRunner,
    ) -> None:
        """
        Apply every migration that has not been run yet.

        Parameters
        ----------
        migrator : orionis.database.migrations.Migrator
            Service that discovers and applies pending migrations.
        seeder_runner : orionis.database.seeders.SeederRunner
            Service that runs pending seeders when ``--seed`` is selected.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.newLine()
        connection = self.targetConnection()
        events = self.progressEvents()
        applied = await migrator.migrate(
            connection=connection,
            events=events,
        )
        if not applied:
            self.reportEmpty("Nothing to migrate. Database is already up to date.")

        if self.getArgument("seed", default=False):
            self.newLine()
            seeded = await seeder_runner.seed(
                connection=connection,
                events=events,
            )
            if not seeded:
                self.reportEmpty(
                    "Nothing to seed. Database is already up to date.",
                )
