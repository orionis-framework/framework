from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.mcp.entities.mcp import McpConfig

@dataclass(frozen=True, slots=True, kw_only=True)
class BootstrapMcp(McpConfig):

    # ----------------------------------------------------------------------------------
    # max_request_size : int, optional
    # --- Maximum serialized request size in bytes.
    # --- Uses MCP_MAX_REQUEST_SIZE, then HTTP_MAX_BODY_SIZE, or 1048576.
    # ----------------------------------------------------------------------------------
    max_request_size: int = field(default_factory=lambda: Env.get(
        "MCP_MAX_REQUEST_SIZE", Env.get("HTTP_MAX_BODY_SIZE", 1024 * 1024),
    ))

    # ----------------------------------------------------------------------------------
    # default_page_size : int, optional
    # --- Default number of entries returned by paginated list operations.
    # --- Uses MCP_DEFAULT_PAGE_SIZE or 50 if not set.
    # ----------------------------------------------------------------------------------
    default_page_size: int = field(
        default_factory=lambda: Env.get("MCP_DEFAULT_PAGE_SIZE", 50),
    )

    # ----------------------------------------------------------------------------------
    # max_page_size : int, optional
    # --- Maximum number of entries returned in one page.
    # --- Uses MCP_MAX_PAGE_SIZE or 100 if not set.
    # --- default_page_size must not exceed this value.
    # ----------------------------------------------------------------------------------
    max_page_size: int = field(
        default_factory=lambda: Env.get("MCP_MAX_PAGE_SIZE", 100),
    )

    # ----------------------------------------------------------------------------------
    # max_concurrent_requests : int, optional
    # --- Maximum number of concurrent MCP requests.
    # --- Uses MCP_MAX_CONCURRENT_REQUESTS, then HTTP_MAX_CONCURRENT_REQUESTS, or 32.
    # ----------------------------------------------------------------------------------
    max_concurrent_requests: int = field(default_factory=lambda: Env.get(
        "MCP_MAX_CONCURRENT_REQUESTS", Env.get("HTTP_MAX_CONCURRENT_REQUESTS", 32),
    ))

    # ----------------------------------------------------------------------------------
    # subscription_buffer_size : int, optional
    # --- Maximum event buffer size per subscription.
    # --- Uses MCP_SUBSCRIPTION_BUFFER_SIZE or 64 if not set.
    # ----------------------------------------------------------------------------------
    subscription_buffer_size: int = field(
        default_factory=lambda: Env.get("MCP_SUBSCRIPTION_BUFFER_SIZE", 64),
    )

    # ----------------------------------------------------------------------------------
    # max_subscriptions : int, optional
    # --- Total number of event-bus subscriptions allowed.
    # --- Uses MCP_MAX_SUBSCRIPTIONS or 1024 if not set.
    # ----------------------------------------------------------------------------------
    max_subscriptions: int = field(
        default_factory=lambda: Env.get("MCP_MAX_SUBSCRIPTIONS", 1024),
    )

    # ----------------------------------------------------------------------------------
    # max_resource_subscriptions : int, optional
    # --- Maximum resource subscriptions per request or client context.
    # --- Uses MCP_MAX_RESOURCE_SUBSCRIPTIONS or 64 if not set.
    # ----------------------------------------------------------------------------------
    max_resource_subscriptions: int = field(
        default_factory=lambda: Env.get("MCP_MAX_RESOURCE_SUBSCRIPTIONS", 64),
    )

    # ----------------------------------------------------------------------------------
    # subscription_keepalive : float, optional
    # --- Interval in seconds between subscription keepalive messages.
    # --- Uses MCP_SUBSCRIPTION_KEEPALIVE or 15.0 if not set.
    # ----------------------------------------------------------------------------------
    subscription_keepalive: float = field(
        default_factory=lambda: Env.get("MCP_SUBSCRIPTION_KEEPALIVE", 15.0),
    )

    # ----------------------------------------------------------------------------------
    # allowed_origins : tuple[str, ...], optional
    # --- Trusted HTTP(S) browser origins. Uses CORS_ALLOW_ORIGINS or an empty tuple.
    # --- An empty tuple rejects requests with an Origin header; requests without
    # --- an Origin header are accepted. Wildcards are not supported.
    # ----------------------------------------------------------------------------------
    allowed_origins: tuple[str, ...] = field(
        default_factory=lambda: Env.get("CORS_ALLOW_ORIGINS", ()),
    )

    # ----------------------------------------------------------------------------------
    # tool_search_max_results : int, optional
    # --- Maximum number of results returned by a tool catalog search.
    # --- Uses MCP_TOOL_SEARCH_MAX_RESULTS or 20 if not set.
    # ----------------------------------------------------------------------------------
    tool_search_max_results: int = field(
        default_factory=lambda: Env.get("MCP_TOOL_SEARCH_MAX_RESULTS", 20),
    )

    # ----------------------------------------------------------------------------------
    # tool_search_max_calls : int, optional
    # --- Maximum tool calls allowed in one catalog execution.
    # --- Uses MCP_TOOL_SEARCH_MAX_CALLS or 5 if not set.
    # ----------------------------------------------------------------------------------
    tool_search_max_calls: int = field(
        default_factory=lambda: Env.get("MCP_TOOL_SEARCH_MAX_CALLS", 5),
    )

    # ----------------------------------------------------------------------------------
    # tool_search_max_output_bytes : int, optional
    # --- Maximum serialized tool catalog output size in bytes.
    # --- Uses MCP_TOOL_SEARCH_MAX_OUTPUT_BYTES or 262144 if not set.
    # ----------------------------------------------------------------------------------
    tool_search_max_output_bytes: int = field(
        default_factory=lambda: Env.get("MCP_TOOL_SEARCH_MAX_OUTPUT_BYTES", 256 * 1024),
    )

    # ----------------------------------------------------------------------------------
    # max_response_size : int, optional
    # --- Maximum serialized response size in bytes.
    # --- Uses MCP_MAX_RESPONSE_SIZE or 4194304 if not set.
    # ----------------------------------------------------------------------------------
    max_response_size: int = field(
        default_factory=lambda: Env.get("MCP_MAX_RESPONSE_SIZE", 4 * 1024 * 1024),
    )

    # ----------------------------------------------------------------------------------
    # max_metadata_size : int, optional
    # --- Maximum serialized request or response metadata size in bytes.
    # --- Uses MCP_MAX_METADATA_SIZE or 65536 if not set.
    # ----------------------------------------------------------------------------------
    max_metadata_size: int = field(
        default_factory=lambda: Env.get("MCP_MAX_METADATA_SIZE", 64 * 1024),
    )
