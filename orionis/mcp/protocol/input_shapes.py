"""Native typed validation plans for modern MRTR wire payloads."""

from typing import Annotated, Literal

import msgspec

type OptionalString = str | msgspec.UnsetType
type Nonnegative = Annotated[int, msgspec.Meta(ge=0)]
type Priority = Annotated[float, msgspec.Meta(ge=0, le=1)]
type FormValue = str | float | bool | list[str]


class FormResult(msgspec.Struct, frozen=True):
    """An elicitation response, with no JSON-RPC error envelope."""

    action: Literal["accept", "decline", "cancel"]
    content: dict[str, FormValue] | msgspec.UnsetType = msgspec.UNSET


class EnumOption(msgspec.Struct, frozen=True):
    """A titled single selection option."""

    const: str
    title: str


class FormField(msgspec.Struct, frozen=True):
    """The non-nesting primitive schema supported by elicitation forms."""

    type: Literal["string", "number", "integer", "boolean", "array"]
    title: OptionalString = msgspec.UNSET
    description: OptionalString = msgspec.UNSET
    minimum: float | msgspec.UnsetType = msgspec.UNSET
    maximum: float | msgspec.UnsetType = msgspec.UNSET
    min_length: Nonnegative | msgspec.UnsetType = msgspec.field(
        name="minLength", default=msgspec.UNSET,
    )
    max_length: Nonnegative | msgspec.UnsetType = msgspec.field(
        name="maxLength", default=msgspec.UNSET,
    )
    min_items: Nonnegative | msgspec.UnsetType = msgspec.field(
        name="minItems", default=msgspec.UNSET,
    )
    max_items: Nonnegative | msgspec.UnsetType = msgspec.field(
        name="maxItems", default=msgspec.UNSET,
    )
    format: Literal["email", "uri", "date", "date-time"] | msgspec.UnsetType = (
        msgspec.UNSET
    )
    enum: tuple[str, ...] | msgspec.UnsetType = msgspec.UNSET
    enum_names: tuple[str, ...] | msgspec.UnsetType = msgspec.field(
        name="enumNames", default=msgspec.UNSET,
    )
    one_of: tuple[EnumOption, ...] | msgspec.UnsetType = msgspec.field(
        name="oneOf", default=msgspec.UNSET,
    )
    items: dict[str, object] | msgspec.UnsetType = msgspec.UNSET
    default: object = msgspec.UNSET


class EnumItems(msgspec.Struct, frozen=True):
    """The two permitted string enumeration item schemas."""

    type: Literal["string"] | msgspec.UnsetType = msgspec.UNSET
    enum: tuple[str, ...] | msgspec.UnsetType = msgspec.UNSET
    any_of: tuple[EnumOption, ...] | msgspec.UnsetType = msgspec.field(
        name="anyOf", default=msgspec.UNSET,
    )


class FormSchema(msgspec.Struct, frozen=True):
    """A flat object containing elicitation form fields."""

    type: Literal["object"]
    properties: dict[str, FormField]
    required: tuple[str, ...] = ()
    schema: OptionalString = msgspec.field(name="$schema", default=msgspec.UNSET)


class FormRequest(msgspec.Struct, frozen=True):
    """Form elicitation parameters."""

    message: str
    requested_schema: FormSchema = msgspec.field(name="requestedSchema")
    mode: Literal["form"] = "form"


class UrlRequest(msgspec.Struct, frozen=True):
    """Out-of-band elicitation parameters."""

    mode: Literal["url"]
    message: str
    url: str


class Root(msgspec.Struct, frozen=True):
    """Wire-only deprecated root descriptor."""

    uri: str
    name: OptionalString = msgspec.UNSET
    meta: dict[str, object] | msgspec.UnsetType = msgspec.field(
        name="_meta", default=msgspec.UNSET,
    )


class RootsResult(msgspec.Struct, frozen=True):
    """Wire-only deprecated roots result."""

    roots: tuple[Root, ...]


class SamplingMessage(msgspec.Struct, frozen=True):
    """Wire-only deprecated sampling message."""

    role: Literal["user", "assistant"]
    content: object
    meta: dict[str, object] | msgspec.UnsetType = msgspec.field(
        name="_meta", default=msgspec.UNSET,
    )


class SamplingResult(SamplingMessage, frozen=True, kw_only=True):
    """Wire-only deprecated sampling response."""

    model: str
    stop_reason: OptionalString = msgspec.field(
        name="stopReason", default=msgspec.UNSET,
    )


class ModelHint(msgspec.Struct, frozen=True):
    """A provider-agnostic model hint."""

    name: OptionalString = msgspec.UNSET


class ModelPreferences(msgspec.Struct, frozen=True):
    """Bounded priorities for a wire sampling request."""

    hints: tuple[ModelHint, ...] | msgspec.UnsetType = msgspec.UNSET
    cost: Priority | msgspec.UnsetType = msgspec.field(
        name="costPriority", default=msgspec.UNSET,
    )
    speed: Priority | msgspec.UnsetType = msgspec.field(
        name="speedPriority", default=msgspec.UNSET,
    )
    intelligence: Priority | msgspec.UnsetType = msgspec.field(
        name="intelligencePriority", default=msgspec.UNSET,
    )


class ToolChoice(msgspec.Struct, frozen=True):
    """The protocol's sampling tool policy."""

    mode: Literal["auto", "required", "none"] = "auto"


class SamplingRequest(msgspec.Struct, frozen=True):
    """Wire-only deprecated sampling parameters."""

    messages: tuple[SamplingMessage, ...]
    max_tokens: int = msgspec.field(name="maxTokens")
    model_preferences: ModelPreferences | msgspec.UnsetType = msgspec.field(
        name="modelPreferences", default=msgspec.UNSET,
    )
    system_prompt: OptionalString = msgspec.field(
        name="systemPrompt", default=msgspec.UNSET,
    )
    include_context: Literal["none", "thisServer", "allServers"] = msgspec.field(
        name="includeContext", default="none",
    )
    temperature: float | msgspec.UnsetType = msgspec.UNSET
    stop_sequences: tuple[str, ...] | msgspec.UnsetType = msgspec.field(
        name="stopSequences", default=msgspec.UNSET,
    )
    metadata: dict[str, object] | msgspec.UnsetType = msgspec.UNSET
    tools: tuple[dict[str, object], ...] | msgspec.UnsetType = msgspec.UNSET
    tool_choice: ToolChoice | msgspec.UnsetType = msgspec.field(
        name="toolChoice", default=msgspec.UNSET,
    )


class ToolUse(msgspec.Struct, tag="tool_use", frozen=True):
    """Wire-only model invocation of a tool."""

    id: str
    name: str
    input: dict[str, object]


class ToolResult(msgspec.Struct, tag="tool_result", frozen=True):
    """Wire-only response to a model's tool invocation."""

    tool_use_id: str = msgspec.field(name="toolUseId")
    content: tuple[object, ...]
    structured_content: object = msgspec.field(
        name="structuredContent", default=msgspec.UNSET,
    )
    is_error: bool | msgspec.UnsetType = msgspec.field(
        name="isError", default=msgspec.UNSET,
    )
