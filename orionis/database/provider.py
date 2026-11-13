# ruff: noqa: PLC0415
# Import database and ORM services only when the provider is activated.
"""Register connection manager services in the application container."""

from __future__ import annotations
from orionis.container.providers.service_provider import ServiceProvider
from orionis.database.contracts.connection_manager import IConnectionManager


class ConnectionManagerProvider(ServiceProvider):
    """Register connection manager services in the application container."""

    def register(self) -> None:
        """
        Register the connection manager as a singleton in the container.

        Returns
        -------
        None
            No return value.
        """
        from orionis.database import ConnectionManager

        self.app.singleton(IConnectionManager, ConnectionManager)

    async def boot(self) -> None:
        """
        Wire the ORM resolver.

        Returns
        -------
        None
            No return value.
        """
        from orionis.orm.resolver import ConnectionResolver

        manager: IConnectionManager = await self.app.make(IConnectionManager)
        ConnectionResolver.setManager(manager)
