from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.validation import (
    validate_http_origin,
    validate_integer,
    validate_seconds,
)
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, slots=True, kw_only=True)
class McpConfig(BaseEntity):
    """
    Bound MCP work and explicitly allow trusted HTTP browser origins.

    Read environment defaults when each instance is created. Explicit constructor
    values take precedence and supplied origin lists are copied to immutable tuples.

    An absent Origin is accepted by the transport. An empty ``allowed_origins``
    rejects every present Origin; there is no wildcard or implicit same-origin
    exception. Each allowed entry is a serialized HTTP(S) origin. Defaults come
    directly from the shared ``CORS_ALLOW_ORIGINS`` environment variable.

    Attributes
    ----------
    max_request_size : int
        Maximum serialized request size in bytes. Read ``MCP_MAX_REQUEST_SIZE``,
        then ``HTTP_MAX_BODY_SIZE``, with a final default of 1 MiB.
    default_page_size : int
        Default number of entries returned by paginated list operations.
        Read ``MCP_DEFAULT_PAGE_SIZE`` with a default of 50.
    max_page_size : int
        Maximum entries per page; must be at least ``default_page_size``.
        Read ``MCP_MAX_PAGE_SIZE`` with a default of 100.
    max_concurrent_requests : int
        Maximum concurrent MCP requests. Read ``MCP_MAX_CONCURRENT_REQUESTS``,
        then ``HTTP_MAX_CONCURRENT_REQUESTS``, with a final default of 32.
    subscription_buffer_size : int
        Maximum buffered events per subscription.
        Read ``MCP_SUBSCRIPTION_BUFFER_SIZE`` with a default of 64.
    max_subscriptions : int
        Maximum total event-bus subscriptions.
        Read ``MCP_MAX_SUBSCRIPTIONS`` with a default of 1024.
    max_resource_subscriptions : int
        Maximum resource subscriptions per request or client context.
        Read ``MCP_MAX_RESOURCE_SUBSCRIPTIONS`` with a default of 64.
    subscription_keepalive : float
        Finite positive interval in seconds between subscription keepalive messages.
        Read ``MCP_SUBSCRIPTION_KEEPALIVE`` with a default of 15.0.
    allowed_origins : tuple[str, ...]
        Explicit trusted HTTP(S) browser origins without wildcards.
        Read ``CORS_ALLOW_ORIGINS`` with a default of an empty tuple.
    tool_search_max_results : int
        Maximum results returned by a tool catalog search.
        Read ``MCP_TOOL_SEARCH_MAX_RESULTS`` with a default of 20.
    tool_search_max_calls : int
        Maximum tool calls allowed in one catalog execution.
        Read ``MCP_TOOL_SEARCH_MAX_CALLS`` with a default of 5.
    tool_search_max_output_bytes : int
        Maximum serialized tool catalog output size in bytes.
        Read ``MCP_TOOL_SEARCH_MAX_OUTPUT_BYTES`` with a default of 256 KiB.
    max_response_size : int
        Maximum serialized response size in bytes.
        Read ``MCP_MAX_RESPONSE_SIZE`` with a default of 4 MiB.
    max_metadata_size : int
        Maximum serialized request or response metadata size in bytes.
        Read ``MCP_MAX_METADATA_SIZE`` with a default of 64 KiB.
    """

    max_request_size: int = field(
        default_factory=lambda: Env.get(
            "MCP_MAX_REQUEST_SIZE", Env.get("HTTP_MAX_BODY_SIZE", 1024 * 1024),
        ),
        metadata={
            "description": "Maximum serialized MCP request size in bytes.",
            "default": 1024 * 1024,
        },
    )

    default_page_size: int = field(
        default_factory=lambda: Env.get("MCP_DEFAULT_PAGE_SIZE", 50),
        metadata={
            "description": "Default entries returned by paginated list operations.",
            "default": 50,
        },
    )

    max_page_size: int = field(
        default_factory=lambda: Env.get("MCP_MAX_PAGE_SIZE", 100),
        metadata={
            "description": "Maximum entries returned in one page.",
            "default": 100,
        },
    )

    max_concurrent_requests: int = field(
        default_factory=lambda: Env.get(
            "MCP_MAX_CONCURRENT_REQUESTS", Env.get("HTTP_MAX_CONCURRENT_REQUESTS", 32),
        ),
        metadata={
            "description": "Maximum concurrent MCP requests.",
            "default": 32,
        },
    )

    subscription_buffer_size: int = field(
        default_factory=lambda: Env.get("MCP_SUBSCRIPTION_BUFFER_SIZE", 64),
        metadata={
            "description": "Maximum event buffer size per subscription.",
            "default": 64,
        },
    )

    max_subscriptions: int = field(
        default_factory=lambda: Env.get("MCP_MAX_SUBSCRIPTIONS", 1024),
        metadata={
            "description": "Maximum total event-bus subscriptions.",
            "default": 1024,
        },
    )

    max_resource_subscriptions: int = field(
        default_factory=lambda: Env.get("MCP_MAX_RESOURCE_SUBSCRIPTIONS", 64),
        metadata={
            "description": (
                "Maximum resource subscriptions per request or client context."
            ),
            "default": 64,
        },
    )

    subscription_keepalive: float = field(
        default_factory=lambda: Env.get("MCP_SUBSCRIPTION_KEEPALIVE", 15.0),
        metadata={
            "description": "Seconds between subscription keepalive messages.",
            "default": 15.0,
        },
    )

    allowed_origins: tuple[str, ...] = field(
        default_factory=lambda: Env.get("CORS_ALLOW_ORIGINS", ()),
        metadata={
            "description": (
                "Explicit trusted HTTP(S) browser origins without wildcards; "
                "empty rejects every present Origin header."
            ),
            "default": (),
        },
    )

    tool_search_max_results: int = field(
        default_factory=lambda: Env.get("MCP_TOOL_SEARCH_MAX_RESULTS", 20),
        metadata={
            "description": "Maximum results returned by a tool catalog search.",
            "default": 20,
        },
    )

    tool_search_max_calls: int = field(
        default_factory=lambda: Env.get("MCP_TOOL_SEARCH_MAX_CALLS", 5),
        metadata={
            "description": "Maximum tool calls allowed in one catalog execution.",
            "default": 5,
        },
    )

    tool_search_max_output_bytes: int = field(
        default_factory=lambda: Env.get("MCP_TOOL_SEARCH_MAX_OUTPUT_BYTES", 256 * 1024),
        metadata={
            "description": "Maximum serialized tool catalog output size in bytes.",
            "default": 256 * 1024,
        },
    )

    max_response_size: int = field(
        default_factory=lambda: Env.get("MCP_MAX_RESPONSE_SIZE", 4 * 1024 * 1024),
        metadata={
            "description": "Maximum serialized MCP response size in bytes.",
            "default": 4 * 1024 * 1024,
        },
    )

    max_metadata_size: int = field(
        default_factory=lambda: Env.get("MCP_MAX_METADATA_SIZE", 64 * 1024),
        metadata={
            "description": "Maximum serialized request or response metadata bytes.",
            "default": 64 * 1024,
        },
    )

    def __post_init__(self) -> None:
        """
        Reject coercion, unbounded budgets, and ambiguous origin allowlists.

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

