# ruff: noqa: PLC0415
"""Service provider for the Orionis storage system."""

from __future__ import annotations
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.providers.service_provider import ServiceProvider
from orionis.storage.contracts.manager import IStorageManager
from orionis.support.facades.storage import Storage as StorageFacade


class StorageProvider(ServiceProvider, DeferrableProvider):
    """
    Service provider for the Orionis storage system.

    Binds :class:`orionis.storage.contracts.IStorageManager` to
    :class:`orionis.storage.StorageManager` as a
    singleton and pins the :class:`orionis.support.facades.Storage` facade
    when this deferrable provider boots. Later attribute access avoids
    container resolution on every call.
    """

    @classmethod
    def provides(cls) -> list[type]:
        """
        Return the services registered by this provider.

        Returns
        -------
        list[type]
            List containing :class:`orionis.storage.contracts.IStorageManager`.
        """
        return [IStorageManager]

    def register(self) -> None:
        """
        Bind IStorageManager to StorageManager as a singleton.

        Returns
        -------
        None
            No return value.
        """
        from orionis.storage import StorageManager

        self.app.singleton(IStorageManager, StorageManager)

    async def boot(self) -> None:
        """
        Pin the Storage facade after all services are registered.

        Returns
        -------
        None
            No return value.
        """
        await StorageFacade.pin()
