"""Provide cache stores operations through ``build``."""

from __future__ import annotations
from aiocache import SimpleMemoryCache
from orionis.cache.serializers.json import MsgspecSerializer


class _MemoryCache(SimpleMemoryCache):
    """Cancel retired expiration callbacks when clearing the memory store."""

    async def _clear(
        self,
        namespace: str | None = None,
        _conn: object = None,
    ) -> bool:
        """Clear entries and release timers before their keys can be reused.

        Parameters
        ----------
        namespace : str | None
            Optional prefix limiting the keys removed by the backend.
        _conn : object
            Connection argument retained for the aiocache backend protocol.

        Returns
        -------
        bool
            Whether the backend completed its clear operation.
        """
        if not namespace:
            for timer in self._handlers.values():
                timer.cancel()
        return await super()._clear(namespace=namespace, _conn=_conn)


def build() -> SimpleMemoryCache:
    """
    Build and return a ``SimpleMemoryCache`` backend.

    The default ``NullSerializer`` is replaced with
    :class:`orionis.cache.serializers.json.MsgspecSerializer`
    so that all stored values pass through JSON encode/decode cycles,
    ensuring consistent behaviour across all drivers.

    Returns
    -------
    ``aiocache.SimpleMemoryCache``
        Configured aiocache in-memory backend.
    """
    return _MemoryCache(serializer=MsgspecSerializer())
