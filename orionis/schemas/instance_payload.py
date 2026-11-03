"""Provide schemas operations through ``instance_payload``."""

from collections.abc import Collection, Mapping
import types
from typing import Annotated, Union, get_args, get_origin
import msgspec

_PLANS: dict[type, tuple] = {}
"""Plans definitions used by ``instance_payload``."""

def matching_type(annotation: object, value: object) -> object | None:
    """
    Select a schema or collection annotation matching an input representation.

    Parameters
    ----------
    annotation : object
        Field annotation, possibly annotated or a union.
    value : object
        Input whose shape and discriminator tag are inspected.

    Returns
    -------
    object | None
        Matching schema or collection annotation, if one applies.
    """
    origin = get_origin(annotation)
    if origin is Annotated:
        return matching_type(get_args(annotation)[0], value)
    if origin is Union or origin is types.UnionType:
        return next((
            match for arg in get_args(annotation)
            if (match := matching_type(arg, value)) is not None
        ), None)
    if (
        isinstance(annotation, type)
        and issubclass(annotation, msgspec.Struct)
        and "__orionis_meta__" in annotation.__dict__
    ):
        return matching_schema(annotation, value)
    if not isinstance(origin, type):
        return None
    expected = (
        Mapping if issubclass(origin, Mapping) else (list, tuple, set, frozenset)
    )
    return annotation if (
        issubclass(origin, Collection) and isinstance(value, expected)
    ) else None

def matching_schema(
    schema: type[msgspec.Struct], value: object,
) -> type[msgspec.Struct] | None:
    """
    Match a schema's wire representation and optional discriminator tag.

    Parameters
    ----------
    schema : type[msgspec.Struct]
        Schema whose object or array representation is expected.
    value : object
        Input to compare with the schema configuration.

    Returns
    -------
    type[msgspec.Struct] | None
        Schema when its shape and tag match, otherwise ``None``.
    """
    config = schema.__struct_config__
    if config.array_like:
        return schema if (
            isinstance(value, list | tuple)
            and (config.tag is None or (value and value[0] == config.tag))
        ) else None
    return schema if (
        isinstance(value, Mapping)
        and (config.tag is None or value.get(config.tag_field) == config.tag)
    ) else None

def instance_payload(value: object) -> object:
    """
    Expand structs using their wire names, tags and container shape.

    Include default values and preserve native leaves so validation cannot
    skip existing struct fields or accept values coerced by serialization.

    Parameters
    ----------
    value : object
        Struct, supported container or native value to prepare for validation.

    Returns
    -------
    object
        Expanded dictionaries and lists, or the original native leaf value.
    """
    if isinstance(value, msgspec.Struct):
        klass = type(value)
        plan = _PLANS.get(klass)
        if plan is None:
            config = klass.__struct_config__
            plan = (
                tuple((f.name, f.encode_name) for f in msgspec.structs.fields(klass)),
                config.array_like, config.tag, config.tag_field,
            )
            _PLANS[klass] = plan
        fields, array_like, tag, tag_field = plan
        if array_like:
            result = [tag] if tag is not None else []
            result.extend(instance_payload(getattr(value, name)) for name, _ in fields)
            return result
        result = {tag_field: tag} if tag is not None else {}
        result.update(
            (encoded, instance_payload(getattr(value, name)))
            for name, encoded in fields
        )
        return result
    if isinstance(value, dict):
        return {key: instance_payload(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [instance_payload(item) for item in value]
    return value
