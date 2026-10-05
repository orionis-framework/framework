from types import MappingProxyType
import msgspec
from orionis.mcp.exceptions import McpInvalidParams, McpProtocolException
from orionis.mcp.protocol.constants import SUPPORTED_VERSIONS
from orionis.mcp.protocol.metavalidation import (
    validate_client_capabilities,
    validate_implementation,
    validate_metadata,
)
from orionis.mcp.protocol.requests import (
    CallToolParams,
    CompleteParams,
    GetPromptParams,
    JsonRpcRequest,
    ListenParams,
    PaginatedParams,
    ReadResourceParams,
    RequestMetadata,
    RequestParams,
)
from orionis.mcp.protocol.results import Error, ErrorResponse

_ENVELOPE = msgspec.json.Decoder(JsonRpcRequest)
METHOD_DECODERS = MappingProxyType(
    {
        "server/discover": msgspec.json.Decoder(RequestParams),
        "tools/list": msgspec.json.Decoder(PaginatedParams),
        "tools/call": msgspec.json.Decoder(CallToolParams),
        "resources/list": msgspec.json.Decoder(PaginatedParams),
        "resources/templates/list": msgspec.json.Decoder(PaginatedParams),
        "resources/read": msgspec.json.Decoder(ReadResourceParams),
        "prompts/list": msgspec.json.Decoder(PaginatedParams),
        "prompts/get": msgspec.json.Decoder(GetPromptParams),
        "completion/complete": msgspec.json.Decoder(CompleteParams),
        "subscriptions/listen": msgspec.json.Decoder(ListenParams),
    },
)

def decode_envelope(data: bytes) -> JsonRpcRequest:
    """
    Parse a single UTF-8 JSON-RPC message without decoding its payload.

    Parameters
    ----------
    data : bytes
        Value supplied for ``data``.

    Returns
    -------
    JsonRpcRequest
        Result of the operation described above.
    """
    try:
        return _ENVELOPE.decode(data)
    except msgspec.ValidationError as exc:
        raise McpProtocolException(-32600, "Invalid Request") from exc
    except msgspec.DecodeError as exc:
        raise McpProtocolException(-32700, "Parse error") from exc

def decode_params(request: JsonRpcRequest) -> RequestParams:
    """
    Validate method-specific parameters and per-request metadata.

    Parameters
    ----------
    request : JsonRpcRequest
        Current request and its trusted execution context.

    Returns
    -------
    RequestParams
        Result of the operation described above.
    """
    decoder = METHOD_DECODERS.get(request.method)
    if decoder is None:
        raise McpProtocolException(
            -32601,
            "Method not found; supported MCP version: 2026-07-28",
            status=404,
        )
    try:
        params = decoder.decode(request.params)
        metadata = msgspec.convert(params.meta, type=RequestMetadata, strict=True)
    except (msgspec.ValidationError, msgspec.DecodeError) as exc:
        raise McpInvalidParams from exc
    if metadata.protocol_version not in SUPPORTED_VERSIONS:
        raise McpProtocolException(
            -32022,
            "Unsupported protocol version",
            data={
                "supported": SUPPORTED_VERSIONS,
                "requested": metadata.protocol_version,
            },
        )
    try:
        validate_metadata(params.meta)
        validate_client_capabilities(metadata.capabilities)
        if metadata.client_info is not msgspec.UNSET:
            validate_implementation(metadata.client_info)
    except (TypeError, ValueError) as exc:
        raise McpInvalidParams from exc
    return params

def encode_error(
    exception: McpProtocolException,
    request_id: str | int | msgspec.UnsetType = msgspec.UNSET,
) -> bytes:
    """
    Serialize only explicitly public exception fields.

    Parameters
    ----------
    exception : McpProtocolException
        Exception being inspected or reported.
    request_id : str | int | msgspec.UnsetType
        Value supplied for ``request_id``.

    Returns
    -------
    bytes
        Result of the operation described above.
    """
    return msgspec.json.encode(
        ErrorResponse(
            id=request_id,
            error=Error(
                code=exception.code, message=exception.message, data=exception.data,
            ),
        ),
    )
