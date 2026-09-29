from __future__ import annotations
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.providers.service_provider import ServiceProvider
from orionis.storage.contracts.manager import IStorageManager
from orionis.storage.manager import StorageManager
from orionis.support.facades.storage import Storage as StorageFacade

class StorageProvider(ServiceProvider, DeferrableProvider):
    """
    Service provider for the Orionis storage system.

    Binds :class:`IStorageManager` to :class:`StorageManager` as a
    singleton and pins the :class:`Storage` facade so that attribute
    access is direct without container resolution overhead on every
    call.
    """

    @classmethod
    def provides(cls) -> list[type]:
        """
        Return the services registered by this provider.

        Returns
        -------
        list[type]
            List containing :class:`IStorageManager`.
        """
        return [IStorageManager]

    def register(self) -> None:
        """
        Bind IStorageManager to StorageManager as a singleton.

        Returns
        -------
        None
        """
        self.app.singleton(IStorageManager, StorageManager)

    async def boot(self) -> None:
        """
        Pin the Storage facade after all services are registered.

        Returns
        -------
        None
        """
        await StorageFacade.pin()
