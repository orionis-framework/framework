from typing import ClassVar

from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.queues.contracts.manager import IQueueManager  # noqa: TC001
from orionis.queues.exceptions import QueueError


class QueueForgetCommand(BaseCommand):
    """Remove one failed job record."""

    __slots__ = ()

    timestamps: bool = False
    signature: str = "queue:forget"
    description: str = "Delete a failed job by its identifier."
    arguments: ClassVar[list[Argument]] = [
        Argument(name_or_flags="id", type_=str, help="Failed job identifier."),
    ]

    async def handle(self, manager: IQueueManager) -> int:
        """Delete the selected failure record and report missing identifiers.

        Parameters
        ----------
        manager : IQueueManager
            Queue manager providing persistent failure storage.

        Returns
        -------
        int
            Zero when the record is deleted or one when it is missing.
        """
        try:
            repository = await manager.failed()
            deleted = await repository.forget(self.getArgument("id"))
        except QueueError as error:
            self.error(str(error), timestamp=False)
            return 1
        if not deleted:
            self.error("Failed job not found.", timestamp=False)
            return 1
        self.success("Failed job deleted.", timestamp=False)
        return 0
