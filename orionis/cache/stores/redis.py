from __future__ import annotations
from aiocache.backends.redis import RedisCache
from orionis.cache.serializers.json import MsgspecSerializer

def build(
    endpoint: str = "127.0.0.1",
    port: int = 6379,
    db: int = 0,
    password: str | None = None,
) -> RedisCache:
    """
    Build and return a ``RedisCache`` backend.

    Parameters
    ----------
    endpoint : str
        Redis host address.
    port : int
        Redis port.
    db : int
        Redis database index.
    password : str | None
        Redis authentication password.

    Returns
    -------
    RedisCache
        Configured aiocache Redis backend.
    """
    return RedisCache(
        endpoint=endpoint,
        port=int(port),
        db=int(db),
        password=password or None,
        serializer=MsgspecSerializer(),
    )
