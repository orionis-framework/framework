from __future__ import annotations
from aiocache import SimpleMemoryCache
from orionis.cache.serializers.json import MsgspecSerializer

def build() -> SimpleMemoryCache:
    """
    Build and return a ``SimpleMemoryCache`` backend.

    The default ``NullSerializer`` is replaced with :class:`MsgspecSerializer`
    so that all stored values pass through JSON encode/decode cycles,
    ensuring consistent behaviour across all drivers.

    Returns
    -------
    SimpleMemoryCache
        Configured aiocache in-memory backend.
    """
    return SimpleMemoryCache(serializer=MsgspecSerializer())
