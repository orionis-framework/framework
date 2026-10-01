from orionis.console.commands.migrate.base import MigrationCommand
from orionis.database.migrations.migrator import Migrator

class MigrateFreshCommand(MigrationCommand):
    """Clear migration and seeder history, then rebuild the schema."""

    # ruff: noqa: TC001

    signature: str = "migrate:fresh"
    description: str = "Clears migration and seeder history, then migrates."

    async def handle(self, migrator: Migrator) -> None:
        """
        Clear migration and seeder history, then apply every migration.

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
