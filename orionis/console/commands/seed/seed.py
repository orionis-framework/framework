from orionis.console.commands.migrate.base import MigrationCommand
from orionis.database.seeders.runner import SeederRunner

class SeedCommand(MigrationCommand):
    """Apply every database seeder that has not been run yet."""

    # ruff: noqa: TC001

    signature: str = "seed"
    description: str = "Runs all pending database seeders."

    async def handle(self, seeder_runner: SeederRunner) -> None:
        """
        Apply pending seeders on the selected database connection.

        Parameters
        ----------
        seeder_runner : SeederRunner
            Service that discovers and runs pending seeders.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.newLine()
        applied = await seeder_runner.seed(
            connection=self.targetConnection(),
            events=self.progressEvents(),
        )
        if not applied:
            self.reportEmpty("Nothing to seed. Database is already up to date.")
