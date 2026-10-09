import math
from typing import TYPE_CHECKING, TypedDict, Literal, cast
import msgspec
from orionis.mcp.protocol.content import (
    EmbeddedResource,
    PromptMessage,
    TextContent,
)
from orionis.mcp.protocol.results import (
    CallToolResult,
    GetPromptResult,
    ReadResourceResult,
)
from orionis.mcp.responses import McpResponse, Progress, mime_format
from orionis.mcp.server.compiler import validate_output

if TYPE_CHECKING:
    from orionis.mcp.context import McpRequest
    from orionis.mcp.server.compiler import CompiledPrimitive

class CacheOptions(TypedDict):
    ttlMs: int
    cacheScope: Literal["private", "public"]

def response_items(result: object) -> tuple[McpResponse, ...]:
    """
    Accept explicit content responses and reject accidental arbitrary objects.

    Parameters
    ----------
    result : object
        Value supplied for ``result``.

    Returns
    -------
    tuple[McpResponse, ...]
        Result of the operation described above.
    """
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
    """
    Validate structured output before publishing a successful result.

    Parameters
    ----------
    primitive : CompiledPrimitive
        Compiled tool, resource or prompt declaration.
    responses : tuple[McpResponse, ...]
        Value supplied for ``responses``.

    Returns
    -------
    CallToolResult
        Result of the operation described above.
    """
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
    """
    Preserve role and individual content-block boundaries.

    Parameters
    ----------
    description : str
        Value supplied for ``description``.
    responses : tuple[McpResponse, ...]
        Value supplied for ``responses``.

    Returns
    -------
    GetPromptResult
        Result of the operation described above.
    """
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
    """
    Use only text/blob contents permitted by resources/read.

    Parameters
    ----------
    primitive : CompiledPrimitive
        Compiled tool, resource or prompt declaration.
    request : McpRequest
        Current request and its trusted execution context.
    responses : tuple[McpResponse, ...]
        Value supplied for ``responses``.
    cache : CacheOptions
        Value supplied for ``cache``.

    Returns
    -------
    ReadResourceResult
        Result of the operation described above.
    """
    contents = []
    for item in responses:
        for part in item.content:
            if isinstance(part, EmbeddedResource):
                contents.append(part.resource)
            elif isinstance(part, TextContent):
                value = (
                    item.structured_content
                    if mime_format(primitive.mime_type) == "msgpack"
                    and item.structured_content is not msgspec.UNSET
                    else part.text
                )
                response = McpResponse.resource(
                    cast("str", request.uri), value, primitive.mime_type,
                )
                contents.append(
                    cast("EmbeddedResource", response.content[0]).resource,
                )
            else:
                message = "resources/read requires text or blob contents"
                raise TypeError(message)
    return ReadResourceResult(
        contents=tuple(contents), meta=_metadata(responses), **cache,
    )

def _metadata(responses: tuple[McpResponse, ...]) -> dict[str, object]:
    """
    Merge response metadata while rejecting conflicting result values.

    Parameters
    ----------
    responses : tuple[McpResponse, ...]
        Value supplied for ``responses``.

    Returns
    -------
    dict[str, object]
        Result of the operation described above.
    """
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
    """
    Enforce monotonic progress and retain the caller's correlation token.

    Parameters
    ----------
    update : Progress
        Value supplied for ``update``.
    token : str | int
        Value supplied for ``token``.
    previous : float
        Value supplied for ``previous``.

    Returns
    -------
    dict[str, object]
        Result of the operation described above.
    """
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
