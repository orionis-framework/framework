from orionis.console.commands.migrate.base_command import MigrationCommand
from orionis.database.migrations.migrator import Migrator

class MigrateResetCommand(MigrationCommand):
    """Revert every migration recorded on the connection."""

    # ruff: noqa: TC001

    # Command signature and description
    signature: str = "migrate:reset"

    # Command description
    description: str = "Reverts every applied database migration."

    async def handle(self, migrator: Migrator) -> None:
        """
        Revert every migration recorded on the connection.

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
        reverted = await migrator.reset(
            connection=self.targetConnection(),
            events=self.progressEvents(),
        )
        if not reverted:
            self.reportEmpty("Nothing to reset.")
