from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.queues.contracts.manager import IQueueManager  # noqa: TC001
from orionis.queues.exceptions import QueueError

class QueueRetryCommand(BaseCommand):
    """Redispatch one failed job through its original connection."""

    __slots__ = ()

    timestamps: bool = False
    signature: str = "queue:retry"
    description: str = "Retry a failed job by its identifier."
    arguments: ClassVar[list[Argument]] = [
        Argument(name_or_flags="id", type_=str, help="Failed job identifier."),
    ]

    async def handle(self, manager: IQueueManager) -> int:
        """
        Restore one failed payload with its preserved job identifier.

        Parameters
        ----------
        manager : IQueueManager
            Queue manager coordinating dispatch and failure record removal.

        Returns
        -------
        int
            Zero after redispatch or one when retry cannot be completed.
        """
        try:
            job_id = await manager.retryFailed(self.getArgument("id"))
        except QueueError as error:
            self.error(str(error), timestamp=False)
            return 1
        self.success(f"Job {job_id} queued for retry.", timestamp=False)
        return 0
