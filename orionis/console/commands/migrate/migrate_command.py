from orionis.console.commands.migrate.base_command import MigrationCommand
from orionis.database.migrations.migrator import Migrator

class MigrateCommand(MigrationCommand):
    """Apply every migration that has not been run yet."""

    # ruff: noqa: TC001

    # Command signature and description
    signature: str = "migrate"

    # Command description
    description: str = "Runs all pending database migrations."

    async def handle(self, migrator: Migrator) -> None:
        """
        Apply every migration that has not been run yet.

        Parameters
        ----------
        migrator : Migrator
            Service that discovers and applies pending migrations.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.newLine()
        applied = await migrator.migrate(
            connection=self.targetConnection(),
            events=self.progressEvents(),
        )
        if not applied:
            self.reportEmpty("Nothing to migrate. Database is already up to date.")
