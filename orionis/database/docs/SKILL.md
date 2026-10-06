---
name: "orionis-database"
description: >-
  Use when a task involves understanding, integrating, or troubleshooting
  the orionis.database module, named connections, driver configuration,
  SQL compilation, task-owned transactions, schema declarations, migrations,
  or seeder tracking. Consult the bundled documentation and inspect the local
  implementation to select verified APIs, respect behavioral constraints,
  and validate proposed usage.
---

# Work with orionis.database

Read [README.md](README.md) or [README.es.md](README.es.md) for the task's API.
Treat this as a repository-local entry point, not platform installation or
registration. Modify framework source only for an explicit request within the
authorized scope.

## Locate and verify the owner

1. Consult [imports](README.md#imports-and-package-exports),
   [module structure](README.md#module-structure), and
   [literal declarations](README.md#literal-declarations). Root exports are lazy
   and selective. Import Schema from its defining module, not a fabricated root
   export. Distinguish runtime Blueprint from its editor-only typing file.
2. Read [../connection.py](../connection.py),
   [../compiler.py](../compiler.py), and [../dialect.py](../dialect.py) for the
   actual control path. Inspect ORM plans/types when a compiler input is unclear;
   do not replace SQLAlchemy Core with its ORM Session/declarative mapping.
3. Preserve literal signatures/defaults and distinguish annotations, generated
   dataclass operations, inherited ORM column methods, import aliases, and actual
   code behavior. SeederEvents is MigrationEvents, not a separate class.

## Respect connection and SQL boundaries

- Check [requirements](README.md#requirements) and
  [dialect helpers](README.md#dialect-functions-and-configuration). Validate the
  configured driver, optional async/sync package and deployment separately.
  A lockfile version or URL object is not an installed driver or reachable DB.
  Do not install dependencies without the future request's authorization.
- Read [manager behavior](README.md#connectionmanager). configFor returns a live
  mapping; addConnection retains it and does not evict an existing Connection.
  Names are not consistently normalized. Disconnecting a Connection directly
  does not remove its manager entry or update its captured configuration.
- Use bindings for values and trusted SQL for identifiers/fragments. Inspect
  [queries](README.md#connection-query-and-lifecycle-api) and
  [compiler](README.md#sqlcompiler). Select materializes rows; scalar expects a
  SelectPlan. Raw bindings are ignored on the plan path. Empty update/delete
  filters are not a safety guard, and row counts/inserted keys are driver-specific.
- Do not infer type support from a factory/stub. StrictArray, MatchType,
  NumericCommon and SchemaType lack compiler mappings; enum/pickle options have
  explicit omissions. Cached definition identity is not deep-change invalidation.
- Separate sanitized QueryException from acquisition, commit/rollback, URL,
  callback or toolkit errors that can propagate differently. Do not print live
  URLs, parameters or driver details while diagnosing private configuration.

## Respect lifecycle and ownership

- Read [transactions](README.md#transactions-and-task-ownership). Async-with
  yields Transaction, not Connection; issue queries through Connection. Nested
  begin opens a savepoint. Children cannot use an active parent's state, and
  cleanup is not shielded against cancellation. Do not share raw engines/contexts
  across loops based only on ContextVar or pool existence.
- Read [concurrency](README.md#transactions-and-concurrency-limits). SQLite memory
  uses one exclusive pooled connection, not StaticPool. Avoid waiting for another
  checkout while holding that only connection. Own database cleanup explicitly;
  manager disposal does not promise to settle active transactions.
- Check [schema behavior](README.md#schema-and-tablecreation) and
  [declaration collectors](README.md#blueprint-column-and-declaration-markers).
  Use async-with for create; TableCreation is not awaitable. Connection selection
  is single-use, even for None. Blueprint returns mutable definitions and tuple
  snapshots; duplicate columns, primary declarations and timestamp defaults have
  specific semantics. Runtime marker acceptance and SchemaDefinition differ.
- Inspect [migrations](README.md#migration-migrator-and-tracking). Use actual
  application path/build APIs, stable unique stems and importable local classes.
  Discovery is cached. Rollback steps count batches, fresh invokes down rather
  than wiping all tables, and full rollback can clear seeder history.
- Keep the verified migration-prefix limit visible: its raw tracking SQL uses
  unprefixed migrations while DDL applies Connection's prefix. Do not conceal
  the resulting failure or silently change implementation during documentation.
- Read [seeding](README.md#seeder-and-seederrunner) and
  [events/context](README.md#events-and-migration-connection-context). Seeder
  claims precede run and commit with data; a visible committed record permits a
  conflicting attempt to skip. Callback errors and nontransactional/external
  effects prevent universal exactly-once/rollback guarantees. Do not make async
  callbacks expecting the synchronous event hooks to await them.

## Validate safely and report evidence

Consult [verification](README.md#verification-and-limitations) and the existing
[../../../tests/database](../../../tests/database). Standard project commands:

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe -B reactor test --start-dir="tests/database" --verbosity=2
.\.venv\Scripts\python.exe -B -m ruff check --no-cache orionis/database tests/database
```

Review bootstrap/log/cache/database effects before execution. Under a read-only
checkout boundary, use native TestingEngine/TestRunner with a booted temporary
Application, disabled result cache and correctly rooted discovery. The bundled
admin-seeder test expects cwd/database/seeders; supply an owned temporary copy
for that path, not a live checkout DB or credentials. Check discovery count and
raw failures/errors/skips, not only a summary.

Compile examples, resolve imports to the inspected checkout, and execute safe
scripts independently with bytecode disabled. Keep scripts, reports and databases
outside the repo. Permit only required internal loop operations through a write/
network barrier; do not use live services or destructive CLI commands merely to
verify docs. Await disconnect, restore resolver state/cwd and close log handlers
before Windows temporary cleanup. Compare ignored/untracked artifacts too.

Report missing drivers/services/files/configuration or execution capacity
precisely. Separate declared bounds, lock resolutions, installed versions,
source-derived behavior and executed cases. Use README uncertainty categories,
preserve initial failures and unrelated work, and never claim a gate passed
without completing its check.
