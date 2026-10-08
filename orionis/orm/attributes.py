from __future__ import annotations
import json
import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any
from orionis.orm.exceptions import MassAssignmentException, OrmException
from orionis.orm.schema.types import ColumnType

if TYPE_CHECKING:
    from collections.abc import Callable
    from orionis.orm.metaclass import ModelMetadata

# Strings interpreted as truthy when casting to bool.
_TRUTHY_STRINGS: frozenset[str] = frozenset({"1", "true", "yes", "on"})

def _cast_bool(value: Any) -> bool:  # noqa: ANN401
    """
    Cast a raw value to ``bool`` handling common textual forms.

    Parameters
    ----------
    value : Any
        Raw attribute value.

    Returns
    -------
    bool
        Boolean representation of the value.
    """
    if isinstance(value, str):
        return value.strip().lower() in _TRUTHY_STRINGS
    return bool(value)

def _cast_datetime(value: Any) -> datetime:  # noqa: ANN401
    """
    Cast a raw value to ``datetime``.

    Parameters
    ----------
    value : Any
        Datetime instance, ISO-8601 string, or POSIX timestamp.

    Returns
    -------
    datetime
        Datetime representation of the value.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    return datetime.fromisoformat(str(value))

def _cast_date(value: Any) -> date:  # noqa: ANN401
    """
    Cast a raw value to ``date``.

    Parameters
    ----------
    value : Any
        Date, datetime, or ISO-8601 string.

    Returns
    -------
    date
        Date representation of the value.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))

def _cast_json(value: Any) -> Any:  # noqa: ANN401
    """
    Cast a raw value to a JSON-decoded Python structure.

    Parameters
    ----------
    value : Any
        JSON string, or an already decoded structure.

    Returns
    -------
    Any
        Decoded Python structure.
    """
    if isinstance(value, (bytes, bytearray, str)):
        return json.loads(value)
    return value

def _cast_uuid(value: Any) -> uuid.UUID:  # noqa: ANN401
    """
    Cast a raw value to :class:`uuid.UUID`.

    Parameters
    ----------
    value : Any
        UUID instance or its string form.

    Returns
    -------
    uuid.UUID
        UUID representation of the value.
    """
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))

# Registry of supported cast names.
_CAST_HANDLERS: dict[str, Callable[[Any], Any]] = {
    "int": int,
    "float": float,
    "bool": _cast_bool,
    "datetime": _cast_datetime,
    "date": _cast_date,
    "json": _cast_json,
    "uuid": _cast_uuid,
}

def get_cast_handler(cast: str) -> Callable[[Any], Any]:
    """
    Return the cast handler registered under the given name.

    Parameters
    ----------
    cast : str
        Cast name declared in a model ``casts`` mapping.

    Returns
    -------
    Callable
        Function converting raw values into the cast type.

    Raises
    ------
    OrmException
        If the cast name is not supported.
    """
    handler = _CAST_HANDLERS.get(str(cast).strip().lower())
    if handler is None:
        supported = ", ".join(sorted(_CAST_HANDLERS))
        error_msg = (
            f"Unsupported cast '{cast}'. Supported casts: {supported}."
        )
        raise OrmException(error_msg)
    return handler

def serialize_for_storage(
    meta: ModelMetadata, values: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert attribute values into driver-friendly storage values.

    Structures stored outside JSON or PickleType columns are serialized to
    strings, and UUID objects targeting neither UUID nor PickleType columns
    are stringified; every other value passes through unchanged.

    Parameters
    ----------
    meta : ModelMetadata
        Metadata of the model owning the attributes.
    values : dict
        Attribute values to serialize.

    Returns
    -------
    dict
        Values ready to be bound into an SQL statement.
    """
    serialized = values.copy()
    columns = meta.columns
    for key, value in values.items():
        if value is None:
            continue
        # JSON structures need explicit encoding outside JSON columns.
        if isinstance(value, (dict, list)):
            column = columns.get(key)
            if column is not None and column.column_type not in {
                ColumnType.JSON, ColumnType.PICKLE_TYPE,
            }:
                serialized[key] = json.dumps(value)
        # UUID objects need their string form outside UUID columns.
        elif isinstance(value, uuid.UUID):
            column = columns.get(key)
            if column is not None and column.column_type not in {
                ColumnType.UUID, ColumnType.PICKLE_TYPE,
            }:
                serialized[key] = str(value)
    return serialized

class AttributesMixin:
    """
    Attribute handling behavior shared by every model.

    Provides mass assignment with fillable/guarded enforcement, cast
    application, and serialization helpers. The mixin operates on the
    ``_attributes`` mapping owned by the model instance.
    """

    __slots__ = ()

    def fill(self, attributes: dict[str, Any]) -> Any:  # noqa: ANN401
        """
        Mass assign the given attributes honoring the assignment rules.

        Parameters
        ----------
        attributes : dict
            Attribute values keyed by column name.

        Returns
        -------
        Model
            The same instance, enabling fluent chaining.

        Raises
        ------
        MassAssignmentException
            If a key is not a column or is guarded from mass assignment.
        """
        meta = self.__meta__
        for key, value in attributes.items():
            if key not in meta.columns:
                error_msg = (
                    f"Attribute '{key}' is not a column of model "
                    f"[{type(self).__name__}]."
                )
                raise MassAssignmentException(error_msg)
            if not meta.isFillable(key):
                error_msg = (
                    f"Attribute '{key}' is not mass assignable on model "
                    f"[{type(self).__name__}]."
                )
                raise MassAssignmentException(error_msg)
            self.setAttribute(key, value)
        return self

    def setAttribute(self, key: str, value: Any) -> None:  # noqa: ANN401
        """
        Assign a single attribute applying its mutator and cast.

        A declared ``set<Name>Attribute`` mutator runs first and its
        return value is what gets stored; the declared cast is applied
        afterwards so both features compose.

        Parameters
        ----------
        key : str
            Attribute name.
        value : Any
            Raw value to assign.

        Returns
        -------
        None
            This method does not return a value.
        """
        meta = self.__meta__
        mutator = meta.mutators.get(key)
        if mutator is not None:
            value = getattr(self, mutator)(value)
        handler = meta.cast_lookup.get(key)
        if handler is not None and value is not None:
            value = handler(value)
        self._attributes[key] = value

    def getAttribute(self, key: str, default: Any = None) -> Any:  # noqa: ANN401
        """
        Return a single attribute value through its accessor.

        A declared ``get<Name>Attribute`` accessor receives the stored
        value (``None`` for computed attributes with no column) and its
        return value is what the caller sees.

        Parameters
        ----------
        key : str
            Attribute name.
        default : Any, optional
            Value returned when the attribute is absent.

        Returns
        -------
        Any
            Attribute value, or the default when absent.
        """
        accessor = self.__meta__.accessors.get(key)
        if accessor is not None:
            return getattr(self, accessor)(self._attributes.get(key, default))
        return self._attributes.get(key, default)

    def hasAccessor(self, key: str) -> bool:
        """
        Report whether an attribute is served by an accessor.

        Parameters
        ----------
        key : str
            Attribute name.

        Returns
        -------
        bool
            ``True`` when the model declares an accessor for the key.
        """
        return key in self.__meta__.accessors

    # ── Serialization ───────────────────────────────────────────────────────

    def toDict(self) -> dict[str, Any]:
        """
        Serialize the visible attributes into a dictionary.

        Accessors are applied, attributes listed in ``hidden`` are
        omitted, and accessor-backed attributes listed in ``appends``
        are added even though they have no column.

        Returns
        -------
        dict
            Visible attribute values keyed by name.
        """
        meta = self.__meta__
        hidden = meta.hidden
        accessors = meta.accessors
        if not hidden and not accessors and not meta.appends:
            return self._attributes.copy()
        data = {
            key: getattr(self, accessors[key])(value)
            if key in accessors
            else value
            for key, value in self._attributes.items()
            if key not in hidden
        }
        for key in meta.appends:
            if key not in hidden:
                data[key] = self.getAttribute(key)
        return data

    def serialize(self) -> dict[str, Any]:
        """
        Serialize the model for collection-level serialization.

        Returns
        -------
        dict
            Visible attribute values keyed by name.
        """
        return self.toDict()

    def toJson(self, **kwargs: Any) -> str:  # noqa: ANN401
        """
        Serialize the visible attributes into a JSON string.

        Parameters
        ----------
        **kwargs : Any
            Additional keyword arguments forwarded to ``json.dumps``.

        Returns
        -------
        str
            JSON representation of the visible attributes.
        """
        kwargs.setdefault("default", str)
        return json.dumps(self.toDict(), **kwargs)

    def only(self, *keys: str) -> dict[str, Any]:
        """
        Return a subset of attributes limited to the given keys.

        Parameters
        ----------
        *keys : str
            Attribute names to include.

        Returns
        -------
        dict
            Attribute values for the requested keys that exist.
        """
        return {
            key: self._attributes[key]
            for key in keys
            if key in self._attributes
        }

    def exclude(self, *keys: str) -> dict[str, Any]:
        """
        Return every attribute except the given keys.

        Parameters
        ----------
        *keys : str
            Attribute names to exclude.

        Returns
        -------
        dict
            Attribute values without the excluded keys.
        """
        excluded = frozenset(keys)
        return {
            key: value
            for key, value in self._attributes.items()
            if key not in excluded
        }
