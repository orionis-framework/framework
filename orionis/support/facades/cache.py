from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.container.facades.facade import Facade


class Cache(Facade):
    """
    Facade for the cache system.

    Proxies all calls to the bound :class:`ICacheManager` singleton.

    Usage (facade pinned at boot)::

        value = await Cache.get("key")
        await Cache.set("key", "value", ttl=60)
        repo  = Cache.store("redis")          # sync — returns CacheRepository
        value = await repo.get("key")

        async with Cache.lock("resource", timeout=5):
            ...
    """

    @classmethod
    def getFacadeAccessor(cls) -> type:
        """
        Return the container accessor for the cache manager.

        Returns
        -------
        type
            :class:`ICacheManager`.
        """
        return ICacheManager
