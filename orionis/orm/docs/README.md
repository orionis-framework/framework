# Orionis ORM

> Async-first Active Record models, query builders, relationships, and database schema definitions.

## Table of contents

- [Requirements](#requirements)
- [Functional description](#functional-description)
- [API reference](#api-reference)
- [Usage examples](#usage-examples)
- [Performance and concurrency considerations](#performance-and-concurrency-considerations)
- [Compatibility notes](#compatibility-notes)

## Requirements

There is no ORM-specific installation step beyond `pip install orionis`. The ORM uses the framework's database subsystem, including `aiosqlite>=0.22.1` for SQLite and `sqlalchemy[asyncio]>=2.0.54,<3.0`. Other database engines require the matching optional package extra and its driver dependencies: `orionis[mysql]` (`aiomysql>=0.3.2`, `pymysql>=1.2.3`), `orionis[pgsql]` (`asyncpg>=0.31.0`, `psycopg2-binary>=2.9.13`), `orionis[oracle]` (`oracledb>=26.0.0`), or `orionis[sqlserver]` (`aioodbc>=0.5.0`, `pyodbc>=5.3.0`). These requirements are declared in `pyproject.toml`.

Queries require the application database provider to install a connection manager in `ConnectionResolver`. In normal application use, framework boot performs this wiring.

## Functional description

`orionis.orm` provides declarative models whose column definitions are discovered by `ModelMeta`, then used for attribute casting, persistence, and query construction. `ModelQueryBuilder` and the raw `QueryBuilder` express asynchronous database operations through Orionis connections.

The ORM also defines relationship builders, result collections and paginators, and engine-independent table and column descriptions consumed by the database compiler and migration subsystem. The public package surface is re-exported from `orionis.orm`; lower-level implementation modules include `orionis.orm.query`, `orionis.orm.relations`, and `orionis.orm.schema`.

## API reference

Unless shown otherwise, query and persistence operations that access the database are `async` and must be awaited. The signatures below follow declarations in the source; `...` in a type constructor row means that the row intentionally describes a family, not a callable signature.

### `Model`

`Model` is the base class for declarative Active Record models. Declare columns as class attributes using schema types, and configure class variables such as `table`, `connection`, `fillable`, `guarded`, `hidden`, `casts`, `timestamps`, `soft_deletes`, and `uuids` where needed. When `table` is `None`, the metaclass derives the table name; primary-key metadata comes from declared column flags unless overridden.

| Signature | Behavior |
|---|---|
| `__init__(self, attributes: dict[str, Any] \| None = None) -> None` | Creates an unsaved model and mass-assigns provided attributes. Raises `MassAssignmentException` for unknown or non-fillable attributes. |
| `query(cls) -> ModelQueryBuilder[Any]` | Starts a builder for the model. |
| `getConnection(cls) -> IConnection` | Resolves the configured connection; raises `OrmConfigurationException` when the manager is not installed. |
| `all(cls) -> Collection` | Async: returns all matching model instances. |
| `find(cls, key: Any) -> Model \| None` | Async: looks up the primary key, returning `None` when absent. |
| `findOrFail(cls, key: Any) -> Model` | Async: lookup that raises `ModelNotFoundException` when absent. |
| `first(cls) -> Model \| None` / `firstOrFail(cls) -> Model` | Async: returns the first row, or raises `ModelNotFoundException` in the `OrFail` form when none exists. |
| `create(cls, attributes: dict[str, Any]) -> Model` | Async: constructs, saves, and returns a model. Can raise `MassAssignmentException` or a database `QueryException`. |
| `destroy(cls, *keys: Any) -> int` | Async: deletes rows with the given primary keys and returns the affected count. |
| `save(self) -> bool` | Async: inserts a new model or writes its dirty attributes; dispatches lifecycle events and maintains enabled timestamps. A listener can veto a write, resulting in `False`. |
| `update(self, attributes: dict[str, Any]) -> bool` | Async: mass-assigns and saves. Can raise `MassAssignmentException` or `QueryException`. |
| `delete(self) -> bool` | Async: deletes an existing row, or stamps the configured delete column when soft deletes apply. |
| `addGlobalScope(cls, name: str, scope: Callable[[ModelQueryBuilder[Any]], None]) -> type[Model]` | Registers a named constraint on model queries. |
| `removeGlobalScope(cls, name: str) -> type[Model]` | Removes a named scope if present. |
| `freshTimestamp(cls) -> datetime` | Produces current UTC time; returns naive UTC unless the selected timestamp column is declared as `TIMESTAMP`. |
| `newUniqueId(cls) -> Any` | Produces a UUID by default for client-generated keys; models may override it. |

Additional inherited public model methods include `fill`, `setAttribute`, `getAttribute`, `hasAccessor`, `toDict`, `serialize`, `toJson`, `only`, `exclude`, `getDirty`, `isDirty`, `isClean`, `wasChanged`, `getChanges`, `getOriginal`, and `syncOriginal`. Relationship methods are listed under [Relationships](#relationships). Attribute serialization omits `hidden` fields and can include declared `appends`; casts supported by the implementation are `int`, `float`, `bool`, `datetime`, `date`, `json`, and `uuid`. Unsupported cast names raise `OrmException`.

### `ModelQueryBuilder`

`ModelQueryBuilder` binds the shared query language to a model and returns hydrated models or `Collection` values. Its common signatures are:

```python
__init__(self, model: type[TModel]) -> None
withRelations(self, *names: str) -> Self
load(self, *names: str) -> Self
withoutGlobalScope(self, name: str) -> Self
withoutGlobalScopes(self, *names: str) -> Self
scope(self, name: str, *args: Any, **kwargs: Any) -> Self
get(self) -> Collection
first(self) -> TModel | None
firstOrFail(self) -> TModel
find(self, key: Any) -> TModel | None
findOrFail(self, key: Any) -> TModel
value(self, column: str) -> Any
pluck(self, column: str) -> Collection
paginate(self, page: int = 1, per_page: int = _DEFAULT_PER_PAGE) -> Paginator
restore(self) -> int
forceDelete(self) -> int
delete(self) -> int
```

The async methods above are awaited. `withTrashed`, `onlyTrashed`, and `withoutTrashed` control inclusion of soft-deleted rows. The builder also exposes the fluent query methods below.

### Query builders and query language

`QueryBuilder` is the model-less entry point used by the database facade; `table(self, name: str, *, alias: str | None = None, connection: str | None = None) -> IRawQueryBuilder` returns `RawQueryBuilder`. `RawQueryBuilder` reads table rows as dictionaries and supports `connection(self, name: str) -> Self`, `table(self, name: str, *, alias: str | None = None) -> Self`, and async `get(self) -> Collection`, `first(self) -> dict[str, Any] | None`, `value(self, column: str) -> Any`, `pluck(self, column: str) -> Collection`, and `paginate(self, page: int = 1, per_page: int = _DEFAULT_PER_PAGE) -> Paginator`.

`QueryBuilder` exposes these signatures: `connection(self, name: str | None = None) -> Self`, `table(self, name: str, *, alias: str | None = None, connection: str | None = None) -> IRawQueryBuilder`, `select(self, sql: str, bindings: dict[str, object] | None = None, name: str | None = None) -> list[dict[str, object]]`, `execute(self, sql: str, bindings: dict[str, object] | None = None, name: str | None = None) -> int`, `statement(self, sql: str, bindings: dict[str, object] | None = None, name: str | None = None) -> bool`, `beginTransaction(self, name: str | None = None) -> None`, `commit(self, name: str | None = None) -> None`, `rollback(self, name: str | None = None) -> None`, and `transaction(self, name: str | None = None) -> ITransaction`. SQL execution and transaction methods are async; a table query is built by `table(...)`.

### `ConnectionResolver`

`ConnectionResolver` is the static bridge to the database connection manager. Its API is `setManager(cls, manager: IConnectionManager) -> None`, `manager(cls) -> IConnectionManager`, `connection(cls, name: str | None = None) -> IConnection`, and `clear(cls) -> None`. `manager()` and `connection()` raise `OrmConfigurationException` if a manager has not been installed. When `name` is `None`, `connection()` first checks for an active migration connection, then delegates to the manager.

Both model and raw table builders use the shared fluent query API. Methods include:

- Projection: `select(*columns)`, `addSelect(*columns)`, `selectRaw(sql, bindings=None, alias=None)`, `selectSub(query, alias)`, `distinct()`.
- Predicates: `where(column, *args)`, `orWhere(column, *args)`, `whereIn`/`orWhereIn`, `whereNotIn`/`orWhereNotIn`, `whereNull`/`orWhereNull`, `whereNotNull`/`orWhereNotNull`, `whereBetween`, `whereNotBetween`, `whereLike`, `whereNotLike`, `whereILike`, `whereNotILike`, `whereStartsWith`, `whereEndsWith`, `whereContains`, `whereRegexpMatch`, `whereColumn`, `orWhereColumn`, `whereRaw`, `orWhereRaw`, `whereExists`, `orWhereExists`, `whereNotExists`, and `orWhereNotExists`.
- Joins and grouping: `join`, `leftJoin`, `rightJoin`, `fullJoin`, `crossJoin`, `joinSub`, `leftJoinSub`, `rightJoinSub`, `groupBy`, `having`, `orHaving`, and `havingRaw`.
- Ordering and paging: `orderBy(column, direction='asc')`, `latest(column=None)`, `oldest(column=None)`, `limit(value)`, `offset(value)`, `take(value)`, `skip(value)`, `forPage(page, per_page=15)`, `lockForUpdate()`, and `sharedLock()`.
- Set operations and execution: `union(query)`, `unionAll(query)`, `count(column='*')`, `exists()`, `doesntExist()`, `max(column)`, `min(column)`, `avg(column)`, `sum(column)`, `insert(values)`, `update(values)`, and `delete()`.

Builder calls are fluent and return the builder except execution methods, which are async and return the type described by their operation (`int`, `bool`, aggregate result, or `InsertResult`). Invalid builder arguments can raise `InvalidQueryException`; database failures can raise database exceptions. Exact parameter annotations are declared in `orionis.orm.contracts.base_builder.IQueryBuilderBase` and implemented by `orionis.orm.query.base_builder.QueryBuilderBase`.

### Relationships

Relationship methods are declared on model instances and return query-capable relation objects:

```python
hasOne(self, related: type[TRelated], foreign_key: str | None = None, local_key: str | None = None) -> HasOneRelation[TRelated]
hasMany(self, related: type[TRelated], foreign_key: str | None = None, local_key: str | None = None) -> HasManyRelation[TRelated]
belongsTo(self, related: type[TRelated], foreign_key: str | None = None, owner_key: str | None = None) -> BelongsToRelation[TRelated]
belongsToMany(self, related: type[TRelated], table: str | None = None, foreign_pivot_key: str | None = None, related_pivot_key: str | None = None, parent_key: str | None = None, related_key: str | None = None) -> BelongsToManyRelation[TRelated]
```

`HasOneRelation` returns one model or `None`; `HasManyRelation` and `BelongsToManyRelation` return `Collection`; `BelongsToRelation` returns one model or `None`. `BelongsToManyRelation` additionally provides async `attach(ids, attributes=None) -> int`, `detach(ids=None) -> int`, `sync(ids: Iterable[Any]) -> dict[str, list[Any]]`, and `toggle(ids: Iterable[Any]) -> dict[str, list[Any]]`, plus `wherePivot(column, *args)`.

`setRelation(name, value) -> Model`, `getRelation(name, default=None) -> Any`, and `relationLoaded(name) -> bool` manage a model's in-memory loaded relation values. `withRelations(*names)` requests eager loading; unresolved relation names raise `RelationNotFoundException` during relation resolution.

### Collections and pagination

`Collection` is the framework-wide collection type, re-exported as `ModelCollection`. Their implementations are the same class (`ModelCollection = Collection`); the collection operations are defined in `orionis.support.types.collection`.

`Paginator` is constructed as `Paginator(items: Collection, total: int, page: int, per_page: int) -> None`. It exposes `items() -> Collection`, `total() -> int`, `page() -> int`, `perPage() -> int`, `lastPage() -> int`, `hasNext() -> bool`, `hasPrevious() -> bool`, `toDict() -> dict[str, Any]`, and `toJson(**kwargs: Any) -> str`; `len(paginator)` is the number of items in the page.

### Schema definitions and column types

`ColumnDefinition` is the shared mutable fluent definition. Its methods are `primary()`, `nullable()`, `default(value)`, `unique()`, `index()`, `foreign(reference)`, `autoIncrement()`, and `comment(text)`, each returning the same `ColumnDefinition`; `hasDefault() -> bool` reports whether a default was set. `foreign` parses a `"table.column"` reference and raises `ValueError` for an invalid reference.

`TableDefinition` is a frozen, slotted dataclass with fields `name`, `columns`, `primary_key`, `schema`, `comment`, `composite_primary_key`, `unique_constraints`, `foreign_keys`, and `indexes`. It offers `columnNames() -> tuple[str, ...]` and `hasColumn(name: str) -> bool`. `ColumnOptions` is a dataclass of type-specific SQL type options. Constraint value objects exported by `orionis.orm.schema` are `CompositeForeignKey`, `ForeignReference`, `TableIndex`, and `UniqueConstraint`; `ForeignReference.parse(reference: str) -> ForeignReference` parses a qualified column reference and `qualified() -> str` formats it.

The root package exports the following logical schema type constructors. Constructors below match their `__init__` declarations (the classes also inherit the column fluent methods):

| Class | Constructor signature |
|---|---|
| `BigInteger`, `Date`, `Integer`, `MatchType`, `SmallInteger`, `StrictBigInt`, `StrictInt`, `StrictSmallInt`, `Time` | `__init__(self) -> None` |
| `Boolean` | `__init__(self, *, create_constraint: bool = False, name: str \| None = None) -> None` |
| `DateTime` | `__init__(self, *, timezone: bool = False) -> None` |
| `Double`, `Float`, `StrictDoublePrecision`, `StrictReal` | `__init__(self, precision: int \| None = None, *, asdecimal: bool = False, decimal_return_scale: int \| None = None) -> None` |
| `Enum` | `__init__(self, *enums: str, name: str \| None = None, create_constraint: bool = False, native_enum: bool = True, length: int \| None = None, validate_strings: bool = False) -> None` |
| `Interval` | `__init__(self, *, native: bool = True, second_precision: int \| None = None, day_precision: int \| None = None) -> None` |
| `LargeBinary` | `__init__(self, length: int \| None = None) -> None` |
| `Numeric` | `__init__(self, precision: int \| None = None, scale: int \| None = None, decimal_return_scale: int \| None = None, *, asdecimal: bool = True) -> None` |
| `NumericCommon` | `__init__(self) -> None` |
| `PickleType` | `__init__(self, protocol: int = 5, pickler: object \| None = None, impl: object \| None = None) -> None` |
| `SchemaType` | `__init__(self, name: str \| None = None) -> None` |
| `StrictArray` | `__init__(self, item_type: ColumnDefinition, *, as_tuple: bool = False, dimensions: int \| None = None, zero_indexes: bool = False) -> None` |
| `StrictBinary`, `StrictBlob` | `__init__(self, length: int \| None = None) -> None` |
| `StrictChar`, `StrictNChar` | `__init__(self, length: int \| None = None, collation: str \| None = None) -> None` |
| `StrictClob`, `StrictNVarChar` | `__init__(self, length: int \| None = None, collation: str \| None = None) -> None` |
| `StrictVarChar`, `String` | `__init__(self, length: int \| None = DEFAULT_STRING_LENGTH, collation: str \| None = None) -> None` |
| `Text`, `Unicode`, `UnicodeText` | `__init__(self, length: int \| None = None, collation: str \| None = None) -> None` |
| `StrictDecimal` | `__init__(self, precision: int \| None = DEFAULT_DECIMAL_PRECISION, scale: int \| None = DEFAULT_DECIMAL_SCALE, decimal_return_scale: int \| None = None, *, asdecimal: bool = True) -> None` |
| `StrictJson` | `__init__(self, *, none_as_null: bool = False) -> None` |
| `StrictTimestamp` | `__init__(self, *, timezone: bool = False) -> None` |
| `StrictVarBinary` | `__init__(self, length: int \| None = None) -> None` |
| `Uuid` | `__init__(self, *, as_uuid: bool = True, native_uuid: bool = True) -> None` |

`ColumnType` describes the logical column kinds consumed by the SQL compiler.

### Exceptions

All ORM exceptions derive from `OrmException`: `OrmConfigurationException` (manager wiring is missing), `ModelNotFoundException` (a required lookup found no record), `MassAssignmentException` (mass assignment violates rules), `InvalidQueryException` (invalid query-builder arguments), `RelationNotFoundException` (a model relation cannot be resolved), and `ScopeNotFoundException` (a requested local scope is undeclared). Database execution can also raise exception types from `orionis.database.exceptions`, including `QueryException`.

## Usage examples

These snippets use the public package imports. Run database operations after the Orionis application has booted and the corresponding tables have been created.

### Common model query

```python
from orionis.orm import Integer, Model, String


class User(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    timestamps = False


async def active_users():
    return await User.query().where("name", "Ada").orderBy("name").get()
```

### Handle a missing row

```python
from orionis.orm import Integer, Model, String, ModelNotFoundException


class User(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    timestamps = False


async def load_user(user_id: int):
    try:
        return await User.findOrFail(user_id)
    except ModelNotFoundException:
        return None
```

### Integrate a relationship

```python
from orionis.orm import HasManyRelation, Integer, Model, String


class Team(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    timestamps = False

    def members(self) -> HasManyRelation["Member"]:
        return self.hasMany(Member)


class Member(Model):
    id = Integer().primary().autoIncrement()
    team_id = Integer()
    name = String()
    timestamps = False


async def members_for(team_id: int):
    team = await Team.findOrFail(team_id)
    return await team.members().get()
```

## Performance and concurrency considerations

- Model instances use `__slots__`; common model metadata is collected once by `ModelMeta` when each model class is created.
- `TableDefinition` is a frozen, slotted dataclass; column definitions themselves are mutable fluent objects.
- Database I/O is asynchronous through Orionis connection abstractions. The ORM code does not define its own thread-safety guarantee or lock around its shared connection resolver.
- A model query returns all selected rows in a `Collection`; pagination limits the queried page and separately exposes the reported total.
- Eager loading batches relation resolution across a list of models. No explicit ORM-level memory or CPU bound is specified in the source.

## Compatibility notes

- The package declares `requires-python = ">=3.14"` in `pyproject.toml`. The source uses generic type parameter syntax such as `def hasMany[TRelated: "Model"](...)`; the supported minimum is set by package metadata.
- SQL type wrappers and schema descriptions are translated by Orionis's database compiler; this module does not promise that every database engine supports every logical type or query operation.
- Optional drivers are selected by the database engine: MySQL (`orionis[mysql]`), PostgreSQL (`orionis[pgsql]`), Oracle (`orionis[oracle]`), and SQL Server (`orionis[sqlserver]`). The source package metadata defines their dependency constraints.
> ⚠️ Not specified in source code: engine-specific SQL support and concurrency guarantees beyond the asynchronous connection interfaces.
