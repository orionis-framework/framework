from __future__ import annotations
from aiocache.backends.memcached import MemcachedCache
from orionis.cache.serializers.json import MsgspecSerializer

def build(
    endpoint: str = "127.0.0.1",
    port: int = 11211,
) -> MemcachedCache:
    """
    Build and return a ``MemcachedCache`` backend.

    Parameters
    ----------
    endpoint : str
        Memcached host address.
    port : int
        Memcached port.

    Returns
    -------
    MemcachedCache
        Configured aiocache Memcached backend.
    """
    return MemcachedCache(
        endpoint=endpoint,
        port=int(port),
        serializer=MsgspecSerializer(),
    )
