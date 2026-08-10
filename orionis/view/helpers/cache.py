from __future__ import annotations
from typing import TYPE_CHECKING, Any
from orionis.cache.contracts.cache_manager import ICacheManager

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

# ruff: noqa: ANN401

def _global_cache(app: IApplication) -> Any:
    """
    Build the ``cache`` template global.

    Parameters
    ----------
    app : IApplication
        Application container to expose in templates.

    Returns
    -------
    Any
        Callable returning the application instance.
    """

    async def cache(key: str, default: Any | None = None) -> Any:
        """
        Retrieve the value from the cache using the application's cache manager.

        Parameters
        ----------
        key : str
            The cache key.
        default : Any | None, optional
            The default value to return if the cache key is not found.

        Returns
        -------
        Any
            The cached value or the default value if the key is not found.
        """
        cache_manager: ICacheManager = await app.make(ICacheManager)
        value: Any | None = await cache_manager.get(key)
        return value if value is not None else default

    return cache
