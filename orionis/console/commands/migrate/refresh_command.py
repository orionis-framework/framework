from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.commands.migrate.base_command import MigrationCommand
from orionis.database.migrations.migrator import Migrator

class MigrateRefreshCommand(MigrationCommand):
    """Roll back migrations and immediately apply them again."""

    # ruff: noqa: TC001

    # Command signature and description
    signature: str = "migrate:refresh"

    # Command description
    description: str = "Rolls back and re-applies database migrations."

    # List of Argument instances defining command-line options and arguments
    arguments: ClassVar[list[Argument]] = [
        *MigrationCommand.arguments,
        Argument(
            name_or_flags=["--step", "-s"],
            type_=int,
            required=False,
            help=(
                "Number of migration batches to roll back before migrating "
                "again. Defaults to every applied migration."
            ),
            dest="step",
        ),
    ]

    async def handle(self, migrator: Migrator) -> None:
        """
        Roll back migrations and immediately apply them again.

        Parameters
        ----------
        migrator : Migrator
            Service that discovers, reverts, and applies migrations.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.newLine()
        step = self.getArgument("step")
        applied = await migrator.refresh(
            int(step) if step else None,
            connection=self.targetConnection(),
            events=self.progressEvents(),
        )
        if not applied:
            self.reportEmpty("Nothing to refresh.")
