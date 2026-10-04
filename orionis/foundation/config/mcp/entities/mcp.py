from dataclasses import dataclass
from orionis.foundation.config.validation import (
    validate_http_origin, validate_integer, validate_seconds,
)
from orionis.support.entities.base import BaseEntity


@dataclass(frozen=True, slots=True, kw_only=True)
class McpConfig(BaseEntity):
    """Bound MCP work and explicitly allow trusted HTTP browser origins.

    An absent Origin is accepted by the transport. An empty ``allowed_origins``
    rejects every present Origin; there is no wildcard or implicit same-origin
    exception. Each allowed entry is a serialized HTTP(S) origin.
    """

    max_request_size: int = 1024 * 1024
    default_page_size: int = 50
    max_page_size: int = 100
    max_concurrent_requests: int = 32
    subscription_buffer_size: int = 64
    max_subscriptions: int = 1024
    max_resource_subscriptions: int = 64
    subscription_keepalive: float = 15.0
    allowed_origins: tuple[str, ...] = ()
    tool_search_max_results: int = 20
    tool_search_max_calls: int = 5
    tool_search_max_output_bytes: int = 256 * 1024
    max_response_size: int = 4 * 1024 * 1024
    max_metadata_size: int = 64 * 1024

    def __post_init__(self) -> None:
        """Reject coercion, unbounded budgets, and ambiguous origin allowlists.

        Returns
        -------
        None
            Retain validated immutable configuration.

        Raises
        ------
        TypeError
            If a budget, duration, or origin has an incompatible type.
        ValueError
            If a budget or duration is invalid, or an origin is malformed.
        """
        for name in (
            "max_request_size", "default_page_size", "max_page_size",
            "max_concurrent_requests", "subscription_buffer_size",
            "max_subscriptions", "max_resource_subscriptions",
            "tool_search_max_results", "tool_search_max_calls",
            "tool_search_max_output_bytes", "max_response_size",
            "max_metadata_size",
        ):
            validate_integer(getattr(self, name), name, minimum=1)
        validate_seconds(
            self.subscription_keepalive, "subscription_keepalive", positive=True,
        )
        if self.default_page_size > self.max_page_size:
            message = "default_page_size must not exceed max_page_size"
            raise ValueError(message)
        if not isinstance(self.allowed_origins, (list, tuple)):
            message = "allowed_origins must be a list or tuple of origin strings"
            raise TypeError(message)
        for origin in self.allowed_origins:
            validate_http_origin(origin)
        object.__setattr__(self, "allowed_origins", tuple(self.allowed_origins))

