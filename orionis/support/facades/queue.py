"""Resolve the queue service through the application facade."""

from orionis.container.facades.facade import Facade
from orionis.queues.contracts.manager import IQueueManager


class Queue(Facade):
    """Resolve the queue service through the application facade."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @classmethod
    def getFacadeAccessor(cls) -> type[IQueueManager]:
        """
        Return the queue manager contract used by the application.

        Returns
        -------
        type[orionis.queues.contracts.manager.IQueueManager]
            Singleton manager binding.
        """
        return IQueueManager
