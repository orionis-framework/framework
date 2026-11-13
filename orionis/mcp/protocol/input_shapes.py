"""Provide mcp protocol operations.

Includes ``FormResult``, ``EnumOption``, ``FormField``, ``EnumItems``.
"""

from typing import Annotated, Literal
import msgspec

type OptionalString = str | msgspec.UnsetType
"""Type alias for ``str | msgspec.UnsetType``."""
type Nonnegative = Annotated[int, msgspec.Meta(ge=0)]
"""Type alias for ``Annotated[int, msgspec.Meta(ge=0)]``."""
type Priority = Annotated[float, msgspec.Meta(ge=0, le=1)]
"""Type alias for ``Annotated[float, msgspec.Meta(ge=0, le=1)]``."""
type FormValue = str | float | bool | list[str]
"""Type alias for ``str | float | bool | list[str]``."""


class FormResult(msgspec.Struct, frozen=True):
    """An elicitation response, with no JSON-RPC error envelope."""

    action: Literal["accept", "decline", "cancel"]
    """Client action completing or declining the form request."""
    content: dict[str, FormValue] | msgspec.UnsetType = msgspec.UNSET


class EnumOption(msgspec.Struct, frozen=True):
    """A titled single selection option."""

    const: str
    """Exact value represented by this enumeration option."""
    title: str
    """Human-readable title displayed for this protocol value."""


class FormField(msgspec.Struct, frozen=True):
    """The non-nesting primitive schema supported by elicitation forms."""

    type: Literal["string", "number", "integer", "boolean", "array"]
    """Discriminator identifying the message or schema variant."""
    title: OptionalString = msgspec.UNSET
    description: OptionalString = msgspec.UNSET
    minimum: float | msgspec.UnsetType = msgspec.UNSET
    maximum: float | msgspec.UnsetType = msgspec.UNSET
    min_length: Nonnegative | msgspec.UnsetType = msgspec.field(
        name="minLength",
        default=msgspec.UNSET,
    )
    """Min length produced by ``msgspec.field``."""
    max_length: Nonnegative | msgspec.UnsetType = msgspec.field(
        name="maxLength",
        default=msgspec.UNSET,
    )
    """Max length produced by ``msgspec.field``."""
    min_items: Nonnegative | msgspec.UnsetType = msgspec.field(
        name="minItems",
        default=msgspec.UNSET,
    )
    """Min items produced by ``msgspec.field``."""
    max_items: Nonnegative | msgspec.UnsetType = msgspec.field(
        name="maxItems",
        default=msgspec.UNSET,
    )
    """Max items produced by ``msgspec.field``."""
    format: Literal["email", "uri", "date", "date-time"] | msgspec.UnsetType = (
        msgspec.UNSET
    )
    enum: tuple[str, ...] | msgspec.UnsetType = msgspec.UNSET
    enum_names: tuple[str, ...] | msgspec.UnsetType = msgspec.field(
        name="enumNames",
        default=msgspec.UNSET,
    )
    """Enum names produced by ``msgspec.field``."""
    one_of: tuple[EnumOption, ...] | msgspec.UnsetType = msgspec.field(
        name="oneOf",
        default=msgspec.UNSET,
    )
    """One of produced by ``msgspec.field``."""
    items: dict[str, object] | msgspec.UnsetType = msgspec.UNSET
    default: object = msgspec.UNSET


class EnumItems(msgspec.Struct, frozen=True):
    """The two permitted string enumeration item schemas."""

    type: Literal["string"] | msgspec.UnsetType = msgspec.UNSET
    enum: tuple[str, ...] | msgspec.UnsetType = msgspec.UNSET
    any_of: tuple[EnumOption, ...] | msgspec.UnsetType = msgspec.field(
        name="anyOf",
        default=msgspec.UNSET,
    )
    """Any of produced by ``msgspec.field``."""


class FormSchema(msgspec.Struct, frozen=True):
    """A flat object containing elicitation form fields."""

    type: Literal["object"]
    """Discriminator identifying the message or schema variant."""
    properties: dict[str, FormField]
    """Field schemas indexed by the corresponding property name."""
    required: tuple[str, ...] = ()
    """Property names that must be present in the submitted object."""
    schema: OptionalString = msgspec.field(name="$schema", default=msgspec.UNSET)
    """Schema produced by ``msgspec.field``."""


class FormRequest(msgspec.Struct, frozen=True):
    """Form elicitation parameters."""

    message: str
    """Human-readable message associated with this operation or result."""
    requested_schema: FormSchema = msgspec.field(name="requestedSchema")
    """Requested schema produced by ``msgspec.field``."""
    mode: Literal["form"] = "form"
    """Mode identifier: ``form``."""


class UrlRequest(msgspec.Struct, frozen=True):
    """Out-of-band elicitation parameters."""

    mode: Literal["url"]
    """Interaction mode requested from the client."""
    message: str
    """Human-readable message associated with this operation or result."""
    url: str
    """URL the client is asked to open or display."""


class Root(msgspec.Struct, frozen=True):
    """Wire-only deprecated root descriptor."""

    uri: str
    """Resource URI identifying the requested or returned content."""
    name: OptionalString = msgspec.UNSET
    meta: dict[str, object] | msgspec.UnsetType = msgspec.field(
        name="_meta",
        default=msgspec.UNSET,
    )
    """Meta produced by ``msgspec.field``."""


class RootsResult(msgspec.Struct, frozen=True):
    """Wire-only deprecated roots result."""

    roots: tuple[Root, ...]
    """Root resources reported by the client."""


class SamplingMessage(msgspec.Struct, frozen=True):
    """Wire-only deprecated sampling message."""

    role: Literal["user", "assistant"]
    """Role assigned to this message in the conversation."""
    content: object
    """Content blocks carried by this protocol value."""
    meta: dict[str, object] | msgspec.UnsetType = msgspec.field(
        name="_meta",
        default=msgspec.UNSET,
    )
    """Meta produced by ``msgspec.field``."""


class SamplingResult(SamplingMessage, frozen=True, kw_only=True):
    """Wire-only deprecated sampling response."""

    model: str
    """Model selected for generation or persistence."""
    stop_reason: OptionalString = msgspec.field(
        name="stopReason",
        default=msgspec.UNSET,
    )
    """Stop reason produced by ``msgspec.field``."""


class ModelHint(msgspec.Struct, frozen=True):
    """A provider-agnostic model hint."""

    name: OptionalString = msgspec.UNSET


class ModelPreferences(msgspec.Struct, frozen=True):
    """Bounded priorities for a wire sampling request."""

    hints: tuple[ModelHint, ...] | msgspec.UnsetType = msgspec.UNSET
    cost: Priority | msgspec.UnsetType = msgspec.field(
        name="costPriority",
        default=msgspec.UNSET,
    )
    """Cost produced by ``msgspec.field``."""
    speed: Priority | msgspec.UnsetType = msgspec.field(
        name="speedPriority",
        default=msgspec.UNSET,
    )
    """Speed produced by ``msgspec.field``."""
    intelligence: Priority | msgspec.UnsetType = msgspec.field(
        name="intelligencePriority",
        default=msgspec.UNSET,
    )
    """Intelligence produced by ``msgspec.field``."""


class ToolChoice(msgspec.Struct, frozen=True):
    """The protocol's sampling tool policy."""

    mode: Literal["auto", "required", "none"] = "auto"
    """Mode identifier: ``auto``."""


class SamplingRequest(msgspec.Struct, frozen=True):
    """Wire-only deprecated sampling parameters."""

    messages: tuple[SamplingMessage, ...]
    """Ordered messages supplied to or returned by the operation."""
    max_tokens: int = msgspec.field(name="maxTokens")
    """Max tokens produced by ``msgspec.field``."""
    model_preferences: ModelPreferences | msgspec.UnsetType = msgspec.field(
        name="modelPreferences",
        default=msgspec.UNSET,
    )
    """Model preferences produced by ``msgspec.field``."""
    system_prompt: OptionalString = msgspec.field(
        name="systemPrompt",
        default=msgspec.UNSET,
    )
    """System prompt produced by ``msgspec.field``."""
    include_context: Literal["none", "thisServer", "allServers"] = msgspec.field(
        name="includeContext",
        default="none",
    )
    """Include context produced by ``msgspec.field``."""
    temperature: float | msgspec.UnsetType = msgspec.UNSET
    stop_sequences: tuple[str, ...] | msgspec.UnsetType = msgspec.field(
        name="stopSequences",
        default=msgspec.UNSET,
    )
    """Stop sequences produced by ``msgspec.field``."""
    metadata: dict[str, object] | msgspec.UnsetType = msgspec.UNSET
    tools: tuple[dict[str, object], ...] | msgspec.UnsetType = msgspec.UNSET
    tool_choice: ToolChoice | msgspec.UnsetType = msgspec.field(
        name="toolChoice",
        default=msgspec.UNSET,
    )
    """Tool choice produced by ``msgspec.field``."""


class ToolUse(msgspec.Struct, tag="tool_use", frozen=True):
    """Wire-only model invocation of a tool."""

    id: str
    """Identifier used to correlate or locate this protocol or storage record."""
    name: str
    """Name identifying this declaration within its containing registry."""
    input: dict[str, object]
    """Structured input supplied to the tool invocation."""


class ToolResult(msgspec.Struct, tag="tool_result", frozen=True):
    """Wire-only response to a model's tool invocation."""

    tool_use_id: str = msgspec.field(name="toolUseId")
    """Tool use id produced by ``msgspec.field``."""
    content: tuple[object, ...]
    """Content blocks carried by this protocol value."""
    structured_content: object = msgspec.field(
        name="structuredContent",
        default=msgspec.UNSET,
    )
    """Structured content produced by ``msgspec.field``."""
    is_error: bool | msgspec.UnsetType = msgspec.field(
        name="isError",
        default=msgspec.UNSET,
    )
    """Is error produced by ``msgspec.field``."""
