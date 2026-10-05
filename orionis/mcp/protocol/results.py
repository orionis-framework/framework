from typing import Literal
import msgspec

class Error(msgspec.Struct, frozen=True, kw_only=True):
    """A safe protocol error."""

    code: int
    message: str
    data: object = msgspec.UNSET

class ErrorResponse(msgspec.Struct, frozen=True, kw_only=True):
    """An unidentifiable malformed request has an omitted ID."""

    error: Error
    id: str | int | msgspec.UnsetType = msgspec.UNSET
    jsonrpc: Literal["2.0"] = "2.0"

class ResultResponse(msgspec.Struct, frozen=True, kw_only=True):
    """A response correlated with one client request."""

    id: str | int
    result: object
    jsonrpc: Literal["2.0"] = "2.0"

class Notification(msgspec.Struct, frozen=True, kw_only=True):
    """A server notification with no request ID."""

    method: str
    params: dict[str, object]
    jsonrpc: Literal["2.0"] = "2.0"

class InputRequiredResult(msgspec.Struct, frozen=True, kw_only=True):
    """An MRTR interim result, never a pushed JSON-RPC request."""

    inputRequests: dict[str, dict[str, object]] | msgspec.UnsetType = msgspec.UNSET
    requestState: str | msgspec.UnsetType = msgspec.UNSET
    meta: dict[str, object] = msgspec.field(name="_meta", default_factory=dict)
    resultType: Literal["input_required"] = "input_required"

class CompleteResult(msgspec.Struct, frozen=True, kw_only=True):
    """Common fields of completed server results."""

    meta: dict[str, object] = msgspec.field(name="_meta", default_factory=dict)
    resultType: Literal["complete"] = "complete"

class CacheableResult(CompleteResult, kw_only=True, frozen=True):
    """Required, conservative client cache hints."""

    ttlMs: int = 0
    cacheScope: Literal["private", "public"] = "private"

class DiscoverResult(CacheableResult, kw_only=True, frozen=True):
    """Self-contained server discovery."""

    supportedVersions: tuple[str, ...]
    capabilities: object
    instructions: str | msgspec.UnsetType = msgspec.UNSET

class ListToolsResult(CacheableResult, kw_only=True, frozen=True):
    """One deterministic tool catalog page."""

    tools: tuple[object, ...]
    nextCursor: str | msgspec.UnsetType = msgspec.UNSET

class ListResourcesResult(CacheableResult, kw_only=True, frozen=True):
    """One deterministic resource page."""

    resources: tuple[object, ...]
    nextCursor: str | msgspec.UnsetType = msgspec.UNSET

class ListResourceTemplatesResult(CacheableResult, kw_only=True, frozen=True):
    """One deterministic template page."""

    resourceTemplates: tuple[object, ...]
    nextCursor: str | msgspec.UnsetType = msgspec.UNSET

class ListPromptsResult(CacheableResult, kw_only=True, frozen=True):
    """One deterministic prompt page."""

    prompts: tuple[object, ...]
    nextCursor: str | msgspec.UnsetType = msgspec.UNSET

class CallToolResult(CompleteResult, kw_only=True, frozen=True):
    """Content with optional structured output of any JSON type."""

    content: tuple[object, ...]
    structuredContent: object = msgspec.UNSET
    isError: bool | msgspec.UnsetType = msgspec.UNSET

class ReadResourceResult(CacheableResult, kw_only=True, frozen=True):
    """Text or blob resource contents."""

    contents: tuple[object, ...]

class GetPromptResult(CompleteResult, kw_only=True, frozen=True):
    """User and assistant prompt messages."""

    messages: tuple[object, ...]
    description: str | msgspec.UnsetType = msgspec.UNSET

class Completion(msgspec.Struct, frozen=True, kw_only=True):
    """At most one hundred completion values."""

    values: tuple[str, ...]
    total: int | msgspec.UnsetType = msgspec.UNSET
    hasMore: bool | msgspec.UnsetType = msgspec.UNSET

class CompleteCompletionResult(CompleteResult, kw_only=True, frozen=True):
    """A completion response."""

    completion: Completion
