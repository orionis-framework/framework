from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class HTTPRateLimit(BaseEntity):

    rate_limit_enabled: bool = field(
        default_factory=lambda: Env.get("RATE_LIMIT_ENABLED", False),
        metadata={
            "description": (
                "Enable or disable global rate limiting."
            ),
        },
    )

    rate_limit_requests: int = field(
        default_factory=lambda: int(Env.get("RATE_LIMIT_REQUESTS", 100)),
        metadata={
            "description": (
                "Maximum number of requests allowed "
                "per window."
            ),
        },
    )

    rate_limit_window_seconds: int = field(
        default_factory=lambda: int(Env.get("RATE_LIMIT_WINDOW", 60)),
        metadata={
            "description": (
                "Time window in seconds for rate "
                "limit counting."
            ),
        },
    )

    def __post_init__(self) -> None:
        """Validate rate-limiting fields.

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

    def __validateRateLimiting(self) -> None:
        """Validate rate-limiting constraints.

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

        if (
            not isinstance(self.rate_limit_requests, int)
            or isinstance(self.rate_limit_requests, bool)
        ):
            error_msg = "Invalid type for 'rate_limit_requests': expected an integer."
            raise TypeError(error_msg)

        if self.rate_limit_requests <= 0:
            error_msg = (
                "Invalid value for 'rate_limit_requests': must be a positive integer."
            )
            raise ValueError(error_msg)

        if (
            not isinstance(self.rate_limit_window_seconds, int)
            or isinstance(self.rate_limit_window_seconds, bool)
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
