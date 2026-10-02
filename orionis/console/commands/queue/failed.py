from orionis.console.base.command import BaseCommand
from orionis.queues.contracts.manager import IQueueManager  # noqa: TC001
from orionis.queues.exceptions import QueueError


class QueueFailedCommand(BaseCommand):
    """List persistent failed jobs and their original exceptions."""

    __slots__ = ()

    timestamps: bool = False
    signature: str = "queue:failed"
    description: str = "List failed queue jobs."

    async def handle(self, manager: IQueueManager) -> int:
        """Display job identifiers, routing, attempts, and exceptions.

        Parameters
        ----------
        manager : IQueueManager
            Queue manager providing the failure repository.

        Returns
        -------
        int
            Zero on success or one when failure storage is unavailable.
        """
        try:
            repository = await manager.failed()
            failures = await repository.all()
        except QueueError as error:
            self.error(str(error), timestamp=False)
            return 1
        if not failures:
            self.info("No failed jobs.", timestamp=False)
        for failed in failures:
            self.info(
                f"{failed.id} | job={failed.job_id} | "
                f"{failed.connection}/{failed.queue} | "
                f"attempts={failed.attempts} | {failed.exception_type}: "
                f"{failed.exception_message}",
                timestamp=False,
            )
        return 0
