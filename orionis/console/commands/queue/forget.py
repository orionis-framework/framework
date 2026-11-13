# ruff: noqa: TC001
# Keep runtime reflection annotations and intentionally deferred imports.
"""Remove one failed job record."""

from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.queues.contracts.manager import IQueueManager
from orionis.queues.exceptions import QueueError


class QueueForgetCommand(BaseCommand):
    """Remove one failed job record."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    timestamps: bool = False
    """Timestamps flag used by ``QueueForgetCommand``."""
    signature: str = "queue:forget"
    """Signature identifier: ``queue:forget``."""
    description: str = "Delete a failed job by its identifier."
    """Description identifier: ``Delete a failed job by its identifier.``."""
    arguments: ClassVar[list[Argument]] = [
        Argument(name_or_flags="id", type_=str, help="Failed job identifier."),
    ]
    """Command-line argument declarations accepted by this command."""

    async def handle(self, manager: IQueueManager) -> int:
        """
        Delete the selected failure record and report missing identifiers.

        Parameters
        ----------
        manager : orionis.queues.contracts.manager.IQueueManager
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
