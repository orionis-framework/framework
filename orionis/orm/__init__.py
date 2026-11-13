"""Group the orm components and public imports."""

from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.orm.collections.collection import Collection, ModelCollection
    from orionis.orm.collections.paginator import Paginator
    from orionis.orm.exceptions import (
        InvalidQueryException,
        MassAssignmentException,
        ModelNotFoundException,
        OrmConfigurationException,
        OrmException,
        RelationNotFoundException,
    )
    from orionis.orm.model import Model
    from orionis.orm.query.builder import ModelQueryBuilder
    from orionis.orm.relations import (
        BelongsToManyRelation,
        BelongsToRelation,
        HasManyRelation,
        HasOneRelation,
        Relation,
    )
    from orionis.orm.resolver import ConnectionResolver
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
    "BelongsToManyRelation",
    "BelongsToRelation",
    "BigInteger",
    "Boolean",
    "Collection",
    "ColumnType",
    "ConnectionResolver",
    "Date",
    "DateTime",
    "Double",
    "Enum",
    "Float",
    "HasManyRelation",
    "HasOneRelation",
    "Integer",
    "Interval",
    "InvalidQueryException",
    "LargeBinary",
    "MassAssignmentException",
    "MatchType",
    "Model",
    "ModelCollection",
    "ModelNotFoundException",
    "ModelQueryBuilder",
    "Numeric",
    "NumericCommon",
    "OrmConfigurationException",
    "OrmException",
    "Paginator",
    "PickleType",
    "Relation",
    "RelationNotFoundException",
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

_RELATIONS_MODULE = "orionis.orm.relations"
"""Module defining the public relation classes."""
_TYPES_MODULE = "orionis.orm.schema.types"
"""Module defining the public column types."""
_EXCEPTIONS_MODULE = "orionis.orm.exceptions"
"""Module defining the public ORM exceptions."""

_EXPORTS = {
    "BelongsToManyRelation": (_RELATIONS_MODULE, "BelongsToManyRelation"),
    "BelongsToRelation": (_RELATIONS_MODULE, "BelongsToRelation"),
    "BigInteger": (_TYPES_MODULE, "BigInteger"),
    "Boolean": (_TYPES_MODULE, "Boolean"),
    "Collection": ("orionis.orm.collections.collection", "Collection"),
    "ColumnType": (_TYPES_MODULE, "ColumnType"),
    "ConnectionResolver": ("orionis.orm.resolver", "ConnectionResolver"),
    "Date": (_TYPES_MODULE, "Date"),
    "DateTime": (_TYPES_MODULE, "DateTime"),
    "Double": (_TYPES_MODULE, "Double"),
    "Enum": (_TYPES_MODULE, "Enum"),
    "Float": (_TYPES_MODULE, "Float"),
    "HasManyRelation": (_RELATIONS_MODULE, "HasManyRelation"),
    "HasOneRelation": (_RELATIONS_MODULE, "HasOneRelation"),
    "Integer": (_TYPES_MODULE, "Integer"),
    "Interval": (_TYPES_MODULE, "Interval"),
    "InvalidQueryException": (_EXCEPTIONS_MODULE, "InvalidQueryException"),
    "LargeBinary": (_TYPES_MODULE, "LargeBinary"),
    "MassAssignmentException": (_EXCEPTIONS_MODULE, "MassAssignmentException"),
    "MatchType": (_TYPES_MODULE, "MatchType"),
    "Model": ("orionis.orm.model", "Model"),
    "ModelCollection": ("orionis.orm.collections.collection", "ModelCollection"),
    "ModelNotFoundException": (_EXCEPTIONS_MODULE, "ModelNotFoundException"),
    "ModelQueryBuilder": ("orionis.orm.query.builder", "ModelQueryBuilder"),
    "Numeric": (_TYPES_MODULE, "Numeric"),
    "NumericCommon": (_TYPES_MODULE, "NumericCommon"),
    "OrmConfigurationException": (_EXCEPTIONS_MODULE, "OrmConfigurationException"),
    "OrmException": (_EXCEPTIONS_MODULE, "OrmException"),
    "Paginator": ("orionis.orm.collections.paginator", "Paginator"),
    "PickleType": (_TYPES_MODULE, "PickleType"),
    "Relation": (_RELATIONS_MODULE, "Relation"),
    "RelationNotFoundException": (_EXCEPTIONS_MODULE, "RelationNotFoundException"),
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
    "Text": (_TYPES_MODULE, "Text"),
    "Time": (_TYPES_MODULE, "Time"),
    "Unicode": (_TYPES_MODULE, "Unicode"),
    "UnicodeText": (_TYPES_MODULE, "UnicodeText"),
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
