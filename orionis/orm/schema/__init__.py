"""Group the orm schema components and public imports."""

from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.orm.schema.column import ColumnDefinition, ColumnOptions
    from orionis.orm.schema.constraints import (
        CompositeForeignKey,
        ForeignReference,
        TableIndex,
        UniqueConstraint,
    )
    from orionis.orm.schema.table import TableDefinition
    from orionis.orm.schema.types import (
        BigInteger,
        Boolean,
        ColumnType,
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
        String,
        Text,
        Time,
        Unicode,
        UnicodeText,
        Uuid,
    )

__all__ = [
    "BigInteger",
    "Boolean",
    "ColumnDefinition",
    "ColumnOptions",
    "ColumnType",
    "CompositeForeignKey",
    "Date",
    "DateTime",
    "Double",
    "Enum",
    "Float",
    "ForeignReference",
    "Integer",
    "Interval",
    "LargeBinary",
    "MatchType",
    "Numeric",
    "NumericCommon",
    "PickleType",
    "SchemaType",
    "SmallInteger",
    "StrictArray",
    "StrictBigInt",
    "StrictBinary",
    "StrictBlob",
    "StrictChar",
    "StrictClob",
    "StrictDecimal",
    "StrictDoublePrecision",
    "StrictInt",
    "StrictJson",
    "StrictNChar",
    "StrictNVarChar",
    "StrictReal",
    "StrictSmallInt",
    "StrictTimestamp",
    "StrictVarBinary",
    "StrictVarChar",
    "String",
    "TableDefinition",
    "TableIndex",
    "Text",
    "Time",
    "Unicode",
    "UnicodeText",
    "UniqueConstraint",
    "Uuid",
]

_TYPES_MODULE = "orionis.orm.schema.types"
"""Module exporting logical column declarations."""

_CONSTRAINTS_MODULE = "orionis.orm.schema.constraints"
"""Module exporting table and foreign-key constraints."""

_EXPORTS = {
    "BigInteger": (_TYPES_MODULE, "BigInteger"),
    "Boolean": (_TYPES_MODULE, "Boolean"),
    "ColumnDefinition": ("orionis.orm.schema.column", "ColumnDefinition"),
    "ColumnOptions": ("orionis.orm.schema.column", "ColumnOptions"),
    "ColumnType": (_TYPES_MODULE, "ColumnType"),
    "CompositeForeignKey": (_CONSTRAINTS_MODULE, "CompositeForeignKey"),
    "Date": (_TYPES_MODULE, "Date"),
    "DateTime": (_TYPES_MODULE, "DateTime"),
    "Double": (_TYPES_MODULE, "Double"),
    "Enum": (_TYPES_MODULE, "Enum"),
    "Float": (_TYPES_MODULE, "Float"),
    "ForeignReference": (_CONSTRAINTS_MODULE, "ForeignReference"),
    "Integer": (_TYPES_MODULE, "Integer"),
    "Interval": (_TYPES_MODULE, "Interval"),
    "LargeBinary": (_TYPES_MODULE, "LargeBinary"),
    "MatchType": (_TYPES_MODULE, "MatchType"),
    "Numeric": (_TYPES_MODULE, "Numeric"),
    "NumericCommon": (_TYPES_MODULE, "NumericCommon"),
    "PickleType": (_TYPES_MODULE, "PickleType"),
    "SchemaType": (_TYPES_MODULE, "SchemaType"),
    "SmallInteger": (_TYPES_MODULE, "SmallInteger"),
    "StrictArray": (_TYPES_MODULE, "StrictArray"),
    "StrictBigInt": (_TYPES_MODULE, "StrictBigInt"),
    "StrictBinary": (_TYPES_MODULE, "StrictBinary"),
    "StrictBlob": (_TYPES_MODULE, "StrictBlob"),
    "StrictChar": (_TYPES_MODULE, "StrictChar"),
    "StrictClob": (_TYPES_MODULE, "StrictClob"),
    "StrictDecimal": (_TYPES_MODULE, "StrictDecimal"),
    "StrictDoublePrecision": (_TYPES_MODULE, "StrictDoublePrecision"),
    "StrictInt": (_TYPES_MODULE, "StrictInt"),
    "StrictJson": (_TYPES_MODULE, "StrictJson"),
    "StrictNChar": (_TYPES_MODULE, "StrictNChar"),
    "StrictNVarChar": (_TYPES_MODULE, "StrictNVarChar"),
    "StrictReal": (_TYPES_MODULE, "StrictReal"),
    "StrictSmallInt": (_TYPES_MODULE, "StrictSmallInt"),
    "StrictTimestamp": (_TYPES_MODULE, "StrictTimestamp"),
    "StrictVarBinary": (_TYPES_MODULE, "StrictVarBinary"),
    "StrictVarChar": (_TYPES_MODULE, "StrictVarChar"),
    "String": (_TYPES_MODULE, "String"),
    "TableDefinition": ("orionis.orm.schema.table", "TableDefinition"),
    "TableIndex": (_CONSTRAINTS_MODULE, "TableIndex"),
    "Text": (_TYPES_MODULE, "Text"),
    "Time": (_TYPES_MODULE, "Time"),
    "Unicode": (_TYPES_MODULE, "Unicode"),
    "UnicodeText": (_TYPES_MODULE, "UnicodeText"),
    "UniqueConstraint": (_CONSTRAINTS_MODULE, "UniqueConstraint"),
    "Uuid": (_TYPES_MODULE, "Uuid"),
}
"""Public export names mapped to their defining modules and attributes."""


def __getattr__(name: str) -> object:
    """
    Resolve and cache a public package export.

    Parameters
    ----------
    name : str
        Public attribute requested from this package.

    Returns
    -------
    object
        Exported object from its defining module.

    Raises
    ------
    AttributeError
        If the requested attribute is not exported.
    """
    return _resolve_export(globals(), _EXPORTS, name)


def __dir__() -> list[str]:
    """
    List loaded attributes and declared public exports.

    Returns
    -------
    list[str]
        Sorted attribute names available on this package.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
