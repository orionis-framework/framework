from orionis.console.base.command import BaseCommand
from orionis.database.exceptions import DatabaseException
from orionis.queues.contracts.manager import IQueueManager  # noqa: TC001
from orionis.queues.exceptions import QueueError

class QueueMigrateCommand(BaseCommand):
    """Create all configured queue tables without removing existing data."""

    __slots__ = ()

    timestamps: bool = False
    signature: str = "queue:migrate"
    description: str = "Create database queue tables and failed-job storage."

    async def handle(self, manager: IQueueManager) -> int:
        """
        Prepare every database queue connection and central failure storage.

        Parameters
        ----------
        manager : IQueueManager
            Queue manager providing the configured storage definitions.

        Returns
        -------
        int
            Zero on success or one for queue configuration or database errors.
        """
        try:
            await manager.migrate()
        except (DatabaseException, QueueError) as error:
            self.error(str(error), timestamp=False)
            return 1
        self.success("Queue tables migrated successfully.", timestamp=False)
        return 0
