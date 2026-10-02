from orionis.container.facades.facade import Facade
from orionis.queues.contracts.manager import IQueueManager

class Queue(Facade):

    __slots__ = ()

    @classmethod
    def getFacadeAccessor(cls) -> type[IQueueManager]:
        """Return the queue manager contract used by the application.

        Returns
        -------
        type[IQueueManager]
            Singleton manager binding.
        """
        return IQueueManager
