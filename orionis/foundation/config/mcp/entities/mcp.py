from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.environment import http_origins
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

    max_request_size: int = field(default_factory=lambda: Env.get(
        "MCP_MAX_REQUEST_SIZE", Env.get("HTTP_MAX_BODY_SIZE", 1024 * 1024),
    ))
    default_page_size: int = field(
        default_factory=lambda: Env.get("MCP_DEFAULT_PAGE_SIZE", 50),
    )
    max_page_size: int = field(
        default_factory=lambda: Env.get("MCP_MAX_PAGE_SIZE", 100),
    )
    max_concurrent_requests: int = field(default_factory=lambda: Env.get(
        "MCP_MAX_CONCURRENT_REQUESTS", Env.get("HTTP_MAX_CONCURRENT_REQUESTS", 32),
    ))
    subscription_buffer_size: int = field(
        default_factory=lambda: Env.get("MCP_SUBSCRIPTION_BUFFER_SIZE", 64),
    )
    max_subscriptions: int = field(
        default_factory=lambda: Env.get("MCP_MAX_SUBSCRIPTIONS", 1024),
    )
    max_resource_subscriptions: int = field(
        default_factory=lambda: Env.get("MCP_MAX_RESOURCE_SUBSCRIPTIONS", 64),
    )
    subscription_keepalive: float = field(
        default_factory=lambda: Env.get("MCP_SUBSCRIPTION_KEEPALIVE", 15.0),
    )
    allowed_origins: tuple[str, ...] = field(
        default_factory=lambda: http_origins("MCP_ALLOWED_ORIGINS"),
    )
    tool_search_max_results: int = field(
        default_factory=lambda: Env.get("MCP_TOOL_SEARCH_MAX_RESULTS", 20),
    )
    tool_search_max_calls: int = field(
        default_factory=lambda: Env.get("MCP_TOOL_SEARCH_MAX_CALLS", 5),
    )
    tool_search_max_output_bytes: int = field(
        default_factory=lambda: Env.get("MCP_TOOL_SEARCH_MAX_OUTPUT_BYTES", 256 * 1024),
    )
    max_response_size: int = field(
        default_factory=lambda: Env.get("MCP_MAX_RESPONSE_SIZE", 4 * 1024 * 1024),
    )
    max_metadata_size: int = field(
        default_factory=lambda: Env.get("MCP_MAX_METADATA_SIZE", 64 * 1024),
    )

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

