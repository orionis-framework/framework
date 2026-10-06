# orionis.session

> `orionis.session` implements lazy server-side HTTP sessions, one-request flash data, secure identifier rotation, and pluggable memory, file, cache, or database storage.

## Overview

The browser cookie carries only a random session identifier. Session data remains in a configured server-side store. `Session` owns in-memory values and lifecycle flags; `SessionManager` restores, ages flash data, registers the request-scoped contract, persists changes, rotates identifiers, and writes or clears the cookie.

A new session is lazy: reading it creates neither an identifier nor storage. The first write or flash activates it. This avoids cookies and backend I/O for requests that never need state.

## Requirements

- Python 3.14 or newer.
- Orionis web session middleware for automatic request start/save and facade injection.
- A writable directory for `file`, configured cache store for `cache`, or database connection for `database`.
- HTTPS when `SESSION_SAME_SITE=none`; the validated config requires a secure cookie.

## Quick start

```python
from orionis.session.session import Session

session = Session()
assert session.id is None
assert session.started is False

session.put("user_id", 42)
assert session.started is True
assert session.dirty is True
assert session.id is not None
assert session.get("user_id") == 42
```

Validation: **Executed successfully** on CPython 3.14.6; no backing store was used.

## Core concepts

### Lazy server-side state

`Session` performs no request, response, cookie, or store I/O. `put()` activates on the first effective write and avoids dirtying when the equal value is already present. `forget`, `clear`, `has`, `get`, and `all` manage the in-memory mapping.

### Flash lifecycle

`flash(key, value)` is readable during the current request and the next one. At each request start, the manager discards the older bag and promotes the new bag. `flashInput` strips credential/CSRF fields, `flashErrors` normalizes mappings or validation exceptions, and repeated reserved-bag writes merge.

### Rotation and invalidation

Call `regenerate()` after authentication or privilege changes. Rotation is deferred until response save so the old record can be deleted before a fresh ID is persisted. `invalidate()` clears values, deletes the backing record, and expires the cookie. If a restored record was concurrently revoked, conditional update/rotation fails closed instead of recreating it.

### Expiration and renewal

Every record carries an absolute UTC expiration. With `renewal_interval=0`, an active session is persisted on each completed request. A positive interval can skip renewal writes for unchanged scalar payloads until its deadline; mutable data and dirty sessions are always persisted.

### Stores

Memory is process-local. File uses compact JSON, atomic replace, bounded lock stripes, validation, and garbage collection. Cache delegates expiry to backend TTL and uses atomic replace for existing records. Database creates a portable table lazily and uses conditional updates to preserve revocation semantics.

## Module structure

| Path | Responsibility |
|---|---|
| `session.py` | Lazy data, flash bags, renewal state, rotation, invalidation. |
| `manager.py` | Request restoration, store selection, persistence, cookies. |
| `flash.py` | Sensitive-input filtering, error normalization, pending flash application. |
| `stores/memory.py` | Isolated in-process records for development/tests. |
| `stores/file.py` | Atomic JSON files with cross-process locking and GC. |
| `stores/cache.py` | Cache-backed records with TTL and replace semantics. |
| `stores/database.py` | Portable database table, lazy schema, conditional updates. |
| `contracts/` | `ISession` and `ISessionStore` boundaries. |
| `entities/record.py`, `exceptions.py` | Store exchange record and storage failures. |

## Public API

`orionis.session` has no package-root exports. Application code normally injects `ISession` or uses `orionis.support.facades.Session`. Infrastructure code imports concrete implementations from their defining modules.

### Session data

- `get`, `put`, `has`, `forget`, `clear`, and `all` handle values.
- `flash` and `getFlash` handle arbitrary one-request data.
- `flashInput` / `getOldInput` and `flashErrors` / `getErrors` support redirect-back forms.
- `setPreviousUrl` / `getPreviousUrl` support navigation recovery.
- `regenerate` and `invalidate` request security-sensitive lifecycle changes.
- Read-only flags expose `id`, `started`, `dirty`, `invalidated`, `isNew`, and `wantsRegenerate`.

### Store contract

`ISessionStore` defines async `read`, `write`, `update`, `delete`, and `gc`. `update` returns `False` if a live existing record cannot be replaced; this prevents a concurrent logout/revocation from being undone.

## Common workflows

### Persist login identity safely

After validating credentials, write the authentication value and call `regenerate()`. Do not place passwords, tokens, or large domain objects in session data.

### Redirect with input/errors

Use response/view redirect helpers when available, or call `flashInput` and `flashErrors` on the current session. Password-like fields are removed automatically, but application-specific secrets still require explicit exclusion.

### Log out

Call `invalidate()`, then return a response through the normal web middleware. The manager deletes storage and emits an expired cookie. If request handling aborts, `abort()` still deletes invalidated or superseded IDs without issuing a new one.

### Choose a store

Use memory only when process-local loss and non-sharing are acceptable. File supports shared local filesystems with locks; cache or database are typical for multi-worker deployments, subject to the chosen backend's own topology and guarantees.

## Examples

### Flash form data without credentials

```python
from orionis.session.session import Session

session = Session()
session.flashInput({
    "email": "ada@example.test",
    "password": "must-not-persist",
    "csrf_token": "must-not-persist",
})
session.flashErrors({"email": "Already registered"})

assert session.getOldInput("email") == "ada@example.test"
assert session.getOldInput("password") is None
assert session.getErrors() == {"email": ["Already registered"]}
```

Validation: **Executed successfully** on CPython 3.14.6.

### Request identifier rotation

```python
from orionis.session.session import Session

session = Session()
session.put("account", 7)
old_id = session.id
session.regenerate()

assert session.wantsRegenerate is True
assert session.id == old_id
assert session.invalidated is False
```

Validation: **Executed successfully** on CPython 3.14.6; actual rotation remains the manager's atomic save responsibility.

### Round-trip a memory-store record

```python
import asyncio
from datetime import UTC, datetime, timedelta
from orionis.session.entities.record import SessionRecord
from orionis.session.stores.memory import MemorySessionStore


async def example() -> None:
    store = MemorySessionStore()
    record = SessionRecord(
        id="example", data={"count": 1},
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    await store.write(record)
    restored = await store.read("example")
    assert restored is not None and restored.data == {"count": 1}
    restored.data["count"] = 2
    assert (await store.read("example")).data["count"] == 1


asyncio.run(example())
```

Validation: **Executed successfully** on CPython 3.14.6; the memory store returns detached records.

### Validate cookie and renewal configuration

```python
from orionis.foundation.config.session import Session as SessionConfig

config = SessionConfig(
    driver="memory",
    lifetime=120,
    renewal_interval=300,
    cookie="sessionid",
    secure=True,
    same_site="none",
)
assert config.driver.value == "memory"
assert config.renewal_interval == 300
assert config.secure is True
```

Validation: **Executed successfully** on CPython 3.14.6.

### Use the request-scoped facade

```python
from orionis.support.facades import Session


def remember_theme(theme: str) -> None:
    Session.put("theme", theme)


def current_theme() -> str:
    return Session.get("theme", "system")
```

Validation: **Import and syntax validated** on CPython 3.14.6; calls require active web middleware and a request-scoped session binding.

## Configuration

| Environment variable | Default | Purpose |
|---|---:|---|
| `SESSION_DRIVER` | `memory` | `memory`, `file`, `cache`, or `database`. |
| `SESSION_LIFETIME` | 120 minutes | Server-side record lifetime. |
| `SESSION_EXPIRE_ON_CLOSE` | false | Omit cookie `Max-Age`. |
| `SESSION_TRACK_PREVIOUS_URL` | true | Remember successful navigation. |
| `SESSION_RENEWAL_INTERVAL` | 0 seconds | Minimum unchanged-session renewal interval. |
| `SESSION_FILES` | `storage/framework/sessions` | File store path below app root. |
| `SESSION_DB_CONNECTION` / `SESSION_DB_TABLE` | default / `sessions` | Database storage. |
| `SESSION_CACHE_STORE` | default cache | Cache repository. |
| `SESSION_COOKIE`, `SESSION_PATH`, `SESSION_DOMAIN` | `sessionid`, `/`, current host | Cookie identity/scope. |
| `SESSION_SECURE`, `SESSION_HTTP_ONLY` | false, true | Cookie transport/script policy. |
| `SESSION_SAME_SITE`, `SESSION_PARTITIONED` | `lax`, false | SameSite and CHIPS attributes. |

The renewal interval must be nonnegative and less than the lifetime in seconds. Cookie names and paths are validated. `SameSite=None` requires `secure=True`.

## Integration with Orionis

The web `StartSession` layer asks `SessionManager` to start a session, registers `ISession` in the application scope, applies pending response/view flash data, and saves after successful handling. On exception or cancellation it invokes abort cleanup.

The `Session` facade resolves the same request-scoped contract. Cache/database stores reuse their framework managers; the database store lazily creates its dedicated schema. Previous-URL tracking is applied by web middleware only for eligible navigation responses.

## Errors and edge cases

- Missing, malformed, expired, mismatched, or corrupted records become a fresh lazy session; invalid cookie IDs are never passed to stores.
- Store I/O failures may raise `SessionStorageException` or backend-specific errors; middleware must not silently issue a misleading cookie.
- File-store values must be JSON serializable. Other stores also require values compatible with their serializer/backend.
- `all()` includes internal flash bags; use application-level accessors rather than exposing it directly to clients.
- Equal writes are no-ops, but mutable values may change after retrieval; renewal logic conservatively persists mutable payloads.
- Memory storage does not cross processes and is not thread-safe beyond the normal single-loop usage model.
- Partitioned-cookie client support varies; configuration only controls the emitted attribute.

## Performance and concurrency

Lazy activation avoids read-miss writes and cookies. Renewal intervals reduce unchanged scalar writes. Cache TTL handles expiry without scans; file/database provide explicit GC for bulk cleanup.

File writes stage and atomically replace under bounded cross-process lock stripes. Cache and database `update` operations require an existing live record, preserving concurrent revocation. Session objects are request-scoped and must not be shared between concurrent requests.

## Compatibility

Cookie behavior follows the Orionis response API and current browser rules for Secure, HttpOnly, SameSite, and Partitioned attributes. File payloads use compact JSON; changing serialized value types can affect old records. All stores exchange `SessionRecord`, so custom stores can implement `ISessionStore` without changing application code.

## Verification notes

- `tests/session`: **256 test methods passed** with the Orionis runner on CPython 3.14.6.
- Six bilingual documentation programs were compiled; five standalone programs were executed successfully.
- The facade program was import/syntax validated because it requires request middleware.
- Evidence covered lazy activation, flash aging/security, renewal, rotation/revocation races, cookies, manager aborts, memory/file/cache/database stores, schema bootstrapping, locking, GC, and configuration validation.

