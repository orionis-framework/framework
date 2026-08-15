from orionis.container.providers.service_provider import ServiceProvider
from orionis.hashing.contracts.hash_manager import IHashManager
from orionis.hashing.hash_manager import HashManager
from orionis.support.facades.hash import Hash as HashFacade

class HashProvider(ServiceProvider):
    """
    Service provider for the Orionis hashing system.

    Binds :class:`IHashManager` to :class:`HashManager` as a singleton and
    pins the :class:`Hash` facade so ``Hash.make(...)`` resolves without
    container overhead on every call.
    """

    def register(self) -> None:
        """
        Bind IHashManager to HashManager as a singleton.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.app.singleton(IHashManager, HashManager)

    async def boot(self) -> None:
        """
        Pin the Hash facade after all services are registered.

        Returns
        -------
        None
            This method does not return a value.
        """
        await HashFacade.pin()
