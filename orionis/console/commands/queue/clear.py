"""Clear every pending state from one logical queue."""

from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.queues.contracts.manager import IQueueManager  # noqa: TC001
from orionis.queues.exceptions import QueueError

class QueueClearCommand(BaseCommand):
    """Clear every pending state from one logical queue."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    timestamps: bool = False
    """Timestamps flag used by ``QueueClearCommand``."""
    signature: str = "queue:clear"
    """Signature identifier: ``queue:clear``."""
    description: str = "Delete ready, delayed, and reserved jobs from a queue."
    """
    Description identifier: ``Delete ready, delayed, and reserved jobs from a
    queue.``.
    """
    arguments: ClassVar[list[Argument]] = [
        Argument(name_or_flags="connection", type_=str, nargs="?", default=None),
        Argument(name_or_flags="--queue", type_=str, default="default"),
    ]
    """Command-line argument declarations accepted by this command."""

    async def handle(self, manager: IQueueManager) -> int:
        """
        Remove the selected queue's jobs and report the count.

        Parameters
        ----------
        manager : orionis.queues.contracts.manager.IQueueManager
            Queue manager resolving the selected backend.

        Returns
        -------
        int
            Zero on success or one for an invalid backend or queue.
        """
        try:
            driver = await manager.connection(self.getArgument("connection"))
            cleared = await driver.clear(self.getArgument("queue", "default"))
        except QueueError as error:
            self.error(str(error), timestamp=False)
            return 1
        self.success(f"Cleared {cleared} job(s).", timestamp=False)
        return 0
