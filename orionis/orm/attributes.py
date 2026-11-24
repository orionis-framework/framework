# ruff: noqa: ANN401, TC001, TC002, TC003
# Retain runtime annotations and dynamic attribute values.
"""Attribute handling behavior shared by every model."""

from __future__ import annotations
import json
import pendulum
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from collections.abc import Callable
from typing import Any, Self
from orionis.orm import metaclass as metaclass_module
from orionis.orm.exceptions import MassAssignmentException, OrmException
from orionis.orm.schema.types import ColumnType
from orionis.support.facades import DateTime

# Strings interpreted as truthy when casting to bool.
_TRUTHY_STRINGS: frozenset[str] = frozenset({"1", "true", "yes", "on"})
"""Strings interpreted as truthy when casting to bool."""


def _cast_bool(value: Any) -> bool:
    """
    Cast a raw value to ``bool`` handling common textual forms.

    Parameters
    ----------
    value : typing.Any
        Raw attribute value.

    Returns
    -------
    bool
        Boolean representation of the value.
    """
    if isinstance(value, str):
        return value.strip().lower() in _TRUTHY_STRINGS
    return bool(value)


def _cast_datetime(value: Any) -> pendulum.DateTime:
    """
    Cast a raw value to ``datetime``.

    Parameters
    ----------
    value : typing.Any
        Datetime instance, ISO-8601 string, or POSIX timestamp.

    Returns
    -------
    ``pendulum.DateTime``
        Datetime in the application timezone.
    """
    if isinstance(value, (int, float)):
        value = datetime.fromtimestamp(value, tz=UTC)
    elif not isinstance(value, datetime):
        value = datetime.fromisoformat(str(value))
    return DateTime.fromDatetime(value)


def _cast_date(value: Any) -> date:
    """
    Cast a raw value to ``date``.

    Parameters
    ----------
    value : typing.Any
        Date, datetime, or ISO-8601 string.

    Returns
    -------
    datetime.date
        Date representation of the value.

    Raises
    ------
    ValueError
        If the input string is not an ISO calendar date.
    """
    if isinstance(value, datetime):
        return DateTime.fromDatetime(value).date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _cast_json(value: Any) -> Any:
    """
    Cast a raw value to a JSON-decoded Python structure.

    Parameters
    ----------
    value : typing.Any
        JSON string, or an already decoded structure.

    Returns
    -------
    typing.Any
        Decoded Python structure.
    """
    if isinstance(value, (bytes, bytearray, str)):
        return json.loads(value)
    return value


def _cast_uuid(value: Any) -> uuid.UUID:
    """
    Cast a raw value to ``uuid.UUID``.

    Parameters
    ----------
    value : typing.Any
        UUID instance or its string form.

    Returns
    -------
    ``uuid.UUID``
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
"""Registry of supported cast names."""


def get_cast_handler(cast: str) -> Callable[[Any], Any]:
    """
    Return the cast handler registered under the given name.

    Parameters
    ----------
    cast : str
        Cast name declared in a model ``casts`` mapping.

    Returns
    -------
    collections.abc.Callable
        Function converting raw values into the cast type.

    Raises
    ------
    orionis.orm.exceptions.OrmException
        If the cast name is not supported.
    """
    handler = _CAST_HANDLERS.get(str(cast).strip().lower())
    if handler is None:
        supported = ", ".join(sorted(_CAST_HANDLERS))
        error_msg = f"Unsupported cast '{cast}'. Supported casts: {supported}."
        raise OrmException(error_msg)
    return handler


def local_stored_timestamp(value: datetime | str) -> pendulum.DateTime:
    """
    Read an ORM-managed UTC timestamp, including offset-less legacy rows.

    Parameters
    ----------
    value : datetime.datetime or str
        Driver value or ISO text from a managed timestamp column.

    Returns
    -------
    ``pendulum.DateTime``
        The stored UTC instant in the application timezone.

    Raises
    ------
    ValueError
        If a string cannot be parsed as an ISO datetime.
    """
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return DateTime.fromDatetime(value)


@dataclass(frozen=True, slots=True)
class DateTimeStorage:
    """
    Bind a datetime according to its column's storage policy.

    Attributes
    ----------
    aware : bool
        Whether the column accepts a datetime with an offset.
    managed : bool
        Whether the ORM maintains this timestamp in UTC.
    """

    aware: bool
    managed: bool

    def bind(self, value: datetime | str | float) -> datetime:
        """
        Store managed timestamps in UTC and user casts in application time.

        Parameters
        ----------
        value : datetime.datetime, str or float
            Datetime, ISO text or POSIX timestamp supplied to the model.

        Returns
        -------
        datetime.datetime
            Value using the timezone representation accepted by the column.

        Raises
        ------
        ValueError
            If a string cannot be parsed as an ISO datetime.
        """
        moment = _cast_datetime(value)
        if self.managed:
            moment = moment.astimezone(UTC)
        return moment if self.aware else moment.replace(tzinfo=None)


def serialize_for_storage(
    meta: metaclass_module.ModelMetadata,
    values: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert attribute values into driver-friendly storage values.

    Structures stored outside JSON or PickleType columns are serialized to
    strings, UUID objects are stringified outside native UUID or PickleType
    columns, and ORM-maintained timestamps are normalized to UTC per column.

    Parameters
    ----------
    meta : orionis.orm.metaclass.ModelMetadata
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
        storage = meta.datetime_storage.get(key)
        if storage is not None and isinstance(value, (datetime, str, int, float)):
            serialized[key] = storage.bind(value)
            continue
        column = columns.get(key)
        if column is None or column.column_type == ColumnType.PICKLE_TYPE:
            continue
        if isinstance(value, (dict, list)) and column.column_type != ColumnType.JSON:
            serialized[key] = json.dumps(value)
        elif isinstance(value, uuid.UUID) and column.column_type != ColumnType.UUID:
            serialized[key] = str(value)
    return serialized


class AttributesMixin:
    """
    Assign, cast and serialize model attributes.

    Provides mass assignment with fillable/guarded enforcement, cast
    application, and serialization helpers. The mixin operates on the
    ``_attributes`` mapping owned by the model instance.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    def fill(self, attributes: dict[str, Any]) -> Self:
        """
        Mass assign the given attributes honoring the assignment rules.

        Parameters
        ----------
        attributes : dict
            Attribute values keyed by column name.

        Returns
        -------
        orionis.orm.Model
            The same instance, enabling fluent chaining.

        Raises
        ------
        orionis.orm.exceptions.MassAssignmentException
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

    def setAttribute(self, key: str, value: Any) -> None:
        """
        Assign a single attribute applying its mutator and cast.

        A declared ``set<Name>Attribute`` mutator runs first and its
        return value is what gets stored; the declared cast is applied
        afterwards so both features compose.

        Parameters
        ----------
        key : str
            Attribute name.
        value : typing.Any
            Raw value to assign.

        Returns
        -------
        None
            No return value.
        """
        meta = self.__meta__
        mutator = meta.mutators.get(key)
        if mutator is not None:
            value = getattr(self, mutator)(value)
        handler = meta.cast_lookup.get(key)
        if handler is not None and value is not None:
            value = handler(value)
        elif key in meta.datetime_storage and value is not None:
            value = _cast_datetime(value)
        self._attributes[key] = value

    def getAttribute(self, key: str, default: Any = None) -> Any:
        """
        Return a single attribute value through its accessor.

        A declared ``get<Name>Attribute`` accessor receives the stored
        value (``None`` for computed attributes with no column) and its
        return value is what the caller sees.

        Parameters
        ----------
        key : str
            Attribute name.
        default : typing.Any, optional
            Value returned when the attribute is absent.

        Returns
        -------
        typing.Any
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
            key: getattr(self, accessors[key])(value) if key in accessors else value
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

    def toJson(self, **kwargs: Any) -> str:
        """
        Serialize the visible attributes into a JSON string.

        Parameters
        ----------
        **kwargs : typing.Any
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
        return {key: self._attributes[key] for key in keys if key in self._attributes}

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
            key: value for key, value in self._attributes.items() if key not in excluded
        }
