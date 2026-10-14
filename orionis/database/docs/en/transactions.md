# Transactions and concurrency

A transaction groups operations that must commit or roll back together. Use one connection name throughout that unit of work. Orionis does not implement distributed transactions across connections.

## Automatic commit and rollback

The async context commits when its body completes normally and rolls back when an exception escapes. This program shows an inner operation failing while preserving the outer operation:

```python
import asyncio
from orionis.database import Connection


async def main() -> None:
    db = Connection("tx", {"driver": "sqlite", "database": ":memory:"})
    try:
        await db.statement("CREATE TABLE events (name TEXT NOT NULL)")
        async with db.transaction():
            await db.execute("INSERT INTO events VALUES (:name)", {"name": "outer"})
            try:
                async with db.transaction():
                    await db.execute(
                        "INSERT INTO events VALUES (:name)", {"name": "inner"}
                    )
                    raise ValueError("discard inner work")
            except ValueError:
                pass
        assert await db.select("SELECT name FROM events") == [{"name": "outer"}]
    finally:
        await db.disconnect()


asyncio.run(main())
```

Inside an application, use `async with DB.transaction():` or `async with DB.transaction("reporting"):`. Manual facade control uses `beginTransaction()`, `commit()`, and `rollback()`; direct connections use `begin()`, `commit()`, and `rollback()`. Prefer the context manager: manual control must handle failures and cancellation on every path. Committing or rolling back without an active transaction raises `TransactionException`.

## Nesting and task ownership

The first level opens a dedicated connection and root transaction. Further levels create savepoints, except on Redshift, where nesting is rejected. Each `commit` or `rollback` ends only the innermost level.

State belongs to the asyncio task that opened the transaction. A child task inherits context but does not own the transaction: Orionis rejects its use with `TransactionException`. Execute transactional queries sequentially in the owning task; do not use `asyncio.gather()` or `create_task()` to share that connection inside the block. Outside a transaction, independent queries may use separate pooled connections.

This also affects [pagination](../../../orm/docs/en/querying.md): the ORM counts and fetches sequentially inside a transaction and may run them concurrently outside one.

## Cancellation and uncertain outcomes

Transaction-control operations wait for the driver to settle before propagating cancellation. Once `COMMIT` has been requested, changes may persist even if the caller receives `CancelledError`. Cancellation does not prove rollback. Waiting to acquire a pooled connection remains cancellable.

The implementation drains operations and cleans up or invalidates interrupted connections as appropriate, including the Redshift thread bridge. It does not promise to abort server work immediately. If a business outcome becomes uncertain after commit, query using a stable identity or apply idempotency before retrying.

## Practical boundaries

Keep blocks short. Avoid HTTP requests or email delivery inside transactions: they retain resources longer and are not undone by SQL rollback. When updating data and submitting a job, examine the [queue backend](../../../queues/docs/en/drivers-and-configuration.md): a database queue participates in its connection's transaction; Redis does not share the SQL transaction. There is no general `afterCommit` API here that makes both systems atomic.

DDL and savepoints depend on the backend. Opening a transaction in the migrator does not make every server's DDL reversible. Test successful and failed migration paths on the selected backend before production use.
