from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.commands.migrate.base import MigrationCommand
from orionis.database.migrations.migrator import Migrator
from orionis.database.seeders.runner import SeederRunner

class MigrateCommand(MigrationCommand):
    """Apply every migration that has not been run yet."""

    # ruff: noqa: TC001

    signature: str = "migrate"
    description: str = "Runs all pending database migrations."

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

    async def handle(
        self,
        migrator: Migrator,
        seeder_runner: SeederRunner,
    ) -> None:
        """
        Apply every migration that has not been run yet.

        Parameters
        ----------
        migrator : Migrator
            Service that discovers and applies pending migrations.
        seeder_runner : SeederRunner
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
