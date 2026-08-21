from __future__ import annotations
import asyncio
from datetime import UTC, datetime, timedelta
from orionis.database.connection import Connection
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, String, Text
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

def _relaxed_sessions_table(table: str) -> TableDefinition:
    """
    Build a sessions table whose payload and expiry accept NULL.

    Parameters
    ----------
    table : str
        Physical table name to create.

    Returns
    -------
    TableDefinition
        Definition mirroring the production layout, except that
        ``payload`` and ``expires_at`` are nullable so the defensive
        read guards can be exercised.
    """
    columns = {
        "id": String(255).primary(),
        "payload": Text().nullable(),
        "expires_at": BigInteger().nullable(),
    }
    for name, column in columns.items():
        column.name = name
    return TableDefinition(name=table, columns=columns, primary_key="id")

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

    async def _relaxedStore(self, table: str) -> DatabaseSessionStore:
        """
        Create a store bound to a table accepting NULL columns.

        Parameters
        ----------
        table : str
            Physical table name to create.

        Returns
        -------
        DatabaseSessionStore
            Store already flagged as ready, so the relaxed schema is not
            replaced by the production one.
        """
        await self._connection.createTable(_relaxed_sessions_table(table))
        store = DatabaseSessionStore(connection=self._connection, table=table)
        store._ready = True
        return store

    async def _insertRelaxedRow(
        self,
        table: str,
        session_id: str,
        payload: str | None,
        expiration: float | None,
    ) -> None:
        """
        Insert a raw row into a relaxed sessions table.

        Parameters
        ----------
        table : str
            Physical table name.
        session_id : str
            Primary-key value of the row.
        payload : str | None
            Raw JSON payload, or ``None`` to leave the column empty.
        expiration : float | None
            Expiry in epoch seconds, or ``None`` to leave it empty.

        Returns
        -------
        None
        """
        await self._connection.execute(
            f"INSERT INTO {table} (id, payload, expires_at) "  # noqa: S608
            "VALUES (:id, :p, :e)",
            {"id": session_id, "p": payload, "e": expiration},
        )

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

    async def testReadRestoresExpiryAsUtcDatetime(self) -> None:
        """
        Rebuild the expiry column as a timezone-aware datetime.

        Validates that the epoch seconds stored in the table are decoded
        back into UTC, truncated to the whole second the column holds.
        """
        record = _make_record("tz")
        await self._store.write(record)
        result = await self._store.read("tz")
        self.assertIsNotNone(result)
        self.assertEqual(result.expires_at.tzinfo, UTC)  # type: ignore[union-attr]
        self.assertEqual(
            result.expires_at.timestamp(),  # type: ignore[union-attr]
            float(int(record.expires_at.timestamp())),
        )

    async def testExpiryIsStoredAsWholeSeconds(self) -> None:
        """
        Persist the expiry as an integer, as the column declares.

        Validates that no fractional epoch value reaches the database,
        since a strict driver rejects a float bound to a BIGINT column.
        """
        record = _make_record("int-expiry")
        await self._store.write(record)

        rows = await self._connection.select(
            "SELECT expires_at FROM sessions WHERE id = :id",
            {"id": "int-expiry"},
        )
        stored = rows[0]["expires_at"]

        self.assertIsInstance(stored, int)
        self.assertEqual(stored, int(record.expires_at.timestamp()))

    async def testReadDeletesExpiredRow(self) -> None:
        """
        Evict the row when an expired record is read.

        Validates the lazy eviction that keeps the table from growing
        without bound.
        """
        await self._store.write(_make_record("gone"))
        await self._store._connection.execute(
            "UPDATE sessions SET expires_at = :e WHERE id = :id",
            {"e": 1.0, "id": "gone"},
        )
        self.assertIsNone(await self._store.read("gone"))
        rows = await self._store._connection.select(
            "SELECT id FROM sessions WHERE id = :id",
            {"id": "gone"},
        )
        self.assertEqual(rows, [])

    async def testReadReturnsNoneForCorruptPayload(self) -> None:
        """
        Treat an undecodable payload as a miss.

        Validates that malformed JSON never escapes the store as a
        decode error.
        """
        await self._store.write(_make_record("corrupt"))
        await self._store._connection.execute(
            "UPDATE sessions SET payload = :p WHERE id = :id",
            {"p": "{not json", "id": "corrupt"},
        )
        self.assertIsNone(await self._store.read("corrupt"))

    async def testReadReturnsNoneWhenExpiryIsNull(self) -> None:
        """
        Treat a row without expiry as expired.

        Validates the defensive guard protecting the store from a
        pre-existing table whose expiry column accepts NULL.
        """
        table = "relaxed_sessions"
        store = await self._relaxedStore(table)
        await self._insertRelaxedRow(table, "no-expiry", "{}", None)

        self.assertIsNone(await store.read("no-expiry"))

        rows = await self._connection.select(
            f"SELECT id FROM {table} WHERE id = :id",  # noqa: S608
            {"id": "no-expiry"},
        )
        self.assertEqual(rows, [])

    async def testReadReturnsNoneWhenPayloadIsNull(self) -> None:
        """
        Treat a row without payload as a miss.

        Validates the defensive guard protecting the store from a row
        whose JSON column was never populated.
        """
        table = "relaxed_payload_sessions"
        store = await self._relaxedStore(table)
        expiration = (datetime.now(UTC) + timedelta(hours=1)).timestamp()
        await self._insertRelaxedRow(table, "no-payload", None, expiration)

        self.assertIsNone(await store.read("no-payload"))

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

    async def testInsertFallsBackToUpdateOnConflict(self) -> None:
        """
        Recover from a concurrent insert by retrying as an update.

        Validates the portable upsert strategy used instead of a
        dialect-specific ``ON CONFLICT`` clause.
        """
        await self._store.write(_make_record("conflict"))
        expiration = (datetime.now(UTC) + timedelta(hours=2)).timestamp()

        await self._store._DatabaseSessionStore__insertOrRetryUpdate(
            "conflict",
            '{"k": "updated"}',
            expiration,
        )

        result = await self._store.read("conflict")
        self.assertIsNotNone(result)
        self.assertEqual(result.data, {"k": "updated"})  # type: ignore[union-attr]

    # ── schema bootstrap ─────────────────────────────────────────────────────

    async def testSchemaIsCreatedOnFirstUseOnly(self) -> None:
        """
        Create the table once and flag the store as ready.

        Validates that repeated calls short-circuit instead of issuing
        redundant DDL statements.
        """
        self.assertFalse(self._store._ready)
        await self._store._ensureSchema()
        self.assertTrue(self._store._ready)
        await self._store._ensureSchema()
        self.assertTrue(self._store._ready)

    async def testConcurrentBootstrapCreatesSchemaOnce(self) -> None:
        """
        Serialise concurrent bootstraps behind the readiness lock.

        Validates that the second waiter observes the flag set by the
        first one and skips the redundant DDL statement.
        """
        await asyncio.gather(
            self._store._ensureSchema(),
            self._store._ensureSchema(),
        )
        self.assertTrue(self._store._ready)
        await self._store.write(_make_record("after-bootstrap"))
        self.assertIsNotNone(await self._store.read("after-bootstrap"))

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
