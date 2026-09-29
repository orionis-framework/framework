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

_EXPORTS = {
    "BelongsToManyRelation": ("orionis.orm.relations", "BelongsToManyRelation"), # NOSONAR
    "BelongsToRelation": ("orionis.orm.relations", "BelongsToRelation"),
    "BigInteger": ("orionis.orm.schema.types", "BigInteger"), # NOSONAR
    "Boolean": ("orionis.orm.schema.types", "Boolean"),
    "Collection": ("orionis.orm.collections.collection", "Collection"),
    "ColumnType": ("orionis.orm.schema.types", "ColumnType"),
    "ConnectionResolver": ("orionis.orm.resolver", "ConnectionResolver"),
    "Date": ("orionis.orm.schema.types", "Date"),
    "DateTime": ("orionis.orm.schema.types", "DateTime"),
    "Double": ("orionis.orm.schema.types", "Double"),
    "Enum": ("orionis.orm.schema.types", "Enum"),
    "Float": ("orionis.orm.schema.types", "Float"),
    "HasManyRelation": ("orionis.orm.relations", "HasManyRelation"),
    "HasOneRelation": ("orionis.orm.relations", "HasOneRelation"),
    "Integer": ("orionis.orm.schema.types", "Integer"),
    "Interval": ("orionis.orm.schema.types", "Interval"),
    "InvalidQueryException": ("orionis.orm.exceptions", "InvalidQueryException"), # NOSONAR
    "LargeBinary": ("orionis.orm.schema.types", "LargeBinary"),
    "MassAssignmentException": ("orionis.orm.exceptions", "MassAssignmentException"),
    "MatchType": ("orionis.orm.schema.types", "MatchType"),
    "Model": ("orionis.orm.model", "Model"),
    "ModelCollection": ("orionis.orm.collections.collection", "ModelCollection"),
    "ModelNotFoundException": ("orionis.orm.exceptions", "ModelNotFoundException"),
    "ModelQueryBuilder": ("orionis.orm.query.builder", "ModelQueryBuilder"),
    "Numeric": ("orionis.orm.schema.types", "Numeric"),
    "NumericCommon": ("orionis.orm.schema.types", "NumericCommon"),
    "OrmConfigurationException": ("orionis.orm.exceptions", "OrmConfigurationException"),
    "OrmException": ("orionis.orm.exceptions", "OrmException"),
    "Paginator": ("orionis.orm.collections.paginator", "Paginator"),
    "PickleType": ("orionis.orm.schema.types", "PickleType"),
    "Relation": ("orionis.orm.relations", "Relation"),
    "RelationNotFoundException": ("orionis.orm.exceptions", "RelationNotFoundException"),
    "SchemaType": ("orionis.orm.schema.types", "SchemaType"),
    "SmallInteger": ("orionis.orm.schema.types", "SmallInteger"),
    "StrictArray": ("orionis.orm.schema.types", "StrictArray"),
    "StrictBigInt": ("orionis.orm.schema.types", "StrictBigInt"),
    "StrictBinary": ("orionis.orm.schema.types", "StrictBinary"),
    "StrictBlob": ("orionis.orm.schema.types", "StrictBlob"),
    "StrictChar": ("orionis.orm.schema.types", "StrictChar"),
    "StrictClob": ("orionis.orm.schema.types", "StrictClob"),
    "StrictDecimal": ("orionis.orm.schema.types", "StrictDecimal"),
    "StrictDoublePrecision": ("orionis.orm.schema.types", "StrictDoublePrecision"),
    "StrictInt": ("orionis.orm.schema.types", "StrictInt"),
    "StrictJson": ("orionis.orm.schema.types", "StrictJson"),
    "StrictNChar": ("orionis.orm.schema.types", "StrictNChar"),
    "StrictNVarChar": ("orionis.orm.schema.types", "StrictNVarChar"),
    "StrictReal": ("orionis.orm.schema.types", "StrictReal"),
    "StrictSmallInt": ("orionis.orm.schema.types", "StrictSmallInt"),
    "StrictTimestamp": ("orionis.orm.schema.types", "StrictTimestamp"),
    "StrictVarBinary": ("orionis.orm.schema.types", "StrictVarBinary"),
    "StrictVarChar": ("orionis.orm.schema.types", "StrictVarChar"),
    "String": ("orionis.orm.schema.types", "String"),
    "Text": ("orionis.orm.schema.types", "Text"),
    "Time": ("orionis.orm.schema.types", "Time"),
    "Unicode": ("orionis.orm.schema.types", "Unicode"),
    "UnicodeText": ("orionis.orm.schema.types", "UnicodeText"),
    "Uuid": ("orionis.orm.schema.types", "Uuid"),
}

def __getattr__(name: str) -> object:
    """Resolve and cache a public package export.

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
    """List loaded attributes and declared public exports.

    Returns
    -------
    list[str]
        Sorted attribute names available on this package.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
