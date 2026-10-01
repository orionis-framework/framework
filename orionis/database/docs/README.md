# Orionis Database

> Async database connections, SQL compilation, schema creation, migrations, and seeders for Orionis applications.

## Table of contents

- [Requirements](#requirements)
- [Functional description](#functional-description)
- [API reference](#api-reference)
- [Usage examples](#usage-examples)
- [Performance and concurrency considerations](#performance-and-concurrency-considerations)
- [Compatibility notes](#compatibility-notes)

## Requirements

The database subsystem is included with `uv add orionis`. The base package declares `sqlalchemy[asyncio]>=2.0.54,<3.0` and `aiosqlite>=0.22.1`; SQLite uses the latter. Other drivers require the matching package extra: `orionis[mysql]` installs `aiomysql>=0.3.2` and `pymysql>=1.2.3`; `orionis[pgsql]` installs `asyncpg>=0.31.0` and `psycopg2-binary>=2.9.13`; `orionis[oracle]` installs `oracledb>=26.0.0`; `orionis[sqlserver]` installs `aioodbc>=0.5.0` and `pyodbc>=5.3.0`. These requirements and bounds are declared in `pyproject.toml`.

For example, run `uv add 'orionis[pgsql]'` for the PostgreSQL extra, or
`uv add 'orionis[database]'` for all optional database drivers.

## Functional description

`orionis.database` loads named connection configurations from the application, lazily creates asynchronous SQLAlchemy engines, and exposes Orionis connection and transaction APIs. `SQLCompiler` translates query plans from `orionis.orm.query` and schema descriptions from `orionis.orm.schema` into SQLAlchemy Core statements.

The module also provides fluent schema declarations, a migration runner, and a seeder runner. It directly uses `orionis.foundation.contracts.application`, `orionis.foundation.config.database.entities.database`, `orionis.container.providers.service_provider`, and `orionis.introspection.modules` for application configuration, provider registration, and module discovery. `ConnectionManagerProvider` installs the manager in `orionis.orm.resolver.ConnectionResolver`; `SchemaProvider` binds `ISchema` to `Schema`.

## API reference

Methods that perform I/O are asynchronous and must be awaited. Public imports from `orionis.database` are listed below; schema declarations are re-exported from `orionis.database.schema`, contracts from `orionis.database.contracts`, and the insert result from `orionis.database.entities`.

### `ConnectionManager`

`__init__(self, app: IApplication) -> None` reads `app.config("database")`, keeps the default name and connection configurations, and caches each connection after its first resolution. The application value may be the framework database configuration entity or a dictionary.

| Signature | Behavior |
|---|---|
| `connection(self, name: str | None = None) -> IConnection` | Resolves the named or default connection; raises `ConnectionNotFoundException` for an undeclared name. The resolved `Connection` is cached. |
| `addConnection(self, name: str, config: dict[str, Any]) -> None` | Registers or replaces a configuration. Raises `ValueError` for an empty name and `TypeError` when `config` is not a `dict`. An already cached connection continues using its prior configuration until disconnected. |
| `hasConnection(self, name: str) -> bool` | Reports whether a configuration is registered. |
| `getDefaultName(self) -> str` | Returns the default connection name. |
| `setDefaultName(self, name: str) -> None` | Changes the default; raises `ConnectionNotFoundException` unless the name is registered. |
| `disconnect(self, name: str | None = None) -> None` | Async: disposes and removes one cached connection, or all cached connections when `name` is `None`. |
| `configFor(self, name: str | None = None) -> dict[str, Any]` | Returns a registered configuration or raises `ConnectionNotFoundException`. |

The manager is bound as a container singleton by `ConnectionManagerProvider.register()`. `ConnectionManagerProvider.boot()` awaits the binding and calls `ConnectionResolver.setManager(...)` as a global ORM integration side effect.

### `Connection`

`__init__(self, name: str, config: dict[str, Any]) -> None` validates the configured driver during construction and lazily creates its async engine when first needed. It applies the configured `prefix` to physical table names and uses `SQLCompiler` to compile ORM query plans.

| Signature | Behavior |
|---|---|
| `getName(self) -> str` | Returns the registered connection name. |
| `select(self, query: SelectPlan | str, bindings: Mapping[str, Any] | None = None) -> list[dict[str, Any]]` | Async: executes a plan or raw SQL and materializes rows as dictionaries. Raw SQL may use named `:param` bindings. |
| `insert(self, plan: InsertPlan) -> InsertResult` | Async: executes an insert; reports an inserted key only for a single-row insert when the driver returns it. |
| `update(self, plan: UpdatePlan) -> int` / `delete(self, plan: DeletePlan) -> int` | Async: execute a plan and return the reported affected-row count. |
| `scalar(self, plan: SelectPlan) -> Any` | Async: returns the first column of the first row, or `None` if no row is produced. |
| `execute(self, sql: str, bindings: Mapping[str, Any] | None = None) -> int` | Async: executes raw data-modifying SQL and returns its affected-row count. |
| `statement(self, sql: str, bindings: Mapping[str, Any] | None = None) -> bool` | Async: executes raw SQL such as DDL and returns `True` when execution completes. |
| `createTable(self, table: TableDefinition, *, if_not_exists: bool = True) -> bool` | Async: compiles and runs table DDL. |
| `dropTable(self, name: str, schema: str | None = None, *, if_exists: bool = True) -> bool` | Async: drops a logical table name after applying the connection prefix. |
| `begin(self) -> None` / `commit(self) -> None` / `rollback(self) -> None` | Async: starts, commits, or rolls back the current transaction level. Starting inside an active transaction opens a savepoint. Missing active state or SQLAlchemy transaction failures raise `TransactionException`. |
| `transaction(self) -> ITransaction` | Returns an async context manager that commits on clean exit and rolls back when an exception escapes. |
| `inTransaction(self) -> bool` | Reports whether the current task has an active transaction level on this connection. |
| `disconnect(self) -> None` | Async: disposes the lazily created engine, if present. |

Compilation or execution errors from the public query methods are surfaced as `QueryException`. Driver imports missing when the engine is created raise `MissingDatabaseDependencyException`. An unsupported or absent driver name raises `UnsupportedDriverException` during `Connection` construction. Raw SQL uses SQLAlchemy `text()` statements with named bindings; the compiled plan path does not take raw bindings. `QueryException` reports the connection and SQLAlchemy error class without SQL text, bound values, or chained driver detail.

### `SQLCompiler`

`__init__(self, prefix: str = "") -> None` initializes `SQLCompiler`, which translates Orionis query plans and `TableDefinition` objects to SQLAlchemy Core statements. It caches SQLAlchemy table metadata and definitions per compiler instance.

| Signature | Return and behavior |
|---|---|
| `compileSelect(self, plan: SelectPlan) -> Select[Any] | CompoundSelect` | Compiles a select plan, including its unions. Raises `QueryException` for unknown columns or invalid clauses. |
| `supportsBatchInsert(plan: InsertPlan) -> bool` | Reports whether the plan can use the compiler's parameterized batch-insert path. |
| `compileInsert(self, plan: InsertPlan, *, parameterized: bool = False) -> Insert` | Compiles an insert plan. |
| `compileUpdate(self, plan: UpdatePlan) -> Update` | Compiles an update plan. |
| `compileDelete(self, plan: DeletePlan) -> Delete` | Compiles a delete plan. |
| `compileCreateTable(self, definition: TableDefinition, *, if_not_exists: bool = True) -> Executable` | Compiles create-table DDL. |
| `compileDropTable(self, name: str, schema: str | None = None, *, if_exists: bool = True) -> Executable` | Compiles drop-table DDL. |

The compiler maps Orionis `ColumnType` values to SQLAlchemy types, resolves qualified columns and aliases, and translates where clauses, joins, aggregates, sorting, paging, locking, and union plans. The exact SQL emitted is dialect dependent.

### Schema API: `Schema`, `TableCreation`, and `Blueprint`

`__init__(self, conn_manager: IConnectionManager) -> None` initializes `Schema` to perform schema operations through a connection manager. `connection(self, name: str | None = None) -> Self` selects one connection for this `Schema` instance; calling it a second time raises `ValueError`. Without an explicit selection, schema calls made during a migration use that migration's connection.

| Signature | Behavior |
|---|---|
| `create(self, name: str) -> TableCreation` | Returns the async context manager used to declare a table with a `Blueprint`; successful context exit creates the table. A qualified name may use `schema.table`. |
| `createFromDefinition(self, definition: TableDefinition) -> bool` | Async: creates a table from the supplied reusable definition. |
| `createFromModel(self, model: type[Model]) -> bool` | Async: creates a concrete model's current table definition. Raises `TypeError` if the argument lacks concrete model metadata. An explicit schema connection selection takes precedence over model connection metadata. |
| `drop(self, name: str) -> bool` | Async: drops a table, accepting `schema.table` for a non-default schema. |

`__init__(self, schema: Schema, name: str) -> None` initializes `TableCreation`, which implements `__aenter__(self) -> Blueprint` and `__aexit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None) -> bool`. On successful block exit it creates the table from the collected definitions; an exception prevents creation and propagates. `TableCreation` is not awaitable.

`Blueprint` is a slotted, mutable collector. Its public methods are `timestamps(self, *, timezone: bool = False) -> None`, `comment(self, text: str) -> Comment`, `foreignKey(self, column: str, ref_table: str, ref_column: str, name: str | None = None) -> ForeignKey`, `index(self, *columns: str, name: str | None = None, unique: bool = False) -> Index`, `primaryKey(self, *columns: str) -> PrimaryKey`, `unique(self, *columns: str, name: str | None = None) -> Unique`, `columns(self) -> tuple[ColumnDefinition, ...]`, and `definitions(self) -> tuple[ColumnDefinition | Comment | ForeignKey | Index | PrimaryKey | Unique, ...]`. `__getattr__(self, name: str) -> Callable[..., ColumnDefinition]` proxies known factories from `Column` and records their definitions; an unknown factory raises `AttributeError`. `timestamps` adds nullable `created_at` and `updated_at` datetime columns.

### `Column` factories and constraints

`Column` provides static factories which return ORM `ColumnDefinition` subclasses. Each factory receives a column `name`; parameters after it configure that SQL type. Their complete signatures are:

```python
id(name: str = "id") -> BigInteger
bigInteger(name: str) -> BigInteger
boolean(name: str, *, create_constraint: bool = False, constraint_name: str | None = None) -> Boolean
date(name: str) -> Date
dateTime(name: str, *, timezone: bool = False) -> DateTime
double(name: str, precision: int | None = None, *, asdecimal: bool = False, decimal_return_scale: int | None = None) -> Double
enum(name: str, *enums: str, constraint_name: str | None = None, create_constraint: bool = False, native_enum: bool = True, length: int | None = None, validate_strings: bool = False) -> Enum
float(name: str, precision: int | None = None, *, asdecimal: bool = False, decimal_return_scale: int | None = None) -> Float
integer(name: str) -> Integer
interval(name: str, *, native: bool = True, second_precision: int | None = None, day_precision: int | None = None) -> Interval
largeBinary(name: str, length: int | None = None) -> LargeBinary
matchType(name: str) -> MatchType
numeric(name: str, precision: int | None = None, scale: int | None = None, decimal_return_scale: int | None = None, *, asdecimal: bool = True) -> Numeric
numericCommon(name: str) -> NumericCommon
pickleType(name: str, protocol: int = 5, pickler: object | None = None, impl: object | None = None) -> PickleType
schemaType(name: str, schema_name: str | None = None) -> SchemaType
smallInteger(name: str) -> SmallInteger
string(name: str, length: int | None = 255, collation: str | None = None) -> String
text(name: str, length: int | None = None, collation: str | None = None) -> Text
time(name: str) -> Time
unicode(name: str, length: int | None = None, collation: str | None = None) -> Unicode
unicodeText(name: str, length: int | None = None, collation: str | None = None) -> UnicodeText
uuid(name: str, *, as_uuid: bool = True, native_uuid: bool = True) -> Uuid
strictArray(name: str, item_type: ColumnDefinition, *, as_tuple: bool = False, dimensions: int | None = None, zero_indexes: bool = False) -> StrictArray
strictBigInt(name: str) -> StrictBigInt
strictBinary(name: str, length: int | None = None) -> StrictBinary
strictBlob(name: str, length: int | None = None) -> StrictBlob
strictChar(name: str, length: int | None = None, collation: str | None = None) -> StrictChar
strictClob(name: str, length: int | None = None, collation: str | None = None) -> StrictClob
strictDecimal(name: str, precision: int | None = 10, scale: int | None = 2, decimal_return_scale: int | None = None, *, asdecimal: bool = True) -> StrictDecimal
strictDoublePrecision(name: str, precision: int | None = None, *, asdecimal: bool = False, decimal_return_scale: int | None = None) -> StrictDoublePrecision
strictInt(name: str) -> StrictInt
strictJson(name: str, *, none_as_null: bool = False) -> StrictJson
strictNChar(name: str, length: int | None = None, collation: str | None = None) -> StrictNChar
strictNVarChar(name: str, length: int | None = None, collation: str | None = None) -> StrictNVarChar
strictReal(name: str, precision: int | None = None, *, asdecimal: bool = False, decimal_return_scale: int | None = None) -> StrictReal
strictSmallInt(name: str) -> StrictSmallInt
strictTimestamp(name: str, *, timezone: bool = False) -> StrictTimestamp
strictVarBinary(name: str, length: int | None = None) -> StrictVarBinary
strictVarChar(name: str, length: int | None = 255, collation: str | None = None) -> StrictVarChar
```

Parameter meanings shared by those signatures: `name` identifies the column; `length`, `precision`, and `scale` are forwarded type dimensions; `collation` selects the string collation; `asdecimal` and `decimal_return_scale` configure numeric conversion; `enums` supplies allowed enum labels; `constraint_name` names a generated constraint; `create_constraint` controls check-constraint generation; `native_enum` and `validate_strings` are enum options; `native`, `second_precision`, and `day_precision` configure intervals; `protocol`, `pickler`, and `impl` configure pickled values; `schema_name` names the schema type; `item_type`, `as_tuple`, `dimensions`, and `zero_indexes` configure arrays; `as_uuid` and `native_uuid` configure UUID representation; `none_as_null` controls JSON `None` storage; and `timezone` controls timestamp/timezone metadata. The implementation forwards these values to the corresponding logical type or SQLAlchemy type construction.

`Blueprint` forwards these static factories dynamically. Returned column definitions inherit the fluent methods `primary()`, `nullable()`, `default(value)`, `unique()`, `index()`, `foreign(reference)`, `autoIncrement()`, and `comment(text)` from `ColumnDefinition` in `orionis.orm.schema.column`; those methods mutate the definition and return it. The `Timestamps` marker is recognized by the schema definition classifier, although it is not included in the `SchemaDefinition` type alias.

Table-level definition objects are `Comment(text: str)`, `ForeignKey(column: str, ref_table: str, ref_column: str, name: str | None = None)`, `Index(*columns: str, name: str | None = None, unique: bool = False)`, `PrimaryKey(*columns: str)`, `Unique(*columns: str, name: str | None = None)`, and `Timestamps(*, timezone: bool = True)`. `Schema` accepts these alongside column definitions. Repeated or conflicting primary-key declarations raise `ValueError` during table definition collection; a schema definition of an unsupported type raises `TypeError`.

### Migrations: `Migration`, `Migrator`, and `MigrationEvents`

Subclasses of the abstract `Migration` contract implement `async def up(self) -> None` and `async def down(self) -> None`. `__init__(self, app: IApplication, conn_manager: IConnectionManager) -> None` initializes `Migrator`, which discovers migrations under the application's `database/migrations` directory and applies them in filename order.

For both application and rollback, the migrator constructs each discovered
migration with `await app.build(migration_cls)`. Type-annotated constructor
dependencies are resolved by the application container. The runner then awaits
the migration's `up()` or `down()` method.

| `Migrator` signature | Behavior |
|---|---|
| `migrate(self, *, connection: str | None = None, events: MigrationEvents | None = None) -> list[str]` | Async: applies pending migrations and returns their names in run order. |
| `rollback(self, steps: int = 1, *, connection: str | None = None, events: MigrationEvents | None = None) -> list[str]` | Async: reverts the selected most recent batches and returns migration names most recent first. Raises `ValueError` if `steps` is not a positive integer, and `MigrationNotFoundException` if a recorded migration file is missing. |
| `reset(self, *, connection: str | None = None, events: MigrationEvents | None = None) -> list[str]` | Async: reverts recorded migrations. |
| `refresh(self, steps: int | None = None, *, connection: str | None = None, events: MigrationEvents | None = None) -> list[str]` | Async: rolls migrations back and applies them again, optionally limiting the rollback steps. |
| `fresh(self, *, connection: str | None = None, events: MigrationEvents | None = None) -> list[str]` | Async: clears migration and seeder history on the selected connection, then reapplies all migrations. |
| `status(self, *, connection: str | None = None) -> list[dict[str, Any]]` | Async: returns per-migration status records. |

Each migration step and its tracking record run within a transaction. An exception from `up` or `down` propagates; the failed migration is not recorded as successfully applied. A recorded migration whose module/class cannot be discovered raises `MigrationNotFoundException` when a rollback needs it.

After a successful rollback removes every recorded migration on the selected
connection, the migrator also drops that connection's `seeders` tracking table.
The next `migrate --seed` can then run seeders against the recreated schema.
A partial rollback preserves seeder tracking because seeded data may remain in
tables that were not reverted. Migration rollback does not directly undo seeder
data; each migration's `down()` determines what happens to its tables and data.
`fresh()` also clears seeder history when an earlier rollback already left the
`migrations` table without records.

`MigrationEvents` is a frozen, slotted, keyword-only dataclass with optional callbacks `on_start: Callable[[str], None] | None`, `on_success: Callable[[str, float], None] | None`, and `on_error: Callable[[str, float], None] | None`. Its `started(name: str) -> None`, `succeeded(name: str, elapsed: float) -> None`, and `failed(name: str, elapsed: float) -> None` methods invoke the corresponding callback only when one is set. `migrate`, `rollback`, `reset`, `refresh`, and `fresh` accept it; `status` does not.

`current_migration_connection() -> IConnection | None` returns the connection bound to the current migration context. `migration_connection_scope(connection: IConnection) -> Generator[None]` binds the connection for the duration of its `with` block and restores the previous binding on exit. The migrator uses this scope so unqualified schema and ORM operations inside a migration use the same connection as the migration transaction.

### Seeders: `Seeder`, `SeederRunner`, and `SeederEvents`

An application seeder is a subclass of `orionis.database.seeders.Seeder` with
`async def run(self) -> None`. Place it in `database/seeders/`; the bundled
`make:database-seeder` command generates the subclass. `SeederRunner` discovers
classes defined in these modules and orders them lexicographically by filename
stem. Each stem is the persisted identifier and must be unique, including
across subdirectories. Use ordered filename prefixes for dependencies.

The runner constructs each pending seeder with `await app.build(seeder_cls)`
before awaiting `run()`. A seeder may declare type-annotated constructor
dependencies that the application container can resolve.

| `SeederRunner` signature | Behavior |
|---|---|
| `__init__(self, app: IApplication, conn_manager: IConnectionManager) -> None` | Resolves the configured seeder directory and database connection. |
| `seed(self, *, connection: str | None = None, events: SeederEvents | None = None) -> list[str]` | Async: runs pending seeders and returns the names completed by this call in execution order. |

The selected connection has a `seeders` tracking table with an `id` primary
key, unique `seeder` name, `batch`, and `seeded_at` epoch timestamp. The runner uses the
tracking rows to select pending seeders. It claims each seeder through the
unique key before calling `run()` and commits the row and seed data in one
transaction. The completion timestamp is written after `run()` succeeds; a
failure rolls back both writes, so the seeder can be retried. A concurrent
claim cannot commit a second copy of the same name. A conflicting attempt
skips a seeder if its completed row is visible; other database errors propagate.
Each invocation with pending seeders uses the highest previous batch plus one.
The transaction scope also binds ordinary Orionis ORM operations in the seeder
to the selected connection. Transactional guarantees depend on the configured
database engine and on the operations performed by the seeder.

`SeederEvents` offers the same `on_start`, `on_success`, and `on_error`
callbacks as `MigrationEvents`. The CLI renders them through the existing
console progress output. Run `python reactor seed` for pending seeders alone,
or `python reactor migrate --seed` to migrate successfully before seeding;
both accept `--database/-d` for a named connection.

The bundled authorization seeder creates an administrator with the `admin`
role and `full_access` permission. Before its first run, edit the literal
administrator name, email, and password directly in
`database/seeders/s0000000001_create_admin_authorization.py`. The seeder hashes the
password through Orionis before storage. Once recorded, editing these values
does not rerun it; add a new seeder for later changes.

### `Transaction`, `InsertResult`, and exceptions

`__init__(self, connection: IConnection) -> None` initializes `Transaction`, which implements `__aenter__(self) -> ITransaction` and `__aexit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None) -> bool`. It begins on entry, commits on normal exit, rolls back on exceptional exit, and returns `False` so exceptions propagate. Start/commit/rollback failures raise `TransactionException`.

`InsertResult` is a frozen, slotted dataclass with fields `last_insert_id: Any` and `row_count: int`. The generated ID can be `None`, including when the driver does not return an ID for a multi-row insert.

All database exceptions derive from `DatabaseException`: `ConnectionNotFoundException` (connection name is absent), `MigrationNotFoundException` (a recorded migration cannot be found), `MissingDatabaseDependencyException` (a required driver package is missing), `QueryException` (query compilation or execution failed), `TransactionException` (invalid or failed transaction control), and `UnsupportedDriverException` (no dialect is registered for the configured driver).

### Contracts, providers, and dialect helpers

`IConnection`, `IConnectionManager`, and `ITransaction` in `orionis.database.contracts` specify the connection, manager, and transaction interfaces implemented by the concrete classes. `ISchema` specifies `connection`, `create`, `createFromDefinition`, `createFromModel`, and `drop`.

`ConnectionManagerProvider.register(self) -> None` registers `IConnectionManager` as a container singleton implemented by `ConnectionManager`; `boot(self) -> None` resolves it and installs it in the ORM resolver. `SchemaProvider.register(self) -> None` binds `ISchema` to `Schema` as a transient service, so connection selection is held by that resolved schema instance.

The module-level dialect helpers are public functions in `orionis.database.dialect`:

- `resolve_driver(config: dict[str, Any]) -> str` normalizes and validates the driver name; unsupported or missing values raise `UnsupportedDriverException`.
- `missing_dependency_error(driver: str, cause: ModuleNotFoundError, *, sync: bool = False) -> MissingDatabaseDependencyException` creates the install-hint exception for a missing async or synchronous DBAPI driver.
- `build_engine_url(config: dict[str, Any], *, sync: bool = False) -> URL` builds a SQLAlchemy URL for the selected async dialect, or blocking DBAPI dialect when `sync=True`.
- `engine_options(config: dict[str, Any], *, sync: bool = False) -> dict[str, Any]` returns engine options, including configured in-memory SQLite pooling and driver-specific connect arguments where applicable.
- `configure_engine(engine: AsyncEngine, config: dict[str, Any]) -> None` installs driver-specific engine connection configuration.

The recognized driver keys are `sqlite`, `mysql`, `pgsql`, `oracle`, and `sqlserver`. Dialect helper behavior outside these documented public helpers is not part of the ORM-facing API.

## Usage examples

Each example is self-contained. The SQLite in-memory connection and schema require the base `orionis` installation. Run them with Python 3.14+.

### Create a table and execute a query

```python
import asyncio

from orionis.database.connection_manager import ConnectionManager
from orionis.database.schema import Column, Schema


class App:
    def config(self, key: str) -> dict:
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {"driver": "sqlite", "database": ":memory:"},
            },
        }


async def main() -> None:
    manager = ConnectionManager(App())
    schema = Schema(manager)
    async with schema.create("users") as table:
        table.integer("id").primary().autoIncrement()
        table.string("name")
    connection = manager.connection()
    await connection.execute(
        "INSERT INTO users (name) VALUES (:name)", {"name": "Ada"},
    )
    rows = await connection.select("SELECT name FROM users")
    print(rows)
    await manager.disconnect()


asyncio.run(main())
```

### Handle a missing connection

```python
from orionis.database.connection_manager import ConnectionManager
from orionis.database.exceptions import ConnectionNotFoundException


class App:
    def config(self, key: str) -> dict:
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {"driver": "sqlite", "database": ":memory:"},
            },
        }


manager = ConnectionManager(App())
try:
    manager.connection("archive")
except ConnectionNotFoundException:
    print("The archive connection is not configured.")
```

### Integrate schema creation with the ORM

```python
import asyncio

from orionis.database.connection_manager import ConnectionManager
from orionis.database.schema import Schema
from orionis.orm import Integer, Model, String
from orionis.orm.resolver import ConnectionResolver


class App:
    def config(self, key: str) -> dict:
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {"driver": "sqlite", "database": ":memory:"},
            },
        }


class User(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    timestamps = False


async def main() -> None:
    manager = ConnectionManager(App())
    ConnectionResolver.setManager(manager)
    try:
        await Schema(manager).createFromModel(User)
        user = await User.create({"name": "Ada"})
        print(user.name)
    finally:
        ConnectionResolver.clear()
        await manager.disconnect()


asyncio.run(main())
```

## Performance and concurrency considerations

- `ConnectionManager` caches one `Connection` per resolved name; each connection lazily creates and retains an async engine until `disconnect()` disposes it.
- `Connection`, `ConnectionManager`, `Schema`, `Transaction`, and `Blueprint` declare `__slots__` for their own state. `Blueprint` has no instance dictionary; `InsertResult` and `MigrationEvents` are frozen, slotted dataclasses whose fields cannot be reassigned after construction.
- Raw SQL statements are cached by SQL string in an `lru_cache` capped at 256 entries.
- `Connection` uses a `ContextVar` and the current asyncio task to track transaction state. Nested transaction calls use savepoints on the same raw connection. A child task inheriting an active transaction context cannot use that transaction: connection operations raise `TransactionException`, and the query must run in the task that opened the transaction.
- In-memory SQLite engine options use a pool size of one and no overflow. SQLAlchemy engine settings and pool behavior for other configurations come from the selected dialect and provided configuration.
- `select` materializes result mappings into a list of dictionaries before releasing its acquired connection. No explicit streaming API or ORM-module memory/CPU limit is specified here.
- Schema and migration operations perform database I/O asynchronously. Each migration and its tracking write are grouped in a transaction.

## Compatibility notes

- `pyproject.toml` declares `requires-python = ">=3.14"`. It also declares SQLAlchemy `>=2.0.54,<3.0`, `aiosqlite>=0.22.1`, and the driver constraints listed under [Requirements](#requirements).
- The async SQLAlchemy dialects configured in source are SQLite (`sqlite+aiosqlite`), MySQL (`mysql+aiomysql`), PostgreSQL (`postgresql+asyncpg`), Oracle (`oracle+oracledb_async`), and SQL Server (`mssql+aioodbc`). Sync DBAPI URLs are available from `build_engine_url(..., sync=True)` for supporting framework consumers.
- Database configuration must include a recognized `driver`; server drivers use connection values from the database configuration, while SQLite uses the `database` path. Oracle can use configured DSN/TNS-name fields. Additional per-driver behavior is implemented in `orionis.database.dialect`.
> ⚠️ Not specified in source code: exact SQL support by database engine and operation. It depends on SQLAlchemy and the configured database server; the module does not declare a support matrix.
