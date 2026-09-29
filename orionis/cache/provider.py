from orionis.cache.cache_manager import CacheManager
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.providers.service_provider import ServiceProvider
from orionis.support.facades.cache import Cache as CacheFacade

class CacheProvider(ServiceProvider, DeferrableProvider):
    """
    Service provider for the Orionis cache system.

    Binds :class:`ICacheManager` to :class:`CacheManager` as a singleton
    and pins the :class:`Cache` facade so that attribute access is direct
    without container resolution overhead on every call.
    """

    @classmethod
    def provides(cls) -> list[type]:
        """
        Return the services registered by this provider.

        Returns
        -------
        list[type]
            List containing :class:`ICacheManager`.
        """
        return [ICacheManager]

    def register(self) -> None:
        """
        Bind ICacheManager to CacheManager as a singleton.

        Returns
        -------
        None
        """
        self.app.singleton(ICacheManager, CacheManager)

    async def boot(self) -> None:
        """
        Pin the Cache facade after all services are registered.

        Returns
        -------
        None
        """
        await CacheFacade.pin()
