# ruff: noqa: TC001
# Keep runtime reflection annotations and intentionally deferred imports.
"""Revert the most recently applied migration batches."""

from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.commands.migrate.base import MigrationCommand
from orionis.database.migrations.migrator import Migrator


class MigrateRollbackCommand(MigrationCommand):
    """Revert the most recently applied migration batches."""

    signature: str = "migrate:rollback"
    """Signature identifier: ``migrate:rollback``."""
    description: str = "Reverts the last batch(es) of database migrations."
    """
    Description identifier: ``Reverts the last batch(es) of database migrations.``.
    """
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
    """Command-line argument declarations accepted by this command."""

    async def handle(self, migrator: Migrator) -> None:
        """
        Revert the most recently applied migration batches.

        Parameters
        ----------
        migrator : orionis.database.migrations.Migrator
            Service that discovers and reverts applied migrations.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.newLine()
        step = self.getArgument("step")
        reverted = await migrator.rollback(
            int(step) if step is not None else 1,
            connection=self.targetConnection(),
            events=self.progressEvents(),
        )
        if not reverted:
            self.reportEmpty("Nothing to roll back.")
