from __future__ import annotations
from enum import StrEnum

class ColumnType(StrEnum):
    """
    Logical column types understood by the Orionis SQL compiler.

    Each member is mapped internally to the corresponding engine type by
    the database layer; models never interact with SQL types directly.
    """

    # Generic Types
    BIG_INTEGER = "big_integer"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    DOUBLE = "double"
    ENUM = "enum"
    FLOAT = "float"
    INTEGER = "integer"
    INTERVAL = "interval"
    LARGE_BINARY = "large_binary"
    MATCH_TYPE = "match_type"
    NUMERIC = "numeric"
    NUMERIC_COMMON = "numeric_common"
    PICKLE_TYPE = "pickle_type"
    SCHEMA_TYPE = "schema_type"
    SMALL_INTEGER = "small_integer"
    STRING = "string"
    TEXT = "text"
    TIME = "time"
    UNICODE = "unicode"
    UNICODE_TEXT = "unicode_text"
    UUID = "uuid"

    # Specific Types
    ARRAY = "array"
    BIGINT = "bigint"
    BINARY = "binary"
    BLOB = "blob"
    CHAR = "char"
    CLOB = "clob"
    DECIMAL = "decimal"
    DOUBLE_PRECISION = "double_precision"
    INT = "int"
    JSON = "json"
    NCHAR = "nchar"
    NVARCHAR = "nvarchar"
    REAL = "real"
    SMALLINT = "smallint"
    TIMESTAMP = "timestamp"
    VARBINARY = "varbinary"
    VARCHAR = "varchar"
