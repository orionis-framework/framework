# Schema types and constraints

This reference complements [models](models-and-attributes.md) and [table creation](../../../database/docs/en/schema.md). Orionis types produce `ColumnDefinition`; Database compilation translates them for the destination dialect. They describe storage rather than request-validation schemas.

## Choose column types

Import these types from `orionis.orm` or `orionis.orm.schema.types`. Relevant optional arguments are shown in parentheses; values after `=` are defaults.

| Family | Types and options |
|---|---|
| Generic integers | `Integer()`, `BigInteger()`, `SmallInteger()` |
| Booleans | `Boolean(create_constraint=False, name=None)` |
| Text | `String(length=255, collation=None)`, `Text(length=None, collation=None)` |
| Unicode | `Unicode(length=None, collation=None)`, `UnicodeText(length=None, collation=None)` |
| Dates | `Date()`, `Time()`, `DateTime(timezone=False)` |
| UUID identity | `Uuid(as_uuid=True, native_uuid=True)` |
| Binary | `LargeBinary(length=None)` |
| Decimal numbers | `Numeric(precision=None, scale=None, decimal_return_scale=None, asdecimal=True)` |
| Floating point | `Float(precision=None, asdecimal=False, decimal_return_scale=None)`, `Double(...)` with the same options |
| Enumeration | `Enum(*enums, name=None, create_constraint=False, native_enum=True, length=None, validate_strings=False)` |
| Interval | `Interval(native=True, second_precision=None, day_precision=None)` |
| Python objects | `PickleType(protocol=5, pickler=None, impl=None)` |

For example, `Numeric(12, 2)` specifies decimal precision/scale; avoid floating point when exact monetary equality is required. `timezone=True` requests a compatible temporal type, but results depend on the backend and driver; it does not change the application timezone itself. Native enums and boolean constraints need dialect support and deliberate evolution when values change.

`PickleType` exists, but unpickling requires trusted data; do not use it for content a third party can modify. Queue serialization does not use this type.

## Explicit SQL types

The `Strict` family names concrete SQL variants. It does not mean strict Python input validation or universal portability.

| Family | Types |
|---|---|
| Integers | `StrictInt()`, `StrictBigInt()`, `StrictSmallInt()` |
| SQL text | `StrictChar`, `StrictVarChar`, `StrictNChar`, `StrictNVarChar`, `StrictClob` |
| SQL binary | `StrictBinary`, `StrictVarBinary`, `StrictBlob` |
| SQL numeric | `StrictReal`, `StrictDoublePrecision`, `StrictDecimal` |
| JSON | `StrictJson(none_as_null=False)` |
| Timestamp | `StrictTimestamp(timezone=False)` |
| Array | `StrictArray(item_type, as_tuple=False, dimensions=None, zero_indexes=False)` |

Text variants accept `length` and `collation`; `StrictVarChar` defaults to 255 while the others default to `None`. Binary variants accept optional length. `StrictReal`/`StrictDoublePrecision` take precision and float-like return options. `StrictDecimal(precision=10, scale=2, decimal_return_scale=None, asdecimal=True)` requires positive precision and nonnegative scale no greater than precision; supply both values or both `None`.

`StrictArray(Integer())` declares an element type; do not assume ARRAY support outside a backend implementing it. `StrictJson` also needs a compatible backend. Public `SchemaType(name=None)`, `NumericCommon()`, and `MatchType()` are auxiliary descriptors rather than ordinary business-column choices. `ColumnType` identifies the compiler vocabulary.

## Common modifiers

All column types provide `.primary()`, `.nullable()`, `.default(value)`, `.unique()`, `.index()`, `.foreign("table.column")`, `.autoIncrement()`, and `.comment(text)`. These return the same definition; do not share mutable definitions between distinct columns.

`default` accepts a static value or zero-argument callable evaluated during compatible insert workflows. It is not an arbitrary SQL default expression. `hasDefault()` distinguishes explicitly supplied defaults, including `None`, from absence. `.foreign()` accepts exactly `table.column`; use appropriate structures for schemas or composite keys rather than inventing longer reference strings.

## Define composite keys and shared tables

`TableDefinition` accepts `name`, `columns`, `primary_key="id"`, `schema=None`, `comment=None`, `composite_primary_key=None`, `unique_constraints=()`, `foreign_keys=()`, and `indexes=()`. Import constraints from `orionis.orm.schema.constraints`:

```python
from orionis.orm import Integer
from orionis.orm.schema.constraints import CompositeForeignKey, TableIndex
from orionis.orm.schema.table import TableDefinition

team_id = Integer()
team_id.name = "team_id"
member_id = Integer()
member_id.name = "member_id"

TEAM_MEMBERS_V1 = TableDefinition(
    name="team_members",
    columns={"team_id": team_id, "member_id": member_id},
    primary_key="team_id",
    composite_primary_key=("team_id", "member_id"),
    foreign_keys=(
        CompositeForeignKey(("team_id",), "teams", ("id",)),
        CompositeForeignKey(("member_id",), "members", ("id",)),
    ),
    indexes=(TableIndex(("member_id",)),),
)
assert TEAM_MEMBERS_V1.hasColumn("member_id")
```

This example declares structure only. `CompositeForeignKey(columns, ref_table, ref_columns, name=None)` relates ordered tuples; `UniqueConstraint(columns, name=None)` defines composite uniqueness and `TableIndex(columns, name=None, unique=False)` defines indexes. `ForeignReference(table, column)` represents a simple reference.

A composite schema PK does not add a complete composite-identity Active Record API: `find`, `save`, and instance operations still use a singular `primary_key`. Use relationships and builders explicitly filtering every key for pivot tables. Constraint declarations also do not imply enforcement on Redshift; check [backend capabilities](../../../database/docs/en/dialects-and-production.md).
