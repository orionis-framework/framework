"""Normalize developer responses into protocol-specific completed results."""

import math
from typing import TYPE_CHECKING, TypedDict, Literal, cast

import msgspec

from orionis.mcp.protocol.content import (
    EmbeddedResource,
    PromptMessage,
    TextContent,
    TextResourceContents,
)
from orionis.mcp.protocol.results import (
    CallToolResult,
    GetPromptResult,
    ReadResourceResult,
)
from orionis.mcp.responses import McpResponse, Progress
from orionis.mcp.server.compiler import validate_output

if TYPE_CHECKING:
    from orionis.mcp.context import McpRequest
    from orionis.mcp.server.compiler import CompiledPrimitive


class CacheOptions(TypedDict):
    ttlMs: int
    cacheScope: Literal["private", "public"]


def response_items(result: object) -> tuple[McpResponse, ...]:
    """Accept explicit content responses and reject accidental arbitrary objects."""
    if isinstance(result, McpResponse):
        responses = (result,)
    elif isinstance(result, (list, tuple)):
        responses = tuple(result)
    else:
        message = "Handlers must return McpResponse values"
        raise TypeError(message)
    if any(
        not isinstance(item, McpResponse) or item.progress_update is not None
        for item in responses
    ):
        message = "Handlers must return content responses"
        raise TypeError(message)
    return responses


def tool_result(
    primitive: CompiledPrimitive,
    responses: tuple[McpResponse, ...],
) -> CallToolResult:
    """Validate structured output before publishing a successful result."""
    values = [
        item.structured_content
        for item in responses
        if item.structured_content is not msgspec.UNSET
    ]
    if len(values) > 1:
        message = "Only one structured result is permitted"
        raise ValueError(message)
    value = values[0] if values else msgspec.UNSET
    is_error = any(item.is_error for item in responses)
    if not is_error:
        validate_output(primitive, value)
    return CallToolResult(
        content=tuple(part for item in responses for part in item.content),
        structuredContent=value,
        isError=is_error,
        meta=_metadata(responses),
    )


def prompt_result(
    description: str,
    responses: tuple[McpResponse, ...],
) -> GetPromptResult:
    """Preserve role and individual content-block boundaries."""
    return GetPromptResult(
        messages=tuple(
            PromptMessage(role=item.role, content=part)
            for item in responses
            for part in item.content
        ),
        description=description or msgspec.UNSET,
        meta=_metadata(responses),
    )


def resource_result(
    primitive: CompiledPrimitive,
    request: McpRequest,
    responses: tuple[McpResponse, ...],
    cache: CacheOptions,
) -> ReadResourceResult:
    """Use only text/blob contents permitted by resources/read."""
    contents = []
    for item in responses:
        for part in item.content:
            if isinstance(part, EmbeddedResource):
                contents.append(part.resource)
            elif isinstance(part, TextContent):
                contents.append(
                    TextResourceContents(
                        uri=cast("str", request.uri),
                        text=part.text,
                        mimeType=primitive.mime_type or msgspec.UNSET,
                    ),
                )
            else:
                message = "resources/read requires text or blob contents"
                raise TypeError(message)
    return ReadResourceResult(
        contents=tuple(contents), meta=_metadata(responses), **cache,
    )


def _metadata(responses: tuple[McpResponse, ...]) -> dict[str, object]:
    """Merge response metadata while rejecting conflicting result values."""
    metadata = {}
    for response in responses:
        for key, value in response.meta.items():
            if key in metadata and metadata[key] != value:
                message = "Conflicting MCP result metadata"
                raise ValueError(message)
            metadata[key] = value
    return metadata


def progress_params(
    update: Progress,
    token: str | int,
    previous: float,
) -> dict[str, object]:
    """Enforce monotonic progress and retain the caller's correlation token."""
    for value in (update.current, update.total):
        if value is not None and (
            type(value) not in (int, float) or not math.isfinite(value)
        ):
            message = "Progress must contain finite JSON numbers"
            raise ValueError(message)
    if update.current is None or (
        update.message is not None and not isinstance(update.message, str)
    ):
        message = "Invalid progress update"
        raise ValueError(message)
    if update.current <= previous:
        message = "Progress must increase"
        raise ValueError(message)
    params = {"progressToken": token, "progress": update.current}
    if update.total is not None:
        params["total"] = update.total
    if update.message is not None:
        params["message"] = update.message
    return params
