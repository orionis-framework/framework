# Configure connections and execute SQL

## Choose a backend

Application configuration lives in `config/database.py`, under `database`. `BootstrapDatabase` extends the `Database` entity and defines a default connection and named connections. `DB_CONNECTION` defaults to `sqlite`. Resolving a name creates a connection object; its engine initializes on the first operation.

| Driver | Additional installation | Common configuration |
|---|---|---|
| `sqlite` | None | `DB_DATABASE`, `DB_FOREIGN_KEYS`, `DB_BUSY_TIMEOUT` |
| `mysql` | `uv add 'orionis[mysql]'` | host, port 3306, database, credentials, charset/collation |
| `pgsql` | `uv add 'orionis[pgsql]'` | port 5432, `DB_SEARCH_PATH`, `DB_SSLMODE` |
| `oracle` | `uv add 'orionis[oracle]'` | port 1521, service/SID/DSN/TNS |
| `sqlserver` | `uv add 'orionis[sqlserver]'` | port 1433, ODBC driver and TLS |
| `redshift` | `uv add 'orionis[redshift]'` | port 5439, TLS and AWS connector options |

`orionis[database]` bundles optional drivers. In a framework checkout, use a command such as `uv sync --extra pgsql`. Installing a Python package does not create a server or install a system ODBC driver. Missing optional dependencies produce `MissingDatabaseDependencyException` when that backend initializes.

## First SQLite program

This program creates data only in memory. User values are bound using `:name` placeholders.

```python
import asyncio
from orionis.database import Connection


async def main() -> None:
    db = Connection("docs", {"driver": "sqlite", "database": ":memory:"})
    try:
        await db.statement(
            "CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL)"
        )
        affected = await db.execute(
            "INSERT INTO notes (body) VALUES (:body)", {"body": "Hello"}
        )
        rows = await db.select(
            "SELECT id, body FROM notes WHERE body = :body", {"body": "Hello"}
        )
        assert affected == 1
        assert rows == [{"id": 1, "body": "Hello"}]
    finally:
        await db.disconnect()


asyncio.run(main())
```

`select()` materializes `list[dict]`, rather than returning an open cursor. `execute()` returns affected rows; `statement()` returns `True` on successful completion. `insert(plan)` returns `InsertResult` with `last_insert_id` and `row_count`; batch inserts do not guarantee a generated identity. `scalar(plan)` returns the first column or `None`. These last methods accept query-builder plans, rather than arbitrary SQL.

## Work inside an application

After bootstrap, use the facade instead of constructing and disconnecting a connection for every request:

```python
from orionis.support.facades import DB


async def find_note(body: str):
    return await DB.table("notes").where("body", body).first()


async def count_notes():
    return await DB.select("SELECT COUNT(*) AS total FROM notes")
```

`DB.connection("reporting")` returns a new gateway. `DB.connection("reporting").table("notes")` targets the registered connection without changing other consumers' selection. The manager provides `connection(name)`, `hasConnection(name)`, `configFor(name)`, `addConnection(name, config)`, and `setDefaultName(name)`. Changing the default affects future consumers without an explicit selection: do that during configuration, rather than using it for request isolation.

## Configuration values and common failures

The current SQLite template uses `database/database.sqlite`, a 5000 ms busy timeout, `DELETE` journal mode, `NORMAL` synchronization, and foreign keys `OFF`. Deliberately enable `DB_FOREIGN_KEYS` when your application relies on references. Server connections share `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME`, and `DB_PASSWORD`; MySQL adds `DB_SOCKET`, `DB_COLLATION`, `DB_STRICT`, and `DB_ENGINE`. A configured URL takes precedence in dialects that support it; inspect the driver's configuration entity before copying `DB_URL` between backends.

Other template settings include `DB_PREFIX` and `DB_PREFIX_INDEXES`; SQLite exposes `DB_JOURNAL_MODE` and `DB_SYNCHRONOUS`; Oracle exposes `DB_SERVICE_NAME`, `DB_SID`, `DB_DSN`, `DB_TNS`, `DB_ENCODING`, and `DB_NENCODING`; SQL Server exposes `DB_ENCRYPT`, `DB_TRUST_SERVER_CERTIFICATE`, and `DB_ODBC_DRIVER`. `DB_CHARSET` applies according to the active driver; do not copy incompatible charset values across backends.

An unknown name raises `ConnectionNotFoundException`; an invalid driver raises `UnsupportedDriverException`; SQL failures raise `QueryException`. Execution errors sanitize SQL, bindings, and credentials. Log business context and the connection name without secrets. Table/column names are not bindable values: choose identifiers from a controlled allowlist. Raw SQL does not automatically add table prefixes either.

Continue with [ORM queries](../../../orm/docs/en/querying.md) or [transactions](transactions.md).
