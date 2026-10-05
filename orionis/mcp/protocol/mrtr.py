from collections.abc import Mapping
from typing import TYPE_CHECKING
import msgspec
from orionis.mcp.context import mutable_json
from orionis.mcp.exceptions import McpInvalidParams, McpProtocolException
from orionis.mcp.protocol.input_shapes import (
    EnumItems,
    FormField,
    FormRequest,
    FormResult,
    RootsResult,
    SamplingMessage,
    SamplingRequest,
    SamplingResult,
    ToolResult,
    ToolUse,
    UrlRequest,
)
from orionis.mcp.protocol.metavalidation import validate_metadata
from orionis.mcp.protocol.results import InputRequiredResult
from orionis.mcp.protocol.validation import validate_content, validate_json
from orionis.mcp.server.templates import validate_uri

if TYPE_CHECKING:
    from orionis.mcp.context import McpRequest

def validate_input_required(result: InputRequiredResult, request: McpRequest) -> None:
    """
    Never request client functionality absent from this request's capabilities.

    Parameters
    ----------
    result : InputRequiredResult
        Value supplied for ``result``.
    request : McpRequest
        Current request and its trusted execution context.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    try:
        msgspec.convert(msgspec.to_builtins(result), type=InputRequiredResult)
        _input_requests(result, request)
    except (TypeError, ValueError) as exc:
        message = "Invalid input-required result"
        raise McpInvalidParams(message) from exc

def _input_requests(result: InputRequiredResult, request: McpRequest) -> None:
    """
    Validate input request fields and the permitted enclosing method.

    Parameters
    ----------
    result : InputRequiredResult
        Value supplied for ``result``.
    request : McpRequest
        Current request and its trusted execution context.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    if request.method not in ("tools/call", "resources/read", "prompts/get"):
        message = "This method cannot request additional input"
        raise ValueError(message)
    if result.inputRequests is msgspec.UNSET and result.requestState is msgspec.UNSET:
        message = "Input-required result needs inputRequests or requestState"
        raise ValueError(message)
    if result.inputRequests is msgspec.UNSET:
        return
    for item in result.inputRequests.values():
        _input_request(item, request)

def _input_request(item: dict[str, object], request: McpRequest) -> None:
    """
    Validate and dispatch one embedded client input request.

    Parameters
    ----------
    item : dict[str, object]
        Embedded method and parameter object.
    request : McpRequest
        Enclosing request carrying the client's capabilities.

    Returns
    -------
    None
        The input request and its required capability have been validated.

    Raises
    ------
    ValueError
        If the input request shape or method is invalid.
    """
    method = item.get("method")
    params = item.get("params", {} if method == "roots/list" else None)
    if not isinstance(params, dict) or "jsonrpc" in item or "id" in item:
        message = "Invalid embedded input request"
        raise ValueError(message)
    if method == "elicitation/create":
        _elicitation(params, request)
    elif method == "sampling/createMessage":
        _sampling(params, request)
    elif method == "roots/list":
        _require(request, "roots")
        if "_meta" in params:
            validate_metadata(params["_meta"], allow_reserved=False)
    else:
        message = "Unknown input request method"
        raise ValueError(message)

def _require(request: McpRequest, capability: str, feature: str | None = None) -> None:
    """
    Require a capability, including the historical implicit form flag.

    Parameters
    ----------
    request : McpRequest
        Current request and its trusted execution context.
    capability : str
        Value supplied for ``capability``.
    feature : str | None
        Value supplied for ``feature``.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    value = request.client_capabilities.get(capability)
    supported = isinstance(value, Mapping) and (
        feature is None or feature in value
        or (capability == "elicitation" and feature == "form" and not value)
    )
    if not supported:
        raise McpProtocolException(
            -32021,
            "Missing required client capability",
            data={"requiredCapabilities": {
                capability: {} if feature is None else {feature: {}},
            }},
        )

def _elicitation(params: dict[str, object], request: McpRequest) -> None:
    """
    Validate the modern form or URL elicitation wire shape.

    Parameters
    ----------
    params : dict[str, object]
        Parameters decoded for the requested operation.
    request : McpRequest
        Current request and its trusted execution context.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    if params.get("mode", "form") == "url":
        value = msgspec.convert(params, type=UrlRequest, strict=True)
        validate_uri(value.url)
        _require(request, "elicitation", "url")
        return
    value = msgspec.convert(params, type=FormRequest, strict=True)
    schema = value.requested_schema
    if any(name not in schema.properties for name in schema.required):
        message = "Required elicitation property is not declared"
        raise ValueError(message)
    for field in schema.properties.values():
        _form_field(field)
    _require(request, "elicitation", "form")

def _form_field(field: FormField) -> None:
    """
    Validate permitted enumeration and default shapes.

    Parameters
    ----------
    field : FormField
        Qualified name of the field being processed.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    default_type = {"string": str, "number": float, "integer": int, "boolean": bool}
    if field.type == "array":
        if field.items is msgspec.UNSET:
            message = "Multi-select form field needs enum items"
            raise ValueError(message)
        items = msgspec.convert(field.items, type=EnumItems, strict=True)
        if not (
            (items.type == "string" and items.enum is not msgspec.UNSET)
            or items.any_of is not msgspec.UNSET
        ):
            message = "Form arrays only support string enumerations"
            raise ValueError(message)
        if field.default is not msgspec.UNSET:
            msgspec.convert(field.default, type=list[str], strict=True)
    elif field.default is not msgspec.UNSET:
        msgspec.convert(field.default, type=default_type[field.type], strict=True)
    for minimum, maximum in (
        (field.minimum, field.maximum),
        (field.min_length, field.max_length),
        (field.min_items, field.max_items),
    ):
        if minimum is not msgspec.UNSET and maximum is not msgspec.UNSET and (
            minimum > maximum
        ):
            message = "Elicitation schema minimum exceeds maximum"
            raise ValueError(message)

def _sampling(params: dict[str, object], request: McpRequest) -> None:
    """
    Retain deprecated sampling only as correctly validated MRTR wire support.

    Parameters
    ----------
    params : dict[str, object]
        Parameters decoded for the requested operation.
    request : McpRequest
        Current request and its trusted execution context.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    value = msgspec.convert(params, type=SamplingRequest, strict=True)
    _require(request, "sampling")
    if value.include_context != "none":
        _require(request, "sampling", "context")
    if value.tools is not msgspec.UNSET or value.tool_choice is not msgspec.UNSET:
        _require(request, "sampling", "tools")
    for message in value.messages:
        _sampling_message(message)
    if value.tools is not msgspec.UNSET:
        for tool in value.tools:
            schema = tool.get("inputSchema")
            if not isinstance(tool.get("name"), str) or not isinstance(
                schema, dict,
            ) or schema.get("type") != "object":
                message = "Invalid sampling tool definition"
                raise ValueError(message)

def _sampling_message(message: SamplingMessage) -> None:
    """
    Check each sampling-specific or common content block.

    Parameters
    ----------
    message : SamplingMessage
        Value supplied for ``message``.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    if message.meta is not msgspec.UNSET:
        validate_metadata(message.meta)
    blocks = message.content if isinstance(message.content, list) else [message.content]
    for block in blocks:
        if not isinstance(block, dict):
            error = "Invalid sampling content"
            raise TypeError(error)
        if block.get("type") == "tool_use":
            msgspec.convert(block, type=ToolUse, strict=True)
        elif block.get("type") == "tool_result":
            result = msgspec.convert(block, type=ToolResult, strict=True)
            for content in result.content:
                validate_content(content)
        elif block.get("type") in ("text", "image", "audio"):
            validate_content(block)
        else:
            error = "Invalid sampling content type"
            raise ValueError(error)
        if "_meta" in block:
            validate_metadata(block["_meta"])

def validate_input_responses(responses: Mapping[str, object]) -> None:
    """
    Validate exact result variants without fabricating request history.

    Parameters
    ----------
    responses : Mapping[str, object]
        Value supplied for ``responses``.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    try:
        for key, original in responses.items():
            value = mutable_json(original)
            if not isinstance(key, str) or not isinstance(value, dict):
                message = "Invalid input response"
                raise TypeError(message)
            validate_json(value)
            _input_response(value)
    except (TypeError, ValueError) as exc:
        message = "Invalid input response"
        raise McpInvalidParams(message) from exc

def _input_response(value: dict[str, object]) -> None:
    """
    Dispatch structural InputResponse variants, never a JSON-RPC error.

    Parameters
    ----------
    value : dict[str, object]
        Value to inspect, transform or validate.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    if "action" in value:
        response = msgspec.convert(value, type=FormResult, strict=True)
        if response.action != "accept" and response.content is not msgspec.UNSET:
            message = "Only accepted form responses contain content"
            raise ValueError(message)
    elif "roots" in value:
        roots = msgspec.convert(value, type=RootsResult, strict=True)
        for root in roots.roots:
            validate_uri(root.uri)
            if not root.uri.startswith("file://"):
                message = "MCP roots must use file URIs"
                raise ValueError(message)
            if root.meta is not msgspec.UNSET:
                validate_metadata(root.meta)
    elif "model" in value:
        _sampling_message(msgspec.convert(value, type=SamplingResult, strict=True))
    else:
        message = "Unknown input response variant"
        raise ValueError(message)
