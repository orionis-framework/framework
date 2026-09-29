from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.orm.schema.types import (
    BigInteger, Boolean, Date, DateTime, Double, Enum, Float, Integer,
    Interval, LargeBinary, MatchType, Numeric, NumericCommon, PickleType,
    SchemaType, SmallInteger, String, Text, Time, Unicode, UnicodeText, Uuid,
    StrictArray, StrictBigInt, StrictBinary, StrictBlob, StrictChar, StrictClob,
    StrictDecimal, StrictDoublePrecision, StrictInt, StrictJson, StrictNChar,
    StrictNVarChar, StrictReal, StrictSmallInt, StrictTimestamp, StrictVarBinary,
    StrictVarChar,
)

if TYPE_CHECKING:
    from orionis.orm.schema.column import ColumnDefinition

class Column:
    """Create :class:`ColumnDefinition` builders for schema declarations."""

    @staticmethod
    def id(name: str = "id") -> BigInteger:
        """
        Build a BIGINT primary key column definition.

        Parameters
        ----------
        name : str, optional
            Name assigned to the column, defaults to ``"id"``.

        Returns
        -------
        BigInteger
            Column definition ready for schema declarations.
        """
        # BigInteger has no type-specific constructor arguments.
        column = BigInteger().primary().autoIncrement()
        column.name = name
        return column

    @staticmethod
    def bigInteger(name: str) -> BigInteger:
        """
        Build a BIGINT column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        BigInteger
            Column definition ready for schema declarations.
        """
        # BigInteger has no type-specific constructor arguments.
        column = BigInteger()
        column.name = name
        return column

    @staticmethod
    def boolean(
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
        Boolean
            Column definition ready for schema declarations.
        """
        # Forward the CHECK-constraint options to the underlying type.
        column = Boolean(
            create_constraint=create_constraint,
            name=constraint_name,
        )
        column.name = name
        return column

    @staticmethod
    def date(name: str) -> Date:
        """
        Build a DATE column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        Date
            Column definition ready for schema declarations.
        """
        # Date has no type-specific constructor arguments.
        column = Date()
        column.name = name
        return column

    @staticmethod
    def dateTime(name: str, *, timezone: bool = False) -> DateTime:
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
        DateTime
            Column definition ready for schema declarations.
        """
        # Forward timezone support to the underlying type.
        column = DateTime(timezone=timezone)
        column.name = name
        return column

    @staticmethod
    def double(
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
        Double
            Column definition ready for schema declarations.
        """
        # Forward the numeric precision options to the underlying type.
        column = Double(
            precision,
            asdecimal=asdecimal,
            decimal_return_scale=decimal_return_scale,
        )
        column.name = name
        return column

    @staticmethod
    def enum(  # noqa: PLR0913
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
        Enum
            Column definition ready for schema declarations.

        Raises
        ------
        ValueError
            If no values are provided or any value is not a string.
        """
        # Forward the allowed values and enum-specific options.
        column = Enum(
            *enums,
            name=constraint_name,
            create_constraint=create_constraint,
            native_enum=native_enum,
            length=length,
            validate_strings=validate_strings,
        )
        column.name = name
        return column

    @staticmethod
    def float(
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
        Float
            Column definition ready for schema declarations.
        """
        # Forward the numeric precision options to the underlying type.
        column = Float(
            precision,
            asdecimal=asdecimal,
            decimal_return_scale=decimal_return_scale,
        )
        column.name = name
        return column

    @staticmethod
    def integer(name: str) -> Integer:
        """
        Build an INTEGER column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        Integer
            Column definition ready for schema declarations.
        """
        # Integer has no type-specific constructor arguments.
        column = Integer()
        column.name = name
        return column

    @staticmethod
    def interval(
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
        Interval
            Column definition ready for schema declarations.
        """
        # Forward the native interval precision options.
        column = Interval(
            native=native,
            second_precision=second_precision,
            day_precision=day_precision,
        )
        column.name = name
        return column

    @staticmethod
    def largeBinary(name: str, length: int | None = None) -> LargeBinary:
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
        LargeBinary
            Column definition ready for schema declarations.

        Raises
        ------
        ValueError
            If the length is not a positive integer or None.
        """
        # Forward the optional length to the underlying type.
        column = LargeBinary(length)
        column.name = name
        return column

    @staticmethod
    def matchType(name: str) -> MatchType:
        """
        Build a MATCH-operator return-type column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        MatchType
            Column definition ready for schema declarations.
        """
        # MatchType has no type-specific constructor arguments.
        column = MatchType()
        column.name = name
        return column

    @staticmethod
    def numeric(
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
        Numeric
            Column definition ready for schema declarations.

        Raises
        ------
        ValueError
            If precision or scale are negative or inconsistent.
        """
        # Forward the numeric precision and scale options.
        column = Numeric(
            precision,
            scale,
            decimal_return_scale,
            asdecimal=asdecimal,
        )
        column.name = name
        return column

    @staticmethod
    def numericCommon(name: str) -> NumericCommon:
        """
        Build a numeric-common placeholder column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        NumericCommon
            Column definition ready for schema declarations.
        """
        # NumericCommon has no type-specific constructor arguments.
        column = NumericCommon()
        column.name = name
        return column

    @staticmethod
    def pickleType(
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
        PickleType
            Column definition ready for schema declarations.
        """
        # Forward the pickle protocol and implementation options.
        column = PickleType(protocol, pickler, impl)
        column.name = name
        return column

    @staticmethod
    def schemaType(name: str, schema_name: str | None = None) -> SchemaType:
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
        SchemaType
            Column definition ready for schema declarations.
        """
        # Forward the schema-level construct name.
        column = SchemaType(schema_name)
        column.name = name
        return column

    @staticmethod
    def smallInteger(name: str) -> SmallInteger:
        """
        Build a SMALLINT column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        SmallInteger
            Column definition ready for schema declarations.
        """
        # SmallInteger has no type-specific constructor arguments.
        column = SmallInteger()
        column.name = name
        return column

    @staticmethod
    def string(
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
        String
            Column definition ready for schema declarations.

        Raises
        ------
        ValueError
            If the length is not a positive integer or None.
        """
        # Forward the length and collation options.
        column = String(length, collation)
        column.name = name
        return column

    @staticmethod
    def text(
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
        Text
            Column definition ready for schema declarations.
        """
        # Forward the length and collation options.
        column = Text(length, collation)
        column.name = name
        return column

    @staticmethod
    def time(name: str) -> Time:
        """
        Build a TIME column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        Time
            Column definition ready for schema declarations.
        """
        # Time has no type-specific constructor arguments.
        column = Time()
        column.name = name
        return column

    @staticmethod
    def unicode(
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
        Unicode
            Column definition ready for schema declarations.
        """
        # Forward the length and collation options.
        column = Unicode(length, collation)
        column.name = name
        return column

    @staticmethod
    def unicodeText(
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
        UnicodeText
            Column definition ready for schema declarations.
        """
        # Forward the length and collation options.
        column = UnicodeText(length, collation)
        column.name = name
        return column

    @staticmethod
    def uuid(
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
        Uuid
            Column definition ready for schema declarations.
        """
        # Forward the UUID representation options.
        column = Uuid(as_uuid=as_uuid, native_uuid=native_uuid)
        column.name = name
        return column

    @staticmethod
    def strictArray(
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
        item_type : ColumnDefinition
            Column definition of the array elements.
        as_tuple : bool, optional
            Whether results are converted to tuples instead of lists.
        dimensions : int or None, optional
            Fixed number of dimensions, when not ``None``.
        zero_indexes : bool, optional
            Whether to convert between zero- and one-based indexes.

        Returns
        -------
        StrictArray
            Column definition ready for schema declarations.
        """
        # Forward the element type and array-shape options.
        column = StrictArray(
            item_type,
            as_tuple=as_tuple,
            dimensions=dimensions,
            zero_indexes=zero_indexes,
        )
        column.name = name
        return column

    @staticmethod
    def strictBigInt(name: str) -> StrictBigInt:
        """
        Build a SQL BIGINT column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        StrictBigInt
            Column definition ready for schema declarations.
        """
        # StrictBigInt has no type-specific constructor arguments.
        column = StrictBigInt()
        column.name = name
        return column

    @staticmethod
    def strictBinary(name: str, length: int | None = None) -> StrictBinary:
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
        StrictBinary
            Column definition ready for schema declarations.
        """
        # Forward the optional length to the underlying type.
        column = StrictBinary(length)
        column.name = name
        return column

    @staticmethod
    def strictBlob(name: str, length: int | None = None) -> StrictBlob:
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
        StrictBlob
            Column definition ready for schema declarations.
        """
        # Forward the optional length to the underlying type.
        column = StrictBlob(length)
        column.name = name
        return column

    @staticmethod
    def strictChar(
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
        StrictChar
            Column definition ready for schema declarations.
        """
        # Forward the length and collation options.
        column = StrictChar(length, collation)
        column.name = name
        return column

    @staticmethod
    def strictClob(
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
        StrictClob
            Column definition ready for schema declarations.
        """
        # Forward the length and collation options.
        column = StrictClob(length, collation)
        column.name = name
        return column

    @staticmethod
    def strictDecimal(
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
        StrictDecimal
            Column definition ready for schema declarations.

        Raises
        ------
        ValueError
            If precision or scale are negative or inconsistent.
        """
        # Forward the numeric precision and scale options.
        column = StrictDecimal(
            precision,
            scale,
            decimal_return_scale,
            asdecimal=asdecimal,
        )
        column.name = name
        return column

    @staticmethod
    def strictDoublePrecision(
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
        StrictDoublePrecision
            Column definition ready for schema declarations.
        """
        # Forward the numeric precision options to the underlying type.
        column = StrictDoublePrecision(
            precision,
            asdecimal=asdecimal,
            decimal_return_scale=decimal_return_scale,
        )
        column.name = name
        return column

    @staticmethod
    def strictInt(name: str) -> StrictInt:
        """
        Build a SQL INT column definition, alias of ``INTEGER``.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        StrictInt
            Column definition ready for schema declarations.
        """
        # StrictInt has no type-specific constructor arguments.
        column = StrictInt()
        column.name = name
        return column

    @staticmethod
    def strictJson(name: str, *, none_as_null: bool = False) -> StrictJson:
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
        StrictJson
            Column definition ready for schema declarations.
        """
        # Forward the None-handling option to the underlying type.
        column = StrictJson(none_as_null=none_as_null)
        column.name = name
        return column

    @staticmethod
    def strictNChar(
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
        StrictNChar
            Column definition ready for schema declarations.
        """
        # Forward the length and collation options.
        column = StrictNChar(length, collation)
        column.name = name
        return column

    @staticmethod
    def strictNVarChar(
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
        StrictNVarChar
            Column definition ready for schema declarations.
        """
        # Forward the length and collation options.
        column = StrictNVarChar(length, collation)
        column.name = name
        return column

    @staticmethod
    def strictReal(
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
        StrictReal
            Column definition ready for schema declarations.
        """
        # Forward the numeric precision options to the underlying type.
        column = StrictReal(
            precision,
            asdecimal=asdecimal,
            decimal_return_scale=decimal_return_scale,
        )
        column.name = name
        return column

    @staticmethod
    def strictSmallInt(name: str) -> StrictSmallInt:
        """
        Build a SQL SMALLINT column definition.

        Parameters
        ----------
        name : str
            Name assigned to the column.

        Returns
        -------
        StrictSmallInt
            Column definition ready for schema declarations.
        """
        # StrictSmallInt has no type-specific constructor arguments.
        column = StrictSmallInt()
        column.name = name
        return column

    @staticmethod
    def strictTimestamp(name: str, *, timezone: bool = False) -> StrictTimestamp:
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
        StrictTimestamp
            Column definition ready for schema declarations.
        """
        # Forward timezone support to the underlying type.
        column = StrictTimestamp(timezone=timezone)
        column.name = name
        return column

    @staticmethod
    def strictVarBinary(name: str, length: int | None = None) -> StrictVarBinary:
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
        StrictVarBinary
            Column definition ready for schema declarations.
        """
        # Forward the optional length to the underlying type.
        column = StrictVarBinary(length)
        column.name = name
        return column

    @staticmethod
    def strictVarChar(
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
        StrictVarChar
            Column definition ready for schema declarations.
        """
        # Forward the length and collation options.
        column = StrictVarChar(length, collation)
        column.name = name
        return column
