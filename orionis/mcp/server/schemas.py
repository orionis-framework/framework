"""Generate valid MCP JSON Schema once from Orionis/msgspec type declarations."""

from typing import Annotated, cast, get_args, get_origin

import msgspec

from orionis.schemas.schema import Schema
from orionis.schemas.validator import Schema as Validator

_META_FIELDS = (
    "gt",
    "ge",
    "lt",
    "le",
    "multiple_of",
    "pattern",
    "min_length",
    "max_length",
    "tz",
    "title",
    "description",
    "examples",
    "extra",
)
_ANNOTATION_KEYS = frozenset(
    {
        "title",
        "description",
        "examples",
        "default",
        "deprecated",
        "readOnly",
        "writeOnly",
        "x-mcp-header",
        "$comment",
    },
)
_DIALECT = "https://json-schema.org/draft/2020-12/schema"


def _schema_hook(annotation: type) -> dict[str, object]:
    """Represent an unconstrained JSON value without inventing custom type schemas."""
    if annotation is object:
        return {"$comment": "Any JSON value."}
    message = f"Unsupported native MCP schema type {annotation!r}."
    raise TypeError(message)


def _check_metadata(annotation: object) -> None:
    """Reject extra schema validation rules the native validator cannot enforce."""
    args = get_args(annotation)
    if get_origin(annotation) is not Annotated:
        return
    clean: list[object] = [args[0]]
    additions: list[dict[str, object]] = []
    for item in args[1:]:
        if not isinstance(item, msgspec.Meta):
            clean.append(item)
            continue
        fields = {
            name: value
            for name in _META_FIELDS
            if (value := getattr(item, name, None)) is not None
        }
        clean.append(msgspec.Meta(**fields))
        if item.extra_json_schema:
            additions.append(item.extra_json_schema)
    native = msgspec.json.schema(Annotated[tuple(clean)], schema_hook=_schema_hook)
    for extra in additions:
        for key, value in extra.items():
            if key in _ANNOTATION_KEYS:
                continue
            if key == "$schema" and value == _DIALECT:
                continue
            if key not in native or native[key] != value:
                message = (
                    f"ExtraJsonSchema keyword {key!r} is not enforced "
                    "by the declared native type."
                )
                raise ValueError(message)


def _check_type(annotation: object, visited: set[object]) -> None:
    """Inspect metadata across nested fields and recursive type declarations."""
    _check_metadata(annotation)
    if isinstance(annotation, type) and issubclass(annotation, msgspec.Struct):
        if annotation in visited:
            return
        visited.add(annotation)
        for item in msgspec.structs.fields(annotation):
            _check_type(item.type, visited)
    else:
        for item in get_args(annotation):
            if not isinstance(item, msgspec.Meta):
                _check_type(item, visited)


def compile_schema(
    annotation: object, *, input_schema: bool = False,
) -> dict[str, object]:
    """Produce the native JSON Schema, preserving local references and constraints."""
    _check_type(annotation, set())
    schema = msgspec.json.schema(annotation, schema_hook=_schema_hook)
    if input_schema:
        if not isinstance(annotation, type) or not issubclass(
            annotation, msgspec.Struct,
        ):
            message = (
                "MCP tool inputs must be Orionis Schema or msgspec.Struct classes."
            )
            raise TypeError(message)
        definitions = schema.get("$defs", {})
        referenced: set[str] = set()
        schema = cast("dict[str, object]", _inline(schema, definitions, (), referenced))
        if referenced:
            # Keep recursive definitions exactly once; acyclic definitions are
            # inlined so nested x-mcp-header fields are statically reachable.
            schema["$defs"] = definitions
        if schema.get("type") != "object":
            message = "MCP input schemas must encode objects, not array-like structs."
            raise TypeError(message)
    return schema


def _inline(
    value: object,
    definitions: dict[str, object],
    ancestors: tuple[str, ...],
    referenced: set[str],
) -> object:
    """Inline acyclic local references while preserving recursive definitions."""
    if isinstance(value, list):
        return [_inline(item, definitions, ancestors, referenced) for item in value]
    if not isinstance(value, dict):
        return value
    reference = value.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/$defs/"):
        name = reference.removeprefix("#/$defs/")
        if name in ancestors:
            referenced.add(name)
            return dict(value)
        expanded = cast("dict[str, object]", _inline(
            definitions[name], definitions, (*ancestors, name), referenced,
        ))
        return {
            **expanded,
            **{
                key: item for key, item in value.items() if key not in ("$ref", "$defs")
            },
        }
    return {
        key: _inline(item, definitions, ancestors, referenced)
        for key, item in value.items()
        if key != "$defs"
    }


def convert_payload(value: object, annotation: object) -> object:
    """Validate native rules for Schema and strict msgspec types otherwise."""
    if isinstance(annotation, type) and issubclass(annotation, Schema):
        return Validator.validate(value, annotation)
    return msgspec.convert(value, type=annotation, strict=True)
