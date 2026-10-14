# Backends and production operation

The query API is shared, but backend capabilities differ. Choose types and operations supported by the target and verify migrations against it. SQLite suits isolated examples; it does not demonstrate another server's locking, identity, or DDL behavior.

## Server connections

PostgreSQL applies `charset`, `search_path`, and `sslmode` to both async and sync paths. The async path uses `asyncpg`; the sync path, also used by the scheduler job store, uses `psycopg2`. Configuring persistent tasks should not lose the search path. MySQL exposes charset, collation, strict mode, and engine. Oracle accepts service, SID, DSN, or TNS; SQL Server needs a system ODBC driver in addition to its Python extra.

TLS options matter. The SQL Server template includes `DB_TRUST_SERVER_CERTIFICATE=True`; adapt that to your certificate-validation policy before production. Keep credentials out of application manuals, logs, and repositories. Pool options depend on the dialect and effective configuration; do not assume undocumented `DB_POOL_*` environment variables exist.

## Amazon Redshift

Redshift uses the official `redshift-connector` with `sqlalchemy-redshift`, rather than treating the service as PostgreSQL through asyncpg. Basic configuration:

```dotenv
DB_CONNECTION=redshift
DB_HOST=warehouse.example.test
DB_PORT=5439
DB_DATABASE=dev
DB_USERNAME=app_user
DB_PASSWORD=replace-with-secret
DB_REDSHIFT_SSL=True
DB_REDSHIFT_SSLMODE=verify-full
DB_REDSHIFT_TIMEOUT=30
```

`verify-full` is the default; `verify-ca` is also supported. `DB_REDSHIFT_TIMEOUT=null` disables the socket timeout. IAM adds `DB_REDSHIFT_IAM`, `DB_REDSHIFT_REGION`, `DB_REDSHIFT_CLUSTER_IDENTIFIER`, `DB_REDSHIFT_DB_USER`, and optionally `DB_REDSHIFT_PROFILE`. Without an explicit profile, the connector uses its credential chain. Serverless adds `DB_REDSHIFT_IS_SERVERLESS`, `DB_REDSHIFT_SERVERLESS_WORK_GROUP`, and `DB_REDSHIFT_SERVERLESS_ACCT_ID`.

The connector is synchronous; Orionis runs connection, query, result, and transaction-control work on a worker reserved for each checked-out Core connection. Independent queries may use different workers; one transaction keeps its worker. Cancellation waits for in-flight operations before cleanup and does not guarantee aborting server work.

| Redshift capability | Consequence |
|---|---|
| No savepoints | Do not nest transactions. |
| No SELECT row locks | `lockForUpdate()` and `sharedLock()` raise `QueryException` at execution, including nested/aggregate plans. |
| No DML `RETURNING` | Omitted server-generated identities are not returned in `last_insert_id`. |
| `IDENTITY(1,1)` | `autoIncrement()` can create native identity, but a model needing its key immediately should use a client-generated key. |
| No traditional indexes | Avoid index declarations. |
| Informational PK/unique/FK | Do not rely on these declarations for exclusion or uniqueness. |

`supportsUniqueConstraints()` returns `False`. Database cache, database sessions, database queues, tracked seeders, and the scheduler database job store reject Redshift: they need enforced uniqueness and, for the scheduler, indexes. These restrictions do not prevent analytical queries or compatible models on Redshift.

## Diagnostics, resources, and volume

`db:show`, `db:table`, and `db:wipe` understand Redshift catalogs and qualified names. Size metrics use allocated 1 MB blocks; limited permissions or empty tables can leave sizes unknown. Displayed constraints are declarations, rather than enforcement guarantees.

Engines initialize lazily and are reused. Close direct connections when finished; let application lifecycle close managed connections. Manager `disconnect(name=None)` closes all cached connections; a supplied name closes only that connection. Do not disconnect a shared service while other tasks use it.

Reads materialize full results. Filter, select columns, and paginate instead of designing a large exporter around assumed cursor streaming. Split large writes and remember each batch consumes memory. Distinguish configuration/driver errors from SQL failures; track latency, row counts, and business operations without exposing bound data. This layer does not guarantee automatic transaction retries.

Independent operations use `engine.begin()` contexts and release their connection after each call; transactions retain their connection until nested levels finish. Parsed raw SQL uses an LRU cache of 256 texts without turning variable values into interpolated SQL. PostgreSQL batch inserts count rows returned by `RETURNING`, including differences when a trigger suppresses an input row.

Campaigns using real credentials/servers belong under local Git-ignored `tests/real_database`, with configuration independent of `.env`. Their existence or historical references do not prove a current run. Changing `DB_CONNECTION` does not turn SQLite tests into coverage for every backend. Validate drivers, SQL, DDL, types, cancellation, and cleanup separately for each destination.
