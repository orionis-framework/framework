from orionis.console.commands.migrate.base_command import MigrationCommand
from orionis.database.migrations.migrator import Migrator

class MigrateStatusCommand(MigrationCommand):
    """Report which migrations are applied and which are pending."""

    # ruff: noqa: TC001

    # Command signature and description
    signature: str = "migrate:status"

    # Command description
    description: str = "Shows the status of every discovered migration."

    async def handle(self, migrator: Migrator) -> None:
        """
        Print the applied/pending status of every migration.

        Parameters
        ----------
        migrator : Migrator
            Service that discovers migrations and reads their history.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.newLine()
        rows = await migrator.status(connection=self.targetConnection())
        if not rows:
            self.reportEmpty("No migrations were found.")
            return

        self.table(
            ["Migration", "Status", "Batch"],
            [
                [
                    row["migration"],
                    "Ran" if row["ran"] else "Pending",
                    str(row["batch"]) if row["batch"] is not None else "-",
                ]
                for row in rows
            ],
        )
        self.newLine()
