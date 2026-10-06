# orionis.database

> Manage named asynchronous connections, compile ORM query/schema descriptions, and run transactional migrations and seeders.

## Table of contents

- [Requirements](#requirements)
- [Functional overview](#functional-overview)
- [Module structure](#module-structure)
- [API reference](#api-reference)
- [Usage examples](#usage-examples)
- [Design characteristics](#design-characteristics)
- [Performance and concurrency](#performance-and-concurrency)
- [Compatibility notes](#compatibility-notes)
- [Verification and limitations](#verification-and-limitations)

## Requirements

The project declares Python **>=3.14** in [pyproject.toml](../../../pyproject.toml).
SQL execution uses SQLAlchemy **Core async**, not its ORM Session/declarative
mapping. SQLite's aiosqlite driver is a core dependency. Configure a driver
and database for each connection; a missing/unsupported driver is not inferred
from the connection's name or a URL.

| Orionis driver | Async SQLAlchemy dialect | Sync helper dialect | Declared packages |
| --- | --- | --- | --- |
| sqlite | sqlite+aiosqlite | sqlite | Core aiosqlite>=0.22.1; sync sqlite3 is standard library. |
| mysql | mysql+aiomysql | mysql+pymysql | Extra mysql: aiomysql>=0.3.2, pymysql>=1.2.3. |
| pgsql | postgresql+asyncpg | postgresql+psycopg2 | Core/extra pgsql: asyncpg>=0.31.0; extra psycopg2-binary>=2.9.13. |
| oracle | oracle+oracledb_async | oracle+oracledb | Extra oracle: oracledb>=26.0.0. |
| sqlserver | mssql+aioodbc | mssql+pyodbc | Extra sqlserver: aioodbc>=0.5.0, pyodbc>=5.3.0; a usable ODBC installation is separate. |

The database extra groups all optional database driver packages. Core SQLAlchemy
is declared as sqlalchemy[asyncio]>=2.0.54,<3.0. Installation hints in
[dialect.py](../dialect.py) use uv add; no package or extra was installed during
this task. See [compatibility](#compatibility-notes) for lock and installed
versions, which are not supported minimums.

[ConnectionManager](../connection_manager.py) requires app.config("database")
to provide the framework Database entity or a mapping with default/connections.
Bare Connection and compiler usage require no booted application. ORM queries
need the [ConnectionResolver](../../orm/resolver.py) integration; the actual
[provider](../provider.py) installs it on boot. Schema needs a connection manager.
Migration/seeder runners additionally need application paths/build and importable
classes. Network configuration, server availability and privileges belong to
the chosen driver/deployment; they were not exercised here.

Use only owned temporary databases for runnable examples. Migrator reset,
refresh, fresh, rollback and schema drop can remove data. The CLI integration
is described, not authorization to operate on the checkout's configured DB.

## Functional overview

`orionis.database` resolves named connections, creates async engines lazily,
translates ORM query plans and schema definitions into SQLAlchemy Core, and
executes queries with task-owned transactions/savepoints. It also collects
table declarations and discovers, tracks, applies or reverts migrations/seeders.

### Direct integrations

The owning implementation is [Connection](../connection.py), with
[SQLCompiler](../compiler.py) and [dialect helpers](../dialect.py). Input plans
and table/column metadata belong to [orionis.orm](../../orm/docs/README.es.md),
with actual definitions in [expressions.py](../../orm/query/expressions.py)
and [TableDefinition](../../orm/schema/table.py). This manual covers their
consumption, not the full ORM API.

[ConnectionManagerProvider](../provider.py) binds IConnectionManager as a
container singleton and sets ConnectionResolver on boot.
[SchemaProvider](../schema_provider.py) binds ISchema transient; its inherited
boot is a no-op and does not globally pin Schema. Runners use
[ModuleInspector](../../introspection/modules/inspector.py) /
[ReflectionModule](../../introspection/modules/reflection.py) and app.build.
The [migration context](../migrations/context.py) lets unqualified Schema/ORM
operations share the selected connection, including during seeders.

### Execution boundaries

Public SQL execution is asynchronous; connection resolution, plan compilation,
URL/options building, schema collection and discovery/imports are synchronous.
A Connection object is not itself an open DB session: first use creates its
engine, and each non-transaction operation uses an engine.begin context.
This is a transaction context that commits on success, despite the private
_acquire docstring's term "autocommit".

Explicit transaction state remembers the asyncio Task that began it. A child
inherits the ContextVar reference but cannot use an active parent's transaction.
The migration-context reference has no equivalent ownership check of its own;
Connection's check still applies to queries. Neither async methods nor a pool
alone establish thread/cross-loop safety for the whole module.

## Module structure

All 39 Python files and the one Blueprint typing stub were inspected. There
are no SQL templates or other non-Python runtime resources in the module.

| Files or group | Responsibility and primary public symbols |
| --- | --- |
| [__init__.py](../__init__.py) | Lazy exports of connections/compiler, Migration/Migrator, seeder APIs, Transaction and database exceptions. |
| [connection.py](../connection.py), [connection_manager.py](../connection_manager.py), [transaction.py](../transaction.py) | Connection, ConnectionManager, Transaction. |
| [compiler.py](../compiler.py), [dialect.py](../dialect.py) | SQLCompiler and five public driver/configuration helper functions. |
| [contracts](../contracts/__init__.py) | IConnection, IConnectionManager, ITransaction exports; defining modules also contain ISchema, IMigrator and Migration. |
| [entities/result.py](../entities/result.py), [entities/__init__.py](../entities/__init__.py) | InsertResult and its reexport. |
| [exceptions.py](../exceptions.py) | DatabaseException plus six subclasses. |
| [provider.py](../provider.py), [schema_provider.py](../schema_provider.py) | ConnectionManagerProvider, SchemaProvider. |
| [schema/schema.py](../schema/schema.py), [schema/table_creation.py](../schema/table_creation.py), [schema/blueprint.py](../schema/blueprint.py), [schema/blueprint.pyi](../schema/blueprint.pyi) | Schema, pending TableCreation, mutable Blueprint and editor-only factory signatures. |
| [schema/column.py](../schema/column.py), [schema/__init__.py](../schema/__init__.py) | Forty Column static factories and schema declaration exports. |
| [schema/comment.py](../schema/comment.py), [schema/foreign.py](../schema/foreign.py), [schema/index.py](../schema/index.py), [schema/primary.py](../schema/primary.py), [schema/timestamp.py](../schema/timestamp.py), [schema/unique.py](../schema/unique.py) | Comment, ForeignKey, Index, PrimaryKey, Timestamps, Unique. |
| [schema/definitions.py](../schema/definitions.py), [schema/definition_bucket.py](../schema/definition_bucket.py) | SchemaDefinition type alias, DefinitionBucket collection auxiliary. |
| [migrations](../migrations/__init__.py) | Migrator reexport; migrator.py, events.py and context.py control discovery/tracking, MigrationEvents/NO_EVENTS and context functions. |
| [seeders](../seeders/__init__.py) | Seeder, SeederRunner, SeederEvents; events.py reuses MigrationEvents rather than defining a second dataclass. |

Every source, including all six initializers, has a linked owner entry in the
[literal appendix](#literal-declarations). No directory outside this module's
direct docs was edited for documentation.

## API reference

Behavior is organized by owning API below. The [literal declarations](#literal-declarations)
retain exact headers, decorators, annotations, default expressions, fields,
exports and type alias. **No-body headers and stub bodies are reference, not
executable examples.** Generated/inherited operations are identified separately.

### Imports and package exports

[orionis.database](../__init__.py) resolves names from its _EXPORTS mapping on
first access and caches them through [_resolve_export](../../_exports.py).
Reading __all__ or dir does not execute every target module. Resolving an export
can import SQLAlchemy/ORM/configuration dependencies; do not indiscriminately
import every symbol to discover the API.

Root exports do not include Schema, Column, Blueprint, InsertResult,
MigrationEvents or providers. Use their defining modules or the actual selective
subpackages. Schema's package exports Blueprint, Column and six marker classes,
not Schema/TableCreation/DefinitionBucket/SchemaDefinition. Contracts exports
only IConnection/IConnectionManager/ITransaction. Migrations exports Migrator
only; seeders exports Seeder/SeederEvents/SeederRunner; entities exports InsertResult.
Unknown lazy export raises AttributeError.

Imported library names and TYPE_CHECKING-only SqlSource/SourceMap in compiler.py
are not independent runtime database APIs. Private helpers/states are described
where they decide public behavior. Named DefinitionBucket is an accessible
integration auxiliary, not an exported schema operation.

### Dialect functions and configuration

Source/import: [orionis.database.dialect](../dialect.py).

| Function | Parameters, result, conditions and effects |
| --- | --- |
| resolve_driver(config) | Read driver, convert to string, strip/lower, require sqlite/mysql/pgsql/oracle/sqlserver. Return normalized string or raise UnsupportedDriverException, including a missing driver. It does not validate an entire connection payload. |
| build_engine_url(config, *, sync=False) | Return a structured SQLAlchemy URL using the async/sync map. No engine or service connection is opened. Invalid numeric ports and malformed mapping values can propagate built-in errors. |
| engine_options(config, *, sync=False) | Return a new dict with echo=False, future=True, hide_parameters=True plus the driver-specific options described below. Unsupported driver propagates. |
| configure_engine(engine, config) | Install synchronous Core engine event listeners for applicable SQLite/MySQL session setup. Return None; no explicit connect occurs here, but listeners run on subsequent engine use. Repeated registration is not guarded as an idempotent operation. |
| missing_dependency_error(driver, cause, *, sync=False) | Build and return MissingDatabaseDependencyException with package/uv extra hint; does not raise it itself. Unknown driver uses the fallback package name; cause text is included. |

Configuration is trusted engine configuration, not a generic SQL input sanitizer:

- SQLite uses database, ignoring the informational url key. Missing/None/empty
  database becomes :memory:. Other strings are literal URL paths; a file: URI
  is not explicitly enabled as a URI driver option. File paths are relative
  to the process's working directory unless absolute.
- For :memory:/empty SQLite, async uses AsyncAdaptedQueuePool and sync uses
  QueuePool, each pool_size=1/max_overflow=0 with check_same_thread=False. It is
  exclusive checkout, **not the former StaticPool behavior**. File-backed
  configuration leaves SQLAlchemy's default pool selection/options in place.
- Async pgsql forwards trimmed sslmode as ssl and search_path/charset as
  server_settings search_path/client_encoding. Sync helpers do not apply those
  asyncpg arguments. Username/password/host/database are trimmed optional text;
  a truthy port is converted with int. No server connection is tested by a URL.
- MySQL adds charset/unix_socket URL query keys. SET NAMES/optional COLLATE
  require ASCII-word identifiers; invalid values are omitted from those session
  statements. Non-None strict selects the exact strict/relaxed sql_mode preset
  using boolean-like normalization, not a freely supplied SQL mode.
- SQL Server query keys include configured/default ODBC Driver 18 for SQL Server,
  Encrypt and TrustServerCertificate normalized to yes/no. Oracle uses dsn or
  tns_name in connect_args with credential-only URL, otherwise SID or service_name.
- SQLite connect listeners set isolation_level=None, apply configured PRAGMAs,
  and a begin listener issues BEGIN so root transactions encompass savepoints
  and DDL. foreign_key_constraints becomes ON/OFF; positive int busy_timeout
  is forwarded; journal_mode/synchronous use enum.value or strings.
- Async MySQL installs a connection-local binary escaper when the driver
  connection exposes a callable escape method. Bytes/bytearray/memoryview become
  hex _binary literals; other values use the original escaper. No global driver
  module is patched. Real MySQL execution was not performed here.

### ConnectionManager

Source/import: [orionis.database.connection_manager.ConnectionManager](../connection_manager.py),
also root-exported. It implements IConnectionManager with slots. The constructor
calls app.config("database"); a ConfigDatabase entity is converted with toDict,
otherwise the returned payload is used directly. It lowercases str(default),
shallow-copies the connections mapping, and begins with an empty object cache.
Missing/malformed configuration can raise TypeError/KeyError/AttributeError;
there is no fallback entity when the section is absent.

| Method | Result, mutability and verified restrictions |
| --- | --- |
| connection(name=None) | Use name or default (empty string also selects default), return cached Connection or construct/cache one without opening its engine. Missing or None-valued config raises ConnectionNotFoundException. Explicit names are not stripped/lowercased. |
| addConnection(name, config) | Require a nonblank string (ValueError, including non-string) and actual dict (TypeError). Retain the provided name unchanged and dict by reference; return None. Replace config without evicting a cached Connection. |
| hasConnection(name) | Membership of configured names, even a None-valued entry; no validation/engine creation. |
| getDefaultName() | Return current default string. |
| setDefaultName(name) | Require configured-name membership or ConnectionNotFoundException; return None. No normalization/disconnection. |
| configFor(name=None) | Return the actual stored config dict, not a copy; missing/None config raises ConnectionNotFoundException. Mutations affect future constructions, not a Connection's shallow-copied top-level config. |
| await disconnect(name=None) | Pop one cached object then await its disconnect, or snapshot/clear all cached objects and dispose them sequentially. Return None. Configurations/default remain registered. Disposal errors can stop iteration after the cache was cleared. |

Dictionary-key errors propagate for unhashable inputs. A cached object's
configuration/prefix is captured when constructed; disconnecting only that
Connection directly does not remove it from the manager's cache. Replacement
does not close objects held by other callers. This module has no public remove
connection, cache size limit or cross-thread synchronization for the manager.

### Connection query and lifecycle API

Source/import: [orionis.database.connection.Connection](../connection.py),
root-exported, implementing slotted IConnection. Constructor(name, config)
validates driver eagerly, shallow-copies config, captures a compiler prefix,
creates a transaction ContextVar, and leaves engine=None. It does not verify
credentials, connectivity or every configuration key.

| Method | Parameters and awaited/direct result |
| --- | --- |
| getName() | Return the captured name. |
| await select(query, bindings=None) | A string uses cached SQLAlchemy text and bindings; a SelectPlan uses SQLCompiler and ignores raw bindings. Materialize rows as list[dict] before releasing the connection. |
| await insert(plan) | Compile InsertPlan and optionally pass homogeneous rows as executemany parameters. Return InsertResult; generated key is read only for a single-row insert when the result supplies a primary key. Multirow last_insert_id is None. |
| await update(plan) / delete(plan) | Compile the plan, execute, return int(rowcount or 0), including a negative driver rowcount if reported. Empty/missing filters do not add a safeguard against all-row mutation. |
| await scalar(plan) | Return first column of the first row, or None. This API accepts a SelectPlan, not the select method's raw-string overload. |
| await execute(sql, bindings=None) | Execute raw SQL text with optional named :param mappings; return int(rowcount or 0). |
| await statement(sql, bindings=None) | Execute raw SQL/DDL, discard its result and return True on completion. |
| await createTable(table, *, if_not_exists=True) | Compile TableDefinition, then run Table.create via run_sync with checkfirst. This also creates indexes from metadata. Return True even when an existing table was kept. |
| await dropTable(name, schema=None, *, if_exists=True) | Apply prefix to logical name, compile/drop, return True. Unlike Schema.drop, a dotted name is not parsed into a separate schema argument here. |
| transaction() | Return a new Transaction manager; no transaction is begun yet. |
| inTransaction() | True only for the owning current asyncio Task with a nonempty transaction stack. Called without a running loop, current_task can raise RuntimeError. |
| await disconnect() | If an engine exists, clear the field and await engine.dispose. Return None. Compiler/config/transaction context are not reset; subsequent engine use can create another engine. |

Parameters are passed without general type coercion or protection of identifiers.
Use bindings for data values and only trusted raw SQL. _run passes parameters
when truthy; otherwise it invokes execute without a mapping. TextClause parsing
is cached by SQL string, not by parameter values. No streaming-result API is
declared: select materializes every row.

Outside an explicit transaction, each operation uses engine.begin; successful
exit commits and failure rolls back. createTable's existence check and actual
create are not a database-level atomic declaration. Prefixes affect compiled
tables/constraints, not arbitrary raw SQL written by the caller.

First engine creation uses URL/options, catches ModuleNotFoundError for a
missing DBAPI package and raises MissingDatabaseDependencyException, then
registers session listeners. Other dependency/URL/acquisition/configuration
failures are not universally translated. _run and createTable's run_sync catch
SQLAlchemyError and raise a sanitized QueryException from None with connection
name and exception class, not SQL/values/driver message. Compilation, acquisition,
context-exit, row conversion and callbacks have their own propagation paths.
The docstrings' broad QueryException descriptions are not an exhaustive wrapper.

### Transactions and task ownership

Source: [Connection](../connection.py),
[orionis.database.transaction.Transaction](../transaction.py).
begin/commit/rollback are async and return None:

- begin opens a dedicated connection/root transaction when no state exists;
  another begin in that owner task pushes begin_nested savepoint. Failure of
  root begin closes the just-opened connection before re-raising.
- commit/rollback require state and a nonempty stack, otherwise TransactionException.
  They pop the innermost level before awaiting its completion. Finally, an empty
  stack clears the ContextVar and closes the raw connection.
- SQLAlchemy failures in those operations become TransactionException with a
  chained driver error/message. This is different from sanitized query errors.
  Cleanup failure and cancellation can propagate; no shield/transaction-level
  retry or automatic restoration of a popped level is implemented.
- A child retaining an active owner's state gets TransactionException on query
  or transaction control; inTransaction returns False there. After the original
  state has settled, a child discards that inherited state and can acquire anew.

Transaction(connection) stores the reference with no type guard. __aenter__
awaits begin and returns **self**, not the connection. Run queries through the
connection inside the block. __aexit__ commits when exc_type is None, otherwise
rolls back, and returns False. It has no independent entered/single-use guard
or query forwarding. An exit/cleanup failure can replace the block's exception.
Nested Transaction contexts operate the connection's savepoint stack.

The ContextVar holds mutable stack state shared by inheritance, guarded by task
identity, not deep copying. SQLite memory pool serializes independent checkout
with one connection; child operations within an active parent do not silently
join it. Do not treat this as cross-loop/thread safety or transactional DDL
support on every database engine.

### SQLCompiler

Source/import: [orionis.database.compiler.SQLCompiler](../compiler.py), root-exported.
Constructor(prefix="") captures prefix or empty, MetaData and table/definition
caches. It returns SQLAlchemy Core statement objects, not SQL strings and not
query results. Compilation itself has no DB I/O.

| Method | Result and controlling conditions |
| --- | --- |
| compileSelect(plan) | Return Select or CompoundSelect. Compile projection, filtering, joins, grouping/having, ordering/paging, locks and unions. Aggregate plans ignore distinct/order/limit/offset; COUNT permits *, other aggregate kinds require a column. |
| supportsBatchInsert(plan) | Static bool predicate: more than one row, equal row key sets, no ClauseElement values, and the specific declared-column key-set guard. This is not full validation of every row/column or a guarantee of backend success. |
| compileInsert(plan, *, parameterized=False) | Empty values -> QueryException. Parameterized=True returns an unpopulated Insert for separately supplied parameter groups; otherwise embed single/multirow values. The caller is responsible for matching the parameterized path with actual parameters. |
| compileUpdate(plan) | Empty values -> QueryException; apply optional where expression without imposing a required filter. |
| compileDelete(plan) | Apply optional where expression without a required filter. |
| compileCreateTable(definition, *, if_not_exists=True) | Return CreateTable using cached/resolved table metadata and requested flag. Connection.createTable uses its element's create method, not merely that DDL text. |
| compileDropTable(name, schema=None, *, if_exists=True) | Return DropTable with physical prefix/schema; use cached table when present, otherwise temporary MetaData. Does not invalidate the compiler cache. |

Input structures and enums are defined in [query expressions](../../orm/query/expressions.py);
they are not redefined by database. Qualified identifiers resolve aliases/logical
sources; missing sources/columns, invalid comparison/join operators or clause
kinds, BETWEEN without exactly two bounds, empty inserts/updates and unmapped
column types raise explicit QueryException. Other toolkit/type errors propagate.

Joins support INNER/LEFT/FULL/CROSS and RIGHT via swapped outer-join sides.
Subquery joins require aliases; non-CROSS joins require ON conditions. Nested
predicates use explicit grouping; runs of AND/OR are combined left to right.
EXISTS/subqueries can reference outer sources. Unions flatten runs of the same
kind, grouping mixed kinds through derived tables. Dialects determine whether
the requested SQL/locking/type can actually execute.

RawExpression uses trusted SQL with bound values. An unbound aliased fragment
uses literal_column.label; bound aliased fragments preserve binding via a typed
scalar subquery. No general validation of user-authored raw SQL is provided.
Schemas with no declared columns are backfilled from referenced names **before**
aliases are constructed; plain schemaless SELECT * uses a literal wildcard.

Tables are cached by schema plus prefixed name. Reusing the same nonempty
TableDefinition identity reuses metadata; a different declared definition rebuilds
it; an empty definition reuses cached metadata when available. Same-object column
mutation is not an invalidation guarantee. Caches are unbounded per compiler and
remain after physical table drop/disconnect. Foreign-reference placeholder tables
use prefixed names without schema-qualified cross-schema handling here.

The type-builder map has observable restrictions:

- BigInteger-family autoincrement primary keys receive an Integer SQLite variant.
  Column-level primary keys force nonnullable SQL metadata. Defaults are client
  defaults and, for non-None non-callables, also server_default literal expressions.
- Enum compilation explicitly uses native_enum=False and create_constraint=False;
  factory enum flags/length/validate_strings are not all forwarded by the compiler.
  PickleType forwards protocol, not its custom pickler/impl options.
- StrictArray, MatchType, NumericCommon and SchemaType have factories but no entry
  in _TYPE_BUILDERS; compilation raises QueryException. Factory availability alone
  does not certify DDL support. Numeric/string/time behavior remains dialect-dependent.

### Schema and TableCreation

Source/import: [orionis.database.schema.schema.Schema](../schema/schema.py),
[TableCreation](../schema/table_creation.py). Schema implements ISchema and
captures a manager; it does not open a connection in its constructor.

| Method | Result, selection rules and errors |
| --- | --- |
| connection(name=None) | Set selection exactly once and return Self; second call raises ValueError, including after connection(None). No connection-name validation occurs until resolution. Explicit None selects manager default and disables migration-context fallback. |
| create(name) | Return TableCreation immediately. Only successful async-with exit collects/builds/creates the table. **TableCreation has no __await__**; await schema.create is not supported. |
| await createFromDefinition(definition) | Resolve selected/migration/default connection and delegate createTable; return bool. No independent definition type guard. |
| await createFromModel(model) | Require ModelMeta and concrete own __meta__ (TypeError otherwise), use metadata.table. Explicit selection overrides model.connection; absent selection and absent model connection can use migration context. Return delegated bool. |
| await drop(name) | Parse logical table or one schema.table component and delegate dropTable on the selected connection; return bool. |

Schema parses names with partition: empty schema/name, empty second component
or additional dots raise ValueError. It does not provide a whitelist of every
SQL identifier or strip arbitrary names. Duplicate column names in collection
overwrite by name; multiple table comments leave the last one. Column-level and
explicit PrimaryKey declarations conflict with ValueError; empty PrimaryKey can
reach IndexError. Unsupported definition kind raises TypeError.

TableCreation.__aenter__ creates/stores a fresh Blueprint and returns it.
__aexit__ calls Schema._createTable only when exc_type is None and a blueprint
exists; return False, preserving exceptions. There is no single-use/reentry guard,
resource close or await protocol. Sequential entry replaces its collector; shared
concurrent use is not coordinated. Exit before entry simply does not create.

### Blueprint, Column and declaration markers

Source/import: [Blueprint](../schema/blueprint.py), [Column](../schema/column.py)
and marker classes from [schema/__init__.py](../schema/__init__.py).
Blueprint is slotted with mutable column/constraint lists and a factory cache.
Its __getattr__ looks up callable attributes on Column, caches a wrapper per
name, appends each produced column and returns it. Unknown/non-callable names
raise AttributeError; wrapper errors propagate. It is not a separate fixed
whitelist of valid SQL column factories. Already returned columns remain mutable.

| Blueprint method | Implemented effect/result |
| --- | --- |
| timestamps(*, timezone=False) | Add nullable created_at/updated_at dateTime columns; return None, not a fluent Self. |
| comment(text) | Normalize/store Comment in constraints and return that object. |
| foreignKey(column, ref_table, ref_column, name=None) | Add/return ForeignKey, wrapping a single-column CompositeForeignKey. |
| index(*columns, name=None, unique=False) | Add/return Index, wrapping TableIndex. |
| primaryKey(*columns) | Add/return PrimaryKey carrying a tuple, not mark existing column objects immediately. |
| unique(*columns, name=None) | Add/return Unique, wrapping UniqueConstraint. |
| columns() | Return a tuple snapshot of column references, in recorded order. |
| definitions() | Return column references followed by constraint references, not globally interleaved declaration order. |

Column's forty static methods construct a new ORM ColumnDefinition subtype,
set its name and return it. id additionally marks primary/autoincrement.
They do not write DDL. Families include integers, strings/text, booleans,
dates/time, numerics, enum/UUID/binary/pickle and Strict SQL type variants.
Their exact defaults, keyword-only bools and *enums are in the appendix.

Shared parameters: name is assigned as the column identifier; length/collation,
precision/scale, asdecimal/decimal_return_scale configure logical types;
enum labels and constraint/native/validation flags configure Enum;
timezone configures dateTime/timestamp; native/second_precision/day_precision
configure interval; protocol/pickler/impl configure PickleType;
schema_name configures SchemaType; item_type/as_tuple/dimensions/zero_indexes
configure StrictArray; as_uuid/native_uuid configure UUID; none_as_null
configures StrictJson. The factories forward values to ORM type constructors,
whose restrictions and compiler omissions are distinct from runtime annotations.

Inherited [ColumnDefinition](../../orm/schema/column/definition.py) methods
primary/nullable/default/unique/index/foreign/autoIncrement/comment mutate the
same definition and return it; hasDefault distinguishes an explicitly set
default from absence. Those methods are not declarations in this module.

Marker constructors store mutable public attributes with no slots/frozen guard:
Comment normalizes NFC, replaces ASCII controls, collapses whitespace and stores
trimmed text; invalid non-text input can raise TypeError. ForeignKey.foreign,
Index.constraint and Unique.constraint reference ORM constraint dataclasses.
PrimaryKey.columns is a tuple, including empty input. Timestamps.timezone is
stored without validation and defaults **True**, unlike Blueprint.timestamps.
The internal classifier handles Timestamps, although SchemaDefinition's actual
union omits it. The union is a PEP 695 type alias, not a validation constructor.

DefinitionBucket is a slotted mutable auxiliary with fresh columns/kwargs dicts
and primary_columns/unique_constraints/foreign_keys/indexes lists. Its public
constructor does no validation; schema classification fills those references.
It is not exported by schema's initializer.

### Blueprint typing surface

[blueprint.pyi](../schema/blueprint.pyi) supplies type-checker/editor signatures
for the dynamic Column factories and six explicit convenience methods. It is
not imported/executed at runtime. Runtime behavior is owned by blueprint.py and
column.py, not a method body of Ellipsis in the stub. The stub does not declare
the runtime constructor, columns(), definitions() or __getattr__.

Its full literal source is reproduced as a reference block alongside Python
owner declarations. No annotation was inferred or added to installed code.
Availability in a stub does not prove that SQLCompiler supports that SQL type.

### Migration, Migrator and tracking

Source/import: [Migration](../contracts/migration.py), root-exported abstract
ABC with async up/down, and [Migrator](../migrations/migrator.py), implementing
IMigrator. Constructor(app, conn_manager) stores both and an initially empty
discovery cache; no database is opened until an operation.

| Migrator method | Awaited result and limits |
| --- | --- |
| migrate(*, connection=None, events=None) | Ensure tracking table, read recorded names, discover/sort pending classes and apply each in order. Return completed names. No pending classes -> []. Assign current maximum batch plus one. |
| rollback(steps=1, *, connection=None, events=None) | Require positive int excluding bool (ValueError). Revert latest distinct batches, newest recorded id first. More steps than batches selects all. Return reverted names. |
| reset(*, connection=None, events=None) | Revert every recorded migration, newest first; return names. No recorded history -> []. |
| refresh(steps=None, *, connection=None, events=None) | reset or validated rollback, then migrate; return reapplied names. Not one transaction covering the whole sequence. |
| fresh(*, connection=None, events=None) | reset through each migration's down, drop migrations tracking, clear seeder history when needed, then migrate. It does not generically wipe every unrelated application table. |
| status(*, connection=None) | Ensure tracking table (a write), read history and return discovered migration/ran/batch records. Recorded names absent from discovery are not separate status rows. |

Discovery uses app.path("database_migrations"), app.basePath and reflection.
It accepts locally defined Migration subclasses, not imported reexports, and
sorts by final module/file stem. Missing directory caches {}; each stem must
be unique, including across subdirectories/multiple classes, or ValueError.
The code does not separately filter abstract subclasses before app.build.
The instance retains discovery, including an empty result, with no public refresh.
Package initializers are normalized by ModuleInspector to package names;
the explicit stem=="__init__" guard is not a universal exclusion of classes
locally declared in an initializer.

Tracking definition: migrations contains auto id, unique migration, batch,
migrated_at integer epoch. Each step binds the selected connection, opens its
transaction, builds the class through app.build, awaits up/down, then inserts
or removes the tracking row. Errors stop later steps; earlier committed steps
remain. Rollback checks all selected recorded names exist before changing any
selected schema, raising MigrationNotFoundException when absent.

Transactional DDL/data depends on the engine and migration operations. There
is no universal rollback for external effects or databases with implicit DDL
commits. Import/build/migration/events/query errors propagate. Migration
tracking createTable has no runner-level concurrent-creator retry, and pending
migrations are not claimed before up; do not infer seeder-style once-only
execution under concurrent migrate calls.

Completing rollback of every recorded migration drops seeders tracking during
the final step. Partial rollback retains it. down determines data/schema removal;
the runner has no independent seeder-data inverse. fresh also clears history
when no recorded migration remains.

**Verified prefix limit:** tracking table DDL applies Connection's prefix, but
Migrator's SELECT/INSERT/DELETE SQL uses the literal unprefixed migrations name.
A nonempty prefix reproduced QueryException on status after creating the prefixed
tracking table. This was documented, not corrected. Seeder tracking uses plans
and has a different prefix path.

### Events and migration connection context

Source/import: [MigrationEvents](../migrations/events.py),
[context functions](../migrations/context.py).
MigrationEvents is frozen/slotted/keyword-only, with on_start, on_success,
on_error default None. Its constructor/equality/hash are dataclass-generated.
started(name), succeeded(name, elapsed), failed(name, elapsed) call the respective
callback if non-None and return None. No callable validation, elapsed conversion,
exception shielding or awaiting of callback results occurs.

NO_EVENTS is one module-level empty MigrationEvents instance. SeederEvents in
[seeders/events.py](../seeders/events.py) is **an import alias of MigrationEvents**,
with the same NO_EVENTS object, not a second class or constructor.

Migration started fires before the step's transaction/try; failed fires for
Exception caught after entering step work, then the exception is re-raised;
succeeded fires after commit. Cancellation/BaseException is not reported by
that Exception handler. A failing started prevents work, a failing failed can
replace the original error, and a failing succeeded can report failure after
data already committed. Seeder callbacks have their own claim ordering below.

current_migration_connection() returns the raw current reference or None.
The synchronous @contextmanager migration_connection_scope(connection) yields
None, sets a ContextVar token, restores it in finally, and does not begin/close
anything or validate the reference. Nested scopes restore the outer binding.
Children inherit the reference; explicit Connection task ownership still applies.

### Seeder and SeederRunner

Source/import: [Seeder](../seeders/seeder.py), [SeederRunner](../seeders/runner.py),
root/subpackage exports. Seeder is an abstract ABC with async run and empty slots.
SeederRunner(app, conn_manager) stores references and a discovery cache.
await seed(*, connection=None, events=None) returns names actually completed by
this call, not every pending/previously recorded name; no pending work returns [].

Discovery uses app.path("database_seeders"), locally defined subclasses, sorted
stems, duplicate-name ValueError, and per-instance caching like Migrator. No
runtime abstract-class exclusion or arbitrary missing-file substitution exists.

The plan-based seeders table stores id, unique seeder, batch, seeded_at.
seed ensures it, reads committed rows, chooses max prior batch+1, and for each
pending class opens a transaction and **inserts the unique claim first** with
timestamp zero. After a successful claim, started fires, migration connection
context is bound, app.build constructs the seeder, run is awaited, timestamp
is updated to completion epoch and data/tracking commit together. succeeded
fires after commit; failures caught as Exception report failed only when started.

A claim QueryException is handled after rollback: if a committed record is then
visible, skip the class; otherwise call started/failed and re-raise the query
error. This covers a conflicting successful runner, not every query failure as
a duplicate. A concurrent table creator is tolerated only if tracking becomes
readable after createTable QueryException. Unique claims prevent two committed
rows, but transactional engine behavior, external side effects and callbacks
still limit the docstring's "exactly once" phrasing.

New/editing source does not rerun an already recorded stem or invalidate cached
discovery. There is no public unseed/history-clear method here. Migrator lifecycle
operations can clear tracking as described. The module contains no built-in
administrative credentials; any application seeder data is outside this API.

### Providers, contracts and exception hierarchy

Providers: [ConnectionManagerProvider](../provider.py) register returns None
after singleton binding; boot awaits IConnectionManager, sets global ORM
ConnectionResolver and returns None. It inherits ServiceProvider's app constructor.
[SchemaProvider](../schema_provider.py) register returns None after transient
ISchema binding; inherited async boot does nothing. Duplicate binding and DI
errors follow the real container, not a provider-specific retry policy.

All six database contracts/abstract bases declare __slots__=():

| Contract | Declared operations |
| --- | --- |
| [IConnection](../contracts/connection.py) | Sixteen name/query/schema/transaction/lifecycle methods implemented by Connection. |
| [IConnectionManager](../contracts/connection_manager.py) | Seven connection/config/default/disconnect operations. |
| [ITransaction](../contracts/transaction.py) | Async enter/exit. |
| [ISchema](../contracts/schema.py) | connection, create, createFromDefinition, createFromModel, drop. |
| [IMigrator](../contracts/migrator.py) | Six async migration operations. |
| [Migration](../contracts/migration.py) | Async up/down. Seeder is its own abstract base with run, not a Migration subclass. |

They specify declarations, not independent runtime coercion/validation. Most
abstract bodies contain only docstrings; ISchema.connection additionally has
literal Ellipsis. The appendices retain decorators and source defaults.

[InsertResult](../entities/result.py) is frozen/slotted dataclass with required
last_insert_id: Any and row_count: int. Generated positional-capable constructor,
equality/hash/repr are not literal declarations; fields are not runtime validated.
It does not inherit BaseEntity or provide toDict. Unhashable ID can make generated
hash fail. Driver-reported counts/keys have the limits described under Connection.

[DatabaseException](../exceptions.py) directly inherits Exception; subclasses
are ConnectionNotFoundException, MigrationNotFoundException,
MissingDatabaseDependencyException, QueryException, TransactionException and
UnsupportedDriverException. No custom constructors/status codes are declared;
standard args/chaining apply. Their raising conditions belong to the owners
above. Callback, parsing, configuration and toolkit failures are not universally
wrapped as DatabaseException.

### Literal declarations

Headers below preserve source declarations, not evaluated runtime signatures.
Field blocks describe generated constructors/storage. Imported alias declarations
and the Blueprint stub are identified separately. Empty/package export entries
are not additional service implementations.

#### __init__.py

Source: [orionis/database/__init__.py](../__init__.py).

`__all__`

```python
__all__ = [
    "Connection",
    "ConnectionManager",
    "ConnectionNotFoundException",
    "DatabaseException",
    "Migration",
    "MigrationNotFoundException",
    "Migrator",
    "MissingDatabaseDependencyException",
    "QueryException",
    "SQLCompiler",
    "Seeder",
    "SeederEvents",
    "SeederRunner",
    "Transaction",
    "TransactionException",
    "UnsupportedDriverException",
]
```

`__getattr__`

```python
def __getattr__(name: str) -> object:
```

`__dir__`

```python
def __dir__() -> list[str]:
```

#### compiler.py

Source: [orionis/database/compiler.py](../compiler.py).

`SQLCompiler`

```python
class SQLCompiler:
```

`SQLCompiler fields`

```python
__slots__ = ("_definitions", "_metadata", "_prefix", "_tables")
```

`SQLCompiler.__init__`

```python
def __init__(self, prefix: str = "") -> None:
```

`SQLCompiler.compileSelect`

```python
def compileSelect(self, plan: SelectPlan) -> Select[Any] | CompoundSelect:
```

`SQLCompiler.supportsBatchInsert`

```python
@staticmethod
def supportsBatchInsert(plan: InsertPlan) -> bool:
```

`SQLCompiler.compileInsert`

```python
def compileInsert(
    self,
    plan: InsertPlan,
    *,
    parameterized: bool = False,
) -> Insert:
```

`SQLCompiler.compileUpdate`

```python
def compileUpdate(self, plan: UpdatePlan) -> Update:
```

`SQLCompiler.compileDelete`

```python
def compileDelete(self, plan: DeletePlan) -> Delete:
```

`SQLCompiler.compileCreateTable`

```python
def compileCreateTable(
    self,
    definition: TableDefinition,
    *,
    if_not_exists: bool = True,
) -> Executable:
```

`SQLCompiler.compileDropTable`

```python
def compileDropTable(
    self,
    name: str,
    schema: str | None = None,
    *,
    if_exists: bool = True,
) -> Executable:
```

#### connection.py

Source: [orionis/database/connection.py](../connection.py).

`Connection`

```python
class Connection(IConnection):
```

`Connection fields`

```python
__slots__ = ("_compiler", "_config", "_engine", "_name", "_tx_state")
```

`Connection.__init__`

```python
def __init__(
    self,
    name: str,
    config: dict[str, Any],
) -> None:
```

`Connection.getName`

```python
def getName(self) -> str:
```

`Connection.select`

```python
async def select(
    self,
    query: SelectPlan | str,
    bindings: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
```

`Connection.insert`

```python
async def insert(
    self,
    plan: InsertPlan,
) -> InsertResult:
```

`Connection.update`

```python
async def update(
    self,
    plan: UpdatePlan,
) -> int:
```

`Connection.delete`

```python
async def delete(
    self,
    plan: DeletePlan,
) -> int:
```

`Connection.scalar`

```python
async def scalar(
    self,
    plan: SelectPlan,
) -> Any:
```

`Connection.execute`

```python
async def execute(
    self,
    sql: str,
    bindings: Mapping[str, Any] | None = None,
) -> int:
```

`Connection.statement`

```python
async def statement(
    self,
    sql: str,
    bindings: Mapping[str, Any] | None = None,
) -> bool:
```

`Connection.createTable`

```python
async def createTable(
    self,
    table: TableDefinition,
    *,
    if_not_exists: bool = True,
) -> bool:
```

`Connection.dropTable`

```python
async def dropTable(
    self,
    name: str,
    schema: str | None = None,
    *,
    if_exists: bool = True,
) -> bool:
```

`Connection.begin`

```python
async def begin(self) -> None:
```

`Connection.commit`

```python
async def commit(self) -> None:
```

`Connection.rollback`

```python
async def rollback(self) -> None:
```

`Connection.transaction`

```python
def transaction(self) -> ITransaction:
```

`Connection.inTransaction`

```python
def inTransaction(self) -> bool:
```

`Connection.disconnect`

```python
async def disconnect(self) -> None:
```

#### connection_manager.py

Source: [orionis/database/connection_manager.py](../connection_manager.py).

`ConnectionManager`

```python
class ConnectionManager(IConnectionManager):

    # ruff: noqa: TC001
```

`ConnectionManager fields`

```python
__slots__ = ("_cached_connections", "_connections", "_default")
```

`ConnectionManager.__init__`

```python
def __init__(
    self,
    app: IApplication,
) -> None:
```

`ConnectionManager.connection`

```python
def connection(
    self,
    name: str | None = None,
) -> IConnection:
```

`ConnectionManager.addConnection`

```python
def addConnection(self, name: str, config: dict[str, Any]) -> None:
```

`ConnectionManager.hasConnection`

```python
def hasConnection(self, name: str) -> bool:
```

`ConnectionManager.getDefaultName`

```python
def getDefaultName(self) -> str:
```

`ConnectionManager.setDefaultName`

```python
def setDefaultName(self, name: str) -> None:
```

`ConnectionManager.disconnect`

```python
async def disconnect(self, name: str | None = None) -> None:
```

`ConnectionManager.configFor`

```python
def configFor(self, name: str | None = None) -> dict[str, Any]:
```

#### contracts/__init__.py

Source: [orionis/database/contracts/__init__.py](../contracts/__init__.py).

`__all__`

```python
__all__ = [
    "IConnection",
    "IConnectionManager",
    "ITransaction",
]
```

#### contracts/connection.py

Source: [orionis/database/contracts/connection.py](../contracts/connection.py).

`IConnection`

```python
class IConnection(ABC):
```

`IConnection fields`

```python
__slots__ = ()
```

`IConnection.getName`

```python
@abstractmethod
def getName(self) -> str:
```

`IConnection.select`

```python
@abstractmethod
async def select(
    self,
    query: SelectPlan | str,
    bindings: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
```

`IConnection.insert`

```python
@abstractmethod
async def insert(self, plan: InsertPlan) -> InsertResult:
```

`IConnection.update`

```python
@abstractmethod
async def update(self, plan: UpdatePlan) -> int:
```

`IConnection.delete`

```python
@abstractmethod
async def delete(self, plan: DeletePlan) -> int:
```

`IConnection.scalar`

```python
@abstractmethod
async def scalar(self, plan: SelectPlan) -> Any:
```

`IConnection.execute`

```python
@abstractmethod
async def execute(
    self,
    sql: str,
    bindings: Mapping[str, Any] | None = None,
) -> int:
```

`IConnection.statement`

```python
@abstractmethod
async def statement(
    self,
    sql: str,
    bindings: Mapping[str, Any] | None = None,
) -> bool:
```

`IConnection.createTable`

```python
@abstractmethod
async def createTable(
    self,
    table: TableDefinition,
    *,
    if_not_exists: bool = True,
) -> bool:
```

`IConnection.dropTable`

```python
@abstractmethod
async def dropTable(
    self,
    name: str,
    schema: str | None = None,
    *,
    if_exists: bool = True,
) -> bool:
```

`IConnection.begin`

```python
@abstractmethod
async def begin(self) -> None:
```

`IConnection.commit`

```python
@abstractmethod
async def commit(self) -> None:
```

`IConnection.rollback`

```python
@abstractmethod
async def rollback(self) -> None:
```

`IConnection.transaction`

```python
@abstractmethod
def transaction(self) -> ITransaction:
```

`IConnection.inTransaction`

```python
@abstractmethod
def inTransaction(self) -> bool:
```

`IConnection.disconnect`

```python
@abstractmethod
async def disconnect(self) -> None:
```

#### contracts/connection_manager.py

Source: [orionis/database/contracts/connection_manager.py](../contracts/connection_manager.py).

`IConnectionManager`

```python
class IConnectionManager(ABC):
```

`IConnectionManager fields`

```python
__slots__ = ()
```

`IConnectionManager.connection`

```python
@abstractmethod
def connection(self, name: str | None = None) -> IConnection:
```

`IConnectionManager.addConnection`

```python
@abstractmethod
def addConnection(self, name: str, config: dict[str, Any]) -> None:
```

`IConnectionManager.hasConnection`

```python
@abstractmethod
def hasConnection(self, name: str) -> bool:
```

`IConnectionManager.getDefaultName`

```python
@abstractmethod
def getDefaultName(self) -> str:
```

`IConnectionManager.setDefaultName`

```python
@abstractmethod
def setDefaultName(self, name: str) -> None:
```

`IConnectionManager.disconnect`

```python
@abstractmethod
async def disconnect(self, name: str | None = None) -> None:
```

`IConnectionManager.configFor`

```python
@abstractmethod
def configFor(self, name: str | None = None) -> dict[str, Any]:
```

#### contracts/migration.py

Source: [orionis/database/contracts/migration.py](../contracts/migration.py).

`Migration`

```python
class Migration(ABC):
```

`Migration fields`

```python
__slots__ = ()
```

`Migration.up`

```python
@abstractmethod
async def up(self) -> None:
```

`Migration.down`

```python
@abstractmethod
async def down(self) -> None:
```

#### contracts/migrator.py

Source: [orionis/database/contracts/migrator.py](../contracts/migrator.py).

`IMigrator`

```python
class IMigrator(ABC):
```

`IMigrator fields`

```python
__slots__ = ()
```

`IMigrator.migrate`

```python
@abstractmethod
async def migrate(
    self,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`IMigrator.rollback`

```python
@abstractmethod
async def rollback(
    self,
    steps: int = 1,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`IMigrator.reset`

```python
@abstractmethod
async def reset(
    self,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`IMigrator.refresh`

```python
@abstractmethod
async def refresh(
    self,
    steps: int | None = None,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`IMigrator.fresh`

```python
@abstractmethod
async def fresh(
    self,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`IMigrator.status`

```python
@abstractmethod
async def status(
    self,
    *,
    connection: str | None = None,
) -> list[dict[str, Any]]:
```

#### contracts/schema.py

Source: [orionis/database/contracts/schema.py](../contracts/schema.py).

`ISchema`

```python
class ISchema(ABC):
```

`ISchema fields`

```python
__slots__ = ()
```

`ISchema.connection`

```python
@abstractmethod
def connection(self, name: str | None = None) -> Self:
```

`ISchema.create`

```python
@abstractmethod
def create(
    self,
    name: str,
) -> TableCreation:
```

`ISchema.createFromDefinition`

```python
@abstractmethod
async def createFromDefinition(self, definition: TableDefinition) -> bool:
```

`ISchema.createFromModel`

```python
@abstractmethod
async def createFromModel(self, model: type[Model]) -> bool:
```

`ISchema.drop`

```python
@abstractmethod
async def drop(self, name: str) -> bool:
```

#### contracts/transaction.py

Source: [orionis/database/contracts/transaction.py](../contracts/transaction.py).

`ITransaction`

```python
class ITransaction(ABC):
```

`ITransaction fields`

```python
__slots__ = ()
```

`ITransaction.__aenter__`

```python
@abstractmethod
async def __aenter__(self) -> ITransaction:
```

`ITransaction.__aexit__`

```python
@abstractmethod
async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc: BaseException | None,
    traceback: TracebackType | None,
) -> bool:
```

#### dialect.py

Source: [orionis/database/dialect.py](../dialect.py).

`resolve_driver`

```python
def resolve_driver(config: dict[str, Any]) -> str:
```

`missing_dependency_error`

```python
def missing_dependency_error(
    driver: str,
    cause: ModuleNotFoundError,
    *,
    sync: bool = False,
) -> MissingDatabaseDependencyException:
```

`build_engine_url`

```python
def build_engine_url(
    config: dict[str, Any],
    *,
    sync: bool = False,
) -> URL:
```

`engine_options`

```python
def engine_options(
    config: dict[str, Any],
    *,
    sync: bool = False,
) -> dict[str, Any]:
```

`configure_engine`

```python
def configure_engine(engine: AsyncEngine, config: dict[str, Any]) -> None:
```

#### entities/__init__.py

Source: [orionis/database/entities/__init__.py](../entities/__init__.py).

`__all__`

```python
__all__ = [
    "InsertResult",
]
```

#### entities/result.py

Source: [orionis/database/entities/result.py](../entities/result.py).

`InsertResult`

```python
@dataclass(frozen=True, slots=True)
class InsertResult:
```

`InsertResult fields`

```python
last_insert_id: Any
row_count: int
```

#### exceptions.py

Source: [orionis/database/exceptions.py](../exceptions.py).

`DatabaseException`

```python
class DatabaseException(Exception):
```

`ConnectionNotFoundException`

```python
class ConnectionNotFoundException(DatabaseException):
```

`MigrationNotFoundException`

```python
class MigrationNotFoundException(DatabaseException):
```

`MissingDatabaseDependencyException`

```python
class MissingDatabaseDependencyException(DatabaseException):
```

`QueryException`

```python
class QueryException(DatabaseException):
```

`TransactionException`

```python
class TransactionException(DatabaseException):
```

`UnsupportedDriverException`

```python
class UnsupportedDriverException(DatabaseException):
```

#### migrations/__init__.py

Source: [orionis/database/migrations/__init__.py](../migrations/__init__.py).

`__all__`

```python
__all__ = [
    "Migrator",
]
```

#### migrations/context.py

Source: [orionis/database/migrations/context.py](../migrations/context.py).

`current_migration_connection`

```python
def current_migration_connection() -> IConnection | None:
```

`migration_connection_scope`

```python
@contextmanager
def migration_connection_scope(connection: IConnection) -> Generator[None]:
```

#### migrations/events.py

Source: [orionis/database/migrations/events.py](../migrations/events.py).

`MigrationEvents`

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class MigrationEvents:
```

`MigrationEvents fields`

```python
on_start: Callable[[str], None] | None = None
on_success: Callable[[str, float], None] | None = None
on_error: Callable[[str, float], None] | None = None
```

`MigrationEvents.started`

```python
def started(self, name: str) -> None:
```

`MigrationEvents.succeeded`

```python
def succeeded(self, name: str, elapsed: float) -> None:
```

`MigrationEvents.failed`

```python
def failed(self, name: str, elapsed: float) -> None:
```

`NO_EVENTS`

```python
NO_EVENTS: MigrationEvents = MigrationEvents()
```

#### migrations/migrator.py

Source: [orionis/database/migrations/migrator.py](../migrations/migrator.py).

`Migrator`

```python
class Migrator(IMigrator):
```

`Migrator fields`

```python
__slots__ = ("__app", "__conn_manager", "__discovered_cache")
```

`Migrator.__init__`

```python
def __init__(
    self,
    app: IApplication,
    conn_manager: IConnectionManager,
) -> None:
```

`Migrator.migrate`

```python
async def migrate(
    self,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`Migrator.rollback`

```python
async def rollback(
    self,
    steps: int = 1,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`Migrator.reset`

```python
async def reset(
    self,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`Migrator.refresh`

```python
async def refresh(
    self,
    steps: int | None = None,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`Migrator.fresh`

```python
async def fresh(
    self,
    *,
    connection: str | None = None,
    events: MigrationEvents | None = None,
) -> list[str]:
```

`Migrator.status`

```python
async def status(
    self,
    *,
    connection: str | None = None,
) -> list[dict[str, Any]]:
```

#### provider.py

Source: [orionis/database/provider.py](../provider.py).

`ConnectionManagerProvider`

```python
class ConnectionManagerProvider(ServiceProvider):
```

`ConnectionManagerProvider.register`

```python
def register(self) -> None:
```

`ConnectionManagerProvider.boot`

```python
async def boot(self) -> None:
```

#### schema/__init__.py

Source: [orionis/database/schema/__init__.py](../schema/__init__.py).

`__all__`

```python
__all__ = [
    "Blueprint",
    "Column",
    "Comment",
    "ForeignKey",
    "Index",
    "PrimaryKey",
    "Timestamps",
    "Unique",
]
```

#### schema/blueprint.py

Source: [orionis/database/schema/blueprint.py](../schema/blueprint.py).

`Blueprint`

```python
class Blueprint:
```

`Blueprint fields`

```python
__slots__ = ("__columns", "__constraints", "__factory_cache")
```

`Blueprint.__init__`

```python
def __init__(self) -> None:
```

`Blueprint.__getattr__`

```python
def __getattr__(self, name: str) -> Callable[..., ColumnDefinition]:
```

`Blueprint.timestamps`

```python
def timestamps(self, *, timezone: bool = False) -> None:
```

`Blueprint.comment`

```python
def comment(self, text: str) -> Comment:
```

`Blueprint.foreignKey`

```python
def foreignKey(
    self,
    column: str,
    ref_table: str,
    ref_column: str,
    name: str | None = None,
) -> ForeignKey:
```

`Blueprint.index`

```python
def index(
    self,
    *columns: str,
    name: str | None = None,
    unique: bool = False,
) -> Index:
```

`Blueprint.primaryKey`

```python
def primaryKey(self, *columns: str) -> PrimaryKey:
```

`Blueprint.unique`

```python
def unique(self, *columns: str, name: str | None = None) -> Unique:
```

`Blueprint.columns`

```python
def columns(self) -> tuple[ColumnDefinition, ...]:
```

`Blueprint.definitions`

```python
def definitions(
    self,
) -> tuple[
    ColumnDefinition | Comment | ForeignKey | Index | PrimaryKey | Unique, ...,
]:
```

#### schema/column.py

Source: [orionis/database/schema/column.py](../schema/column.py).

`Column`

```python
class Column:
```

`Column.id`

```python
@staticmethod
def id(name: str = "id") -> BigInteger:
```

`Column.bigInteger`

```python
@staticmethod
def bigInteger(name: str) -> BigInteger:
```

`Column.boolean`

```python
@staticmethod
def boolean(
    name: str,
    *,
    create_constraint: bool = False,
    constraint_name: str | None = None,
) -> Boolean:
```

`Column.date`

```python
@staticmethod
def date(name: str) -> Date:
```

`Column.dateTime`

```python
@staticmethod
def dateTime(name: str, *, timezone: bool = False) -> DateTime:
```

`Column.double`

```python
@staticmethod
def double(
    name: str,
    precision: int | None = None,
    *,
    asdecimal: bool = False,
    decimal_return_scale: int | None = None,
) -> Double:
```

`Column.enum`

```python
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
```

`Column.float`

```python
@staticmethod
def float(
    name: str,
    precision: int | None = None,
    *,
    asdecimal: bool = False,
    decimal_return_scale: int | None = None,
) -> Float:
```

`Column.integer`

```python
@staticmethod
def integer(name: str) -> Integer:
```

`Column.interval`

```python
@staticmethod
def interval(
    name: str,
    *,
    native: bool = True,
    second_precision: int | None = None,
    day_precision: int | None = None,
) -> Interval:
```

`Column.largeBinary`

```python
@staticmethod
def largeBinary(name: str, length: int | None = None) -> LargeBinary:
```

`Column.matchType`

```python
@staticmethod
def matchType(name: str) -> MatchType:
```

`Column.numeric`

```python
@staticmethod
def numeric(
    name: str,
    precision: int | None = None,
    scale: int | None = None,
    decimal_return_scale: int | None = None,
    *,
    asdecimal: bool = True,
) -> Numeric:
```

`Column.numericCommon`

```python
@staticmethod
def numericCommon(name: str) -> NumericCommon:
```

`Column.pickleType`

```python
@staticmethod
def pickleType(
    name: str,
    protocol: int = 5,
    pickler: object | None = None,
    impl: object | None = None,
) -> PickleType:
```

`Column.schemaType`

```python
@staticmethod
def schemaType(name: str, schema_name: str | None = None) -> SchemaType:
```

`Column.smallInteger`

```python
@staticmethod
def smallInteger(name: str) -> SmallInteger:
```

`Column.string`

```python
@staticmethod
def string(
    name: str,
    length: int | None = 255,
    collation: str | None = None,
) -> String:
```

`Column.text`

```python
@staticmethod
def text(
    name: str,
    length: int | None = None,
    collation: str | None = None,
) -> Text:
```

`Column.time`

```python
@staticmethod
def time(name: str) -> Time:
```

`Column.unicode`

```python
@staticmethod
def unicode(
    name: str,
    length: int | None = None,
    collation: str | None = None,
) -> Unicode:
```

`Column.unicodeText`

```python
@staticmethod
def unicodeText(
    name: str,
    length: int | None = None,
    collation: str | None = None,
) -> UnicodeText:
```

`Column.uuid`

```python
@staticmethod
def uuid(
    name: str,
    *,
    as_uuid: bool = True,
    native_uuid: bool = True,
) -> Uuid:
```

`Column.strictArray`

```python
@staticmethod
def strictArray(
    name: str,
    item_type: ColumnDefinition,
    *,
    as_tuple: bool = False,
    dimensions: int | None = None,
    zero_indexes: bool = False,
) -> StrictArray:
```

`Column.strictBigInt`

```python
@staticmethod
def strictBigInt(name: str) -> StrictBigInt:
```

`Column.strictBinary`

```python
@staticmethod
def strictBinary(name: str, length: int | None = None) -> StrictBinary:
```

`Column.strictBlob`

```python
@staticmethod
def strictBlob(name: str, length: int | None = None) -> StrictBlob:
```

`Column.strictChar`

```python
@staticmethod
def strictChar(
    name: str,
    length: int | None = None,
    collation: str | None = None,
) -> StrictChar:
```

`Column.strictClob`

```python
@staticmethod
def strictClob(
    name: str,
    length: int | None = None,
    collation: str | None = None,
) -> StrictClob:
```

`Column.strictDecimal`

```python
@staticmethod
def strictDecimal(
    name: str,
    precision: int | None = 10,
    scale: int | None = 2,
    decimal_return_scale: int | None = None,
    *,
    asdecimal: bool = True,
) -> StrictDecimal:
```

`Column.strictDoublePrecision`

```python
@staticmethod
def strictDoublePrecision(
    name: str,
    precision: int | None = None,
    *,
    asdecimal: bool = False,
    decimal_return_scale: int | None = None,
) -> StrictDoublePrecision:
```

`Column.strictInt`

```python
@staticmethod
def strictInt(name: str) -> StrictInt:
```

`Column.strictJson`

```python
@staticmethod
def strictJson(name: str, *, none_as_null: bool = False) -> StrictJson:
```

`Column.strictNChar`

```python
@staticmethod
def strictNChar(
    name: str,
    length: int | None = None,
    collation: str | None = None,
) -> StrictNChar:
```

`Column.strictNVarChar`

```python
@staticmethod
def strictNVarChar(
    name: str,
    length: int | None = None,
    collation: str | None = None,
) -> StrictNVarChar:
```

`Column.strictReal`

```python
@staticmethod
def strictReal(
    name: str,
    precision: int | None = None,
    *,
    asdecimal: bool = False,
    decimal_return_scale: int | None = None,
) -> StrictReal:
```

`Column.strictSmallInt`

```python
@staticmethod
def strictSmallInt(name: str) -> StrictSmallInt:
```

`Column.strictTimestamp`

```python
@staticmethod
def strictTimestamp(name: str, *, timezone: bool = False) -> StrictTimestamp:
```

`Column.strictVarBinary`

```python
@staticmethod
def strictVarBinary(name: str, length: int | None = None) -> StrictVarBinary:
```

`Column.strictVarChar`

```python
@staticmethod
def strictVarChar(
    name: str,
    length: int | None = 255,
    collation: str | None = None,
) -> StrictVarChar:
```

#### schema/comment.py

Source: [orionis/database/schema/comment.py](../schema/comment.py).

`Comment`

```python
class Comment:
```

`Comment.__init__`

```python
def __init__(self, text: str) -> None:
```

#### schema/definition_bucket.py

Source: [orionis/database/schema/definition_bucket.py](../schema/definition_bucket.py).

`DefinitionBucket`

```python
class DefinitionBucket:
```

`DefinitionBucket fields`

```python
__slots__ = (
        "columns",
        "foreign_keys",
        "indexes",
        "kwargs",
        "primary_columns",
        "unique_constraints",
    )
```

`DefinitionBucket.__init__`

```python
def __init__(self) -> None:
```

#### schema/definitions.py

Source: [orionis/database/schema/definitions.py](../schema/definitions.py).

`SchemaDefinition`

```python
type SchemaDefinition = (
    ColumnDefinition | Comment | ForeignKey | Index | PrimaryKey | Unique
)
```

#### schema/foreign.py

Source: [orionis/database/schema/foreign.py](../schema/foreign.py).

`ForeignKey`

```python
class ForeignKey:
```

`ForeignKey.__init__`

```python
def __init__(
    self,
    column: str,
    ref_table: str,
    ref_column: str,
    name: str | None = None,
) -> None:
```

#### schema/index.py

Source: [orionis/database/schema/index.py](../schema/index.py).

`Index`

```python
class Index:
```

`Index.__init__`

```python
def __init__(
    self,
    *columns: str,
    name: str | None = None,
    unique: bool = False,
) -> None:
```

#### schema/primary.py

Source: [orionis/database/schema/primary.py](../schema/primary.py).

`PrimaryKey`

```python
class PrimaryKey:
```

`PrimaryKey.__init__`

```python
def __init__(self, *columns: str) -> None:
```

#### schema/schema.py

Source: [orionis/database/schema/schema.py](../schema/schema.py).

`Schema`

```python
class Schema(ISchema):

    # ruff: noqa: TC001
```

`Schema fields`

```python
__slots__ = (
        "__conn_manager", "__connection_name", "__connection_selected",
    )
```

`Schema.__init__`

```python
def __init__(self, conn_manager: IConnectionManager) -> None:
```

`Schema.connection`

```python
def connection(self, name: str | None = None) -> Self:
```

`Schema.create`

```python
def create(self, name: str) -> TableCreation:
```

`Schema.createFromDefinition`

```python
async def createFromDefinition(self, definition: TableDefinition) -> bool:
```

`Schema.createFromModel`

```python
async def createFromModel(self, model: type[Model]) -> bool:
```

`Schema.drop`

```python
async def drop(self, name: str) -> bool:
```

#### schema/table_creation.py

Source: [orionis/database/schema/table_creation.py](../schema/table_creation.py).

`TableCreation`

```python
class TableCreation:
```

`TableCreation fields`

```python
__slots__ = ("__blueprint", "__name", "__schema")
```

`TableCreation.__init__`

```python
def __init__(
    self,
    schema: Schema,
    name: str,
) -> None:
```

`TableCreation.__aenter__`

```python
async def __aenter__(self) -> Blueprint:
```

`TableCreation.__aexit__`

```python
async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc: BaseException | None,
    traceback: TracebackType | None,
) -> bool:
```

#### schema/timestamp.py

Source: [orionis/database/schema/timestamp.py](../schema/timestamp.py).

`Timestamps`

```python
class Timestamps:
```

`Timestamps.__init__`

```python
def __init__(self, *, timezone: bool = True) -> None:
```

#### schema/unique.py

Source: [orionis/database/schema/unique.py](../schema/unique.py).

`Unique`

```python
class Unique:
```

`Unique.__init__`

```python
def __init__(self, *columns: str, name: str | None = None) -> None:
```

#### schema_provider.py

Source: [orionis/database/schema_provider.py](../schema_provider.py).

`SchemaProvider`

```python
class SchemaProvider(ServiceProvider):
```

`SchemaProvider.register`

```python
def register(self) -> None:
```

#### seeders/__init__.py

Source: [orionis/database/seeders/__init__.py](../seeders/__init__.py).

`__all__`

```python
__all__ = ["Seeder", "SeederEvents", "SeederRunner"]
```

#### seeders/events.py

Source: [orionis/database/seeders/events.py](../seeders/events.py).

`SeederEvents`

```python
from orionis.database.migrations.events import MigrationEvents as SeederEvents
```

`__all__`

```python
__all__ = ["NO_EVENTS", "SeederEvents"]
```

#### seeders/runner.py

Source: [orionis/database/seeders/runner.py](../seeders/runner.py).

`SeederRunner`

```python
class SeederRunner:
```

`SeederRunner fields`

```python
__slots__ = ("__app", "__conn_manager", "__discovered_cache")
```

`SeederRunner.__init__`

```python
def __init__(
    self,
    app: IApplication,
    conn_manager: IConnectionManager,
) -> None:
```

`SeederRunner.seed`

```python
async def seed(
    self,
    *,
    connection: str | None = None,
    events: SeederEvents | None = None,
) -> list[str]:
```

#### seeders/seeder.py

Source: [orionis/database/seeders/seeder.py](../seeders/seeder.py).

`Seeder`

```python
class Seeder(ABC):
```

`Seeder fields`

```python
__slots__ = ()
```

`Seeder.run`

```python
@abstractmethod
async def run(self) -> None:
```

#### transaction.py

Source: [orionis/database/transaction.py](../transaction.py).

`Transaction`

```python
class Transaction(ITransaction):
```

`Transaction fields`

```python
__slots__ = ("_connection",)
```

`Transaction.__init__`

```python
def __init__(self, connection: IConnection) -> None:
```

`Transaction.__aenter__`

```python
async def __aenter__(self) -> ITransaction:
```

`Transaction.__aexit__`

```python
async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc: BaseException | None,
    traceback: TracebackType | None,
) -> bool:
```

#### schema/blueprint.pyi

Source: [orionis/database/schema/blueprint.pyi](../schema/blueprint.pyi). Editor/type-checker reference, not executable runtime code.

```python
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
```


## Usage examples

Run each block independently with Orionis/core dependencies installed on Python
3.14+. The verified executions used the local checkout, bytecode disabled,
separate processes, temporary cwd/resources, and barriers against writes outside
the validation root or service connections. No checkout database/bootstrap or
external service was used. Reference/stub blocks above are not these scripts.

### 1. Execute raw SQL and CRUD plans on SQLite

Expect a generated single-row key, materialized dictionaries, a batch result
without one generated ID, and plan-based update/delete/scalar operations.

```python
import asyncio
from orionis.database.connection import Connection
from orionis.database.schema.column import Column
from orionis.orm.query.expressions import (
    AggregateClause,
    AggregateFunction,
    DeletePlan,
    InsertPlan,
    SelectPlan,
    UpdatePlan,
    WhereClause,
)
from orionis.orm.schema.table import TableDefinition

async def main() -> None:
    connection = Connection("local", {"driver": "sqlite", "database": ":memory:"})
    table = TableDefinition("entries", {
        "id": Column.id(), "label": Column.string("label"),
    })
    try:
        assert await connection.createTable(table)
        result = await connection.insert(InsertPlan(table, [{"label": "first"}]))
        assert isinstance(result.last_insert_id, int) and result.row_count == 1
        batch = await connection.insert(InsertPlan(table, [
            {"label": "second"}, {"label": "third"},
        ]))
        assert batch.last_insert_id is None and batch.row_count == 2
        assert await connection.select(
            "SELECT label FROM entries WHERE label=:label", {"label": "first"},
        ) == [{"label": "first"}]
        where = [WhereClause("label", value="second")]
        assert await connection.update(UpdatePlan(table, {"label": "updated"},
                                                   wheres=where)) == 1
        assert await connection.delete(DeletePlan(
            table, wheres=[WhereClause("label", value="third")],
        )) == 1
        count = SelectPlan(table, aggregate=AggregateClause(AggregateFunction.COUNT))
        assert await connection.scalar(count) == 2
    finally:
        await connection.disconnect()

asyncio.run(main())
```

### 2. Manage named configuration and handle real query errors

Expect cached identity until manager disconnect, a live config mapping without
replacement of an existing Connection, and sanitized QueryException for missing SQL.

```python
import asyncio
from orionis.database.connection_manager import ConnectionManager
from orionis.database.exceptions import (
    ConnectionNotFoundException,
    QueryException,
    UnsupportedDriverException,
)

class Settings:
    def config(self, key: str) -> dict:
        assert key == "database"
        return {"default": "sqlite", "connections": {
            "sqlite": {"driver": "sqlite", "database": ":memory:"},
        }}

async def main() -> None:
    manager = ConnectionManager(Settings())
    first = manager.connection()
    assert first is manager.connection("sqlite")
    manager.addConnection("sqlite", {"driver": "sqlite", "database": ":memory:"})
    manager.configFor()["prefix"] = "local_"
    assert manager.connection() is first
    try:
        await first.select("SELECT :value FROM missing_table", {"value": "private"})
    except QueryException as error:
        assert "private" not in str(error) and "missing_table" not in str(error)
        assert error.__suppress_context__
    else:
        raise AssertionError("Missing table query succeeded")
    try:
        manager.connection("absent")
    except ConnectionNotFoundException:
        pass
    else:
        raise AssertionError("Unknown connection was accepted")
    manager.addConnection("bad", {"driver": "unsupported"})
    try:
        manager.connection("bad")
    except UnsupportedDriverException:
        pass
    else:
        raise AssertionError("Unsupported driver was accepted")
    await manager.disconnect("sqlite")
    assert manager.connection() is not first
    await manager.disconnect()

asyncio.run(main())
```

### 3. Nest savepoints and enforce transaction ownership

Expect the inner failure to roll back only its savepoint, outer data to commit,
and a child query to be rejected while the owner transaction is active.

```python
import asyncio
from orionis.database.connection import Connection
from orionis.database.exceptions import TransactionException
from orionis.database.transaction import Transaction

async def main() -> None:
    connection = Connection("local", {"driver": "sqlite", "database": ":memory:"})
    try:
        await connection.statement("CREATE TABLE entries (label TEXT NOT NULL)")
        async with connection.transaction() as transaction:
            assert isinstance(transaction, Transaction)
            await connection.execute("INSERT INTO entries VALUES (:label)",
                                     {"label": "outer"})
            try:
                async with connection.transaction():
                    await connection.execute("INSERT INTO entries VALUES (:label)",
                                             {"label": "inner"})
                    raise ValueError("rollback inner savepoint")
            except ValueError:
                pass
            try:
                await asyncio.create_task(connection.select("SELECT 1"))
            except TransactionException:
                pass
            else:
                raise AssertionError("A child used its parent's transaction")
            assert connection.inTransaction()
        assert not connection.inTransaction()
        assert await connection.select("SELECT label FROM entries") == [
            {"label": "outer"},
        ]
    finally:
        if connection.inTransaction():
            await connection.rollback()
        await connection.disconnect()

asyncio.run(main())
```

### 4. Inspect dialect options and compile without a server

Expect URL/options construction without connecting, bound predicate compilation,
and QueryException when a factory type lacks a compiler mapping.

```python
from sqlalchemy.dialects import sqlite
from orionis.database.compiler import SQLCompiler
from orionis.database.dialect import (
    build_engine_url,
    engine_options,
    missing_dependency_error,
    resolve_driver,
)
from orionis.database.exceptions import (
    MissingDatabaseDependencyException,
    QueryException,
)
from orionis.database.schema.column import Column
from orionis.orm.query.expressions import SelectPlan, WhereClause
from orionis.orm.schema.table import TableDefinition

config = {"driver": " SQLITE ", "database": ":memory:"}
assert resolve_driver(config) == "sqlite"
assert build_engine_url(config).drivername == "sqlite+aiosqlite"
assert build_engine_url(config, sync=True).drivername == "sqlite"
options = engine_options(config)
assert options["pool_size"] == 1 and options["max_overflow"] == 0
error = missing_dependency_error("mysql", ModuleNotFoundError("local probe"))
assert isinstance(error, MissingDatabaseDependencyException)
table = TableDefinition("entries", {"id": Column.integer("id")})
compiler = SQLCompiler(prefix="local_")
statement = compiler.compileSelect(SelectPlan(
    table, columns=("id",), wheres=[WhereClause("id", value=7)],
))
rendered = statement.compile(dialect=sqlite.dialect())
assert "local_entries" in str(rendered) and 7 in rendered.params.values()
try:
    compiler.compileCreateTable(TableDefinition("unsupported", {
        "value": Column.matchType("value"),
    }))
except QueryException:
    pass
else:
    raise AssertionError("An unmapped logical type compiled successfully")
```

### 5. Collect a schema and abort an exceptional declaration

Expect the local table and an index, column references preserved in Blueprint,
no table after an exception, and repeated connection selection rejected.

```python
import asyncio
from orionis.database.connection_manager import ConnectionManager
from orionis.database.schema.schema import Schema

class Settings:
    def config(self, key: str) -> dict:
        assert key == "database"
        return {"default": "sqlite", "connections": {
            "sqlite": {"driver": "sqlite", "database": ":memory:"},
        }}

async def main() -> None:
    manager = ConnectionManager(Settings())
    schema = Schema(manager)
    try:
        async with schema.create("entries") as table:
            table.id()
            label = table.string("label").nullable()
            table.index("label", name="entries_label_index")
            table.timestamps()
            assert label is table.columns()[1]
            assert len(table.definitions()) == 5
        await manager.connection().execute(
            "INSERT INTO entries (label) VALUES (:label)", {"label": "created"},
        )
        assert await manager.connection().select("SELECT label FROM entries") == [
            {"label": "created"},
        ]
        try:
            async with schema.create("aborted") as table:
                table.id()
                raise LookupError("abort declaration")
        except LookupError:
            pass
        assert await manager.connection().select(
            "SELECT name FROM sqlite_master WHERE name=:name", {"name": "aborted"},
        ) == []
        schema.connection(None)
        try:
            schema.connection("sqlite")
        except ValueError:
            pass
        else:
            raise AssertionError("Schema connection selection was overwritten")
    finally:
        await manager.disconnect()

asyncio.run(main())
```

### 6. Share a table definition with a real ORM model

Expect a model to use the same reusable definition created by Schema and the
real ConnectionManager/ConnectionResolver integration. The previous resolver
state is restored even when no manager was initially installed.

```python
import asyncio
from typing import ClassVar
from orionis.database.connection_manager import ConnectionManager
from orionis.database.schema.column import Column
from orionis.database.schema.schema import Schema
from orionis.orm.exceptions import OrmConfigurationException
from orionis.orm.model import Model
from orionis.orm.resolver import ConnectionResolver
from orionis.orm.schema.table import TableDefinition

ENTRY_V1 = TableDefinition("entries", {
    "id": Column.id(), "label": Column.string("label"),
})

class Entry(Model):
    table_definition = ENTRY_V1
    timestamps = False
    fillable: ClassVar[list[str]] = ["label"]

class Settings:
    def config(self, key: str) -> dict:
        assert key == "database"
        return {"default": "sqlite", "connections": {
            "sqlite": {"driver": "sqlite", "database": ":memory:"},
        }}

async def main() -> None:
    try:
        previous = ConnectionResolver.manager()
    except OrmConfigurationException:
        previous = None
    manager = ConnectionManager(Settings())
    ConnectionResolver.setManager(manager)
    try:
        schema = Schema(manager)
        assert await schema.createFromDefinition(ENTRY_V1)
        entry = await Entry.create({"label": "integrated"})
        found = await Entry.find(entry.id)
        assert found is not None and found.label == "integrated"
        assert await schema.createFromModel(Entry)
    finally:
        if previous is None:
            ConnectionResolver.clear()
        else:
            ConnectionResolver.setManager(previous)
        await manager.disconnect()

asyncio.run(main())
```

### 7. Discover, migrate, seed and rebuild a temporary application

This is a complete filesystem/container integration, not checkout migration.
Expect one migration/seeder execution, no repeated seed, committed tracking,
and seeder history removed after complete rollback before replay.

```python
import asyncio
import logging
import os
import sys
import tempfile
from pathlib import Path

previous = Path.cwd()
old_path = sys.path.copy()
with tempfile.TemporaryDirectory(prefix="database-lifecycle-") as directory:
    root = Path(directory)
    os.chdir(root)
    sys.path.insert(0, str(root))
    try:
        from orionis.database.contracts.connection_manager import IConnectionManager
        from orionis.database.migrations.events import MigrationEvents
        from orionis.database.migrations.migrator import Migrator
        from orionis.database.seeders.runner import SeederRunner
        from orionis.foundation.application import Application

        migrations = root / "local_migrations"
        seeders = root / "local_seeders"
        migrations.mkdir()
        seeders.mkdir()
        migration_source = (
            "from orionis.database.contracts.migration import Migration\n"
            "from orionis.database.contracts.schema import ISchema\n"
            "class CreateEntries(Migration):\n"
            "    def __init__(self, schema: ISchema) -> None:\n"
            "        self.schema = schema\n"
            "    async def up(self) -> None:\n"
            "        async with self.schema.create('entries') as table:\n"
            "            table.id()\n"
            "            table.string('label')\n"
            "    async def down(self) -> None:\n"
            "        await self.schema.drop('entries')\n"
        )
        seeder_source = (
            "from orionis.database.seeders.seeder import Seeder\n"
            "from orionis.orm.resolver import ConnectionResolver\n"
            "class SeedEntries(Seeder):\n"
            "    async def run(self) -> None:\n"
            "        await ConnectionResolver.connection().execute(\n"
            "            'INSERT INTO entries (label) VALUES (:label)',\n"
            "            {'label': 'seeded'},\n"
            "        )\n"
        )
        compile(migration_source, "m001.py", "exec")
        compile(seeder_source, "s001.py", "exec")
        (migrations / "m001.py").write_text(migration_source, encoding="utf-8")
        (seeders / "s001.py").write_text(seeder_source, encoding="utf-8")

        async def main() -> None:
            app = Application(base_path=root)
            app.withConfigPaths(database_migrations=migrations,
                                database_seeders=seeders)
            app.create()
            app.config("database", {"default": "sqlite", "connections": {
                "sqlite": {"driver": "sqlite", "database": str(root / "local.db")},
            }})
            await app.boot()
            manager = await app.make(IConnectionManager)
            try:
                migrator = Migrator(app, manager)
                runner = SeederRunner(app, manager)
                events = []
                reporter = MigrationEvents(on_start=events.append)
                assert await migrator.migrate(events=reporter) == ["m001"]
                assert events == ["m001"]
                assert await runner.seed() == ["s001"]
                assert await runner.seed() == []
                assert (await migrator.status())[0]["ran"]
                rows = await manager.connection().select("SELECT label FROM entries")
                assert rows == [
                    {"label": "seeded"},
                ]
                assert await migrator.rollback() == ["m001"]
                assert not (await migrator.status())[0]["ran"]
                assert await migrator.migrate() == ["m001"]
                assert await runner.seed() == ["s001"]
            finally:
                await manager.disconnect()

        asyncio.run(main())
    finally:
        logging.shutdown()
        sys.path[:] = old_path
        os.chdir(previous)
```

## Design characteristics

| Observed mechanism | Consumer consequence |
| --- | --- |
| Lazy root exports and engine construction | Importing a package/constructing a connection is distinct from resolving exports or opening a service connection. |
| Core statements and framework IR | The compiler uses SQLAlchemy Core without ORM sessions; emitted syntax/support remains dialect-dependent. |
| Slots on connections/managers/contexts/contracts | Storage is fixed for those instances; declaration markers without slots still have mutable public attributes. |
| Frozen InsertResult/MigrationEvents | Generated field assignment guards, not validation/deep immutability of referenced IDs/callbacks. |
| Task-owned mutable transaction stack | Nested savepoints reuse a raw connection; children cannot take over an active owner. |
| Mutable Blueprint with cached wrappers | Snapshots retain column objects; factory wrappers retain the collector/factory and capture declaration effects. |
| Discovery cache plus unique persisted stems | Files are discovered once per runner; filename identity determines recorded execution and ambiguity. |
| Migration context and seeder claim transaction | Unqualified ORM/schema work uses the chosen connection; seeder claims precede user code while migration tracking follows it. |

## Performance and concurrency

### Caches and materialization

Sources: [connection.py](../connection.py), [manager](../connection_manager.py),
[compiler](../compiler.py), [Blueprint](../schema/blueprint.py),
[Migrator](../migrations/migrator.py), [SeederRunner](../seeders/runner.py).
Raw text has a module-level LRU(256) keyed by SQL string; values/bindings are not
cached. Connection holds one compiler/engine; manager caches named Connection
objects without a public size bound. Disconnect removes manager entries only
when called on the manager; direct engine disposal keeps compiler definitions.

Compiler table/definition caches are per instance and unbounded; raw-table
columns are added eagerly before alias resolution. Same definition identity
can preserve stale metadata after mutation. Blueprint retains lists and per-name
factory wrappers; columns/definitions return shallow tuple snapshots. Runners
materialize tracking rows/pending classes and cache discovered class maps,
including empty discovery. Callbacks/class imports can retain external state.

select materializes all mappings inside acquisition. Batch insert uses reusable
parameterized executemany only when supportsBatchInsert says so; SQL expression
rows retain the explicit VALUES path. No timing, allocation, throughput or
portable complexity benchmark was performed in this documentation task.

### Transactions and concurrency limits

SQLite memory checkout uses one pooled connection with no overflow, retaining
one database and serializing independent transactions. A task trying unrelated
checkout while itself retaining that only connection can wait for pool timeout;
pool existence is not a deadlock detector. Files and other drivers use their
actual driver/pool policies, not this special memory guarantee.

Engine construction, manager/compiler mutation and runner discovery have no
whole-module thread/cross-loop locking contract. First engine construction is
synchronous before its first await, but sharing engines/raw connections across
loops is not certified. Manager disconnect/removal and concurrent callers are
not coordinated as a lease-based lifetime mechanism.

Per-task transactions reject inherited active ownership; cleanup pops levels
before awaited commit/rollback and is not shielded. Cancellation/state/resource
errors can propagate. Clearing a manager cache or disposing an engine is not
guaranteed to settle an active transaction. Plan/default/DDL callbacks and driver
work have their own blocking/async boundaries.

Migrations commit per step and do not claim pending names before up; no whole-run
lock prevents competing migrate calls. Seeders use a unique claim and per-step
transaction, plus a tracking-table creation retry. These mechanisms do not make
external effects or callback results exactly-once. Concurrent batch numbering
and DDL behavior depend on the database; callbacks execute synchronously and can
fail before work, during rollback reporting or after commit.

## Compatibility notes

Minimum declared Python is >=3.14. Source uses union/built-in generic annotations,
PEP 695 SchemaDefinition, dataclass slots, ContextVar and async contexts.
An annotation alone does not add runtime validation; TYPE_CHECKING-only names
may not be resolvable by arbitrary annotation evaluation. All executions here
used **CPython 3.14.6 on Windows**; no other runtime/platform was certified.

| Dependency | Declared range | Lockfile resolution | Installed validation version |
| --- | --- | --- | --- |
| `sqlalchemy` | `>=2.0.54,<3.0` | `2.1.1` | `2.1.1` |
| `aiosqlite` | `>=0.22.1` | `0.22.1` | `0.22.1` |
| `apscheduler` | `>=3.11.3,<4.0` | `3.11.3` | `3.11.3` |
| `asyncpg` | `>=0.31.0` | `0.31.0` | `0.31.0` |
| `aiomysql` | `>=0.3.2` | `0.3.2` | Not installed |
| `pymysql` | `>=1.2.3` | `1.2.3` | Not installed |
| `psycopg2-binary` | `>=2.9.13` | `2.9.13` | Not installed |
| `oracledb` | `>=26.0.0` | `26.0.1` | Not installed |
| `aioodbc` | `>=0.5.0` | `0.5.0` | Not installed |
| `pyodbc` | `>=5.3.0` | `5.3.0` | Not installed |
| `ruff` | `>=0.16.8` | `0.16.9` | `0.16.9` |

Evidence: [pyproject.toml](../../../pyproject.toml), [uv.lock](../../../uv.lock)
and installed distribution metadata recorded for this execution. A package
absent locally can still have a lock resolution; that does not make its driver
executable. asyncpg is installed but no PostgreSQL service was used. Sync helpers
prepare URLs/options but Connection remains async; there is no manager
scheduleTaskStore/sqlAlchemyJobStore method in this inspected module.

Unsupported type mappings, enum/pickle option omissions, transactional DDL
differences, ODBC setup and migration-prefix tracking are explicit limits,
not claims of universal SQL portability. SQLite memory behavior and TableCreation
awaitability differ from older repository instructions; source wins.

## Verification and limitations

### Inventory and tests

The inventory covers 39 Python sources, 35 public classes, 156 public/special
methods, nine functions, one type alias, 19 field blocks, eight export/constant
blocks and the explicit SeederEvents import alias. There are 229 runtime
reference blocks plus one complete Blueprint typing-file block.
Public candidates are traced to owning groups; imported toolkit types and
TYPE_CHECKING-only aliases are excluded from independent runtime API.

Native TestingEngine discovery/TestRunner ran **243/243 passed** with no raw
failures/errors/skips in a real booted temporary Application. A write/network
audit barrier allowed only the owned temporary root and asyncio's Windows
internal socketpair. No operation was blocked on the successful run. The first
run had 242 passed and one failed: bundled-admin-seeder discovery expected
Path.cwd()/database/seeders, absent in the sandbox. A temporary copy of those
files supplied that resource; the full suite then passed. The initial failure
was retained; no source/test was fixed or silently skipped.

Separate local probes verified Transaction's return/commit/rollback semantics,
SeederEvents alias identity, TableCreation's lack of awaitability, and the
nonempty migration-prefix QueryException. After native execution, a whole-tree
hash/mtime comparison found only the authorized README edit, no outside artifacts.

### Example and document status

| Example | Syntax | Local imports | Execution |
| --- | --- | --- | --- |
| 1 | Passed | Passed | Executed successfully. |
| 2 | Passed | Passed | Executed successfully. |
| 3 | Passed | Passed | Executed successfully. |
| 4 | Passed | Passed | Executed successfully. |
| 5 | Passed | Passed | Executed successfully. |
| 6 | Passed | Passed | Executed successfully. |
| 7 | Passed | Passed | Executed successfully. |

Both manuals have 79 corresponding headings and 237 byte-identical code blocks.
The 229 runtime references and full typing stub match the inspected source;
210 public candidates are mapped to their API groups. Seven examples per
language passed syntax, actual local-import resolution and independent execution.
All 137 relative links/anchors per manual and 22 skill links were checked.
The skill YAML has only name/description, with derived name orionis-database.
Scoped Ruff passed for orionis/database and tests/database without fixes/cache;
editor diagnostics are clear for all three deliverables.

The full baseline comparison includes hidden, ignored and untracked files,
source/tests/config/dependencies, directory entries, prior module docs, Git index
and HEAD. Documentation writes target only this module's direct docs. Scripts,
results, caches and temporary DB/resource trees stay outside the repository.
No additional docs content was removed; the final directory contains exactly
README.md, README.es.md and SKILL.md, with no subdirectories or artifacts.

### Remaining limits

Query sanitization is specific to caught execution errors, not a universal
exception boundary. Parent/child transaction handling, memory pooling,
unsupported factory mappings, event aliases, fresh semantics and prefix tracking
were documented from their owning implementations. DDL/external side effects
cannot be summarized as universal transactional guarantees. No source changes,
automatic formatting, dependency installs, benchmarks or Git index edits were
performed by this documentation task.

> ⚠️ Not specified in the source: whole-module thread/cross-loop safety, atomic connection replacement/disposal with in-flight use, or universal rollback of external migration/seeder effects.

> ⚠️ Not executed in this environment: live MySQL/PostgreSQL/Oracle/SQL Server services, deployment-specific ODBC/permissions/DDL behavior, Linux/macOS/free-threaded execution or Python versions other than 3.14.6.
