from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.environment import http_origins
from orionis.foundation.config.mcp.entities.mcp import McpConfig

@dataclass(frozen=True, slots=True, kw_only=True)
class BootstrapMcp(McpConfig):
    """Read MCP environment defaults through the framework configuration entity."""

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
