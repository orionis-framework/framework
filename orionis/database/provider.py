from __future__ import annotations
from orionis.container.providers.service_provider import ServiceProvider
from orionis.database.contracts.connection_manager import IConnectionManager

class ConnectionManagerProvider(ServiceProvider):

    # ruff: noqa: PLC0415

    def register(self) -> None:
        """
        Register the connection manager as a singleton in the container.

        Returns
        -------
        None
            Register the connection manager binding.
        """
        from orionis.database import ConnectionManager
        self.app.singleton(IConnectionManager, ConnectionManager)

    async def boot(self) -> None:
        """
        Wire the ORM resolver.

        Returns
        -------
        None
            Install the resolved manager in the ORM resolver.
        """
        from orionis.orm.resolver import ConnectionResolver

        manager: IConnectionManager = await self.app.make(IConnectionManager)
        ConnectionResolver.setManager(manager)
