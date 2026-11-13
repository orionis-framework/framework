"""Prepare explicitly coercible values without changing the source payload."""

from collections.abc import Collection, Iterable, Mapping
from functools import lru_cache
import types
from typing import Annotated, Union, get_args, get_origin
import msgspec
from orionis.schemas.constraint_plan import constraint_plan
from orionis.schemas.instance_payload import (
    instance_payload,
    matching_schema,
    matching_type,
)
from orionis.schemas.metadata import Coerce
from orionis.schemas.rules_executor import _collection_item_type

_convert = msgspec.convert
_ValidationError = msgspec.ValidationError


def _requires_preparation(annotation: object) -> bool:
    """
    Find coercion markers or struct types requiring instance revalidation.

    Parameters
    ----------
    annotation : object
        Field, collection item or union annotation to inspect.

    Returns
    -------
    bool
        Whether conversion requires coercion or expansion of existing structs.
    """
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Annotated:
        return any(
            isinstance(item, Coerce) for item in args[1:]
        ) or _requires_preparation(args[0])
    if isinstance(annotation, type) and issubclass(annotation, msgspec.Struct):
        return True
    if isinstance(origin, type) and issubclass(origin, Mapping):
        args = args[1:]
    return any(_requires_preparation(arg) for arg in args)


@lru_cache(maxsize=1024)
def _field_plan(
    schema: type[msgspec.Struct],
    *,
    enabled: bool,
) -> tuple[tuple[str, int, object], ...]:
    """
    Cache fields requiring coercion or struct expansion and their wire positions.

    Parameters
    ----------
    schema : type[``msgspec.Struct``]
        Schema whose fields are prepared.
    enabled : bool
        Whether an enclosing marker enables every field in this schema.

    Returns
    -------
    tuple[tuple[str, int, object], ``...``]
        Encoded names, positional indices and field annotations.
    """
    offset = int(schema.__struct_config__.tag is not None)
    return tuple(
        (field.encode_name, index, field.type)
        for index, field in enumerate(msgspec.structs.fields(schema), offset)
        if enabled or _requires_preparation(field.type)
    )


def coerce_payload(
    payload: object,
    schema: type[msgspec.Struct],
    *,
    enabled: bool = False,
) -> object:
    """
    Prepare marked values and existing structs using copy-on-write containers.

    Existing struct constructors and mutations bypass native validation, so
    expand those instances before the final conversion. Unmarked scalar fields
    remain strict and schemas without preparation retain their original inputs.

    Parameters
    ----------
    payload : object
        Input mapping, positional data or existing schema instance.
    schema : type[``msgspec.Struct``]
        Schema declaring the target types and coercion metadata.
    enabled : bool, optional
        Whether an enclosing marker enables all descendant fields.

    Returns
    -------
    object
        Prepared payload, or the original value when no changes are needed.
    """
    if isinstance(payload, schema):
        payload = instance_payload(payload)
    plan = _field_plan(schema, enabled=enabled)
    if not plan:
        return payload
    if matching_schema(schema, payload) is None:
        return payload
    if isinstance(payload, Mapping):
        return _coerce_mapping(
            payload,
            (
                (name, payload[name], annotation)
                for name, _, annotation in plan
                if name in payload
            ),
            enabled=enabled,
        )
    if isinstance(payload, list | tuple):
        return _coerce_array(payload, plan, enabled=enabled)
    return payload


def _coerce_mapping(
    payload: Mapping[object, object],
    entries: Iterable[tuple[object, object, object]],
    *,
    enabled: bool,
) -> object:
    """
    Normalize selected mapping entries without changing their source.

    Parameters
    ----------
    payload : Mapping[object, object]
        Original mapping copied only when a value changes.
    entries : Iterable[tuple[object, object, object]]
        Keys, current values and target annotations to normalize.
    enabled : bool
        Whether an enclosing marker enables every selected value.

    Returns
    -------
    object
        Updated mapping or the original input when no values change.
    """
    mapping = None
    for key, value, annotation in entries:
        converted = _coerce_value(value, annotation, enabled=enabled)
        if converted is not value:
            if mapping is None:
                mapping = dict(payload)
            mapping[key] = converted
    return payload if mapping is None else mapping


def _coerce_array(
    payload: list | tuple,
    plan: tuple[tuple[str, int, object], ...],
    *,
    enabled: bool,
) -> object:
    """
    Normalize declared array fields without consuming the discriminator tag.

    Parameters
    ----------
    payload : list | tuple
        Positional schema input.
    plan : tuple[tuple[str, int, object], ``...``]
        Encoded field names, indices and target annotations.
    enabled : bool
        Whether an enclosing marker enables every field.

    Returns
    -------
    object
        Updated positional input or the original sequence.
    """
    sequence = None
    for _, index, annotation in plan:
        if index >= len(payload):
            continue
        value = payload[index]
        converted = _coerce_value(value, annotation, enabled=enabled)
        if converted is not value:
            if sequence is None:
                sequence = list(payload)
            sequence[index] = converted
    return payload if sequence is None else sequence


def _coerce_collection(
    value: object,
    annotation: object,
    *,
    enabled: bool,
) -> object:
    """
    Prepare collection values while preserving keys and fixed tuple positions.

    Parameters
    ----------
    value : object
        Input collection or incompatible value left for validation.
    annotation : object
        Collection annotation declaring its item types.
    enabled : bool
        Whether an enclosing marker enables every collection value.

    Returns
    -------
    object
        Prepared collection, or the unchanged input.
    """
    origin = get_origin(annotation)
    args = get_args(annotation)
    if not args:
        return value
    if issubclass(origin, Mapping):
        if not isinstance(value, Mapping):
            return value
        return _coerce_mapping(
            value,
            ((key, item, args[1]) for key, item in value.items()),
            enabled=enabled,
        )
    if not isinstance(value, list | tuple | set | frozenset):
        return value
    if not enabled:
        schema = _plain_struct_item(origin, args)
        if schema is not None:
            return _expand_struct_sequence(value, schema)
    sequence = []
    changed = False
    for index, item in enumerate(value):
        item_type = _collection_item_type(annotation, str(index))
        converted = (
            _coerce_value(item, item_type, enabled=enabled)
            if item_type is not None
            else item
        )
        sequence.append(converted)
        changed |= converted is not item
    if changed:
        value = tuple(sequence) if isinstance(value, tuple) else sequence
    return value


def _plain_struct_item(
    origin: type,
    args: tuple[object, ...],
) -> type[msgspec.Struct] | None:
    """
    Select uniform struct items whose fields need no further preparation.

    Parameters
    ----------
    origin : type
        Collection origin used to distinguish fixed and variadic tuples.
    args : tuple[object, ``...``]
        Collection type arguments, already extracted by the caller.

    Returns
    -------
    type[``msgspec.Struct``] | None
        Uniform struct type with an empty preparation plan, if applicable.
    """
    uniform = len(args) == 1 and origin is not tuple
    variadic = origin is tuple and args[1:] == (Ellipsis,)
    if not (uniform or variadic):
        return None
    schema = args[0]
    if not isinstance(schema, type) or not issubclass(schema, msgspec.Struct):
        return None
    return None if _field_plan(schema, enabled=False) else schema


def _expand_struct_sequence(
    value: list | tuple | set | frozenset,
    schema: type[msgspec.Struct],
) -> object:
    """
    Expand existing struct items and leave native input representations intact.

    Parameters
    ----------
    value : list | tuple | set | frozenset
        Homogeneous collection copied only when an instance needs expansion.
    schema : type[``msgspec.Struct``]
        Item type with no descendant coercion or struct preparation.

    Returns
    -------
    object
        Original collection or a copy containing expanded instance payloads.
    """
    sequence = None
    for index, item in enumerate(value):
        if isinstance(item, schema):
            if sequence is None:
                sequence = list(value)
            sequence[index] = instance_payload(item)
    if sequence is None:
        return value
    return tuple(sequence) if isinstance(value, tuple) else sequence


def _coerce_union(
    value: object,
    annotation: object,
    *,
    enabled: bool,
) -> object:
    """
    Preserve compatible union branches and normalize only matching structures.

    Parameters
    ----------
    value : object
        Union input to prepare.
    annotation : object
        Declared union and its branch metadata.
    enabled : bool
        Whether an enclosing marker enables every branch.

    Returns
    -------
    object
        Prepared branch value or unchanged incompatible input.
    """
    args = get_args(annotation)
    # Shape selection avoids constructing nested schemas twice just to match.
    for branch in args:
        if matching_type(branch, value) is not None:
            return _coerce_value(value, branch, enabled=enabled)
    base_type, _ = constraint_plan(annotation)
    try:
        _convert(value, type=base_type)
    except _ValidationError:
        for branch in args:
            converted = _coerce_value(value, branch, enabled=enabled)
            if converted is not value:
                return converted
    return value


def _coerce_value(
    value: object,
    annotation: object,
    *,
    enabled: bool,
) -> object:
    """
    Normalize a selected annotation before applying any value constraints.

    Parameters
    ----------
    value : object
        Value to normalize.
    annotation : object
        Declared type, possibly annotated, nested or a union.
    enabled : bool
        Whether an enclosing marker already enabled coercion.

    Returns
    -------
    object
        Converted value or input retained for standard error reporting.
    """
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Annotated:
        return _coerce_value(
            value,
            args[0],
            enabled=enabled or any(isinstance(item, Coerce) for item in args[1:]),
        )
    if origin is Union or origin is types.UnionType:
        return _coerce_union(value, annotation, enabled=enabled)
    if isinstance(annotation, type) and issubclass(annotation, msgspec.Struct):
        return coerce_payload(value, annotation, enabled=enabled)
    if isinstance(origin, type) and issubclass(origin, Collection):
        return _coerce_collection(value, annotation, enabled=enabled)
    if enabled:
        try:
            return _convert(value, type=annotation, strict=False)
        except _ValidationError:
            # Keep invalid input so the standard collector reports every error.
            pass
    return value
