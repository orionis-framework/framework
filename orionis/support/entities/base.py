"""Initialize, serialize and describe dataclass entities with extra attributes."""

from __future__ import annotations
from copy import deepcopy
from dataclasses import MISSING, Field, fields, is_dataclass
from enum import Enum
from keyword import iskeyword
from typing import TYPE_CHECKING, Any, ClassVar, cast

if TYPE_CHECKING:
    from collections.abc import Callable


def _serialize_value(value: object) -> object:
    """
    Recursively copy configuration values, entities and enum members.

    Parameters
    ----------
    value : object
        Value to convert or copy.

    Returns
    -------
    object
        A converted dataclass, enum value, container or deep copy.

    Notes
    -----
    Dictionaries and lists become plain dictionaries and lists. Tuples keep
    their shape, including named tuple types. Cyclic entity and container graphs
    are not supported.
    """
    if isinstance(value, Enum):
        return _serialize_value(value.value)

    if isinstance(value, BaseEntity):
        return value.toDict()

    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _serialize_value(getattr(value, item.name))
            for item in fields(value)
        }

    if isinstance(value, dict):
        return {
            _serialize_value(key): _serialize_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [_serialize_value(item) for item in value]

    if isinstance(value, tuple):
        items = tuple(_serialize_value(item) for item in value)
        result = type(value)(*items) if hasattr(type(value), "_fields") else items
    else:
        result = deepcopy(value)
    return result


def _default_value(value: object) -> object:
    """
    Evaluate a declared default and serialize the resulting value.

    Parameters
    ----------
    value : object
        Declared default value or zero-argument default provider.

    Returns
    -------
    object
        The serialized default or the serialized result of the provider.
    """
    result = cast("Callable[[], object]", value)() if callable(value) else value
    return _serialize_value(result)


class BaseEntity:
    """
    Provide a shared constructor, serialization and dataclass metadata.

    Notes
    -----
    Use ``@dataclass(init=False)`` on each subclass that should inherit the
    shared constructor. It accepts only keyword arguments for ordinary fields
    and public extra attributes; ``InitVar`` parameters are not supported.
    Extras require an instance dictionary, normally provided by ``slots=False``.

    Fields marked ``init=False`` cannot be supplied by the caller. Their
    defaults are initialized, or ``__post_init__`` must set them when no default
    exists. Subclasses are responsible for type validation.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    _orionis_field_metadata: ClassVar[tuple[tuple[Field[Any], tuple[str, ...]], ...]]
    """Cache declared fields and normalized type names for each concrete class."""

    def __init__(self, **kwargs: object) -> None:
        """
        Initialize declared fields and public extra attributes.

        Parameters
        ----------
        **kwargs : object
            Values for declared init fields and public extra attributes.

        Returns
        -------
        ``None``
            Initialize declared fields and extras, then run subclass validation.

        Raises
        ------
        TypeError
            If the subclass is not a dataclass, a required field is missing,
            a non-init field is supplied, an extra name is invalid or reserved,
            or extras cannot be stored because the instance has no dictionary.
        """
        if not is_dataclass(self):
            message = f"{type(self).__name__} must be decorated with dataclass."
            raise TypeError(message)

        declared = {item.name: item for item in fields(self)}
        extra_names = [name for name in kwargs if name not in declared]

        # Reject invalid input before running factories or mutating the instance.
        self._validateExtraNames(extra_names)
        for item in declared.values():
            if not item.init and item.name in kwargs:
                message = f"Field {item.name!r} has init=False and cannot be supplied."
                raise TypeError(message)
            if (
                item.init
                and item.name not in kwargs
                and item.default is MISSING
                and item.default_factory is MISSING
            ):
                message = f"Missing required argument: {item.name!r}."
                raise TypeError(message)

        for name, item in declared.items():
            if name in kwargs:
                value = kwargs[name]
            elif item.default_factory is not MISSING:
                value = item.default_factory()
            elif item.default is not MISSING:
                value = item.default
            else:
                continue
            object.__setattr__(self, name, value)

        for name in extra_names:
            object.__setattr__(self, name, kwargs[name])

        self.__post_init__()

    def _validateExtraNames(self, names: list[str]) -> None:
        """
        Validate names and storage for public extra attributes.

        Parameters
        ----------
        names : list[str]
            Supplied keyword names that are not declared fields.

        Returns
        -------
        ``None``
            Confirm that all supplied extras have valid names and storage.

        Raises
        ------
        TypeError
            If a name is invalid, private or already defined on the class,
            or if the instance has no dictionary for the supplied extras.
        """
        for name in names:
            if not name.isidentifier() or iskeyword(name):
                message = f"Invalid attribute name: {name!r}."
                raise TypeError(message)
            if name.startswith("_") or hasattr(type(self), name):
                message = f"Reserved attribute name: {name!r}."
                raise TypeError(message)

        if names and not hasattr(self, "__dict__"):
            message = (
                f"{type(self).__name__} cannot store dynamic attributes; "
                "use a dataclass with slots=False."
            )
            raise TypeError(message)

    def __post_init__(self) -> None:
        """
        Provide a no-op hook for subclass validation and normalization.

        Returns
        -------
        ``None``
            Leave the initialized fields and extra attributes unchanged.
        """

    @classmethod
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
        cached: tuple[tuple[Field[Any], tuple[str, ...]], ...] | None = (
            cls.__dict__.get("_orionis_field_metadata")
        )
        if cached is not None:
            return cached
        metadata: list[tuple[Field[Any], tuple[str, ...]]] = []
        for item in fields(cls):
            type_name = getattr(item.type, "__name__", None)
            if type_name is None:
                type_names = tuple(part.strip() for part in str(item.type).split("|"))
            else:
                type_names = (type_name,)
            metadata.append((item, type_names))
        result = tuple(metadata)
        # Each concrete class owns its cache, even when annotations refer to it.
        cls._orionis_field_metadata = result
        return result

    def _dynamicAttributes(self) -> dict[str, object]:
        """
        Return public instance attributes that are not declared fields.

        Returns
        -------
        dict[str, object]
            Public extra names and their current values.
        """
        declared_names = {item.name for item in fields(self)}
        state = getattr(self, "__dict__", {})
        return {
            name: value
            for name, value in state.items()
            if name not in declared_names and not name.startswith("_")
        }

    def toDict(self) -> dict[str, Any]:
        """
        Return a recursively copied dictionary of declared and extra values.

        Returns
        -------
        dict[str, typing.Any]
            Declared fields and public extra attributes mapped to their values.

        Notes
        -----
        Unlike ``dataclasses.asdict``, nested entities include their own public
        extra attributes. Enum members are replaced by their values, including
        inside dictionaries, lists and tuples. Declared private fields are
        included; private extra attributes are not.

        This method does not encode JSON or support cyclic entity or container
        graphs.
        """
        result = {
            item.name: _serialize_value(getattr(self, item.name))
            for item in fields(self)
        }
        result.update(
            {
                name: _serialize_value(value)
                for name, value in self._dynamicAttributes().items()
            },
        )
        return result

    def getFields(self, *, include_dynamic: bool = False) -> list[dict[str, Any]]:
        """
        Describe declared fields and, optionally, dynamic attributes.

        Parameters
        ----------
        include_dynamic : bool, optional
            Append descriptions of public extra attributes on this instance,
            using their current types, ``None`` for their defaults, and
            ``{"dynamic": True}`` for their metadata. Defaults to ``False``.

        Returns
        -------
        list[dict[str, typing.Any]]
            Field descriptions containing names, types, defaults, and metadata.

        Notes
        -----
        Declared defaults are evaluated and serialized on each call.
        Descriptions of dynamic attributes are not cached.
        """
        result: list[dict[str, Any]] = []
        for item, type_names in self._cachedFieldMetadata():
            metadata = dict(item.metadata) if item.metadata else {}
            if "default" in metadata:
                metadata["default"] = _default_value(metadata["default"])

            if item.default is not MISSING:
                default = _default_value(item.default)
            elif item.default_factory is not MISSING:
                default = _default_value(item.default_factory)
            else:
                default = metadata.get("default")

            result.append(
                {
                    "name": item.name,
                    "types": list(type_names),
                    "default": default,
                    "metadata": metadata,
                },
            )

        if include_dynamic:
            for name, value in self._dynamicAttributes().items():
                result.append(
                    {
                        "name": name,
                        "types": [type(value).__name__],
                        "default": None,
                        "metadata": {"dynamic": True},
                    },
                )

        return result
