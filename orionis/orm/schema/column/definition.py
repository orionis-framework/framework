# Resolve public annotations at runtime and accept arbitrary column defaults.
# ruff: noqa: ANN401, TC001, TC003
"""Framework-agnostic description of a database column."""

from __future__ import annotations
import operator
from collections.abc import Callable
from dataclasses import fields
from typing import TYPE_CHECKING, Any, Self
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.constraints.foreign_reference import ForeignReference
from orionis.orm.schema.types.column_type import ColumnType

if TYPE_CHECKING:
    from orionis.orm.model import Model

# Sentinel used to distinguish "no default" from a legitimate ``None`` default.
_NO_DEFAULT: object = object()
"""Sentinel used to distinguish "no default" from a legitimate ``None`` default."""

# Field names copied from ColumnOptions onto every ColumnDefinition instance.
_OPTION_FIELDS: tuple[str, ...] = tuple(field.name for field in fields(ColumnOptions))
"""Field names copied from ColumnOptions onto every ColumnDefinition instance."""

# Read every declared column option in declaration order.
_OPTION_GETTER: Callable[[ColumnOptions], tuple[Any, ...]] = operator.attrgetter(
    *_OPTION_FIELDS,
)
"""Read every declared column option in declaration order."""

# Store the values used by columns with no type-specific options.
_DEFAULT_OPTION_VALUES: tuple[Any, ...] = _OPTION_GETTER(ColumnOptions())
"""Store the values used by columns with no type-specific options."""


class ColumnDefinition[TValue = Any]:
    """
    Framework-agnostic description of a database column.

    Column types such as :class:`orionis.orm.schema.types.Integer` or
    :class:`orionis.orm.schema.types.String` subclass this definition and
    expose a fluent API to declare constraints. The definition never touches
    the underlying SQL engine; the database compiler translates it later.

    On a model instance a declared column reads as its Python value, or
    None before it has a value. If a cast or accessor changes that type,
    specify the result on the declaration, for example ``String[Decimal]()``
    for a string column exposed as a Decimal.
    """

    __slots__ = (
        "as_decimal",
        "as_tuple",
        "as_uuid",
        "collation",
        "column_type",
        "comment_text",
        "comparator",
        "constraint_name",
        "create_constraint",
        "day_precision",
        "decimal_return_scale",
        "default_value",
        "dimensions",
        "enum_name",
        "enum_values",
        "foreign_ref",
        "has_index",
        "impl",
        "is_auto_increment",
        "is_nullable",
        "is_primary",
        "is_unique",
        "item_type",
        "length",
        "name",
        "native",
        "native_enum",
        "native_uuid",
        "none_as_null",
        "pickler",
        "precision",
        "protocol",
        "scale",
        "second_precision",
        "timezone",
        "validate_strings",
        "zero_indexes",
    )
    """Declare the instance attribute slots reserved by this class."""

    if TYPE_CHECKING:
        # ModelMeta removes declarations. Model attributes expose the stored
        # value, or None for a declared column that has not been populated.
        def __get__(self, instance: Model, owner: type[Model]) -> TValue | None:
            """Read the model attribute through its configured accessor or cast.

            Returns
            -------
            ``TValue`` or None
                Stored or transformed value, or None when unset.
            """
            ...

        def __set__(self, instance: Model, value: object) -> None:
            """Accept input for the model's configured mutator and cast.

            Returns
            -------
            None
                Assignment stores the processed value on the model.
            """

    def __init__(
        self,
        column_type: ColumnType,
        options: ColumnOptions | None = None,
    ) -> None:
        """
        Initialize the column definition with its type metadata.

        Parameters
        ----------
        column_type : orionis.orm.schema.types.ColumnType
            Logical column type used by the SQL compiler.
        options : orionis.orm.schema.column.ColumnOptions or None, optional
            Type-specific knobs mirroring the SQLAlchemy constructor
            keywords of the concrete subclass. Defaults to every
            :class:`orionis.orm.schema.column.ColumnOptions` field at its own default
            value.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Attribute name is attached later by the model metaclass.
        self.name: str = ""
        """Attribute name is attached later by the model metaclass."""
        self.column_type = column_type
        """Logical column type used by the SQL compiler."""
        values = _DEFAULT_OPTION_VALUES if options is None else _OPTION_GETTER(options)
        for field_name, value in zip(
            _OPTION_FIELDS,
            values,
            strict=True,
        ):
            setattr(self, field_name, value)
        self.is_primary: bool = False
        """Is primary flag used by ``ColumnDefinition``."""
        self.is_nullable: bool = False
        """Is nullable flag used by ``ColumnDefinition``."""
        self.is_unique: bool = False
        """Is unique flag used by ``ColumnDefinition``."""
        self.has_index: bool = False
        """Has index flag used by ``ColumnDefinition``."""
        self.is_auto_increment: bool = False
        """Is auto increment flag used by ``ColumnDefinition``."""
        self.default_value: Any = _NO_DEFAULT
        """Default value supplied through ``_NO_DEFAULT``."""
        self.foreign_ref: ForeignReference | None = None
        """Foreign-key target referenced by this column."""
        self.comment_text: str | None = None
        """Comment attached to the column definition."""

    # ── Fluent constraints ──────────────────────────────────────────────────

    def primary(self) -> Self:
        """
        Mark the column as the primary key of the table.

        Returns
        -------
        orionis.orm.schema.column.ColumnDefinition
            The same definition, enabling fluent chaining.
        """
        self.is_primary = True
        return self

    def nullable(self) -> Self:
        """
        Allow the column to store ``NULL`` values.

        Returns
        -------
        orionis.orm.schema.column.ColumnDefinition
            The same definition, enabling fluent chaining.
        """
        self.is_nullable = True
        return self

    def default(self, value: Any) -> Self:
        """
        Assign a default value applied when no value is provided on insert.

        Parameters
        ----------
        value : typing.Any
            Static value, or a zero-argument callable evaluated per insert.

        Returns
        -------
        orionis.orm.schema.column.ColumnDefinition
            The same definition, enabling fluent chaining.
        """
        self.default_value = value
        return self

    def unique(self) -> Self:
        """
        Add a unique constraint to the column.

        Returns
        -------
        orionis.orm.schema.column.ColumnDefinition
            The same definition, enabling fluent chaining.
        """
        self.is_unique = True
        return self

    def index(self) -> Self:
        """
        Create a non-unique index on the column.

        Returns
        -------
        orionis.orm.schema.column.ColumnDefinition
            The same definition, enabling fluent chaining.
        """
        self.has_index = True
        return self

    def foreign(self, reference: str) -> Self:
        """
        Declare a foreign key pointing at another table column.

        Parameters
        ----------
        reference : str
            Qualified reference in the form ``"table.column"``.

        Returns
        -------
        orionis.orm.schema.column.ColumnDefinition
            The same definition, enabling fluent chaining.

        Raises
        ------
        ValueError
            If the reference is not a valid ``"table.column"`` string.
        """
        self.foreign_ref = ForeignReference.parse(reference)
        return self

    def autoIncrement(self) -> Self:
        """
        Mark the column as auto-incrementing.

        Returns
        -------
        orionis.orm.schema.column.ColumnDefinition
            The same definition, enabling fluent chaining.
        """
        self.is_auto_increment = True
        return self

    def comment(self, text: str) -> Self:
        """
        Attach a descriptive comment rendered alongside the column DDL.

        Parameters
        ----------
        text : str
            Comment text stored by the database engine.

        Returns
        -------
        orionis.orm.schema.column.ColumnDefinition
            The same definition, enabling fluent chaining.
        """
        self.comment_text = str(text).strip()
        return self

    # ── Introspection helpers ───────────────────────────────────────────────

    def hasDefault(self) -> bool:
        """
        Report whether a default value has been assigned.

        Returns
        -------
        bool
            ``True`` when :meth:`default` was called with any value.
        """
        return self.default_value is not _NO_DEFAULT

    def __repr__(self) -> str:
        """
        Return a concise developer representation of the column.

        Returns
        -------
        str
            Representation including name and logical type.
        """
        return f"<{type(self).__name__} name={self.name!r} type={self.column_type!s}>"
