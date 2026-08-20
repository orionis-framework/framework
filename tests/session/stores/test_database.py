from __future__ import annotations
from datetime import UTC, datetime, timedelta
from orionis.database.connection import Connection
from orionis.session.entities.record import SessionRecord
from orionis.session.stores.database import DatabaseSessionStore
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

class TestDatabaseSessionStore(TestCase):
    """Unit tests for the database-backed DatabaseSessionStore."""

    async def asyncSetUp(self) -> None:
        """
        Create an in-memory SQLite connection and a fresh store per test.

        Provides an isolated, writable database so every test operates
        on its own state without side effects. Tables are created lazily
        by the store on first access.
        """
        self._connection = Connection(
            "sqlite",
            {"driver": "sqlite", "database": ":memory:", "prefix": ""},
        )
        self._store = DatabaseSessionStore(
            connection=self._connection,
            table="sessions",
        )

    async def asyncTearDown(self) -> None:
        """
        Dispose the in-memory engine after each test.

        Releases the pooled in-memory database.
        """
        await self._connection.disconnect()

    # ── read ─────────────────────────────────────────────────────────────────

    async def testReadAbsentKeyReturnsNone(self) -> None:
        """
        Return None for a session identifier that was never written.

        Validates that reading from an empty table does not raise and
        correctly signals a miss.
        """
        result = await self._store.read("nonexistent")
        self.assertIsNone(result)

    async def testReadReturnsStoredRecord(self) -> None:
        """
        Return the record previously written under the given identifier.

        Validates the basic write/read round-trip for a live, non-expired
        session record.
        """
        record = _make_record("abc")
        await self._store.write(record)
        result = await self._store.read("abc")
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "abc")  # type: ignore[union-attr]
        self.assertEqual(result.data, {"k": "v"})  # type: ignore[union-attr]

    async def testReadReturnsNoneForExpiredRecord(self) -> None:
        """
        Evict and return None for an expired session record.

        Validates that a record whose expires_at is in the past is
        treated as a miss and removed from the table.
        """
        record = _make_record("expired", offset_seconds=-10)
        await self._store.write(record)
        result = await self._store.read("expired")
        self.assertIsNone(result)

    async def testReadPreservesDataPayload(self) -> None:
        """
        Return the exact data payload stored with the session record.

        Validates that arbitrary key-value pairs inside the data field
        survive a write/read cycle without modification.
        """
        record = SessionRecord(
            id="data-test",
            data={"user_id": 42, "role": "admin"},
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        await self._store.write(record)
        result = await self._store.read("data-test")
        self.assertIsNotNone(result)
        self.assertEqual(result.data, {"user_id": 42, "role": "admin"})  # type: ignore[union-attr]

    # ── write ────────────────────────────────────────────────────────────────

    async def testWriteOfExpiredRecordDeletesInsteadOfStoring(self) -> None:
        """
        Delete rather than store an already-expired record.

        Validates that write() never persists a record whose expiry is
        in the past.
        """
        await self._store.write(_make_record("stale"))
        expired = _make_record("stale", offset_seconds=-5)
        await self._store.write(expired)
        result = await self._store.read("stale")
        self.assertIsNone(result)

    async def testWriteOverwritesExistingEntry(self) -> None:
        """
        Replace an existing record when the same identifier is written again.

        Validates that a second write for the same session ID replaces
        the previous record without leaving a duplicate.
        """
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
        await self._store.write(record_v1)
        await self._store.write(record_v2)
        result = await self._store.read("dup")
        self.assertIsNotNone(result)
        self.assertEqual(result.data, {"v": 2})  # type: ignore[union-attr]

    async def testWriteMultipleDistinctKeys(self) -> None:
        """
        Store several records without cross-contamination.

        Validates that writing multiple session records with different
        identifiers keeps each record independently retrievable.
        """
        await self._store.write(_make_record("s1"))
        await self._store.write(_make_record("s2"))
        r1 = await self._store.read("s1")
        r2 = await self._store.read("s2")
        self.assertIsNotNone(r1)
        self.assertIsNotNone(r2)
        self.assertEqual(r1.id, "s1")  # type: ignore[union-attr]
        self.assertEqual(r2.id, "s2")  # type: ignore[union-attr]

    # ── delete ───────────────────────────────────────────────────────────────

    async def testDeleteRemovesExistingRecord(self) -> None:
        """
        Remove a previously written record from the table.

        Validates that delete() causes subsequent read() calls to
        return None for the deleted identifier.
        """
        await self._store.write(_make_record("to-delete"))
        await self._store.delete("to-delete")
        result = await self._store.read("to-delete")
        self.assertIsNone(result)

    async def testDeleteAbsentKeyIsNoOp(self) -> None:
        """
        Silently ignore delete() calls for non-existent identifiers.

        Validates that calling delete() on an unknown session ID does
        not raise any exception.
        """
        await self._store.delete("ghost")

    # ── gc ───────────────────────────────────────────────────────────────────

    async def testGcRemovesExpiredRecords(self) -> None:
        """
        Sweep away expired rows while keeping live ones.

        Validates that gc() performs a bulk delete of every record whose
        expires_at is in the past, leaving unrelated live records intact.
        """
        await self._store.write(_make_record("alive"))
        await self._store._ensureSchema()
        await self._store._connection.execute(
            "INSERT INTO sessions (id, payload, expires_at) "
            "VALUES (:id, :p, :e)",
            {"id": "dead", "p": "{}", "e": 1.0},
        )
        await self._store.gc()
        self.assertIsNotNone(await self._store.read("alive"))
        rows = await self._store._connection.select(
            "SELECT id FROM sessions WHERE id = :id",
            {"id": "dead"},
        )
        self.assertEqual(rows, [])
