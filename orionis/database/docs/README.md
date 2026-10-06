# orionis.database

> `orionis.database` manages named asynchronous SQL connections, parameterized execution, task-local transactions, schema creation, migrations, and seeders for Orionis.

## Overview

This module is Orionis's database runtime beneath the query builder and ORM. `ConnectionManager` turns validated application configuration into reusable named `Connection` objects. A connection lazily creates a SQLAlchemy async engine, or a thread-backed Core engine for Redshift, compiles Orionis query plans, executes raw parameterized SQL, exposes schema helpers, and owns transactions.

`Migrator` discovers versioned migration classes and records batches; `SeederRunner` discovers seeders and can claim once-only execution. `Schema` converts fluent blueprints or ORM table definitions into physical tables. Applications normally obtain connections through `ConnectionResolver`/query builders or use the database and schema facades, while extension and tooling code may use these classes directly.

## Requirements

- Python 3.14 or newer.
- `sqlalchemy[asyncio]>=2.0.54,<3.0` and `aiosqlite>=0.22.1`, installed by Orionis.
- Driver extras for other databases: `orionis[mysql]`, `orionis[pgsql]`, `orionis[oracle]`, `orionis[sqlserver]`, or `orionis[redshift]`.
- A reachable server and credentials for server databases; SQLite can use a file or `:memory:`.
- Migration and seeder directories are resolved relative to the application base path.

## Quick start

Use a standalone in-memory SQLite connection with bound parameters:

```python
import asyncio

from orionis.database import Connection


async def main() -> None:
    connection = Connection(
        "docs",
        {"driver": "sqlite", "database": ":memory:", "prefix": ""},
    )
    try:
        await connection.statement(
            "CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL)"
        )
        await connection.execute(
            "INSERT INTO notes (body) VALUES (:body)",
            {"body": "hello"},
        )
        print(await connection.select("SELECT id, body FROM notes"))
    finally:
        await connection.disconnect()


asyncio.run(main())  # [{'id': 1, 'body': 'hello'}]
```

The engine is created on the first statement and disposed explicitly at the end.

Validation: **Executed successfully** on CPython 3.14.6.

## Core concepts

### Manager versus connection

`ConnectionManager` owns configuration, a default connection name, and a cache of connection objects. `connection(name=None)` lazily constructs and reuses the selected connection. `disconnect` disposes and removes cached engines without deleting configuration.

### Plans versus raw SQL

The ORM/query builder sends immutable select/insert/update/delete plans to `Connection`, where `SQLCompiler` creates dialect-neutral SQLAlchemy statements and applies table prefixes. Raw strings are supported for `select`, `execute`, and `statement`, using named `:parameter` bindings.

### Transaction ownership

Transaction state is held in a `ContextVar` and tagged with the current asyncio task. The first `begin` opens a dedicated connection and root transaction; nested `begin` creates a savepoint on supported backends. Redshift rejects nesting with `TransactionException`. `transaction()` commits the current level on success and rolls it back when an exception escapes.

### Schema, migrations, and seeders

`Schema` builds table definitions from a fluent `Blueprint` or an ORM model. A `Migration` supplies async `up` and `down`; the migrator records names and batches in a tracking table. A `Seeder` supplies async `run`; the runner discovers classes and optionally records once-only executions.

## Module structure

| Area | Responsibility |
|---|---|
| `connection.py`, `connection_manager.py` | Engine lifecycle, execution, transactions, named connection reuse. |
| `compiler.py`, `dialect.py` | Query-plan compilation, URLs/options, session setup, driver validation. |
| `redshift.py`, `threaded/` | AWS connector dialect capabilities and thread-backed Core execution. |
| `schema/`, `schema_provider.py` | Blueprint constraints and physical table operations. |
| `migrations/` | Discovery, batch tracking, migrate/rollback/reset/refresh/fresh/status. |
| `seeders/` | Seeder contract, discovery, events, concurrency-safe run tracking. |
| `entities/`, `contracts/`, `exceptions.py` | Results, public interfaces, and database error hierarchy. |
| `provider.py` | Connection manager singleton and ORM resolver wiring. |

## Public API

### `ConnectionManager`

```text
manager.connection(name=None) -> Connection
manager.addConnection(name, config) -> None
manager.hasConnection(name) -> bool
manager.configFor(name=None) -> dict
manager.getDefaultName() -> str
manager.setDefaultName(name) -> None
await manager.disconnect(name=None)
```

The manager validates names/config dictionaries and reports unknown connections with `ConnectionNotFoundException`. Returned configuration is copied. Calling `disconnect()` with no name disconnects all cached connections; selecting a name affects only that connection.

### `Connection`

Recommended construction is through the manager. Direct construction accepts a connection name and normalized config, validating the driver immediately but delaying engine creation.

#### Queries

| Method | Return |
|---|---|
| `select(plan_or_sql, bindings=None)` | Materialized `list[dict]`. |
| `insert(plan)` | `InsertResult(last_insert_id, row_count)`; batch inserts omit generated id. |
| `update(plan)`, `delete(plan)` | Affected row count. |
| `scalar(select_plan)` | First column of first row or `None`. |
| `execute(sql, bindings=None)` | Affected row count for raw DML. |
| `statement(sql, bindings=None)` | `True` for successful DDL/maintenance. |

#### Schema and lifecycle

`createTable(definition, if_not_exists=True)` and `dropTable(name, schema=None, if_exists=True)` apply configured prefixes. `disconnect()` disposes the cached engine; a later operation creates a new one.

#### Transactions

`begin`, `commit`, and `rollback` control the innermost transaction/savepoint. `transaction()` is the preferred async context manager. `inTransaction()` reports only state owned by the current task.

### `Schema` and blueprint types

The schema service selects a connection with `.connection(name)`. `create(name)` returns a `TableCreation` builder; `createFromDefinition` and `createFromModel` materialize existing definitions; `drop` removes a table. `Blueprint` accepts column definitions plus `PrimaryKey`, `Unique`, `Index`, `ForeignKey`, `Timestamps`, and `Comment` objects exported from `orionis.database.schema`.

### `Migration` and `Migrator`

Migration classes implement `up()` and `down()`. `Migrator` selects the requested connection and exposes `migrate`, `rollback`, `reset`, `refresh`, `fresh`, and `status`; steps run transactionally and lifecycle callbacks come from `MigrationEvents`. Migration files are ordered by their names, and the tracking table records batch numbers.

### `Seeder`, `SeederRunner`, and `SeederEvents`

Seeder subclasses implement async `run`. The runner can execute a named class or discovered seeders, optionally force reruns, and emits before/after/error events. Once-only claims are persisted so competing workers do not both run the same recorded seeder.

### Exceptions

`DatabaseException` is the base for missing connection/migration/dependency, query, transaction, and unsupported-driver errors. These types are exported at package level.

## Common workflows

### Execute a parameterized query

Obtain a connection, pass user data through a bindings mapping, consume the returned plain dictionaries, and disconnect only when you own the connection lifecycle. Never interpolate user values into raw SQL.

### Run an atomic unit of work

Use `async with connection.transaction():`. Nested contexts use savepoints except on Redshift, which supports root transactions only. Keep all transactional queries in the task that opened the transaction; child tasks are explicitly rejected.

### Apply migrations

Create timestamp/version-prefixed migration files with `Migration` subclasses, then run the reactor migration commands or call `Migrator`. Rollback reverses the selected latest batches in reverse application order.

### Seed application data

Put `Seeder` subclasses in the configured seeder path and use `db:seed`/`seed` or `SeederRunner`. Use once-only tracking for idempotent administrative seeders and force only when deliberate reruns are safe.

## Examples

### Commit a transaction

```python
import asyncio

from orionis.database import Connection


async def main() -> None:
    db = Connection("tx", {"driver": "sqlite", "database": ":memory:"})
    try:
        await db.statement("CREATE TABLE counters (value INTEGER NOT NULL)")
        async with db.transaction():
            await db.execute("INSERT INTO counters (value) VALUES (:value)", {"value": 3})
        print(await db.select("SELECT value FROM counters"))  # [{'value': 3}]
    finally:
        await db.disconnect()


asyncio.run(main())
```

Validation: **Executed successfully** on CPython 3.14.6.

### Roll back when an exception escapes

```python
import asyncio

from orionis.database import Connection


async def main() -> None:
    db = Connection("rollback", {"driver": "sqlite", "database": ":memory:"})
    try:
        await db.statement("CREATE TABLE entries (value TEXT NOT NULL)")
        try:
            async with db.transaction():
                await db.execute("INSERT INTO entries (value) VALUES ('temporary')")
                raise RuntimeError("cancel")
        except RuntimeError:
            pass
        print(await db.select("SELECT value FROM entries"))  # []
    finally:
        await db.disconnect()


asyncio.run(main())
```

Validation: **Executed successfully** on CPython 3.14.6.

### Use a nested savepoint

```python
import asyncio

from orionis.database import Connection


async def main() -> None:
    db = Connection("nested", {"driver": "sqlite", "database": ":memory:"})
    try:
        await db.statement("CREATE TABLE events (name TEXT NOT NULL)")
        async with db.transaction():
            await db.execute("INSERT INTO events VALUES ('outer')")
            try:
                async with db.transaction():
                    await db.execute("INSERT INTO events VALUES ('inner')")
                    raise ValueError("rollback savepoint")
            except ValueError:
                pass
        print(await db.select("SELECT name FROM events"))  # [{'name': 'outer'}]
    finally:
        await db.disconnect()


asyncio.run(main())
```

Only the inner savepoint rolls back; the root transaction commits.

Validation: **Executed successfully** on CPython 3.14.6.

### Define a migration and seeder

```python
from orionis.database import Migration, Seeder
from orionis.support.facades import DB, Schema


class CreateFlags(Migration):
    async def up(self) -> None:
        async with Schema.create("flags") as table:
            table.id()
            table.string("name", 80)
            table.unique("name")

    async def down(self) -> None:
        await Schema.drop("flags")


class DefaultFlags(Seeder):
    async def run(self) -> None:
        await DB.table("flags").insert({"name": "enabled"})
```

The migrator binds the selected connection while it invokes these facade operations; the application container resolves the facade services.

Validation: **Import-only** on CPython 3.14.6; execution requires a booted application container and migration/seeder runtime.

## Configuration

`database.default` uses `DB_CONNECTION` and defaults to `sqlite`. Common settings include `DB_URL`, `DB_DATABASE`, `DB_PREFIX`, `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, and `DB_CHARSET`.

| Driver | Important additional settings | Default port/path |
|---|---|---|
| SQLite | `DB_FOREIGN_KEYS`, `DB_BUSY_TIMEOUT`, `DB_JOURNAL_MODE`, `DB_SYNCHRONOUS` | `database/database.sqlite` |
| MySQL | `DB_SOCKET`, `DB_COLLATION`, `DB_PREFIX_INDEXES`, `DB_STRICT`, `DB_ENGINE` | `3306` |
| PostgreSQL | `DB_SEARCH_PATH`, `DB_SSLMODE`, `DB_PREFIX_INDEXES` | `5432` |
| Oracle | `DB_SERVICE_NAME`, `DB_SID`, `DB_DSN`, `DB_TNS`, encodings | `1521` |
| SQL Server | `DB_ENCRYPT`, `DB_TRUST_SERVER_CERTIFICATE`, `DB_ODBC_DRIVER` | `1433` |
| Amazon Redshift | `DB_REDSHIFT_SSL`, `DB_REDSHIFT_SSLMODE`, `DB_REDSHIFT_TIMEOUT`, IAM/Serverless options | `5439` |

Migration/seeder table names and paths are supplied by their application configuration/commands. URLs, when present, take precedence over decomposed connection fields in dialect URL construction.

### Amazon Redshift

Install the optional extra in an application:

```sh
uv add 'orionis[redshift]'
```

For a framework checkout, use `uv sync --extra redshift`. The extra declares `redshift-connector>=2.1.17,<3.0`, the official AWS Python driver, and `sqlalchemy-redshift>=1.0.0,<2.0`. PostgreSQL's `asyncpg` or `psycopg2` drivers are not used for Redshift.

The editable application template exposes `Redshift` in `BootstrapDatabase.connections`; both it and `ConnectionName.REDSHIFT` are public exports from `orionis.foundation.config.database`.

```dotenv
DB_CONNECTION="redshift"
DB_HOST="your-cluster.endpoint.amazonaws.com"
DB_PORT=5439
DB_DATABASE="dev"
DB_USERNAME="awsuser"
DB_PASSWORD="replace-with-database-credential"
DB_REDSHIFT_SSL=True
DB_REDSHIFT_SSLMODE="verify-full"
DB_REDSHIFT_TIMEOUT=30
```

`verify-full` is the default TLS policy; `verify-ca` is also supported. `DB_REDSHIFT_TIMEOUT=null` selects no socket timeout. PostgreSQL's `DB_SSLMODE` is independent of `DB_REDSHIFT_SSLMODE`, so configuring one backend does not invalidate the other.

IAM uses `DB_REDSHIFT_IAM=True`, `DB_REDSHIFT_REGION`, `DB_REDSHIFT_CLUSTER_IDENTIFIER`, and `DB_REDSHIFT_DB_USER`. `DB_REDSHIFT_PROFILE` selects an AWS profile; when omitted, the official connector uses the SDK credential chain. Serverless additionally exposes `DB_REDSHIFT_IS_SERVERLESS`, `DB_REDSHIFT_SERVERLESS_WORK_GROUP`, and `DB_REDSHIFT_SERVERLESS_ACCT_ID`. Credentials and endpoint resolution remain the responsibility of the official connector.

The existing asynchronous query API remains unchanged:

```python
import asyncio

from orionis.database import Connection
from orionis.foundation.config.database import Redshift


async def main() -> None:
    connection = Connection("warehouse", Redshift().toDict())
    try:
        rows = await connection.select("SELECT :value AS value", {"value": 1})
        print(rows)
    finally:
        await connection.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
```

This example requires a reachable Redshift endpoint; it was not run against AWS. Local validation uses the actual AWS DBAPI/dialect for construction and SQL compilation, and an isolated blocking SQLite Core engine for adapter execution and cancellation.

The connector is synchronous. Blocking connection/query/result/transaction work runs on one reserved worker per checked-out Core connection. Independent queries may use separate workers; one transaction keeps its own worker. Cancellation waits for an in-flight operation to finish before cleanup, so it does not guarantee that server-side work is aborted. The same official connector also serves synchronous scheduler engines.

Redshift-specific limitations:

- No savepoints or nested transactions.
- No DML `RETURNING` or PostgreSQL sequences. `autoIncrement()` emits native `IDENTITY(1,1)`, but an omitted server-generated key is not returned in `InsertResult.last_insert_id`. Provide a client-generated primary key when an ORM model must know its key immediately.
- No traditional indexes. Avoid index declarations in Redshift schemas.
- Primary, unique and foreign keys are informational only. Redshift is not a suitable backend for framework cache locks, once-only seeder claims, or other workflows requiring enforced uniqueness.
- `db:show`, `db:table` and `db:wipe` use Redshift catalogs and qualified names. Sizes use allocated 1-MB blocks; restricted or missing size metrics are unknown, and empty tables may have no size entry. Reported constraints are declarations, not enforcement guarantees.

## Integration with Orionis

`ConnectionManagerProvider` registers the manager singleton and installs it into ORM `ConnectionResolver` during boot. `SchemaProvider` binds the schema service/facade. Query builders and models create plans but connections compile and execute them. Cache, auth, queues, scheduler, sessions, and migrations use the same manager/resolver.

Reactor commands expose migrate, rollback, reset, refresh, fresh, status, seed, database inspection, and wipe workflows. Application shutdown disconnects managed engines.

## Errors and edge cases

- Unsupported driver names fail at `Connection` construction. Missing optional driver modules raise `MissingDatabaseDependencyException` when the engine is built.
- SQLAlchemy execution errors become sanitized `QueryException` messages naming the connection and exception type, without SQL, bindings, or credentials.
- `commit`/`rollback` without active state raise `TransactionException`.
- An active transaction cannot be used from a child task; run its queries in the task that began it.
- Raw SQL accepts named bindings. An empty binding mapping is equivalent to no parameters.
- Result rows are materialized before releasing the connection; very large selects therefore allocate the full result list.
- Migration discovery rejects malformed/duplicate classes and missing migrations; destructive `fresh`/reset workflows should be used deliberately.

## Performance and concurrency

Engines and connection objects are lazy and cached. Non-transactional operations use `engine.begin()` contexts and release them after each call. Transactions retain one raw connection until all nested levels settle. Parsed raw SQL text is cached with an LRU of 256 statements.

Transaction state is task-local and nested work uses savepoints. Concurrent tasks can share a `Connection` object for independent operations but cannot inherit its open transaction. Pool sizing and driver options come from normalized connection configuration.

Migrator and seeder tracking uses database transactions/conditional claims rather than process-only locks, so separate workers observe persisted state.

## Compatibility

Orionis declares Python 3.14+, SQLAlchemy 2.0.54+, and aiosqlite 0.22.1+; validation used CPython 3.14.6 on Windows. Supported drivers are SQLite, MySQL, PostgreSQL, Oracle, SQL Server, and Amazon Redshift. The lockfile's resolved versions are not minimum support claims; use the project extras for declared driver minimums.

## Verification notes

Exports, connection/manager, compiler/dialects, transactions, schema, migrations, seeders, providers, configuration, ORM integration, and `tests/database` were inspected. All 243 database tests passed through the Orionis runner on CPython 3.14.6. The four connection programs were executed successfully; the migration/seeder definitions were imported without running application-bound operations.
