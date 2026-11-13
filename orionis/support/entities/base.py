"""Provide dictionary serialization and field metadata for dataclass entities."""

from __future__ import annotations
from dataclasses import Field, MISSING, asdict, fields, is_dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable


# Serialize enum members while preserving other values.
def _enum_serializer(value: object) -> object:
    """
    Serialize enum members and preserve all other values.

    Parameters
    ----------
    value : object
        Value to serialize.

    Returns
    -------
    object
        The enum member's value, or the original value when it is not an enum.
    """
    if isinstance(value, Enum):
        return value.value
    return value


# Build a dictionary while serializing enum field values.
def _dict_factory(items: list[tuple[str, object]]) -> dict[str, object]:
    """
    Build a dictionary and serialize enum field values.

    Parameters
    ----------
    items : list[tuple[str, object]]
        Field names and values supplied by ``dataclasses.asdict``.

    Returns
    -------
    dict[str, object]
        A dictionary with enum values serialized.
    """
    return {key: _enum_serializer(value) for key, value in items}


def _default_value(value: object) -> object:
    """Evaluate a declared default and serialize entity or enum values.

    Parameters
    ----------
    value : object
        Declared default value or zero-argument default provider.

    Returns
    -------
    object
        Evaluated default with dataclasses and enums converted to data.
    """
    result = cast("Callable[[], object]", value)() if callable(value) else value
    if is_dataclass(result):
        return asdict(result)
    return _enum_serializer(result)


# Provide serialization and field metadata for dataclass entities.
class BaseEntity:
    """Provide dictionary serialization and field metadata for dataclass entities."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    # Provide a no-op hook for subclass validation after initialization.
    def __post_init__(self) -> None:
        """
        Provide a no-op initialization hook for subclass validation.

        Returns
        -------
        None
            No return value.
        """

    @classmethod
    # Cache field definitions and their normalized type names per class.
    def _cachedFieldMetadata(
        cls,
    ) -> tuple[tuple[Field[Any], tuple[str, ...]], ...]:
        """
        Retrieve field definitions and normalized types cached by class.

        Returns
        -------
        ``tuple[tuple[dataclasses.Field[Any], tuple[str, ...]], ...]``
            Cached field definitions paired with their normalized type names.
        """
        cached = cls.__dict__.get("_orionis_field_metadata")
        if cached is not None:
            return cached
        metadata = []
        for field in fields(cls):
            type_name = getattr(field.type, "__name__", None)
            if type_name is None:
                type_names = tuple(part.strip() for part in str(field.type).split("|"))
            else:
                type_names = (type_name,)
            metadata.append((field, type_names))
        result = tuple(metadata)
        # The class owns its metadata, including fields that reference itself.
        # Read its own namespace above so subclasses never reuse parent fields.
        cls._orionis_field_metadata = result
        return result

    # Convert this dataclass instance into a recursively copied dictionary.
    def toDict(self) -> dict[str, Any]:
        """
        Convert the dataclass instance to a recursively copied dictionary.

        Returns
        -------
        dict[str, typing.Any]
            A recursively copied mapping of field names to values.
        """
        return asdict(self, dict_factory=_dict_factory)

    # Describe field names, normalized types, defaults, and metadata.
    def getFields(self) -> list[dict[str, Any]]:
        """
        Describe field names, normalized types, defaults, and metadata.

        Returns
        -------
        list[dict[str, typing.Any]]
            Field descriptions containing names, types, defaults, and metadata.
        """
        result = []
        for field, type_names in self._cachedFieldMetadata():
            metadata = dict(field.metadata) if field.metadata else {}
            if "default" in metadata:
                metadata["default"] = _default_value(metadata["default"])

            if field.default is not MISSING:
                default = _default_value(field.default)
            elif field.default_factory is not MISSING:
                default = _default_value(field.default_factory)
            else:
                default = metadata.get("default")

            result.append(
                {
                    "name": field.name,
                    "types": list(type_names),
                    "default": default,
                    "metadata": metadata,
                },
            )
        return result
