# ruff: noqa: PT009, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify session storage contracts and isolated persistence behavior."""

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
        """Return None for a session identifier that was never written.

        Validates that reading from an empty store does not raise and
        correctly signals a cache miss.

        Returns
        -------
        None
            No return value.
        """
        store = MemorySessionStore()
        result = await store.read("nonexistent")
        self.assertIsNone(result)

    async def testReadReturnsStoredRecord(self) -> None:
        """Return the record previously written under the given identifier.

        Validates the basic write/read round-trip for a live, non-expired
        session record.

        Returns
        -------
        None
            No return value.
        """
        store = MemorySessionStore()
        record = _make_record("abc")
        await store.write(record)
        result = await store.read("abc")
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "abc")  # type: ignore[union-attr]

    async def testReadReturnsNoneForExpiredRecord(self) -> None:
        """Return a miss and evict each expired record during its first read.

        Returns
        -------
        None
            No return value.
        """
        for offset in (-1, -10):
            with self.subTest(offset=offset):
                store = MemorySessionStore()
                record = _make_record("expired", offset_seconds=offset)
                await store.write(record)
                self.assertIsNone(await store.read(record.id))
                self.assertNotIn(record.id, store._storage)

    async def testReadPreservesDataPayload(self) -> None:
        """Return the exact data payload stored with the session record.

        Validates that arbitrary key-value pairs inside the data field
        survive a write/read cycle without modification.

        Returns
        -------
        None
            No return value.
        """
        store = MemorySessionStore()
        record = SessionRecord(
            id="data-test",
            data={"user_id": 42, "role": "admin", "tags": ["editor"]},
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        await store.write(record)
        record.data["tags"].append("changed")
        result = await store.read("data-test")
        self.assertIsNotNone(result)
        expected = {"user_id": 42, "role": "admin", "tags": ["editor"]}
        self.assertEqual(result.data, expected)
        result.data["tags"].append("also changed")
        self.assertEqual((await store.read(record.id)).data, expected)

    # ── write ────────────────────────────────────────────────────────────────

    async def testWriteCreatesNewEntry(self) -> None:
        """Insert a record into the store under its identifier.

        Validates that after a write the record is retrievable and
        the store contains exactly one entry.

        Returns
        -------
        None
            No return value.
        """
        store = MemorySessionStore()
        record = _make_record("new-entry")
        await store.write(record)
        self.assertIn("new-entry", store._storage)

    async def testWriteOverwritesExistingEntry(self) -> None:
        """Replace an existing record when the same identifier is written again.

        Validates that a second write for the same session ID replaces
        the previous record without leaving a duplicate.

        Returns
        -------
        None
            No return value.
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
        """Store several records without cross-contamination.

        Validates that writing multiple session records with different
        identifiers keeps each record independently retrievable.

        Returns
        -------
        None
            No return value.
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
        """Remove a previously written record from the store.

        Validates that delete() causes subsequent read() calls to
        return None for the deleted identifier.

        Returns
        -------
        None
            No return value.
        """
        store = MemorySessionStore()
        await store.write(_make_record("to-delete"))
        self.assertTrue(await store.delete("to-delete"))
        result = await store.read("to-delete")
        self.assertIsNone(result)

    async def testDeleteAbsentKeyIsNoOp(self) -> None:
        """Silently ignore delete() calls for non-existent identifiers.

        Validates that calling delete() on an unknown session ID does
        not raise any exception.

        Returns
        -------
        None
            No return value.
        """
        store = MemorySessionStore()
        self.assertFalse(await store.delete("ghost"))

    async def testDeleteDoesNotAffectOtherRecords(self) -> None:
        """Preserve unrelated records when a specific one is deleted.

        Validates that delete() targets only the specified identifier
        and leaves all other records intact.

        Returns
        -------
        None
            No return value.
        """
        store = MemorySessionStore()
        await store.write(_make_record("keep"))
        await store.write(_make_record("remove"))
        await store.delete("remove")
        result = await store.read("keep")
        self.assertIsNotNone(result)

    # ── gc ───────────────────────────────────────────────────────────────────

    async def testGcRemovesExpiredRecords(self) -> None:
        """Evict all records whose expiry is in the past during gc().

        Validates that the garbage-collection sweep identifies and
        removes stale records from the internal dictionary.

        Returns
        -------
        None
            No return value.
        """
        store = MemorySessionStore()
        await store.write(_make_record("live", offset_seconds=3600))
        await store.write(_make_record("dead", offset_seconds=-1))
        await store.gc()
        self.assertIn("live", store._storage)
        self.assertNotIn("dead", store._storage)

    async def testGcKeepsLiveRecords(self) -> None:
        """Leave non-expired records untouched during gc().

        Validates that the garbage-collection sweep does not evict
        records that are still within their lifetime window.

        Returns
        -------
        None
            No return value.
        """
        store = MemorySessionStore()
        await store.write(_make_record("session-a", offset_seconds=7200))
        await store.write(_make_record("session-b", offset_seconds=3600))
        await store.gc()
        self.assertEqual(len(store._storage), 2)

    async def testGcOnEmptyStoreIsNoOp(self) -> None:
        """Execute gc() on an empty store without raising.

        Validates that the garbage-collection sweep handles the
        trivial case of an empty internal dictionary gracefully.

        Returns
        -------
        None
            No return value.
        """
        store = MemorySessionStore()
        await store.gc()
        self.assertEqual(len(store._storage), 0)
