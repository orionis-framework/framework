# ruff: noqa: ANN401, TC001, TC003
# Keep public callback and application annotations resolvable at runtime.
# Preserve heterogeneous template payload values.
"""Provide view globals operations through ``_global_cache``."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.foundation.contracts.application import IApplication


def _global_cache(app: IApplication) -> Callable[..., Awaitable[Any]]:
    """
    Build the ``cache`` template global.

    Parameters
    ----------
    app : orionis.IApplication
        Application container to expose in templates.

    Returns
    -------
    collections.abc.Callable
        Async callable reading the configured cache store.
    """

    async def cache(key: str, default: Any | None = None) -> Any:
        """
        Retrieve the value from the cache using the application's cache manager.

        Parameters
        ----------
        key : str
            The cache key.
        default : typing.Any | None, optional
            The default value to return if the cache key is not found.

        Returns
        -------
        typing.Any
            The cached value or the default value if the key is not found.
        """
        cache_manager: ICacheManager = await app.make(ICacheManager)
        value: Any | None = await cache_manager.get(key)
        return value if value is not None else default

    return cache
