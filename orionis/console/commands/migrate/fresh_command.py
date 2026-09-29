from orionis.console.commands.migrate.base_command import MigrationCommand
from orionis.database.migrations.migrator import Migrator

class MigrateFreshCommand(MigrationCommand):
    """Drop the tracking table and apply every migration from scratch."""

    # ruff: noqa: TC001

    # Command signature and description
    signature: str = "migrate:fresh"

    # Command description
    description: str = "Drops the migrations table and migrates from scratch."

    async def handle(self, migrator: Migrator) -> None:
        """
        Drop the tracking table and apply every migration from scratch.

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
        applied = await migrator.fresh(
            connection=self.targetConnection(),
            events=self.progressEvents(),
        )
        if not applied:
            self.reportEmpty("Nothing to migrate.")
