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

    def id(self, name: str = "id") -> BigInteger:
        ...

    def bigInteger(self, name: str) -> BigInteger:
        ...

    def boolean(
        self,
        name: str,
        *,
        create_constraint: bool = False,
        constraint_name: str | None = None,
    ) -> Boolean:
        ...

    def date(self, name: str) -> Date:
        ...

    def dateTime(self, name: str, *, timezone: bool = False) -> DateTime:
        ...

    def double(
        self,
        name: str,
        precision: int | None = None,
        *,
        asdecimal: bool = False,
        decimal_return_scale: int | None = None,
    ) -> Double:
        ...

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
        ...

    def float(
        self,
        name: str,
        precision: int | None = None,
        *,
        asdecimal: bool = False,
        decimal_return_scale: int | None = None,
    ) -> Float:
        ...

    def integer(self, name: str) -> Integer:
        ...

    def interval(
        self,
        name: str,
        *,
        native: bool = True,
        second_precision: int | None = None,
        day_precision: int | None = None,
    ) -> Interval:
        ...

    def largeBinary(self, name: str, length: int | None = None) -> LargeBinary:
        ...

    def matchType(self, name: str) -> MatchType:
        ...

    def numeric(
        self,
        name: str,
        precision: int | None = None,
        scale: int | None = None,
        decimal_return_scale: int | None = None,
        *,
        asdecimal: bool = True,
    ) -> Numeric:
        ...

    def numericCommon(self, name: str) -> NumericCommon:
        ...

    def pickleType(
        self,
        name: str,
        protocol: int = 5,
        pickler: object | None = None,
        impl: object | None = None,
    ) -> PickleType:
        ...

    def schemaType(
        self,
        name: str,
        schema_name: str | None = None,
    ) -> SchemaType:
        ...

    def smallInteger(self, name: str) -> SmallInteger:
        ...

    def string(
        self,
        name: str,
        length: int | None = 255,
        collation: str | None = None,
    ) -> String:
        ...

    def text(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> Text:
        ...

    def time(self, name: str) -> Time:
        ...

    def unicode(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> Unicode:
        ...

    def unicodeText(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> UnicodeText:
        ...

    def uuid(
        self,
        name: str,
        *,
        as_uuid: bool = True,
        native_uuid: bool = True,
    ) -> Uuid:
        ...

    def strictArray(
        self,
        name: str,
        item_type: ColumnDefinition,
        *,
        as_tuple: bool = False,
        dimensions: int | None = None,
        zero_indexes: bool = False,
    ) -> StrictArray:
        ...

    def strictBigInt(self, name: str) -> StrictBigInt:
        ...

    def strictBinary(
        self,
        name: str,
        length: int | None = None,
    ) -> StrictBinary:
        ...

    def strictBlob(self, name: str, length: int | None = None) -> StrictBlob:
        ...

    def strictChar(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> StrictChar:
        ...

    def strictClob(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> StrictClob:
        ...

    def strictDecimal(
        self,
        name: str,
        precision: int | None = 10,
        scale: int | None = 2,
        decimal_return_scale: int | None = None,
        *,
        asdecimal: bool = True,
    ) -> StrictDecimal:
        ...

    def strictDoublePrecision(
        self,
        name: str,
        precision: int | None = None,
        *,
        asdecimal: bool = False,
        decimal_return_scale: int | None = None,
    ) -> StrictDoublePrecision:
        ...

    def strictInt(self, name: str) -> StrictInt:
        ...

    def strictJson(
        self,
        name: str,
        *,
        none_as_null: bool = False,
    ) -> StrictJson:
        ...

    def strictNChar(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> StrictNChar:
        ...

    def strictNVarChar(
        self,
        name: str,
        length: int | None = None,
        collation: str | None = None,
    ) -> StrictNVarChar:
        ...
    def strictReal(
        self,
        name: str,
        precision: int | None = None,
        *,
        asdecimal: bool = False,
        decimal_return_scale: int | None = None,
    ) -> StrictReal:
        ...

    def strictSmallInt(self, name: str) -> StrictSmallInt:
        ...

    def strictTimestamp(
        self,
        name: str,
        *,
        timezone: bool = False,
    ) -> StrictTimestamp:
        ...

    def strictVarBinary(
        self,
        name: str,
        length: int | None = None,
    ) -> StrictVarBinary:
        ...

    def strictVarChar(
        self,
        name: str,
        length: int | None = 255,
        collation: str | None = None,
    ) -> StrictVarChar:
        ...

    def timestamps(self, *, timezone: bool = False) -> None:
        ...

    def comment(self, text: str) -> Comment:
        ...

    def foreignKey(
        self,
        column: str,
        ref_table: str,
        ref_column: str,
        name: str | None = None,
    ) -> ForeignKey:
        ...

    def index(
        self,
        *columns: str,
        name: str | None = None,
        unique: bool = False,
    ) -> Index:
        ...

    def primaryKey(self, *columns: str) -> PrimaryKey:
        ...

    def unique(self, *columns: str, name: str | None = None) -> Unique:
        ...
