from __future__ import annotations
import operator
from dataclasses import fields
from typing import TYPE_CHECKING, Any
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.constraints.foreign_reference import ForeignReference

if TYPE_CHECKING:
    from collections.abc import Callable
    from orionis.orm.schema.types.column_type import ColumnType

# Sentinel used to distinguish "no default" from a legitimate ``None`` default.
_NO_DEFAULT: object = object()

# Field names copied from ColumnOptions onto every ColumnDefinition instance.
_OPTION_FIELDS: tuple[str, ...] = tuple(field.name for field in fields(ColumnOptions))

# Read every declared column option in declaration order.
_OPTION_GETTER: Callable[[ColumnOptions], tuple[Any, ...]] = operator.attrgetter(
    *_OPTION_FIELDS,
)

# Store the values used by columns with no type-specific options.
_DEFAULT_OPTION_VALUES: tuple[Any, ...] = _OPTION_GETTER(ColumnOptions())

class ColumnDefinition:
    """
    Framework-agnostic description of a database column.

    Column types such as :class:`~orionis.orm.schema.types.Integer` or
    :class:`~orionis.orm.schema.types.String` subclass this definition and
    expose a fluent API to declare constraints. The definition never touches
    the underlying SQL engine; the database compiler translates it later.
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

    def __init__(
        self,
        column_type: ColumnType,
        options: ColumnOptions | None = None,
    ) -> None:
        """
        Initialize the column definition with its type metadata.

        Parameters
        ----------
        column_type : ColumnType
            Logical column type used by the SQL compiler.
        options : ColumnOptions or None, optional
            Type-specific knobs mirroring the SQLAlchemy constructor
            keywords of the concrete subclass. Defaults to every
            :class:`ColumnOptions` field at its own default value.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Attribute name is attached later by the model metaclass.
        self.name: str = ""
        self.column_type = column_type
        values = (
            _DEFAULT_OPTION_VALUES if options is None else _OPTION_GETTER(options)
        )
        for field_name, value in zip(
            _OPTION_FIELDS, values, strict=True,
        ):
            setattr(self, field_name, value)
        self.is_primary: bool = False
        self.is_nullable: bool = False
        self.is_unique: bool = False
        self.has_index: bool = False
        self.is_auto_increment: bool = False
        self.default_value: Any = _NO_DEFAULT
        self.foreign_ref: ForeignReference | None = None
        self.comment_text: str | None = None

    # ── Fluent constraints ──────────────────────────────────────────────────

    def primary(self) -> ColumnDefinition:
        """
        Mark the column as the primary key of the table.

        Returns
        -------
        ColumnDefinition
            The same definition, enabling fluent chaining.
        """
        self.is_primary = True
        return self

    def nullable(self) -> ColumnDefinition:
        """
        Allow the column to store ``NULL`` values.

        Returns
        -------
        ColumnDefinition
            The same definition, enabling fluent chaining.
        """
        self.is_nullable = True
        return self

    def default(self, value: Any) -> ColumnDefinition:  # noqa: ANN401
        """
        Assign a default value applied when no value is provided on insert.

        Parameters
        ----------
        value : Any
            Static value, or a zero-argument callable evaluated per insert.

        Returns
        -------
        ColumnDefinition
            The same definition, enabling fluent chaining.
        """
        self.default_value = value
        return self

    def unique(self) -> ColumnDefinition:
        """
        Add a unique constraint to the column.

        Returns
        -------
        ColumnDefinition
            The same definition, enabling fluent chaining.
        """
        self.is_unique = True
        return self

    def index(self) -> ColumnDefinition:
        """
        Create a non-unique index on the column.

        Returns
        -------
        ColumnDefinition
            The same definition, enabling fluent chaining.
        """
        self.has_index = True
        return self

    def foreign(self, reference: str) -> ColumnDefinition:
        """
        Declare a foreign key pointing at another table column.

        Parameters
        ----------
        reference : str
            Qualified reference in the form ``"table.column"``.

        Returns
        -------
        ColumnDefinition
            The same definition, enabling fluent chaining.

        Raises
        ------
        ValueError
            If the reference is not a valid ``"table.column"`` string.
        """
        self.foreign_ref = ForeignReference.parse(reference)
        return self

    def autoIncrement(self) -> ColumnDefinition:
        """
        Mark the column as auto-incrementing.

        Returns
        -------
        ColumnDefinition
            The same definition, enabling fluent chaining.
        """
        self.is_auto_increment = True
        return self

    def comment(self, text: str) -> ColumnDefinition:
        """
        Attach a descriptive comment rendered alongside the column DDL.

        Parameters
        ----------
        text : str
            Comment text stored by the database engine.

        Returns
        -------
        ColumnDefinition
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
        return (
            f"<{type(self).__name__} name={self.name!r} "
            f"type={self.column_type!s}>"
        )
