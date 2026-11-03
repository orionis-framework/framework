"""Provide mcp protocol operations.

Includes ``Error``, ``ErrorResponse``, ``ResultResponse``, ``Notification``.
"""

from typing import Literal
import msgspec

# Protocol fields retain the official MCP property names.
# ruff: noqa: N815

class Error(msgspec.Struct, frozen=True, kw_only=True):
    """A safe protocol error."""

    code: int
    """Machine-readable status or error code."""
    message: str
    """Human-readable message associated with this operation or result."""
    data: object = msgspec.UNSET

class ErrorResponse(msgspec.Struct, frozen=True, kw_only=True):
    """An unidentifiable malformed request has an omitted ID."""

    error: Error
    """First error retained while background work continues to drain."""
    id: str | int | msgspec.UnsetType = msgspec.UNSET
    jsonrpc: Literal["2.0"] = "2.0"
    """Jsonrpc identifier: ``2.0``."""

class ResultResponse(msgspec.Struct, frozen=True, kw_only=True):
    """A response correlated with one client request."""

    id: str | int
    """Identifier used to correlate or locate this protocol or storage record."""
    result: object
    """Successful result payload returned for the request."""
    jsonrpc: Literal["2.0"] = "2.0"
    """Jsonrpc identifier: ``2.0``."""

class Notification(msgspec.Struct, frozen=True, kw_only=True):
    """A server notification with no request ID."""

    method: str
    """JSON-RPC notification method sent to the client."""
    params: dict[str, object]
    """Parameters carried by the JSON-RPC message."""
    jsonrpc: Literal["2.0"] = "2.0"
    """Jsonrpc identifier: ``2.0``."""

class InputRequiredResult(msgspec.Struct, frozen=True, kw_only=True):
    """An MRTR interim result, never a pushed JSON-RPC request."""

    inputRequests: dict[str, dict[str, object]] | msgspec.UnsetType = msgspec.UNSET
    requestState: str | msgspec.UnsetType = msgspec.UNSET
    meta: dict[str, object] = msgspec.field(name="_meta", default_factory=dict)
    """Meta produced by ``msgspec.field``."""
    resultType: Literal["input_required"] = "input_required"
    """Result type identifier: ``input_required``."""

class CompleteResult(msgspec.Struct, frozen=True, kw_only=True):
    """Common fields of completed server results."""

    meta: dict[str, object] = msgspec.field(name="_meta", default_factory=dict)
    """Meta produced by ``msgspec.field``."""
    resultType: Literal["complete"] = "complete"
    """Result type identifier: ``complete``."""

class CacheableResult(CompleteResult, kw_only=True, frozen=True):
    """Required, conservative client cache hints."""

    ttlMs: int = 0
    """Ttl ms value used by ``CacheableResult``."""
    cacheScope: Literal["private", "public"] = "private"
    """Cache scope identifier: ``private``."""

class DiscoverResult(CacheableResult, kw_only=True, frozen=True):
    """Self-contained server discovery."""

    supportedVersions: tuple[str, ...]
    """Protocol versions accepted by the server."""
    capabilities: object
    """Capabilities advertised by the compiled server."""
    instructions: str | msgspec.UnsetType = msgspec.UNSET

class ListToolsResult(CacheableResult, kw_only=True, frozen=True):
    """One deterministic tool catalog page."""

    tools: tuple[object, ...]
    """Tool declarations available through this server or catalog."""
    nextCursor: str | msgspec.UnsetType = msgspec.UNSET

class ListResourcesResult(CacheableResult, kw_only=True, frozen=True):
    """One deterministic resource page."""

    resources: tuple[object, ...]
    """Resource declarations available through this server."""
    nextCursor: str | msgspec.UnsetType = msgspec.UNSET

class ListResourceTemplatesResult(CacheableResult, kw_only=True, frozen=True):
    """One deterministic template page."""

    resourceTemplates: tuple[object, ...]
    """Parameterized resource templates advertised by the server."""
    nextCursor: str | msgspec.UnsetType = msgspec.UNSET

class ListPromptsResult(CacheableResult, kw_only=True, frozen=True):
    """One deterministic prompt page."""

    prompts: tuple[object, ...]
    """Prompt declarations available through this server."""
    nextCursor: str | msgspec.UnsetType = msgspec.UNSET

class CallToolResult(CompleteResult, kw_only=True, frozen=True):
    """Content with optional structured output of any JSON type."""

    content: tuple[object, ...]
    """Content blocks carried by this protocol value."""
    structuredContent: object = msgspec.UNSET
    isError: bool | msgspec.UnsetType = msgspec.UNSET

class ReadResourceResult(CacheableResult, kw_only=True, frozen=True):
    """Text or blob resource contents."""

    contents: tuple[object, ...]
    """Resource content items returned by the read operation."""

class GetPromptResult(CompleteResult, kw_only=True, frozen=True):
    """User and assistant prompt messages."""

    messages: tuple[object, ...]
    """Ordered messages supplied to or returned by the operation."""
    description: str | msgspec.UnsetType = msgspec.UNSET

class Completion(msgspec.Struct, frozen=True, kw_only=True):
    """At most one hundred completion values."""

    values: tuple[str, ...]
    """Candidate values returned by the completion operation."""
    total: int | msgspec.UnsetType = msgspec.UNSET
    hasMore: bool | msgspec.UnsetType = msgspec.UNSET

class CompleteCompletionResult(CompleteResult, kw_only=True, frozen=True):
    """A completion response."""

    completion: Completion
    """Completion provider or result associated with the primitive."""
