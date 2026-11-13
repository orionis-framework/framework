# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify session storage contracts and isolated persistence behavior."""

from __future__ import annotations
import asyncio
import os
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from orionis.session.entities.record import SessionRecord
from orionis.session.stores.file import FileSessionStore
from orionis.test import TestCase


def _make_record(
    session_id: str = "test-id",
    *,
    offset_seconds: int = 3600,
    data: dict | None = None,
) -> SessionRecord:
    """
    Build a SessionRecord with a configurable expiry offset.

    Parameters
    ----------
    session_id : str
        Identifier to embed in the record.
    offset_seconds : int
        Seconds from now until the record expires. Use a negative
        value to produce an already-expired record.
    data : dict or None
        Optional payload; defaults to ``{"key": "value"}``.

    Returns
    -------
    SessionRecord
        A ready-to-use record for testing.
    """
    return SessionRecord(
        id=session_id,
        data=data if data is not None else {"key": "value"},
        expires_at=datetime.now(UTC) + timedelta(seconds=offset_seconds),
    )


class TestFileSessionStore(TestCase):
    """Unit tests for the filesystem-backed FileSessionStore."""

    def setUp(self) -> None:
        """Create an isolated temporary directory before each test.

        Provides a fresh directory for every test so file-system
        operations cannot leak state between tests.

        Returns
        -------
        None
            No return value.
        """
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self._directory = Path(self._tmpdir.name)

    def _store(self) -> FileSessionStore:
        """
        Construct a FileSessionStore backed by the temporary directory.

        Returns
        -------
        FileSessionStore
            A fresh store instance for each caller.
        """
        return FileSessionStore(directory=self._directory)

    # ── construction ─────────────────────────────────────────────────────────

    def testInitCreatesDirectoryWhenMissing(self) -> None:
        """Create the storage directory on instantiation if absent.

        Validates that FileSessionStore.mkdir() is invoked so that a
        nested path that does not yet exist is created automatically.

        Returns
        -------
        None
            No return value.
        """
        nested = self._directory / "deep" / "nested"
        FileSessionStore(directory=nested)
        self.assertTrue(nested.is_dir())

    def testInitAcceptsExistingDirectory(self) -> None:
        """Accept a pre-existing directory without error.

        Validates that constructing the store when the directory already
        exists does not raise an exception.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        self.assertIsNotNone(store)

    # ── _path helper ─────────────────────────────────────────────────────────

    def testPathReturnsCorrectFilename(self) -> None:
        """Return the expected .json file path for a given session ID.

        Validates that _path() appends the .json extension and places
        the file inside the store directory.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        p = store._path("my-session")
        self.assertEqual(p, self._directory / "my-session.json")

    # ── _serialize / _deserialize round-trip ─────────────────────────────────

    def testSerializeDeserializeRoundTrip(self) -> None:
        """Recover the original record after serialisation and deserialisation.

        Validates that _serialize() followed by _deserialize() produces
        a record equal to the original in all fields.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        original = _make_record("rt", data={"user": "bob", "age": 30})
        raw = store._serialize(original)
        recovered = store._deserialize(raw)
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.id, original.id)  # type: ignore[union-attr]
        self.assertEqual(recovered.data, original.data)  # type: ignore[union-attr]

    def testDeserializeCorruptBytesReturnsNone(self) -> None:
        """Treat both malformed and empty JSON bytes as misses.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        for content in (b"not-json-at-all!!!", b""):
            with self.subTest(content=content):
                self.assertIsNone(store._deserialize(content))

    # ── _readFile / _writeFile ────────────────────────────────────────────────

    def testWriteFileAndReadFileRoundTrip(self) -> None:
        """Recover bytes written by _writeFile via _readFile.

        Validates the low-level file I/O helpers produce identical
        content on the round trip.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        path = self._directory / "test.bin"
        content = b"hello bytes"
        store._writeFile(path, content)
        result = store._readFile(path)
        self.assertEqual(result, content)

    def testReadFileMissingReturnsNone(self) -> None:
        """Return None when the target file does not exist.

        Validates that _readFile() signals absence with None rather
        than propagating a FileNotFoundError.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        result = store._readFile(self._directory / "absent.bin")
        self.assertIsNone(result)

    def testWriteFileIsAtomic(self) -> None:
        """Leave no .tmp artefact after a successful write.

        Validates that _writeFile() cleans up the temporary file and
        only the final destination exists after the call.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        path = self._directory / "atomic.json"
        store._writeFile(path, b"data")
        leftovers = [
            entry.name
            for entry in self._directory.iterdir()
            if entry.name.endswith(".tmp")
        ]
        self.assertTrue(path.exists())
        self.assertEqual(leftovers, [])

    # ── read ─────────────────────────────────────────────────────────────────

    async def testReadAbsentSessionReturnsNone(self) -> None:
        """Return None for a session identifier with no corresponding file.

        Validates that reading a non-existent session ID from the file
        store signals a cache miss without raising.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        result = await store.read("ghost-session")
        self.assertIsNone(result)

    async def testReadReturnsLiveRecord(self) -> None:
        """Return the record for a live, non-expired session file.

        Validates the basic write/read round-trip at the async API level,
        including that the session data payload is preserved.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        record = _make_record("live-session", data={"token": "xyz"})
        await store.write(record)
        result = await store.read("live-session")
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "live-session")  # type: ignore[union-attr]
        self.assertEqual(result.data, {"token": "xyz"})  # type: ignore[union-attr]

    async def testReadExpiredRecordReturnsNone(self) -> None:
        """Return a miss and remove files at both expired deadline offsets.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        for offset in (-1, -5):
            with self.subTest(offset=offset):
                record = _make_record(f"expired{offset}", offset_seconds=offset)
                await store.write(record)
                self.assertIsNone(await store.read(record.id))
                self.assertFalse(store._path(record.id).exists())

    async def testReadCorruptFileReturnsNone(self) -> None:
        """Return a miss and remove each malformed session payload.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        for content in (b"{{broken json", b"not json"):
            with self.subTest(content=content):
                path = store._path("corrupt-session")
                store._writeFile(path, content)
                self.assertIsNone(await store.read("corrupt-session"))
                self.assertFalse(path.exists())

    # ── write ────────────────────────────────────────────────────────────────

    async def testWriteCreatesSessionFile(self) -> None:
        """Persist a session record as a JSON file on disk.

        Validates that write() creates the expected file in the store
        directory so that a subsequent read() can retrieve it.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        await store.write(_make_record("new-file"))
        path = store._path("new-file")
        self.assertTrue(path.exists())

    async def testWriteOverwritesExistingFile(self) -> None:
        """Replace the existing session file on a second write.

        Validates that writing the same session ID twice leaves only one
        file containing the latest data.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        record_v1 = _make_record("over", data={"v": 1})
        record_v2 = _make_record("over", data={"v": 2})
        await store.write(record_v1)
        await store.write(record_v2)
        result = await store.read("over")
        self.assertIsNotNone(result)
        self.assertEqual(result.data, {"v": 2})  # type: ignore[union-attr]

    # ── delete ───────────────────────────────────────────────────────────────

    async def testDeleteRemovesSessionFile(self) -> None:
        """Delete the session file via the async delete() method.

        Validates that after delete() the file is absent from disk and
        subsequent reads return None.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        await store.write(_make_record("to-delete"))
        self.assertTrue(await store.delete("to-delete"))
        path = store._path("to-delete")
        self.assertFalse(path.exists())

    async def testDeleteAbsentSessionIsNoOp(self) -> None:
        """Silently ignore delete() when no file exists for the identifier.

        Validates that calling delete() on an unknown session ID does
        not raise a FileNotFoundError or any other exception.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        self.assertFalse(await store.delete("nonexistent-session"))

    async def testDeleteDoesNotAffectOtherSessions(self) -> None:
        """Preserve unrelated session files when one is deleted.

        Validates that delete() targets only the specified identifier
        and does not remove adjacent session files.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        await store.write(_make_record("keep-me"))
        await store.write(_make_record("remove-me"))
        await store.delete("remove-me")
        result = await store.read("keep-me")
        self.assertIsNotNone(result)

    # ── gc ───────────────────────────────────────────────────────────────────

    async def testGcRemovesExpiredFiles(self) -> None:
        """Evict expired session files during the gc sweep.

        Validates that gc() identifies and deletes files whose
        expires_at timestamps are in the past.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        await store.write(_make_record("live", offset_seconds=3600))
        await store.write(_make_record("dead", offset_seconds=-1))
        await store.gc()
        self.assertTrue(store._path("live").exists())
        self.assertFalse(store._path("dead").exists())

    async def testGcRemovesCorruptFiles(self) -> None:
        """Delete corrupt JSON files during the gc sweep.

        Validates that _gcSweep() removes files that cannot be decoded,
        preventing stale garbage from accumulating in the session directory.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        corrupt_path = self._directory / "bad.json"
        corrupt_path.write_bytes(b"not-valid-json")
        await store.gc()
        self.assertFalse(corrupt_path.exists())

    async def testGcKeepsLiveFiles(self) -> None:
        """Leave valid, non-expired session files untouched during gc().

        Validates that the garbage-collection sweep does not evict
        sessions that are still within their lifetime.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        await store.write(_make_record("session-a", offset_seconds=7200))
        await store.write(_make_record("session-b", offset_seconds=3600))
        await store.gc()
        self.assertTrue(store._path("session-a").exists())
        self.assertTrue(store._path("session-b").exists())

    async def testGcOnEmptyDirectoryIsNoOp(self) -> None:
        """Execute gc() on an empty directory without raising.

        Validates that the gc sweep handles the trivial case of no
        session files gracefully.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        await store.gc()
        remaining = list(self._directory.iterdir())
        self.assertEqual(remaining, [])

    async def testGcIgnoresNonJsonFiles(self) -> None:
        """Leave non-JSON files untouched during the gc sweep.

        Validates that gc() only processes .json files and does not
        interfere with any other content in the session directory.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        other_file = self._directory / "readme.txt"
        other_file.write_text("documentation", encoding="utf-8")
        await store.gc()
        self.assertTrue(other_file.exists())

    async def testGcIgnoresDirectories(self) -> None:
        """Leave sub-directories untouched during the gc sweep.

        Validates that a directory whose name ends in ``.json`` is
        skipped instead of being treated as a session file.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        nested = self._directory / "nested.json"
        nested.mkdir()
        await store.gc()
        self.assertTrue(nested.is_dir())


class TestFileSessionStoreAtomicWrites(TestCase):
    """Regression tests for the staging file backing every write."""

    def setUp(self) -> None:
        """Create an isolated temporary directory before each test.

        Provides a fresh directory so staging files from one test can
        never influence another.

        Returns
        -------
        None
            No return value.
        """
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self._directory = Path(self._tmpdir.name)

    def _store(self) -> FileSessionStore:
        """
        Construct a FileSessionStore backed by the temporary directory.

        Returns
        -------
        FileSessionStore
            A fresh store instance for each caller.
        """
        return FileSessionStore(directory=self._directory)

    def _temps(self) -> list[str]:
        """
        List the staging files currently present in the directory.

        Returns
        -------
        list[str]
            Names of every file whose suffix is ``.tmp``.
        """
        return [
            entry.name
            for entry in self._directory.iterdir()
            if entry.name.endswith(".tmp")
        ]

    def testTempPathIsUniquePerCall(self) -> None:
        """Derive a different staging path on every call.

        Validates that two writers of the same session never share a
        staging file, which would let them publish a mixed payload.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        path = self._directory / "abc.json"

        first = store._tempPath(path)
        second = store._tempPath(path)

        self.assertNotEqual(first, second)
        self.assertEqual(first.parent, path.parent)
        self.assertTrue(first.name.endswith(".tmp"))
        self.assertTrue(second.name.endswith(".tmp"))

    async def testConcurrentWritesToTheSameSessionAllSucceed(self) -> None:
        """Publish every concurrent write of one session without failing.

        Validates that parallel requests sharing a session identifier
        neither raise nor leave the stored payload half written.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        expires = datetime.now(UTC) + timedelta(hours=1)
        blob = "x" * 8192
        records = [
            SessionRecord(
                id="shared",
                data={"n": n, "blob": blob},
                expires_at=expires,
            )
            for n in range(25)
        ]

        results = await asyncio.gather(
            *(store.write(record) for record in records),
            return_exceptions=True,
        )

        failures = [r for r in results if isinstance(r, BaseException)]
        self.assertEqual(failures, [])

        restored = await store.read("shared")
        self.assertIsNotNone(restored)
        self.assertEqual(restored.data["blob"], blob)  # type: ignore[union-attr]
        self.assertIn(restored.data["n"], range(25))  # type: ignore[union-attr]
        self.assertEqual(self._temps(), [])

    async def testFailedWriteRemovesItsTempFile(self) -> None:
        """Reclaim the staging file when the write cannot be published.

        Validates that a rename failure propagates without leaking an
        orphaned staging file into the session directory.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()

        # A directory at the destination makes the rename fail portably.
        (self._directory / "blocked.json").mkdir()

        with self.assertRaises(OSError):
            await store.write(
                SessionRecord(
                    id="blocked",
                    data={},
                    expires_at=datetime.now(UTC) + timedelta(hours=1),
                ),
            )

        self.assertEqual(self._temps(), [])

    async def testGcReclaimsStaleTempFiles(self) -> None:
        """Remove staging files left behind by an interrupted write.

        Validates that an orphan too old to belong to a live write is
        swept instead of accumulating forever.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        orphan = self._directory / "abc.json.deadbeefdeadbeef.tmp"
        orphan.write_bytes(b"partial payload")
        stale = time.time() - 7200
        os.utime(orphan, (stale, stale))

        await store.gc()

        self.assertFalse(orphan.exists())

    async def testGcKeepsTempFilesOfInFlightWrites(self) -> None:
        """Preserve a staging file that a concurrent write may still fill.

        Validates that the sweep only reclaims staging files old enough
        to be certain no writer owns them.

        Returns
        -------
        None
            No return value.
        """
        store = self._store()
        in_flight = self._directory / "abc.json.cafebabecafebabe.tmp"
        in_flight.write_bytes(b"in flight")

        await store.gc()

        self.assertTrue(in_flight.exists())
