"""Native, stateless MCP server support for Orionis."""

from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.mcp.config import McpConfig
    from orionis.mcp.context import McpContext, McpRequest
    from orionis.mcp.protocol.constants import MCP_PROTOCOL_VERSION
    from orionis.mcp.protocol.metadata import (
        CacheHint, ContentAnnotations, Icon, PromptArgument, ToolAnnotations,
    )
    from orionis.mcp.protocol.results import Completion, InputRequiredResult
    from orionis.mcp.responses import McpResponse
    from orionis.mcp.server.catalog import ToolCatalog
    from orionis.mcp.server.extension import McpExtension
    from orionis.mcp.server.primitives import Prompt, Resource, Server, Tool
    from orionis.mcp.state import McpState

__all__ = [
    "MCP_PROTOCOL_VERSION",
    "CacheHint",
    "Completion",
    "ContentAnnotations",
    "Icon",
    "InputRequiredResult",
    "McpConfig",
    "McpContext",
    "McpExtension",
    "McpRequest",
    "McpResponse",
    "McpState",
    "Prompt",
    "PromptArgument",
    "Resource",
    "Server",
    "Tool",
    "ToolAnnotations",
    "ToolCatalog",
]

_EXPORTS = {
    "MCP_PROTOCOL_VERSION": ("orionis.mcp.protocol.constants", "MCP_PROTOCOL_VERSION"),
    "CacheHint": ("orionis.mcp.protocol.metadata", "CacheHint"),
    "Completion": ("orionis.mcp.protocol.results", "Completion"),
    "ContentAnnotations": ("orionis.mcp.protocol.metadata", "ContentAnnotations"),
    "Icon": ("orionis.mcp.protocol.metadata", "Icon"),
    "InputRequiredResult": ("orionis.mcp.protocol.results", "InputRequiredResult"),
    "McpConfig": ("orionis.mcp.config", "McpConfig"),
    "McpContext": ("orionis.mcp.context", "McpContext"),
    "McpExtension": ("orionis.mcp.server.extension", "McpExtension"),
    "McpRequest": ("orionis.mcp.context", "McpRequest"),
    "McpResponse": ("orionis.mcp.responses", "McpResponse"),
    "McpState": ("orionis.mcp.state", "McpState"),
    "Prompt": ("orionis.mcp.server.primitives", "Prompt"),
    "PromptArgument": ("orionis.mcp.protocol.metadata", "PromptArgument"),
    "Resource": ("orionis.mcp.server.primitives", "Resource"),
    "Server": ("orionis.mcp.server.primitives", "Server"),
    "Tool": ("orionis.mcp.server.primitives", "Tool"),
    "ToolAnnotations": ("orionis.mcp.protocol.metadata", "ToolAnnotations"),
    "ToolCatalog": ("orionis.mcp.server.catalog", "ToolCatalog"),
}

def __getattr__(name: str) -> object:
    """
    Resolve and cache a public package export.

    Parameters
    ----------
    name : str
        Public attribute requested from this package.

    Returns
    -------
    object
        Exported object from its defining module.

    Raises
    ------
    AttributeError
        If the requested attribute is not exported.
    """
    return _resolve_export(globals(), _EXPORTS, name)

def __dir__() -> list[str]:
    """
    List loaded attributes and declared public exports.

    Returns
    -------
    list[str]
        Sorted attribute names available on this package.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
