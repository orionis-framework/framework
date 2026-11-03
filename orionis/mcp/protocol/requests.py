"""Provide mcp protocol operations.

Includes ``JsonRpcRequest``, ``RequestParams``, ``PaginatedParams``,
``InputResponseParams``.
"""

from typing import Literal
import msgspec

# Protocol fields retain the official MCP property names.
# ruff: noqa: N815

type RequestId = str | int
"""Type alias for ``str | int``."""
type Metadata = dict[str, object]
"""Type alias for ``dict[str, object]``."""
type LoggingLevel = Literal[
    "debug",
    "info",
    "notice",
    "warning",
    "error",
    "critical",
    "alert",
    "emergency",
]
"""
Type alias for ``Literal['debug', 'info', 'notice', 'warning', 'error', 'critical',
'alert', 'emergency']``.
"""

class JsonRpcRequest(msgspec.Struct, frozen=True, kw_only=True):
    """A request or notification, with lazily decoded parameters."""

    jsonrpc: Literal["2.0"]
    """JSON-RPC version marker, which must be ``2.0``."""
    method: str
    """JSON-RPC method requested by the client."""
    id: RequestId | msgspec.UnsetType = msgspec.UNSET
    params: msgspec.Raw = msgspec.Raw(b"{}")
    """Parameters carried by the JSON-RPC message."""

class RequestParams(msgspec.Struct, frozen=True, kw_only=True):
    """Common metadata, retained verbatim including extension keys."""

    meta: Metadata = msgspec.field(name="_meta")
    """Meta produced by ``msgspec.field``."""

class PaginatedParams(RequestParams, frozen=True):
    """An opaque stateless cursor."""

    cursor: str | msgspec.UnsetType = msgspec.UNSET

class InputResponseParams(RequestParams, frozen=True):
    """Explicit state and client inputs for an MRTR retry."""

    inputResponses: dict[str, dict[str, object]] | msgspec.UnsetType = msgspec.UNSET
    requestState: str | msgspec.UnsetType = msgspec.UNSET

class CallToolParams(InputResponseParams, kw_only=True, frozen=True):
    """Client-controlled tool payload, separate from DI."""

    name: str
    """Name identifying this declaration within its containing registry."""
    arguments: dict[str, object] = msgspec.field(default_factory=dict)
    """Command-line argument declarations accepted by this command."""

class ReadResourceParams(InputResponseParams, kw_only=True, frozen=True):
    """The requested resource URI."""

    uri: str
    """Resource URI identifying the requested or returned content."""

class GetPromptParams(InputResponseParams, kw_only=True, frozen=True):
    """String-valued prompt arguments."""

    name: str
    """Name identifying this declaration within its containing registry."""
    arguments: dict[str, str] = msgspec.field(default_factory=dict)
    """Command-line argument declarations accepted by this command."""

class PromptReference(msgspec.Struct, frozen=True, tag="ref/prompt"):
    """Reference a prompt for completion."""

    name: str
    """Name identifying this declaration within its containing registry."""

class ResourceTemplateReference(msgspec.Struct, frozen=True, tag="ref/resource"):
    """Reference an RFC 6570 resource template for completion."""

    uri: str
    """Resource URI identifying the requested or returned content."""

class CompletionArgument(msgspec.Struct, frozen=True):
    """One incomplete argument."""

    name: str
    """Name identifying this declaration within its containing registry."""
    value: str
    """Payload retained for subsequent resolution or restoration."""

class CompletionContext(msgspec.Struct, frozen=True):
    """Previously completed arguments."""

    arguments: dict[str, str] = msgspec.field(default_factory=dict)
    """Command-line argument declarations accepted by this command."""

class CompleteParams(RequestParams, frozen=True):
    """Typed completion reference and context."""

    ref: PromptReference | ResourceTemplateReference
    """Reference identifying the primitive for completion."""
    argument: CompletionArgument
    """Argument whose value requires completion."""
    context: CompletionContext | msgspec.UnsetType = msgspec.UNSET

class SubscriptionFilter(msgspec.Struct, frozen=True, omit_defaults=True):
    """Explicit opt-in to server change notifications."""

    toolsListChanged: bool = False
    """Tools list changed flag used by ``SubscriptionFilter``."""
    promptsListChanged: bool = False
    """Prompts list changed flag used by ``SubscriptionFilter``."""
    resourcesListChanged: bool = False
    """Resources list changed flag used by ``SubscriptionFilter``."""
    resourceSubscriptions: tuple[str, ...] = ()
    """Resource URIs for which change notifications are requested."""

class ListenParams(RequestParams, frozen=True):
    """A filter belonging to one long-lived request."""

    notifications: SubscriptionFilter
    """Notification categories selected by the subscriber."""

class CancelledParams(msgspec.Struct, frozen=True, kw_only=True):
    """STDIO cancellation notification parameters."""

    requestId: RequestId
    """Identifier of the request being cancelled."""
    reason: str | msgspec.UnsetType = msgspec.UNSET

class RequestMetadata(msgspec.Struct, frozen=True, kw_only=True):
    """Validate reserved metadata while preserving the original mapping."""

    protocol_version: str = msgspec.field(
        name="io.modelcontextprotocol/protocolVersion",
    )
    """Protocol version produced by ``msgspec.field``."""
    capabilities: dict[str, object] = msgspec.field(
        name="io.modelcontextprotocol/clientCapabilities",
    )
    """Capabilities advertised by the compiled server."""
    client_info: dict[str, object] | msgspec.UnsetType = msgspec.field(
        name="io.modelcontextprotocol/clientInfo",
        default=msgspec.UNSET,
    )
    """Client info produced by ``msgspec.field``."""
    log_level: LoggingLevel | msgspec.UnsetType = msgspec.field(
        name="io.modelcontextprotocol/logLevel",
        default=msgspec.UNSET,
    )
    """Log level produced by ``msgspec.field``."""
    progressToken: RequestId | msgspec.UnsetType = msgspec.UNSET
