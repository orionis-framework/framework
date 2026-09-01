from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.foundation.config.http.entitites.rate_limit import HTTPRateLimit
from orionis.http.layer.store.memory_rate_limit import MemoryRateLimitStore

if TYPE_CHECKING:
    from orionis.http.adapters.request.contracts.transport import TransportAdapter
    from orionis.http.default.contracts.responses import IDefaultResponses
    from orionis.http.responses import Response

class RateLimitMiddleware:

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
        """
        # Validate the raw configuration through the entity dataclass.
        cfg = HTTPRateLimit(**config)
        self.__rate_limit_enabled = cfg.rate_limit_enabled
        self.__rate_limit_requests = cfg.rate_limit_requests
        self.__rate_limit_window_seconds = cfg.rate_limit_window_seconds

        # Pre-render the Retry-After header value for rejection responses.
        self.__retry_after_value = str(cfg.rate_limit_window_seconds)

        # The in-memory store is only needed when the limiter is active.
        self.__store = (
            MemoryRateLimitStore()
            if cfg.rate_limit_enabled
            else None
        )
        self.__default_responses = default_responses

    def isEnabled(self) -> bool:
        """Report whether rate limiting is active for this application.

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

        Skips enforcement when rate limiting is disabled or when the
        client IP cannot be resolved.  Returns a ``429`` response on
        the first request that exceeds the configured quota, or
        ``None`` when the request is within the allowed limit.

        Parameters
        ----------
        adapter : TransportAdapter
            Transport abstraction providing client IP and header
            negotiation helpers.

        Returns
        -------
        Response | None
            A ``429`` HTTP response when the limit is exceeded, or
            ``None`` when the request is allowed to proceed.
        """
        if not self.__rate_limit_enabled:
            return None

        # Skip rate-limiting when the client IP cannot be determined.
        client_ip = adapter.client()
        if not client_ip:
            return None

        allowed = await self.__store.hit(
            client_ip,
            self.__rate_limit_requests,
            self.__rate_limit_window_seconds,
        )

        # If the request exceeds the limit, return a 429 response with a
        # Retry-After header indicating when the client can retry.
        if not allowed:
            return self.__default_responses.error(
                status_code=429,
                content="Too Many Requests",
                expects_json=adapter.wantsJson(),
                headers={
                    "Retry-After": self.__retry_after_value,
                },
            )

        return None
