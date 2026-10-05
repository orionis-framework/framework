from typing import Literal
import msgspec
type RequestId = str | int
type Metadata = dict[str, object]
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

class JsonRpcRequest(msgspec.Struct, frozen=True, kw_only=True):
    """A request or notification, with lazily decoded parameters."""

    jsonrpc: Literal["2.0"]
    method: str
    id: RequestId | msgspec.UnsetType = msgspec.UNSET
    params: msgspec.Raw = msgspec.Raw(b"{}")

class RequestParams(msgspec.Struct, frozen=True, kw_only=True):
    """Common metadata, retained verbatim including extension keys."""

    meta: Metadata = msgspec.field(name="_meta")

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
    arguments: dict[str, object] = msgspec.field(default_factory=dict)

class ReadResourceParams(InputResponseParams, kw_only=True, frozen=True):
    """The requested resource URI."""

    uri: str

class GetPromptParams(InputResponseParams, kw_only=True, frozen=True):
    """String-valued prompt arguments."""

    name: str
    arguments: dict[str, str] = msgspec.field(default_factory=dict)

class PromptReference(msgspec.Struct, frozen=True, tag="ref/prompt"):
    """Reference a prompt for completion."""

    name: str

class ResourceTemplateReference(msgspec.Struct, frozen=True, tag="ref/resource"):
    """Reference an RFC 6570 resource template for completion."""

    uri: str

class CompletionArgument(msgspec.Struct, frozen=True):
    """One incomplete argument."""

    name: str
    value: str

class CompletionContext(msgspec.Struct, frozen=True):
    """Previously completed arguments."""

    arguments: dict[str, str] = msgspec.field(default_factory=dict)

class CompleteParams(RequestParams, frozen=True):
    """Typed completion reference and context."""

    ref: PromptReference | ResourceTemplateReference
    argument: CompletionArgument
    context: CompletionContext | msgspec.UnsetType = msgspec.UNSET

class SubscriptionFilter(msgspec.Struct, frozen=True, omit_defaults=True):
    """Explicit opt-in to server change notifications."""

    toolsListChanged: bool = False
    promptsListChanged: bool = False
    resourcesListChanged: bool = False
    resourceSubscriptions: tuple[str, ...] = ()

class ListenParams(RequestParams, frozen=True):
    """A filter belonging to one long-lived request."""

    notifications: SubscriptionFilter

class CancelledParams(msgspec.Struct, frozen=True, kw_only=True):
    """STDIO cancellation notification parameters."""

    requestId: RequestId
    reason: str | msgspec.UnsetType = msgspec.UNSET

class RequestMetadata(msgspec.Struct, frozen=True, kw_only=True):
    """Validate reserved metadata while preserving the original mapping."""

    protocol_version: str = msgspec.field(
        name="io.modelcontextprotocol/protocolVersion",
    )
    capabilities: dict[str, object] = msgspec.field(
        name="io.modelcontextprotocol/clientCapabilities",
    )
    client_info: dict[str, object] | msgspec.UnsetType = msgspec.field(
        name="io.modelcontextprotocol/clientInfo",
        default=msgspec.UNSET,
    )
    log_level: LoggingLevel | msgspec.UnsetType = msgspec.field(
        name="io.modelcontextprotocol/logLevel",
        default=msgspec.UNSET,
    )
    progressToken: RequestId | msgspec.UnsetType = msgspec.UNSET
