"""Create the native scheduler task table without starting scheduled tasks."""

from orionis.console.base.command import BaseCommand
from orionis.console.contracts.store import IScheduleStore
from orionis.database.exceptions import DatabaseException

class ScheduleMigrateCommand(BaseCommand):
    """Create the native scheduler task table without starting scheduled tasks."""

    # ruff: noqa: TC001

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    timestamps: bool = False
    """Timestamps flag used by ``ScheduleMigrateCommand``."""
    signature: str = "schedule:migrate"
    """Signature identifier: ``schedule:migrate``."""
    description: str = "Create the configured database scheduler task table."
    """
    Description identifier: ``Create the configured database scheduler task
    table.``.
    """

    async def handle(self, store: IScheduleStore) -> int:
        """
        Create the native job store schema using the scheduler configuration.

        Parameters
        ----------
        store : orionis.console.contracts.store.IScheduleStore
            Service owning the database job store configuration and schema.

        Returns
        -------
        int
            Zero on success or one for configuration or database errors.
        """
        try:
            await store.migrate()
        except (DatabaseException, RuntimeError) as error:
            self.error(str(error), timestamp=False)
            return 1
        self.success("Scheduler table migrated successfully.", timestamp=False)
        return 0
