from orionis.container.providers.service_provider import ServiceProvider
from orionis.foundation.enums.lifespan import Lifespan
from orionis.queues.contracts.manager import IQueueManager
from orionis.queues.contracts.serializer import IJobSerializer
from orionis.queues.manager import QueueManager
from orionis.queues.serializer import JobSerializer
from orionis.support.facades.queue import Queue

class QueueProvider(ServiceProvider):
    """
    Register queue services eagerly while keeping backend I/O lazy.

    Pin the queue facade at startup and close queue-owned resources at shutdown.
    """

    __slots__ = ()

    def register(self) -> None:
        """
        Bind the job serializer and queue manager as application singletons.

        Returns
        -------
        None
            Register singleton bindings for lazy service resolution.
        """
        self.app.singleton(IJobSerializer, JobSerializer)
        self.app.singleton(IQueueManager, QueueManager)

    async def boot(self) -> None:
        """
        Discover application jobs and configure the queue service lifecycle.

        Returns
        -------
        None
            Register discovered jobs, attach the manager's shutdown callback,
            and pin the queue facade for direct pending dispatch.

        Raises
        ------
        QueueConfigurationError
            If the jobs path is invalid or a discovered module cannot be imported.
        """
        manager = await self.app.make(IQueueManager)
        await manager.boot()
        self.app.on(Lifespan.SHUTDOWN, manager.close)
        await Queue.pin()
