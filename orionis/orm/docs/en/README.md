# ORM and queries

Orionis combines Active Record models, fluent queries, relationships, and factories. Models describe attributes and behavior; [Database](../../../database/docs/en/README.md) owns connections, SQL compilation, and transactions. The engine is not part of the model API.

Declarations and builders are synchronous. Reading or writing data requires `await`. Bootstrap the application and create tables through migrations before querying; declaring a class does not create its table.

1. [Models, attributes, and persistence](models-and-attributes.md): define an entity, protect input, and save changes.
2. [Query, update, and paginate](querying.md): models versus tables, filters, joins, aggregates, and bulk writes.
3. [Relate and load models](relationships.md): direct relationships, eager loading, and pivot tables.
4. [Events, scopes, and soft deletes](events-and-scopes.md): domain behavior, query policies, and logical deletion.
5. [Factories and testing](factories-and-testing.md): reproducible data, states, sequences, and controlled persistence.
6. [Schema types and constraints](schema-and-type-reference.md): type catalog, modifiers, composite keys, and shared definitions.

Examples that only declare models or compose plans perform no database access. Async facade examples require bootstrap and matching tables; each chapter explains its prerequisites. Python 3.14 or later is required.

The database provider installs a manager in `ConnectionResolver`; querying without that bridge raises `OrmConfigurationException`. The ORM consumes `database` configuration without a separate configuration file. `QueryBuilderProvider` registers the `DB` singleton gateway; each query call creates its own builder.

## Bounded execution and performance

Use `async for batch in Model.query().orderBy("id").chunks(1000): ...` for bounded hydration, or the same method on `DB.table(...)`. Each batch runs the normal `get()` path, including global scopes, retrieved events, casts and eager loading. Existing limit/offset are honored and the original query is unchanged. `get()` still materializes the full result by design.

Supply a deterministic, preferably unique order. This API uses LIMIT/OFFSET pagination, so deep pages can cost more; concurrent writes can shift rows unless the surrounding transaction provides a consistent snapshot. It is not a server-side cursor. Each batch releases its query cursor/connection before yielding, except for a connection intentionally owned by the caller's transaction. Close an iterator on early exit; retained batches and relation fan-out remain the caller's memory responsibility.
