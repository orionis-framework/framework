from __future__ import annotations
from dataclasses import Field, MISSING, asdict, fields, is_dataclass
from enum import Enum
from typing import Any

# Cache normalized dataclass field metadata by entity class.
_FIELD_METADATA_CACHE: dict[
    type, tuple[tuple[Field[Any], tuple[str, ...]], ...],
] = {}

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

# Provide serialization and field metadata for dataclass entities.
class BaseEntity:
    """Provide dictionary serialization and field metadata for dataclass entities."""

    __slots__ = ()

    # Provide a no-op hook for subclass validation after initialization.
    def __post_init__(self) -> None:
        """
        Provide a no-op initialization hook for subclass validation.

        Returns
        -------
        None
            No value; subclasses may override this hook for validation.
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
        tuple[tuple[Field[Any], tuple[str, ...]], ...]
            Cached field definitions paired with their normalized type names.
        """
        try:
            return _FIELD_METADATA_CACHE[cls]
        except KeyError:
            metadata = []
            for field in fields(cls):
                type_name = getattr(field.type, "__name__", None)
                if type_name is None:
                    type_names = tuple(
                        part.strip() for part in str(field.type).split("|")
                    )
                else:
                    type_names = (type_name,)
                metadata.append((field, type_names))
            result = tuple(metadata)
            _FIELD_METADATA_CACHE[cls] = result
            return result

    # Convert this dataclass instance into a recursively copied dictionary.
    def toDict(self) -> dict[str, Any]:
        """
        Convert the dataclass instance to a recursively copied dictionary.

        Returns
        -------
        dict[str, Any]
            A recursively copied mapping of field names to values.
        """
        return asdict(self, dict_factory=_dict_factory)

    # Describe field names, normalized types, defaults, and metadata.
    def getFields(self) -> list[dict[str, Any]]: # NOSONAR
        """
        Describe field names, normalized types, defaults, and metadata.

        Returns
        -------
        list[dict[str, Any]]
            Field descriptions containing names, types, defaults, and metadata.
        """
        result = []
        for field, type_names in self._cachedFieldMetadata():
            metadata = dict(field.metadata) if field.metadata else {}
            if "default" in metadata:
                metadata_default = metadata["default"]
                if callable(metadata_default):
                    metadata_default = metadata_default()
                if is_dataclass(metadata_default):
                    metadata_default = asdict(metadata_default)
                elif isinstance(metadata_default, Enum):
                    metadata_default = metadata_default.value
                metadata["default"] = metadata_default

            if field.default is not MISSING:
                default = field.default() if callable(field.default) else field.default
            elif field.default_factory is not MISSING:
                default = field.default_factory()
            else:
                default = metadata.get("default")

            if is_dataclass(default):
                default = asdict(default)
            elif isinstance(default, Enum):
                default = default.value

            result.append({
                "name": field.name,
                "types": list(type_names),
                "default": default,
                "metadata": metadata,
            })
        return result
