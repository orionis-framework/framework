from __future__ import annotations
from asyncio import timeout
from hashlib import sha256
from typing import TYPE_CHECKING
from uuid import uuid4
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import TimeoutError as RedisTimeoutError

if TYPE_CHECKING:
    from orionis.foundation.config.http.entitites.rate_limit import HTTPRateLimit

# Redis owns the clock and makes expiration, quota checking and insertion atomic.
_HIT = """
local time = redis.call('TIME')
local now = tonumber(time[1]) * 1000000 + tonumber(time[2])
local window = tonumber(ARGV[2]) * 1000000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then return 0 end
redis.call('ZADD', KEYS[1], now, ARGV[3])
redis.call('PEXPIRE', KEYS[1], tonumber(ARGV[2]) * 1000)
return 1
"""

class RedisRateLimitStore:
    """Share sliding-window quotas using a single-key atomic Redis script."""

    __slots__ = ("__client", "__owns_client", "__prefix", "__timeout")

    def __init__(
        self,
        config: HTTPRateLimit,
        *,
        client: Redis | None = None,
    ) -> None:
        """
        Build a lazy Redis connection, optionally using an external client.

        Parameters
        ----------
        config : HTTPRateLimit
            Validated connection URL, namespace and operation timeout.
        client : Redis | None, optional
            Externally owned transport. The caller remains responsible for it.

        Returns
        -------
        None
            Prepare the backend without opening a network connection.
        """
        self.__prefix = config.rate_limit_redis_prefix
        self.__timeout = config.rate_limit_redis_timeout_seconds
        self.__owns_client = client is None
        self.__client = client if client is not None else Redis.from_url(
            config.rate_limit_redis_url,
            socket_connect_timeout=config.rate_limit_redis_timeout_seconds,
            socket_timeout=config.rate_limit_redis_timeout_seconds,
            retry_on_timeout=False,
            retry=Retry(NoBackoff(), 0),
            max_connections=100,
            protocol=2,
        )

    async def hit(self, key: str, limit: int, window: int) -> bool:
        """
        Accept an attempt only when its distributed sliding quota permits.

        Parameters
        ----------
        key : str
            Client identity. Only its SHA-256 digest is persisted in Redis.
        limit : int
            Maximum accepted attempts in the window.
        window : int
            Window duration in seconds, consistent across all workers.

        Returns
        -------
        bool
            Whether Redis atomically accepted the attempt.

        Raises
        ------
        redis.exceptions.RedisError
            When storage is unavailable or contains an incompatible key type.
        """
        if limit <= 0:
            return False
        digest = sha256(key.encode()).hexdigest()
        redis_key = f"{self.__prefix}:{digest}"
        try:
            async with timeout(self.__timeout):
                result = await self.__client.eval(
                    _HIT, 1, redis_key, limit, window, uuid4().hex,
                )
        except TimeoutError as exc:
            error_msg = "Rate-limit Redis operation timed out."
            raise RedisTimeoutError(error_msg) from exc
        return bool(result)

    async def close(self) -> None:
        """
        Close connections created by this store without deleting quotas.

        Returns
        -------
        None
            Release an owned client's connection pool.
        """
        if self.__owns_client:
            await self.__client.aclose()
