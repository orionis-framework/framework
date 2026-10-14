from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.orm.schema.types.big_integer import BigInteger
    from orionis.orm.schema.types.boolean import Boolean
    from orionis.orm.schema.types.column_type import ColumnType
    from orionis.orm.schema.types.date import Date
    from orionis.orm.schema.types.date_time import DateTime
    from orionis.orm.schema.types.double import Double
    from orionis.orm.schema.types.enum_type import Enum
    from orionis.orm.schema.types.float_type import Float
    from orionis.orm.schema.types.integer import Integer
    from orionis.orm.schema.types.interval import Interval
    from orionis.orm.schema.types.large_binary import LargeBinary
    from orionis.orm.schema.types.match_type import MatchType
    from orionis.orm.schema.types.numeric import Numeric
    from orionis.orm.schema.types.numeric_common import NumericCommon
    from orionis.orm.schema.types.pickle_type import PickleType
    from orionis.orm.schema.types.schema_type import SchemaType
    from orionis.orm.schema.types.small_integer import SmallInteger
    from orionis.orm.schema.types.strict_array import StrictArray
    from orionis.orm.schema.types.strict_big_int import StrictBigInt
    from orionis.orm.schema.types.strict_binary import StrictBinary
    from orionis.orm.schema.types.strict_blob import StrictBlob
    from orionis.orm.schema.types.strict_char import StrictChar
    from orionis.orm.schema.types.strict_clob import StrictClob
    from orionis.orm.schema.types.strict_decimal import StrictDecimal
    from orionis.orm.schema.types.strict_double_precision import StrictDoublePrecision
    from orionis.orm.schema.types.strict_int import StrictInt
    from orionis.orm.schema.types.strict_json import StrictJson
    from orionis.orm.schema.types.strict_nchar import StrictNChar
    from orionis.orm.schema.types.strict_nvarchar import StrictNVarChar
    from orionis.orm.schema.types.strict_real import StrictReal
    from orionis.orm.schema.types.strict_small_int import StrictSmallInt
    from orionis.orm.schema.types.strict_timestamp import StrictTimestamp
    from orionis.orm.schema.types.strict_var_binary import StrictVarBinary
    from orionis.orm.schema.types.strict_varchar import StrictVarChar
    from orionis.orm.schema.types.string_type import String
    from orionis.orm.schema.types.text import Text
    from orionis.orm.schema.types.time_type import Time
    from orionis.orm.schema.types.unicode import Unicode
    from orionis.orm.schema.types.unicode_text import UnicodeText
    from orionis.orm.schema.types.uuid_type import Uuid

__all__ = [
    "BigInteger",
    "Boolean",
    "ColumnType",
    "Date",
    "DateTime",
    "Double",
    "Enum",
    "Float",
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
    "Text",
    "Time",
    "Unicode",
    "UnicodeText",
    "Uuid",
]

_EXPORTS = {
    "BigInteger": ("orionis.orm.schema.types.big_integer", "BigInteger"),
    "Boolean": ("orionis.orm.schema.types.boolean", "Boolean"),
    "ColumnType": ("orionis.orm.schema.types.column_type", "ColumnType"),
    "Date": ("orionis.orm.schema.types.date", "Date"),
    "DateTime": ("orionis.orm.schema.types.date_time", "DateTime"),
    "Double": ("orionis.orm.schema.types.double", "Double"),
    "Enum": ("orionis.orm.schema.types.enum_type", "Enum"),
    "Float": ("orionis.orm.schema.types.float_type", "Float"),
    "Integer": ("orionis.orm.schema.types.integer", "Integer"),
    "Interval": ("orionis.orm.schema.types.interval", "Interval"),
    "LargeBinary": ("orionis.orm.schema.types.large_binary", "LargeBinary"),
    "MatchType": ("orionis.orm.schema.types.match_type", "MatchType"),
    "Numeric": ("orionis.orm.schema.types.numeric", "Numeric"),
    "NumericCommon": ("orionis.orm.schema.types.numeric_common", "NumericCommon"),
    "PickleType": ("orionis.orm.schema.types.pickle_type", "PickleType"),
    "SchemaType": ("orionis.orm.schema.types.schema_type", "SchemaType"),
    "SmallInteger": ("orionis.orm.schema.types.small_integer", "SmallInteger"),
    "StrictArray": ("orionis.orm.schema.types.strict_array", "StrictArray"),
    "StrictBigInt": ("orionis.orm.schema.types.strict_big_int", "StrictBigInt"),
    "StrictBinary": ("orionis.orm.schema.types.strict_binary", "StrictBinary"),
    "StrictBlob": ("orionis.orm.schema.types.strict_blob", "StrictBlob"),
    "StrictChar": ("orionis.orm.schema.types.strict_char", "StrictChar"),
    "StrictClob": ("orionis.orm.schema.types.strict_clob", "StrictClob"),
    "StrictDecimal": ("orionis.orm.schema.types.strict_decimal", "StrictDecimal"),
    "StrictDoublePrecision": ("orionis.orm.schema.types.strict_double_precision", "StrictDoublePrecision"),
    "StrictInt": ("orionis.orm.schema.types.strict_int", "StrictInt"),
    "StrictJson": ("orionis.orm.schema.types.strict_json", "StrictJson"),
    "StrictNChar": ("orionis.orm.schema.types.strict_nchar", "StrictNChar"),
    "StrictNVarChar": ("orionis.orm.schema.types.strict_nvarchar", "StrictNVarChar"),
    "StrictReal": ("orionis.orm.schema.types.strict_real", "StrictReal"),
    "StrictSmallInt": ("orionis.orm.schema.types.strict_small_int", "StrictSmallInt"),
    "StrictTimestamp": ("orionis.orm.schema.types.strict_timestamp", "StrictTimestamp"),
    "StrictVarBinary": ("orionis.orm.schema.types.strict_var_binary", "StrictVarBinary"),
    "StrictVarChar": ("orionis.orm.schema.types.strict_varchar", "StrictVarChar"),
    "String": ("orionis.orm.schema.types.string_type", "String"),
    "Text": ("orionis.orm.schema.types.text", "Text"),
    "Time": ("orionis.orm.schema.types.time_type", "Time"),
    "Unicode": ("orionis.orm.schema.types.unicode", "Unicode"),
    "UnicodeText": ("orionis.orm.schema.types.unicode_text", "UnicodeText"),
    "Uuid": ("orionis.orm.schema.types.uuid_type", "Uuid"),
}

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
