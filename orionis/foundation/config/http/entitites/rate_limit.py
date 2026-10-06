from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.http.entitites.redis import Redis
from orionis.foundation.config.validation import validate_integer, validate_string
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class HTTPRateLimit(BaseEntity):
    """
    Represent the rate-limiting configuration for HTTP.

    Attributes
    ----------
    rate_limit_enabled : bool
        Whether global rate limiting is enabled.
    rate_limit_requests : int
        Maximum number of requests allowed per window.
    rate_limit_window_seconds : int
        Time window in seconds for rate limit counting.
    rate_limit_store : str
        ``memory`` for one process or ``redis`` for shared worker quotas.
    rate_limit_max_keys : int
        Maximum retained clients in the memory store.
    rate_limit_max_events : int
        Maximum retained accepted timestamps in the memory store.
    rate_limit_redis : Redis | dict
        Redis connection settings, used only by the Redis store.
    rate_limit_redis_prefix : str
        Application namespace for Redis quota keys.
    rate_limit_redis_timeout_seconds : int
        Bound Redis connect and socket operations in seconds.
    """

    rate_limit_enabled: bool = field(
        default_factory=lambda: Env.get("RATE_LIMIT_ENABLED", False),
        metadata={
            "description": ("Enable or disable global rate limiting."),
            "default": False,
        },
    )

    rate_limit_requests: int = field(
        default_factory=lambda: Env.get("RATE_LIMIT_REQUESTS", 100),
        metadata={
            "description": ("Maximum number of requests allowed per window."),
            "default": 100,
        },
    )

    rate_limit_window_seconds: int = field(
        default_factory=lambda: Env.get("RATE_LIMIT_WINDOW", 60),
        metadata={
            "description": ("Time window in seconds for rate limit counting."),
            "default": 60,
        },
    )

    rate_limit_store: str = field(
        default_factory=lambda: Env.get("RATE_LIMIT_STORE", "memory"),
        metadata={
            "description": "Rate-limit backend.",
            "default": "memory",
        },
    )

    rate_limit_max_keys: int = field(
        default_factory=lambda: Env.get("RATE_LIMIT_MAX_KEYS", 10_000),
        metadata={
            "description": "Memory client capacity.",
            "default": 10_000,
        },
    )

    rate_limit_max_events: int = field(
        default_factory=lambda: Env.get("RATE_LIMIT_MAX_EVENTS", 100_000),
        metadata={
            "description": "Memory timestamp capacity.",
            "default": 100_000,
        },
    )

    rate_limit_redis: Redis | dict = field(
        default_factory=Redis,
        metadata={
            "description": "Redis connection settings.",
            "default": lambda: Redis().toDict(),
        },
    )

    rate_limit_redis_prefix: str = field(
        default_factory=lambda: Env.get(
            "RATE_LIMIT_REDIS_PREFIX", "orionis:http:rate-limit",
        ),
        metadata={
            "description": "Application namespace for Redis rate limits.",
            "default": "orionis:http:rate-limit",
        },
    )

    rate_limit_redis_timeout_seconds: int = field(
        default_factory=lambda: Env.get("RATE_LIMIT_REDIS_TIMEOUT", 1),
        metadata={"description": "Redis operation timeout.", "default": 1},
    )

    def __post_init__(self) -> None:
        """
        Validate rate-limiting fields.

        Raises
        ------
        TypeError
            If any field has an unexpected type.
        ValueError
            If numeric fields are not positive.

        Returns
        -------
        None
        """
        super().__post_init__()
        self.__validateRateLimiting()
        self.__validateStore()

    def __validateStore(self) -> None:
        """
        Validate backend selection, bounded capacity and Redis transport.

        Returns
        -------
        None
            Reject invalid backend settings during configuration loading.
        """
        validate_string(self.rate_limit_store, "rate_limit_store")
        if self.rate_limit_store not in {"memory", "redis"}:
            error_msg = "'rate_limit_store' must be 'memory' or 'redis'."
            raise ValueError(error_msg)
        for name in (
            "rate_limit_max_keys", "rate_limit_max_events",
            "rate_limit_redis_timeout_seconds",
        ):
            validate_integer(getattr(self, name), name, minimum=1)
        if isinstance(self.rate_limit_redis, dict):
            object.__setattr__(
                self, "rate_limit_redis", Redis(**self.rate_limit_redis),
            )
        elif not isinstance(self.rate_limit_redis, Redis):
            error_msg = "'rate_limit_redis' must be a Redis instance or dict."
            raise TypeError(error_msg)
        validate_string(self.rate_limit_redis_prefix, "rate_limit_redis_prefix")

    def __validateRateLimiting(self) -> None:
        """
        Validate rate-limiting constraints.

        Check ``rate_limit_enabled``,
        ``rate_limit_requests``, and
        ``rate_limit_window_seconds``.

        Raises
        ------
        TypeError
            If any field has an unexpected type.
        ValueError
            If numeric fields are not positive.

        Returns
        -------
        None
        """
        if not isinstance(self.rate_limit_enabled, bool):
            error_msg = "Invalid type for 'rate_limit_enabled': expected a boolean."
            raise TypeError(error_msg)

        if not isinstance(self.rate_limit_requests, int) or isinstance(
            self.rate_limit_requests,
            bool,
        ):
            error_msg = "Invalid type for 'rate_limit_requests': expected an integer."
            raise TypeError(error_msg)

        if self.rate_limit_requests <= 0:
            error_msg = (
                "Invalid value for 'rate_limit_requests': must be a positive integer."
            )
            raise ValueError(error_msg)

        if not isinstance(self.rate_limit_window_seconds, int) or isinstance(
            self.rate_limit_window_seconds,
            bool,
        ):
            error_msg = (
                "Invalid type for 'rate_limit_window_seconds': expected an integer."
            )
            raise TypeError(error_msg)

        if self.rate_limit_window_seconds <= 0:
            error_msg = (
                "Invalid value for 'rate_limit_window_seconds': "
                "must be a positive integer."
            )
            raise ValueError(error_msg)
