# Database integration boundaries

The full model and query language reference lives in the
[ORM manual](../../orm/README.es.md). This note records the persistence guarantees
used by [Auth](../../auth/docs/README.md) and Session.

## Architecture

Model and raw query builders share `QueryBuilderBase` and produce Orionis IR plans.
`Connection` passes these to `SQLCompiler` and SQLAlchemy Core's async engine.
SQLAlchemy Session, declarative models and ORM relationships are not used.

Connections are obtained from the configured resolver. Transactions are task-local
and nested scopes use SAVEPOINT. Do not execute concurrent statements through one
inherited transactional connection; independent tasks need independent transactions.
SQLite concurrency tests use a file, not a shared `:memory:` connection.

## Auth persistence

Role and permission names are globally unique. Owners are polymorphic type/key
pairs with canonical textual keys, supporting integer, string and UUID models.
Pivots have composite primary keys and restrictive foreign keys to roles and
permissions. Permanent owner deletion requires application cleanup because no
single owner table can be referenced by a polymorphic FK.

Permission loading is one UNION SELECT. The compiler flattens consecutive UNION
operators of the same kind; mixed operators use derived tables to preserve order
without invalid SQLite parentheses. Database read isolation remains configured by
the application; this is not a cross-request permission cache.

Unique constraints decide duplicate registrar writes. Failed inserts are rolled
back locally before duplicate recovery, so PostgreSQL transactions are not left
aborted. Schemaless insertions may not return generated IDs; Auth retrieves them
using their unique name or digest when needed.

PAT storage contains only a SHA-256 digest, plus owner, abilities and timestamps.
Usage and revocation are conditional updates. Session SQL storage uses IR plans,
including prefixes and dialect quoting, and cannot recreate a deleted session
through conditional `update()`.

## Errors and migrations

SQL errors expose the connection and error class, not SQL values or driver detail
messages. Engine parameters are hidden and exception chaining is suppressed at
the public query boundary to reduce credential exposure.

Migrations already applied are not re-run when their source changes. Existing
Auth tables require a reviewed migration or a rebuild only when data is disposable.
Back up data before changing keys, constraints or indexes. The audit tests apply
and roll back real migrations only on temporary databases.
