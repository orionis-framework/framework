"""Check application-produced wire values before sending them to clients."""

import base64
import math
from collections.abc import Mapping
from datetime import datetime
from typing import cast

import msgspec

from orionis.mcp.protocol.content import (
    AudioContent,
    BlobResourceContents,
    Content,
    ImageContent,
    ResourceLink,
    TextContent,
    TextResourceContents,
)
from orionis.mcp.protocol.metadata import Icon
from orionis.mcp.protocol.metavalidation import validate_metadata
from orionis.mcp.protocol.results import (
    CacheableResult,
    CallToolResult,
    CompleteCompletionResult,
    CompleteResult,
    DiscoverResult,
    GetPromptResult,
    InputRequiredResult,
    ListPromptsResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ListToolsResult,
    ReadResourceResult,
)
from orionis.mcp.server.templates import validate_uri

_RESULT_TYPES = {
    "server/discover": DiscoverResult,
    "tools/list": ListToolsResult,
    "tools/call": CallToolResult,
    "resources/list": ListResourcesResult,
    "resources/templates/list": ListResourceTemplatesResult,
    "resources/read": ReadResourceResult,
    "prompts/list": ListPromptsResult,
    "prompts/get": GetPromptResult,
    "completion/complete": CompleteCompletionResult,
    "subscriptions/listen": CompleteResult,
}
_CONTENT_TYPES = {
    "text": TextContent,
    "image": ImageContent,
    "audio": AudioContent,
    "resource_link": ResourceLink,
}
_MAX_COMPLETIONS = 100


def validate_json(value: object) -> None:
    """Reject non-JSON values and nonfinite numbers rather than changing data."""
    if value is None or type(value) in (str, int, bool):
        return
    if isinstance(value, float) and math.isfinite(value):
        return
    if isinstance(value, (tuple, list)):
        for item in value:
            validate_json(item)
        return
    if isinstance(value, Mapping) and all(isinstance(key, str) for key in value):
        for item in value.values():
            validate_json(item)
        return
    message = "MCP values must contain finite JSON data"
    raise ValueError(message)


def validate_result(result: object, method: str) -> None:
    """Reject invalid direct Struct construction and method/result mismatches."""
    expected = _RESULT_TYPES.get(method)
    if expected is None and isinstance(result, CompleteResult):
        expected = type(result)
    if isinstance(result, InputRequiredResult):
        if method not in ("tools/call", "resources/read", "prompts/get"):
            message = "This method cannot return input_required"
            raise ValueError(message)
        expected = InputRequiredResult
    if expected is None or type(result) is not expected:
        message = "MCP result does not match its request method"
        raise ValueError(message)
    # Static list entries are trusted compiled Raw objects; conversion leaves them
    # untouched. Content below is application-produced and validated individually.
    value = msgspec.to_builtins(result, builtin_types=(msgspec.Raw,))
    msgspec.convert(value, type=expected, strict=True)
    validate_metadata(value.get("_meta", {}), allow_reserved=False)
    if isinstance(result, CacheableResult) and result.ttlMs < 0:
        message = "MCP cache TTL must be nonnegative"
        raise ValueError(message)
    _result_payload(result)


def _result_payload(result: object) -> None:
    """Check only dynamic application payloads; registry metadata is precompiled."""
    if isinstance(result, CallToolResult):
        for item in result.content:
            validate_content(item)
        if result.structuredContent is not msgspec.UNSET:
            validate_json(result.structuredContent)
    elif isinstance(result, ReadResourceResult):
        for item in result.contents:
            validate_resource(item)
    elif isinstance(result, GetPromptResult):
        for item in result.messages:
            _message(item)
    elif isinstance(result, CompleteCompletionResult):
        completion = result.completion
        if len(completion.values) > _MAX_COMPLETIONS or (
            completion.total is not msgspec.UNSET and completion.total < 0
        ):
            message = "Invalid completion result"
            raise ValueError(message)


def _object(value: object) -> dict[str, object]:
    """Convert a public wire struct without a second JSON serialization."""
    value = msgspec.to_builtins(value)
    if not isinstance(value, dict):
        message = "MCP content must be an object"
        raise TypeError(message)
    validate_json(value)
    return value


def _common(value: dict[str, object]) -> None:
    """Validate annotations and metadata shared by content variants."""
    common = msgspec.convert(value, type=Content, strict=True)
    if common.meta is not msgspec.UNSET:
        validate_metadata(common.meta, allow_reserved=False)
    annotations = common.annotations
    if annotations is not msgspec.UNSET:
        if annotations.priority is not msgspec.UNSET and (
            not math.isfinite(annotations.priority)
            or not 0 <= annotations.priority <= 1
        ):
            message = "Invalid content priority"
            raise ValueError(message)
        if annotations.lastModified is not msgspec.UNSET:
            datetime.fromisoformat(annotations.lastModified)


def validate_content(content: object) -> None:
    """Validate all five standard MCP content variants."""
    value = _object(content)
    _common(value)
    kind = value.get("type")
    if kind == "resource":
        validate_resource(value.get("resource"))
        return
    expected = _CONTENT_TYPES.get(cast("str", kind))
    if expected is None:
        message = "Unknown MCP content type"
        raise ValueError(message)
    msgspec.convert(value, type=expected, strict=True)
    if kind in ("image", "audio"):
        base64.b64decode(cast("str", value["data"]), validate=True)
    if kind == "resource_link":
        validate_uri(cast("str", value["uri"]))
        if "size" in value and cast("int", value["size"]) < 0:
            message = "Resource size must be nonnegative"
            raise ValueError(message)
        for icon in cast("list[object]", value.get("icons", [])):
            msgspec.convert(icon, type=Icon, strict=True)


def validate_resource(content: object) -> None:
    """Check text/blob resource contents and their explicit URI."""
    value = _object(content)
    if ("text" in value) == ("blob" in value):
        message = "Resource contents need exactly one of text or blob"
        raise ValueError(message)
    expected = TextResourceContents if "text" in value else BlobResourceContents
    msgspec.convert(value, type=expected, strict=True)
    validate_uri(cast("str", value["uri"]))
    if "blob" in value:
        base64.b64decode(cast("str", value["blob"]), validate=True)
    if "_meta" in value:
        validate_metadata(value["_meta"], allow_reserved=False)


def _message(message: object) -> None:
    """Validate a prompt role and its single content block."""
    value = _object(message)
    if value.get("role") not in ("user", "assistant"):
        error = "Invalid prompt message role"
        raise ValueError(error)
    validate_content(value.get("content"))
