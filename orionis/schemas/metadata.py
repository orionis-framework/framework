from __future__ import annotations
from dataclasses import dataclass
from orionis.schemas.meta.document import DocumentMetadata

@dataclass(frozen=True, slots=True)
class Title(DocumentMetadata):
    """
    Provide a human-readable title for the field in JSON Schema / OpenAPI.

    Parameters
    ----------
    value : str
        The field title shown in generated schema output.
    """

    value: str

@dataclass(frozen=True, slots=True)
class Description(DocumentMetadata):
    """
    Provide a human-readable description for the field in JSON Schema / OpenAPI.

    Parameters
    ----------
    value : str
        The field description shown in generated schema output.
    """

    value: str

@dataclass(frozen=True, slots=True)
class Examples(DocumentMetadata):
    """
    Provide example values for the field in JSON Schema / OpenAPI.

    Parameters
    ----------
    values : list[object]
        A list of example values; each must be JSON-serialisable.
    """

    values: list[object]

@dataclass(frozen=True, slots=True)
class ExtraJsonSchema(DocumentMetadata):
    """
    Inject additional raw JSON Schema properties for the field.

    The ``data`` mapping is merged directly into the generated JSON Schema
    object, allowing arbitrary schema extensions (e.g. ``readOnly``,
    ``deprecated``, vendor-specific ``x-`` properties).

    Parameters
    ----------
    data : dict[str, object]
        Key/value pairs to merge into the JSON Schema object.
    """

    data: dict[str, object]

@dataclass(frozen=True, slots=True)
class Extra(DocumentMetadata):
    """
    Attach arbitrary extra data to the field metadata.

    The ``data`` mapping is passed through as-is and is not interpreted
    by the schema generation pipeline. Use it for application-specific
    annotations that do not belong in the JSON Schema output.

    Parameters
    ----------
    data : dict[str, object]
        Arbitrary key/value pairs to attach to the field.
    """

    data: dict[str, object]

@dataclass(frozen=True, slots=True)
class Message(DocumentMetadata):
    """
    Attach a custom type-mismatch error message to a field.

    Use this inside ``Annotated`` to override the default msgspec
    "Expected <type>" error when the field value has the wrong type.
    It is the only way to provide a custom message for plain-type fields
    (e.g. ``code: Annotated[str, Message("Must be a string.")]``).

    It may also be combined with constraint metadata to cover both
    type errors and constraint errors on the same field.

    Parameters
    ----------
    text : str
        The custom error message shown when type validation fails.
    """

    text: str

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__: list[str] = [
    "Description",
    "DocumentMetadata",
    "Examples",
    "Extra",
    "ExtraJsonSchema",
    "Message",
    "Title",
]
