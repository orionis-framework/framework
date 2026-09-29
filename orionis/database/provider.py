from __future__ import annotations
from orionis.container.providers.service_provider import ServiceProvider
from orionis.database.connection_manager import ConnectionManager
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.orm.resolver import ConnectionResolver

class ConnectionManagerProvider(ServiceProvider):

    def register(self) -> None:
        """
        Register the connection manager as a singleton in the container.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.app.singleton(IConnectionManager, ConnectionManager)

    async def boot(self) -> None:
        """
        Wire the ORM resolver.

        Returns
        -------
        None
            This method does not return a value.
        """
        manager: IConnectionManager = await self.app.make(IConnectionManager)
        ConnectionResolver.setManager(manager)
