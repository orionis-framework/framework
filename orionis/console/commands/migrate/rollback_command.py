from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.commands.migrate.base_command import MigrationCommand
from orionis.database.migrations.migrator import Migrator

class MigrateRollbackCommand(MigrationCommand):
    """Revert the most recently applied migration batches."""

    # ruff: noqa: TC001

    # Command signature and description
    signature: str = "migrate:rollback"

    # Command description
    description: str = "Reverts the last batch(es) of database migrations."

    # List of Argument instances defining command-line options and arguments
    arguments: ClassVar[list[Argument]] = [
        *MigrationCommand.arguments,
        Argument(
            name_or_flags=["--step", "-s"],
            type_=int,
            required=False,
            help=(
                "Number of migration batches to roll back. Defaults to 1 "
                "(the most recent batch)."
            ),
            dest="step",
        ),
    ]

    async def handle(self, migrator: Migrator) -> None:
        """
        Revert the most recently applied migration batches.

        Parameters
        ----------
        migrator : Migrator
            Service that discovers and reverts applied migrations.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.newLine()
        reverted = await migrator.rollback(
            int(self.getArgument("step") or 1),
            connection=self.targetConnection(),
            events=self.progressEvents(),
        )
        if not reverted:
            self.reportEmpty("Nothing to roll back.")
