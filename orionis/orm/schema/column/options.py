from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from orionis.orm.schema.column.definition import ColumnDefinition

@dataclass(frozen=True, slots=True)
class ColumnOptions:
    """
    Secondary, type-specific knobs mirroring SQLAlchemy constructor args.

    A single options object keeps :class:`ColumnDefinition` constructible
    with a handful of parameters while still exposing every keyword that
    the equivalent SQLAlchemy Core type accepts, one attribute per keyword.

    Attributes
    ----------
    length : int or None
        Maximum length for string-like or binary columns.
    precision : int or None
        Total digits for numeric/decimal columns.
    scale : int or None
        Decimal digits for numeric/decimal columns.
    decimal_return_scale : int or None
        Default scale applied when converting floats to decimals.
    as_decimal : bool
        Whether numeric values are returned as ``Decimal``.
    enum_values : tuple of str
        Allowed values for enum columns.
    enum_name : str or None
        Name of the enumerated database type, when applicable.
    native_enum : bool
        Whether to use the backend's native ``ENUM`` type.
    validate_strings : bool
        Whether to validate string values against enum members.
    create_constraint : bool
        Whether to add a CHECK constraint for non-native enum/boolean.
    constraint_name : str or None
        Explicit name for the generated CHECK constraint.
    timezone : bool
        Whether the datetime column is timezone-aware.
    collation : str or None
        Column-level collation for string columns.
    as_uuid : bool
        Whether UUID values are interpreted as ``uuid.UUID`` objects.
    native_uuid : bool
        Whether to use the backend's native UUID-storing type.
    item_type : ColumnDefinition or None
        Element type declaration for array columns.
    dimensions : int or None
        Fixed number of dimensions for array columns.
    as_tuple : bool
        Whether array results are converted to tuples.
    zero_indexes : bool
        Whether array indexes convert between zero- and one-based
        conventions.
    none_as_null : bool
        Whether ``None`` persists as SQL ``NULL`` in JSON columns.
    native : bool
        Whether to use the backend's native ``INTERVAL`` type.
    second_precision : int or None
        Fractional seconds precision for native interval columns.
    day_precision : int or None
        Day precision for native interval columns.
    protocol : int
        Pickle protocol used by pickle-backed columns.
    pickler : object or None
        Object exposing ``dumps``/``loads``, defaults to ``pickle``.
    comparator : Callable or None
        Predicate used to compare pickled values for equality.
    impl : object or None
        Binary-storing type used in place of the default.
    """

    length: int | None = None
    precision: int | None = None
    scale: int | None = None
    decimal_return_scale: int | None = None
    as_decimal: bool = True
    enum_values: tuple[str, ...] = ()
    enum_name: str | None = None
    native_enum: bool = True
    validate_strings: bool = False
    create_constraint: bool = False
    constraint_name: str | None = None
    timezone: bool = False
    collation: str | None = None
    as_uuid: bool = True
    native_uuid: bool = True
    item_type: ColumnDefinition | None = None
    dimensions: int | None = None
    as_tuple: bool = False
    zero_indexes: bool = False
    none_as_null: bool = False
    native: bool = True
    second_precision: int | None = None
    day_precision: int | None = None
    protocol: int = 5
    pickler: object | None = None
    comparator: Callable[[object, object], bool] | None = None
    impl: object | None = None
