# ruff: noqa: PLC0415
"""Service provider for the Orionis cache system."""

from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.providers.service_provider import ServiceProvider
from orionis.support.facades.cache import Cache as CacheFacade


class CacheProvider(ServiceProvider, DeferrableProvider):
    """
    Service provider for the Orionis cache system.

    Binds :class:`orionis.cache.contracts.ICacheManager` to
    :class:`orionis.cache.CacheManager` as a singleton
    and pins the ``Cache`` facade when this deferrable provider boots, so
    later attribute access avoids container resolution on every call.
    """

    @classmethod
    def provides(cls) -> list[type]:
        """
        Return the services registered by this provider.

        Returns
        -------
        list[type]
            List containing :class:`orionis.cache.contracts.ICacheManager`.
        """
        return [ICacheManager]

    def register(self) -> None:
        """Bind ICacheManager to CacheManager as a singleton.

        Returns
        -------
        None
            No return value.
        """
        from orionis.cache import CacheManager

        self.app.singleton(ICacheManager, CacheManager)

    async def boot(self) -> None:
        """Pin the Cache facade after all services are registered.

        Returns
        -------
        None
            No return value.
        """
        await CacheFacade.pin()
