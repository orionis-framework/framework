# ruff: noqa: PYI021
# Document every declared factory, including its typed fluent interface.
"""Describe the complete typed fluent blueprint interface."""

from orionis.database.schema.comment import Comment
from orionis.database.schema.foreign import ForeignKey
from orionis.database.schema.index import Index
from orionis.database.schema.primary import PrimaryKey
from orionis.database.schema.unique import Unique
from orionis.orm.schema.column import ColumnDefinition
from orionis.orm.schema.types import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Double,
    Enum,
    Float,
    Integer,
    Interval,
    LargeBinary,
    MatchType,
    Numeric,
    NumericCommon,
    PickleType,
    SchemaType,
    SmallInteger,
    String,
    StrictArray,
    StrictBigInt,
    StrictBinary,
    StrictBlob,
    StrictChar,
    StrictClob,
    StrictDecimal,
    StrictDoublePrecision,
    StrictInt,
    StrictJson,
    StrictNChar,
    StrictNVarChar,
    StrictReal,
    StrictSmallInt,
    StrictTimestamp,
    StrictVarBinary,
    StrictVarChar,
    Text,
    Time,
    Unicode,
    UnicodeText,
    Uuid,
)

class Blueprint:
    """Collect column factories and table constraints in declaration order."""

    def id(self, name: str = "id") -> BigInteger:
        """
        Build a BIGINT primary key column definition.

        Parameters
        ----------
        name : str, optional
            Name assigned to the column, defaults to ``"id"``.

        Returns
        -------
        orionis.orm.schema.types.BigInteger
            Column definition ready for schema declarations.
        """

    def bigInteger(self, name: str) -> BigInteger:
        """
        Build a BIGINT column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        orionis.orm.schema.types.BigInteger
            Column definition ready for schema declarations.
        """

    def boolean(
        self,
        name: str,
        *,
        create_constraint: bool = False,
        constraint_name: str | None = None,
    ) -> Boolean:
        """
        Build a boolean column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        create_constraint : bool, optional
            When the boolean is emulated as int/smallint, also create a
            CHECK constraint ensuring 1 or 0 as a value.
        constraint_name : str or None, optional
            Name of the CHECK constraint, when generated.

        Returns
        -------
        orionis.orm.schema.types.Boolean
            Column definition ready for schema declarations.
        """

    def date(self, name: str) -> Date:
        """
        Build a DATE column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        orionis.orm.schema.types.Date
            Column definition ready for schema declarations.
        """

    def dateTime(self, name: str, *, timezone: bool = False) -> DateTime:
        """
        Build a DATETIME column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        timezone : bool, optional
            Whether the datetime type should enable timezone support, if
            available on the base date/time-holding type.

        Returns
        -------
        orionis.orm.schema.types.DateTime
            Column definition ready for schema declarations.
        """

    def double(
        self,
        name: str,
        precision: int | None = None,
        *,
        asdecimal: bool = False,
        decimal_return_scale: int | None = None,
    ) -> Double:
        """
        Build a DOUBLE column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        precision : int or None, optional
            Numeric precision for use in DDL ``CREATE TABLE``.
        asdecimal : bool, optional
            Whether values are coerced to ``decimal.Decimal``.
        decimal_return_scale : int or None, optional
            Default scale used when converting floats to decimals.

        Returns
        -------
        orionis.orm.schema.types.Double
            Column definition ready for schema declarations.
        """

    def enum(
        self,
        name: str,
        *enums: str,
        constraint_name: str | None = None,
        create_constraint: bool = False,
        native_enum: bool = True,
        length: int | None = None,
        validate_strings: bool = False,
    ) -> Enum:
        """
        Build a string-backed enumeration column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        *enums : str
            Allowed string values, at least one is required.
        constraint_name : str or None, optional
            Name of the enumerated database type.
        create_constraint : bool, optional
            When emulating a non-native enum, also build a CHECK
            constraint against the allowed values.
        native_enum : bool, optional
            Whether to use the backend's native ``ENUM`` type.
        length : int or None, optional
            Custom ``VARCHAR`` length for non-native enumerations.
        validate_strings : bool, optional
            Whether to validate string literals against allowed values.

        Returns
        -------
        orionis.orm.schema.types.Enum
            Column definition ready for schema declarations.

        Raises
        ------
        ValueError
            If no values are provided or any value is not a string.
        """

    def float(
        self,
        name: str,
        precision: int | None = None,
        *,
        asdecimal: bool = False,
        decimal_return_scale: int | None = None,
    ) -> Float:
        """
        Build a FLOAT column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        precision : int or None, optional
            Numeric precision for use in DDL ``CREATE TABLE``.
        asdecimal : bool, optional
            Whether values are coerced to ``decimal.Decimal``.
        decimal_return_scale : int or None, optional
            Default scale used when converting floats to decimals.

        Returns
        -------
        orionis.orm.schema.types.Float
            Column definition ready for schema declarations.
        """

    def integer(self, name: str) -> Integer:
        """
        Build an INTEGER column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        orionis.orm.schema.types.Integer
            Column definition ready for schema declarations.
        """

    def interval(
        self,
        name: str,
        *,
        native: bool = True,
        second_precision: int | None = None,
        day_precision: int | None = None,
    ) -> Interval:
        """
        Build an INTERVAL column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        native : bool, optional
            Whether to use the backend's native ``INTERVAL`` type, when
            supported (PostgreSQL, Oracle Database).
        second_precision : int or None, optional
            Fractional seconds precision for native interval types.
        day_precision : int or None, optional
            Day precision for native interval types.

        Returns
        -------
        orionis.orm.schema.types.Interval
            Column definition ready for schema declarations.
        """

    def largeBinary(self, name: str, length: int | None = None) -> LargeBinary:
        """
        Build a large binary column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        length : int or None, optional
            Length for the column for use in DDL statements, for those
            binary types that accept a length.

        Returns
        -------
        orionis.orm.schema.types.LargeBinary
            Column definition ready for schema declarations.

        Raises
        ------
        ValueError
            If the length is not a positive integer or None.
        """

    def matchType(self, name: str) -> MatchType:
        """
        Build a MATCH-operator return-type column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        orionis.orm.schema.types.MatchType
            Column definition ready for schema declarations.
        """

    def numeric(
        self,
        name: str,
        precision: int | None = None,
        scale: int | None = None,
        decimal_return_scale: int | None = None,
        *,
        asdecimal: bool = True,
    ) -> Numeric:
        """
        Build a NUMERIC column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        precision : int or None, optional
            Numeric precision for use in DDL ``CREATE TABLE``.
        scale : int or None, optional
            Numeric scale for use in DDL ``CREATE TABLE``.
        decimal_return_scale : int or None, optional
            Default scale used when converting floats to decimals.
        asdecimal : bool, optional
            Whether values are returned as ``decimal.Decimal`` objects.

        Returns
        -------
        orionis.orm.schema.types.Numeric
            Column definition ready for schema declarations.

        Raises
        ------
        ValueError
            If precision or scale are negative or inconsistent.
        """

    def numericCommon(self, name: str) -> NumericCommon:
        """
        Build a numeric-common placeholder column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        orionis.orm.schema.types.NumericCommon
            Column definition ready for schema declarations.
        """

    def pickleType(
        self,
        name: str,
        protocol: int = 5,
        pickler: object | None = None,
        impl: object | None = None,
    ) -> PickleType:
        """
        Build a pickle-backed column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        protocol : int, optional
            Pickle protocol, defaults to ``pickle.HIGHEST_PROTOCOL``.
        pickler : object or None, optional
            Object exposing pickle-compatible ``dumps``/``loads`` methods.
        impl : object or None, optional
            Binary-storing type used in place of the default ``LargeBinary``.

        Returns
        -------
        orionis.orm.schema.types.PickleType
            Column definition ready for schema declarations.
        """

    def schemaType(
        self,
        name: str,
        schema_name: str | None = None,
    ) -> SchemaType:
        """
        Build a schema-level placeholder column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        schema_name : str or None, optional
            Name of the associated schema-level construct.

        Returns
        -------
        orionis.orm.schema.types.SchemaType
            Column definition ready for schema declarations.
        """

    def smallInteger(self, name: str) -> SmallInteger:
        """
        Build a SMALLINT column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        orionis.orm.schema.types.SmallInteger
            Column definition ready for schema declarations.
        """

    def string(
        self,
        name: str,
        length: int | None = 255,
        collation: str | None = None,
    ) -> String:
        """
        Build a VARCHAR column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        length : int or None, optional
            Length for the column for use in DDL and CAST expressions.
        collation : str or None, optional
            Column-level collation for use in DDL and CAST expressions.

        Returns
        -------
        orionis.orm.schema.types.String
            Column definition ready for schema declarations.

        Raises
        ------
        ValueError
            If the length is not a positive integer or None.
        """

    def text(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> Text:
        """
        Build a TEXT/CLOB column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        length : int or None, optional
            Length for the column for use in DDL and CAST expressions.
        collation : str or None, optional
            Column-level collation for use in DDL and CAST expressions.

        Returns
        -------
        orionis.orm.schema.types.Text
            Column definition ready for schema declarations.
        """

    def time(self, name: str) -> Time:
        """
        Build a TIME column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        orionis.orm.schema.types.Time
            Column definition ready for schema declarations.
        """

    def unicode(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> Unicode:
        """
        Build an NVARCHAR column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        length : int or None, optional
            Length for the column for use in DDL and CAST expressions.
        collation : str or None, optional
            Column-level collation for use in DDL and CAST expressions.

        Returns
        -------
        orionis.orm.schema.types.Unicode
            Column definition ready for schema declarations.
        """

    def unicodeText(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> UnicodeText:
        """
        Build an NCLOB/NTEXT column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        length : int or None, optional
            Length for the column for use in DDL and CAST expressions.
        collation : str or None, optional
            Column-level collation for use in DDL and CAST expressions.

        Returns
        -------
        orionis.orm.schema.types.UnicodeText
            Column definition ready for schema declarations.
        """

    def uuid(
        self,
        name: str,
        *,
        as_uuid: bool = True,
        native_uuid: bool = True,
    ) -> Uuid:
        """
        Build a UUID column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        as_uuid : bool, optional
            Whether values are interpreted as Python ``uuid.UUID`` objects.
        native_uuid : bool, optional
            Whether to use the backend's native UUID-storing type.

        Returns
        -------
        orionis.orm.schema.types.Uuid
            Column definition ready for schema declarations.
        """

    def strictArray(
        self,
        name: str,
        item_type: ColumnDefinition,
        *,
        as_tuple: bool = False,
        dimensions: int | None = None,
        zero_indexes: bool = False,
    ) -> StrictArray:
        """
        Build a SQL ARRAY column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        item_type : orionis.orm.schema.column.ColumnDefinition
            Column definition of the array elements.
        as_tuple : bool, optional
            Whether results are converted to tuples instead of lists.
        dimensions : int or None, optional
            Fixed number of dimensions, when not ``None``.
        zero_indexes : bool, optional
            Whether to convert between zero- and one-based indexes.

        Returns
        -------
        orionis.orm.schema.types.StrictArray
            Column definition ready for schema declarations.
        """

    def strictBigInt(self, name: str) -> StrictBigInt:
        """
        Build a SQL BIGINT column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        orionis.orm.schema.types.StrictBigInt
            Column definition ready for schema declarations.
        """

    def strictBinary(
        self,
        name: str,
        length: int | None = None,
    ) -> StrictBinary:
        """
        Build a SQL BINARY column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        length : int or None, optional
            Length for the column for use in DDL statements.

        Returns
        -------
        orionis.orm.schema.types.StrictBinary
            Column definition ready for schema declarations.
        """

    def strictBlob(self, name: str, length: int | None = None) -> StrictBlob:
        """
        Build a SQL BLOB column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        length : int or None, optional
            Length for the column for use in DDL statements.

        Returns
        -------
        orionis.orm.schema.types.StrictBlob
            Column definition ready for schema declarations.
        """

    def strictChar(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> StrictChar:
        """
        Build a SQL CHAR column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        length : int or None, optional
            Length for the column for use in DDL and CAST expressions.
        collation : str or None, optional
            Column-level collation for use in DDL and CAST expressions.

        Returns
        -------
        orionis.orm.schema.types.StrictChar
            Column definition ready for schema declarations.
        """

    def strictClob(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> StrictClob:
        """
        Build an Oracle/Informix CLOB column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        length : int or None, optional
            Length for the column for use in DDL and CAST expressions.
        collation : str or None, optional
            Column-level collation for use in DDL and CAST expressions.

        Returns
        -------
        orionis.orm.schema.types.StrictClob
            Column definition ready for schema declarations.
        """

    def strictDecimal(
        self,
        name: str,
        precision: int | None = 10,
        scale: int | None = 2,
        decimal_return_scale: int | None = None,
        *,
        asdecimal: bool = True,
    ) -> StrictDecimal:
        """
        Build a SQL DECIMAL column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        precision : int or None, optional
            Numeric precision for use in DDL ``CREATE TABLE``.
        scale : int or None, optional
            Numeric scale for use in DDL ``CREATE TABLE``.
        decimal_return_scale : int or None, optional
            Default scale used when converting floats to decimals.
        asdecimal : bool, optional
            Whether values are returned as ``decimal.Decimal`` objects.

        Returns
        -------
        orionis.orm.schema.types.StrictDecimal
            Column definition ready for schema declarations.

        Raises
        ------
        ValueError
            If precision or scale are negative or inconsistent.
        """

    def strictDoublePrecision(
        self,
        name: str,
        precision: int | None = None,
        *,
        asdecimal: bool = False,
        decimal_return_scale: int | None = None,
    ) -> StrictDoublePrecision:
        """
        Build a SQL DOUBLE PRECISION column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        precision : int or None, optional
            Numeric precision for use in DDL ``CREATE TABLE``.
        asdecimal : bool, optional
            Whether values are coerced to ``decimal.Decimal``.
        decimal_return_scale : int or None, optional
            Default scale used when converting floats to decimals.

        Returns
        -------
        orionis.orm.schema.types.StrictDoublePrecision
            Column definition ready for schema declarations.
        """

    def strictInt(self, name: str) -> StrictInt:
        """
        Build a SQL INT column definition, alias of ``INTEGER``.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        orionis.orm.schema.types.StrictInt
            Column definition ready for schema declarations.
        """

    def strictJson(
        self,
        name: str,
        *,
        none_as_null: bool = False,
    ) -> StrictJson:
        """
        Build a SQL JSON column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        none_as_null : bool, optional
            When ``True``, persist Python ``None`` as SQL ``NULL`` instead
            of the JSON encoding of ``null``.

        Returns
        -------
        orionis.orm.schema.types.StrictJson
            Column definition ready for schema declarations.
        """

    def strictNChar(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> StrictNChar:
        """
        Build a SQL NCHAR column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        length : int or None, optional
            Length for the column for use in DDL and CAST expressions.
        collation : str or None, optional
            Column-level collation for use in DDL and CAST expressions.

        Returns
        -------
        orionis.orm.schema.types.StrictNChar
            Column definition ready for schema declarations.
        """

    def strictNVarChar(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> StrictNVarChar:
        """
        Build a SQL NVARCHAR column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        length : int or None, optional
            Length for the column for use in DDL and CAST expressions.
        collation : str or None, optional
            Column-level collation for use in DDL and CAST expressions.

        Returns
        -------
        orionis.orm.schema.types.StrictNVarChar
            Column definition ready for schema declarations.
        """
    def strictReal(
        self,
        name: str,
        precision: int | None = None,
        *,
        asdecimal: bool = False,
        decimal_return_scale: int | None = None,
    ) -> StrictReal:
        """
        Build a SQL REAL column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        precision : int or None, optional
            Numeric precision for use in DDL ``CREATE TABLE``.
        asdecimal : bool, optional
            Whether values are coerced to ``decimal.Decimal``.
        decimal_return_scale : int or None, optional
            Default scale used when converting floats to decimals.

        Returns
        -------
        orionis.orm.schema.types.StrictReal
            Column definition ready for schema declarations.
        """

    def strictSmallInt(self, name: str) -> StrictSmallInt:
        """
        Build a SQL SMALLINT column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        orionis.orm.schema.types.StrictSmallInt
            Column definition ready for schema declarations.
        """

    def strictTimestamp(
        self,
        name: str,
        *,
        timezone: bool = False,
    ) -> StrictTimestamp:
        """
        Build a SQL TIMESTAMP column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        timezone : bool, optional
            Whether the TIMESTAMP type should enable timezone support,
            if available on the target database.

        Returns
        -------
        orionis.orm.schema.types.StrictTimestamp
            Column definition ready for schema declarations.
        """

    def strictVarBinary(
        self,
        name: str,
        length: int | None = None,
    ) -> StrictVarBinary:
        """
        Build a SQL VARBINARY column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        length : int or None, optional
            Length for the column for use in DDL statements.

        Returns
        -------
        orionis.orm.schema.types.StrictVarBinary
            Column definition ready for schema declarations.
        """

    def strictVarChar(
        self,
        name: str,
        length: int | None = 255,
        collation: str | None = None,
    ) -> StrictVarChar:
        """
        Build a SQL VARCHAR column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.
        length : int or None, optional
            Length for the column for use in DDL and CAST expressions.
        collation : str or None, optional
            Column-level collation for use in DDL and CAST expressions.

        Returns
        -------
        orionis.orm.schema.types.StrictVarChar
            Column definition ready for schema declarations.
        """

    def timestamps(self, *, timezone: bool = False) -> None:
        """
        Add nullable ``created_at`` and ``updated_at`` columns.

        Parameters
        ----------
        timezone : bool, optional
            Whether the timestamp columns should be timezone-aware.

        Returns
        -------
        None
            No return value.
        """

    def comment(self, text: str) -> Comment:
        """
        Attach a table-level comment.

        Parameters
        ----------
        text : str
            The comment text content.

        Returns
        -------
        orionis.database.schema.Comment
            The constraint recorded on this blueprint.
        """

    def foreignKey(
        self,
        column: str,
        ref_table: str,
        ref_column: str,
        name: str | None = None,
    ) -> ForeignKey:
        """
        Declare a foreign key constraint on this table.

        Parameters
        ----------
        column : str
            The local column name.
        ref_table : str
            The referenced table name.
        ref_column : str
            The referenced column name.
        name : str | None, optional
            The constraint name. Defaults to None.

        Returns
        -------
        orionis.database.schema.ForeignKey
            The constraint recorded on this blueprint.
        """

    def index(
        self,
        *columns: str,
        name: str | None = None,
        unique: bool = False,
    ) -> Index:
        """
        Declare an index over one or more columns.

        Parameters
        ----------
        columns : str
            Column names to include in the index.
        name : str | None, optional
            Name of the index. If not provided, a default name will be
            generated.
        unique : bool, optional
            Whether the index should enforce uniqueness. Default is False.

        Returns
        -------
        orionis.database.schema.Index
            The constraint recorded on this blueprint.
        """

    def primaryKey(self, *columns: str) -> PrimaryKey:
        """
        Declare a (composite) primary key over one or more columns.

        Parameters
        ----------
        columns : str
            Column names that compose the primary key.

        Returns
        -------
        orionis.database.schema.PrimaryKey
            The constraint recorded on this blueprint.
        """

    def unique(self, *columns: str, name: str | None = None) -> Unique:
        """
        Declare a unique constraint over one or more columns.

        Parameters
        ----------
        columns : str
            Column names to apply the unique constraint to.
        name : str | None, optional
            Name of the unique constraint. If not provided, a default
            name will be generated.

        Returns
        -------
        orionis.database.schema.Unique
            The constraint recorded on this blueprint.
        """

    def columns(self) -> tuple[ColumnDefinition, ...]:
        """Return the columns collected in declaration order.

        Returns
        -------
        tuple of ColumnDefinition
            Snapshot of the collected columns.
        """

    def definitions(
        self,
    ) -> tuple[
        ColumnDefinition | Comment | ForeignKey | Index | PrimaryKey | Unique,
        ...,
    ]:
        """Return the collected columns followed by table constraints.

        Returns
        -------
        tuple
            Snapshot of the complete declaration.
        """
