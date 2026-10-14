from __future__ import annotations
import sys
from typing import TYPE_CHECKING
from orionis.foundation.config.http.entitites.rate_limit import HTTPRateLimit
from orionis.http.layer.store.memory_rate_limit import MemoryRateLimitStore

if TYPE_CHECKING:
    from orionis.http.adapters.request.contracts.transport import TransportAdapter
    from orionis.http.default.contracts.responses import IDefaultResponses
    from orionis.http.responses import Response

class RateLimitMiddleware:

    # ruff: noqa: PLC0415

    __slots__ = (
        "__default_responses",
        "__rate_limit_enabled",
        "__rate_limit_requests",
        "__rate_limit_window_seconds",
        "__retry_after_value",
        "__store",
    )

    def __init__(
        self,
        config: dict,
        default_responses: IDefaultResponses,
    ) -> None:
        """Initialize the middleware with the given rate-limit configuration.

        Parameters
        ----------
        config : dict
            A dictionary whose keys must match ``HTTPRateLimit`` fields.
        default_responses : IDefaultResponses
            Predefined default responses for common HTTP errors.

        Returns
        -------
        None
            Configure the limiter and its enabled storage backend.
        """
        # Validate the raw configuration through the entity dataclass.
        cfg = HTTPRateLimit(**config)
        self.__rate_limit_enabled = cfg.rate_limit_enabled
        self.__rate_limit_requests = cfg.rate_limit_requests
        self.__rate_limit_window_seconds = cfg.rate_limit_window_seconds

        # Pre-render the Retry-After header value for rejection responses.
        self.__retry_after_value = str(cfg.rate_limit_window_seconds)

        self.__store = None
        if cfg.rate_limit_enabled:
            if cfg.rate_limit_store == "redis":
                from orionis.http.layer.store.redis_rate_limit import (
                    RedisRateLimitStore,
                )

                self.__store = RedisRateLimitStore(cfg)
            else:
                self.__store = MemoryRateLimitStore(
                    max_keys=cfg.rate_limit_max_keys,
                    max_events=cfg.rate_limit_max_events,
                )
        self.__default_responses = default_responses

    async def close(self) -> None:
        """
        Release an owned Redis connection pool during application shutdown.

        Returns
        -------
        None
            Leave quota state intact while closing network resources.
        """
        if self.__store is None or isinstance(self.__store, MemoryRateLimitStore):
            return

        from orionis.http.layer.store.redis_rate_limit import RedisRateLimitStore

        if isinstance(self.__store, RedisRateLimitStore):
            await self.__store.close()

    def isEnabled(self) -> bool:
        """
        Report whether rate limiting is active for this application.

        Returns
        -------
        bool
            ``True`` when the limiter is enabled, ``False`` otherwise.
        """
        return self.__rate_limit_enabled

    async def handle(
        self,
        adapter: TransportAdapter,
    ) -> Response | None:
        """Enforce the sliding-window rate limit for the incoming request.

        Skip disabled limits and unresolved client addresses.

        Parameters
        ----------
        adapter : TransportAdapter
            Transport abstraction providing client IP and header
            negotiation helpers.

        Returns
        -------
        Response | None
            Return 429 for exhausted quotas, 503 for Redis failures, or
            ``None`` when the request is allowed to proceed.
        """
        if not self.__rate_limit_enabled:
            return None

        # Skip rate-limiting when the client IP cannot be determined.
        client_ip = adapter.client()
        if not client_ip:
            return None

        try:
            allowed = await self.__store.hit(
                client_ip,
                self.__rate_limit_requests,
                self.__rate_limit_window_seconds,
            )
        except Exception as exc:
            # A Redis exception can only originate from an already loaded SDK.
            redis_exceptions = sys.modules.get("redis.exceptions")
            if redis_exceptions is None or not isinstance(
                exc, redis_exceptions.RedisError,
            ):
                raise
            return await self.__default_responses.error(
                status_code=503,
                content="Rate limit service unavailable",
                expects_json=adapter.wantsJson(),
                headers={"Retry-After": "1"},
            )

        # If the request exceeds the limit, return a 429 response with a
        # Retry-After header indicating when the client can retry.
        if not allowed:
            return await self.__default_responses.error(
                status_code=429,
                content="Too Many Requests",
                expects_json=adapter.wantsJson(),
                headers={
                    "Retry-After": self.__retry_after_value,
                },
            )

        return None
