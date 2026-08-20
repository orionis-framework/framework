from __future__ import annotations
from datetime import UTC, datetime, timedelta
from typing import Any
from orionis.session.entities.record import SessionRecord
from orionis.session.stores.cache import CacheSessionStore
from orionis.test import TestCase

# ruff: noqa: ANN401

class _FakeCacheRepository:
    """Minimal in-memory stand-in for ICacheRepository."""

    def __init__(self) -> None:
        self.data: dict[str, Any] = {}
        self.ttls: dict[str, float | None] = {}

    async def get(self, key: str) -> Any:
        return self.data.get(key)

    async def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
        self.data[key] = value
        self.ttls[key] = ttl
        return True

    async def delete(self, key: str) -> bool:
        existed = key in self.data
        self.data.pop(key, None)
        self.ttls.pop(key, None)
        return existed

class _FakeCacheManager:
    """Fake ICacheManager exposing only the store() factory method."""

    def __init__(self) -> None:
        self.repository = _FakeCacheRepository()
        self.requested_store: str | None = "__unset__"

    def store(self, name: str | None = None) -> _FakeCacheRepository:
        self.requested_store = name
        return self.repository

def _make_record(
    session_id: str = "test-id",
    *,
    offset_seconds: int = 3600,
) -> SessionRecord:
    """
    Build a SessionRecord with a configurable expiry offset.

    Parameters
    ----------
    session_id : str
        Identifier to embed in the record.
    offset_seconds : int
        Seconds added to the current UTC time to compute expires_at.
        Use a negative value to produce an already-expired record.

    Returns
    -------
    SessionRecord
        A ready-to-use record for testing.
    """
    return SessionRecord(
        id=session_id,
        data={"k": "v"},
        expires_at=datetime.now(UTC) + timedelta(seconds=offset_seconds),
    )

class TestCacheSessionStore(TestCase):
    """Unit tests for the cache-backed CacheSessionStore."""

    # ── construction ─────────────────────────────────────────────────────────

    def testConstructorRequestsDefaultStoreByDefault(self) -> None:
        """
        Request the default cache store when none is specified.

        Validates that omitting the ``store`` argument forwards ``None``
        to ``ICacheManager.store()``.
        """
        manager = _FakeCacheManager()
        CacheSessionStore(cache=manager)
        self.assertIsNone(manager.requested_store)

    def testConstructorForwardsNamedStore(self) -> None:
        """
        Forward an explicit store name to ``ICacheManager.store()``.

        Validates that the requested cache store is honoured instead of
        always resolving the default one.
        """
        manager = _FakeCacheManager()
        CacheSessionStore(cache=manager, store="sessions")
        self.assertEqual(manager.requested_store, "sessions")

    # ── read ─────────────────────────────────────────────────────────────────

    async def testReadAbsentKeyReturnsNone(self) -> None:
        """
        Return None for a session identifier that was never written.

        Validates that reading from an empty cache does not raise and
        correctly signals a cache miss.
        """
        store = CacheSessionStore(cache=_FakeCacheManager())
        result = await store.read("nonexistent")
        self.assertIsNone(result)

    async def testReadReturnsStoredRecord(self) -> None:
        """
        Return the record previously written under the given identifier.

        Validates the basic write/read round-trip for a live, non-expired
        session record.
        """
        store = CacheSessionStore(cache=_FakeCacheManager())
        record = _make_record("abc")
        await store.write(record)
        result = await store.read("abc")
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "abc")  # type: ignore[union-attr]
        self.assertEqual(result.data, {"k": "v"})  # type: ignore[union-attr]

    async def testReadUsesNamespacedKey(self) -> None:
        """
        Store the payload under a namespaced cache key.

        Validates that raw session identifiers never collide with other
        unrelated cache entries.
        """
        manager = _FakeCacheManager()
        store = CacheSessionStore(cache=manager)
        await store.write(_make_record("ns"))
        self.assertIn("session:ns", manager.repository.data)

    async def testReadRebuildsExpiryFromPayload(self) -> None:
        """
        Restore the expiry timestamp carried by the cached payload.

        Validates that the record handed back to the manager is complete
        and not merely the stored data bag.
        """
        store = CacheSessionStore(cache=_FakeCacheManager())
        record = _make_record("expiry")
        await store.write(record)
        result = await store.read("expiry")
        self.assertIsNotNone(result)
        self.assertEqual(result.expires_at, record.expires_at)  # type: ignore[union-attr]

    # ── write ────────────────────────────────────────────────────────────────

    async def testWriteAppliesTtlFromExpiresAt(self) -> None:
        """
        Derive the cache entry TTL from ``record.expires_at``.

        Validates that the TTL passed to the repository is a positive
        number of seconds not exceeding the requested offset.
        """
        manager = _FakeCacheManager()
        store = CacheSessionStore(cache=manager)
        record = _make_record("ttl-test", offset_seconds=120)
        await store.write(record)
        ttl = manager.repository.ttls["session:ttl-test"]
        self.assertIsNotNone(ttl)
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 120)

    async def testWriteOfExpiredRecordDeletesInsteadOfStoring(self) -> None:
        """
        Delete rather than store an already-expired record.

        Validates that write() never persists a record whose expiry is
        in the past, removing any stale entry instead.
        """
        manager = _FakeCacheManager()
        store = CacheSessionStore(cache=manager)
        await manager.repository.set("session:expired", {"id": "expired"})
        record = _make_record("expired", offset_seconds=-10)
        await store.write(record)
        self.assertNotIn("session:expired", manager.repository.data)

    async def testWriteOverwritesExistingEntry(self) -> None:
        """
        Replace an existing record when the same identifier is written again.

        Validates that a second write for the same session ID replaces
        the previous record without leaving a duplicate.
        """
        store = CacheSessionStore(cache=_FakeCacheManager())
        record_v1 = SessionRecord(
            id="dup",
            data={"v": 1},
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        record_v2 = SessionRecord(
            id="dup",
            data={"v": 2},
            expires_at=datetime.now(UTC) + timedelta(hours=2),
        )
        await store.write(record_v1)
        await store.write(record_v2)
        result = await store.read("dup")
        self.assertIsNotNone(result)
        self.assertEqual(result.data, {"v": 2})  # type: ignore[union-attr]

    # ── delete ───────────────────────────────────────────────────────────────

    async def testDeleteRemovesExistingRecord(self) -> None:
        """
        Remove a previously written record from the cache.

        Validates that delete() causes subsequent read() calls to
        return None for the deleted identifier.
        """
        store = CacheSessionStore(cache=_FakeCacheManager())
        await store.write(_make_record("to-delete"))
        await store.delete("to-delete")
        result = await store.read("to-delete")
        self.assertIsNone(result)

    async def testDeleteAbsentKeyIsNoOp(self) -> None:
        """
        Silently ignore delete() calls for non-existent identifiers.

        Validates that calling delete() on an unknown session ID does
        not raise any exception.
        """
        store = CacheSessionStore(cache=_FakeCacheManager())
        await store.delete("ghost")

    async def testDeleteUsesNamespacedKey(self) -> None:
        """
        Remove the namespaced entry rather than the raw identifier.

        Validates that eviction targets the same key used on write.
        """
        manager = _FakeCacheManager()
        store = CacheSessionStore(cache=manager)
        await store.write(_make_record("ns-delete"))
        await store.delete("ns-delete")
        self.assertNotIn("session:ns-delete", manager.repository.data)

    # ── gc ───────────────────────────────────────────────────────────────────

    async def testGcIsANoOp(self) -> None:
        """
        Leave stored records untouched, since expiry is TTL-driven.

        Validates that calling gc() never evicts a live record: eviction
        of cache-backed sessions is delegated entirely to the backend.
        """
        manager = _FakeCacheManager()
        store = CacheSessionStore(cache=manager)
        await store.write(_make_record("still-there"))
        await store.gc()
        result = await store.read("still-there")
        self.assertIsNotNone(result)
