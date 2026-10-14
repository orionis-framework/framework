# Choosing storage and understanding concurrency

Select `SESSION_DRIVER` for your process topology and availability needs. Every store exchanges `SessionRecord`, containing an identifier, data and UTC expiration. The cookie does not contain the payload.

| Driver | Appropriate use | Operational limit |
|---|---|---|
| `memory` | Tests and single-process development. | Data and revocations are not shared across workers and disappear on restart. |
| `file` | Persistence on an appropriate shared local filesystem. | JSON-compatible data, writable paths and temporary capacity; verify remote filesystem lock semantics. |
| `cache` | Reuse configured cache TTL and atomic replacement. | Guarantees and availability depend on the backend. |
| `database` | Share records across workers through a configured database. | Dedicated table and schema permissions for lazy creation. |

`SESSION_FILES` defaults to `storage/framework/sessions` under the application root. `SESSION_CACHE_STORE` selects a cache repository; `SESSION_DB_CONNECTION` and `SESSION_DB_TABLE` select connection/table (`sessions` by default). Do not change driver or serialization format assuming existing records migrate automatically.

## An isolated store contract check

```python
import asyncio
from datetime import UTC, datetime, timedelta
from orionis.session.entities.record import SessionRecord
from orionis.session.stores.memory import MemorySessionStore

async def example():
    store = MemorySessionStore()
    record = SessionRecord(id="docs-example", data={"count": 1},
                           expires_at=datetime.now(UTC) + timedelta(minutes=5))
    await store.write(record)
    loaded = await store.read(record.id)
    assert loaded is not None and loaded.data == {"count": 1}
    assert await store.delete(record.id)
    assert not await store.update(record)

asyncio.run(example())
```

The example ID belongs to the store API. The manager validates cookie IDs before sending them to storage; do not use this example to accept a client-selected session ID.

## Preserving revocation across races

`ISessionStore` defines asynchronous `read`, `write`, `update`, `delete` and `gc`. `write` persists a record; `update` must replace only an existing live record and return `False` when this is no longer possible. Do not implement `update` as an unconditional upsert: a delayed request could recreate a session removed by logout.

Rotation deletes the previous ID before storing the new one. Conditional updates preserve revocation, but do not merge business data from simultaneous requests updating a still-valid session. Avoid critical counters or financial transactions in session payloads; use domain storage with its concurrency controls.

## I/O and cleanup

File storage uses compact JSON, atomic replacement and bounded lock stripes. Cache delegates expiry to backend TTL; database performs conditional updates and creates its structure lazily. `gc()` collects expired records where needed; do not assume every backend removes files immediately at expiry.

For a custom store implement [ISessionStore](../../contracts/store.py), preserve independent copies where appropriate and test expiration, failed update after deletion, corruption and I/O failures. The manager integrates four current drivers: another store needs application service integration; an arbitrary `SESSION_DRIVER` string does not register a class.

Evidence: [manager](../../manager.py), [memory](../../stores/memory.py), [file](../../stores/file.py), [cache](../../stores/cache.py), [database](../../stores/database.py). Tests: [memory](../../../../tests/session/stores/test_memory.py), [file](../../../../tests/session/stores/test_file.py), [database](../../../../tests/session/stores/test_database.py), [cache](../../../../tests/session/stores/test_cache.py).
