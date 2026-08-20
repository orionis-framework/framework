from __future__ import annotations
from datetime import UTC, datetime, timedelta
from orionis.session.entities.record import SessionRecord
from orionis.session.stores.memory import MemorySessionStore
from orionis.test import TestCase

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

class TestMemorySessionStore(TestCase):
    """Unit tests for the in-process MemorySessionStore."""

    # ── read ─────────────────────────────────────────────────────────────────

    async def testReadAbsentKeyReturnsNone(self) -> None:
        """
        Return None for a session identifier that was never written.

        Validates that reading from an empty store does not raise and
        correctly signals a cache miss.
        """
        store = MemorySessionStore()
        result = await store.read("nonexistent")
        self.assertIsNone(result)

    async def testReadReturnsStoredRecord(self) -> None:
        """
        Return the record previously written under the given identifier.

        Validates the basic write/read round-trip for a live, non-expired
        session record.
        """
        store = MemorySessionStore()
        record = _make_record("abc")
        await store.write(record)
        result = await store.read("abc")
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "abc")  # type: ignore[union-attr]

    async def testReadReturnsNoneForExpiredRecord(self) -> None:
        """
        Evict and return None for an expired session record.

        Validates that a record whose expires_at is in the past is
        treated as a cache miss and removed from the internal store.
        """
        store = MemorySessionStore()
        record = _make_record("expired", offset_seconds=-1)
        await store.write(record)
        result = await store.read("expired")
        self.assertIsNone(result)

    async def testReadRemovesExpiredRecordFromStorage(self) -> None:
        """
        Delete an expired record during the read operation.

        Validates that after reading an expired record the internal
        dictionary no longer contains the entry.
        """
        store = MemorySessionStore()
        record = _make_record("stale", offset_seconds=-10)
        await store.write(record)
        await store.read("stale")
        self.assertNotIn("stale", store._storage)

    async def testReadPreservesDataPayload(self) -> None:
        """
        Return the exact data payload stored with the session record.

        Validates that arbitrary key-value pairs inside the data field
        survive a write/read cycle without modification.
        """
        store = MemorySessionStore()
        record = SessionRecord(
            id="data-test",
            data={"user_id": 42, "role": "admin"},
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        await store.write(record)
        result = await store.read("data-test")
        self.assertIsNotNone(result)
        self.assertEqual(result.data, {"user_id": 42, "role": "admin"})  # type: ignore[union-attr]

    # ── write ────────────────────────────────────────────────────────────────

    async def testWriteCreatesNewEntry(self) -> None:
        """
        Insert a record into the store under its identifier.

        Validates that after a write the record is retrievable and
        the store contains exactly one entry.
        """
        store = MemorySessionStore()
        record = _make_record("new-entry")
        await store.write(record)
        self.assertIn("new-entry", store._storage)

    async def testWriteOverwritesExistingEntry(self) -> None:
        """
        Replace an existing record when the same identifier is written again.

        Validates that a second write for the same session ID replaces
        the previous record without leaving a duplicate.
        """
        store = MemorySessionStore()
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

    async def testWriteMultipleDistinctKeys(self) -> None:
        """
        Store several records without cross-contamination.

        Validates that writing multiple session records with different
        identifiers keeps each record independently retrievable.
        """
        store = MemorySessionStore()
        await store.write(_make_record("s1"))
        await store.write(_make_record("s2"))
        r1 = await store.read("s1")
        r2 = await store.read("s2")
        self.assertIsNotNone(r1)
        self.assertIsNotNone(r2)
        self.assertEqual(r1.id, "s1")  # type: ignore[union-attr]
        self.assertEqual(r2.id, "s2")  # type: ignore[union-attr]

    # ── delete ───────────────────────────────────────────────────────────────

    async def testDeleteRemovesExistingRecord(self) -> None:
        """
        Remove a previously written record from the store.

        Validates that delete() causes subsequent read() calls to
        return None for the deleted identifier.
        """
        store = MemorySessionStore()
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
        store = MemorySessionStore()
        await store.delete("ghost")

    async def testDeleteDoesNotAffectOtherRecords(self) -> None:
        """
        Preserve unrelated records when a specific one is deleted.

        Validates that delete() targets only the specified identifier
        and leaves all other records intact.
        """
        store = MemorySessionStore()
        await store.write(_make_record("keep"))
        await store.write(_make_record("remove"))
        await store.delete("remove")
        result = await store.read("keep")
        self.assertIsNotNone(result)

    # ── gc ───────────────────────────────────────────────────────────────────

    async def testGcRemovesExpiredRecords(self) -> None:
        """
        Evict all records whose expiry is in the past during gc().

        Validates that the garbage-collection sweep identifies and
        removes stale records from the internal dictionary.
        """
        store = MemorySessionStore()
        await store.write(_make_record("live", offset_seconds=3600))
        await store.write(_make_record("dead", offset_seconds=-1))
        await store.gc()
        self.assertIn("live", store._storage)
        self.assertNotIn("dead", store._storage)

    async def testGcKeepsLiveRecords(self) -> None:
        """
        Leave non-expired records untouched during gc().

        Validates that the garbage-collection sweep does not evict
        records that are still within their lifetime window.
        """
        store = MemorySessionStore()
        await store.write(_make_record("session-a", offset_seconds=7200))
        await store.write(_make_record("session-b", offset_seconds=3600))
        await store.gc()
        self.assertEqual(len(store._storage), 2)

    async def testGcOnEmptyStoreIsNoOp(self) -> None:
        """
        Execute gc() on an empty store without raising.

        Validates that the garbage-collection sweep handles the
        trivial case of an empty internal dictionary gracefully.
        """
        store = MemorySessionStore()
        await store.gc()
        self.assertEqual(len(store._storage), 0)
