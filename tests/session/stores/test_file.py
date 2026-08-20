from __future__ import annotations
import tempfile
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
        """
        Create an isolated temporary directory before each test.

        Provides a fresh directory for every test so file-system
        operations cannot leak state between tests.
        """
        self._tmpdir = tempfile.TemporaryDirectory()
        self._directory = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        """
        Remove the temporary directory and its contents after each test.

        Ensures that all session files created during a test are cleaned
        up regardless of whether the test passed or failed.
        """
        self._tmpdir.cleanup()

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
        """
        Create the storage directory on instantiation if absent.

        Validates that FileSessionStore.mkdir() is invoked so that a
        nested path that does not yet exist is created automatically.
        """
        nested = self._directory / "deep" / "nested"
        FileSessionStore(directory=nested)
        self.assertTrue(nested.is_dir())

    def testInitAcceptsExistingDirectory(self) -> None:
        """
        Accept a pre-existing directory without error.

        Validates that constructing the store when the directory already
        exists does not raise an exception.
        """
        store = self._store()
        self.assertIsNotNone(store)

    # ── _path helper ─────────────────────────────────────────────────────────

    def testPathReturnsCorrectFilename(self) -> None:
        """
        Return the expected .json file path for a given session ID.

        Validates that _path() appends the .json extension and places
        the file inside the store directory.
        """
        store = self._store()
        p = store._path("my-session")
        self.assertEqual(p, self._directory / "my-session.json")

    # ── _serialize / _deserialize round-trip ─────────────────────────────────

    def testSerializeDeserializeRoundTrip(self) -> None:
        """
        Recover the original record after serialisation and deserialisation.

        Validates that _serialize() followed by _deserialize() produces
        a record equal to the original in all fields.
        """
        store = self._store()
        original = _make_record("rt", data={"user": "bob", "age": 30})
        raw = store._serialize(original)
        recovered = store._deserialize(raw)
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.id, original.id)  # type: ignore[union-attr]
        self.assertEqual(recovered.data, original.data)  # type: ignore[union-attr]

    def testDeserializeCorruptBytesReturnsNone(self) -> None:
        """
        Return None when the raw bytes are not valid JSON.

        Validates that _deserialize() gracefully handles corruption
        without raising an exception.
        """
        store = self._store()
        result = store._deserialize(b"not-json-at-all!!!")
        self.assertIsNone(result)

    def testDeserializeEmptyBytesReturnsNone(self) -> None:
        """
        Return None when given an empty byte string.

        Validates that _deserialize() handles the empty-input edge case
        without raising.
        """
        store = self._store()
        result = store._deserialize(b"")
        self.assertIsNone(result)

    # ── _readFile / _writeFile ────────────────────────────────────────────────

    def testWriteFileAndReadFileRoundTrip(self) -> None:
        """
        Recover bytes written by _writeFile via _readFile.

        Validates the low-level file I/O helpers produce identical
        content on the round trip.
        """
        store = self._store()
        path = self._directory / "test.bin"
        content = b"hello bytes"
        store._writeFile(path, content)
        result = store._readFile(path)
        self.assertEqual(result, content)

    def testReadFileMissingReturnsNone(self) -> None:
        """
        Return None when the target file does not exist.

        Validates that _readFile() signals absence with None rather
        than propagating a FileNotFoundError.
        """
        store = self._store()
        result = store._readFile(self._directory / "absent.bin")
        self.assertIsNone(result)

    def testWriteFileIsAtomic(self) -> None:
        """
        Leave no .tmp artefact after a successful write.

        Validates that _writeFile() cleans up the temporary file and
        only the final destination exists after the call.
        """
        store = self._store()
        path = self._directory / "atomic.json"
        store._writeFile(path, b"data")
        tmp = path.with_suffix(".tmp")
        self.assertTrue(path.exists())
        self.assertFalse(tmp.exists())

    # ── read ─────────────────────────────────────────────────────────────────

    async def testReadAbsentSessionReturnsNone(self) -> None:
        """
        Return None for a session identifier with no corresponding file.

        Validates that reading a non-existent session ID from the file
        store signals a cache miss without raising.
        """
        store = self._store()
        result = await store.read("ghost-session")
        self.assertIsNone(result)

    async def testReadReturnsLiveRecord(self) -> None:
        """
        Return the record for a live, non-expired session file.

        Validates the basic write/read round-trip at the async API level,
        including that the session data payload is preserved.
        """
        store = self._store()
        record = _make_record("live-session", data={"token": "xyz"})
        await store.write(record)
        result = await store.read("live-session")
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "live-session")  # type: ignore[union-attr]
        self.assertEqual(result.data, {"token": "xyz"})  # type: ignore[union-attr]

    async def testReadExpiredRecordReturnsNone(self) -> None:
        """
        Return None and delete the file for an expired session.

        Validates that a session file whose expires_at is in the past is
        treated as a cache miss and lazily evicted.
        """
        store = self._store()
        record = _make_record("expired-session", offset_seconds=-1)
        await store.write(record)
        result = await store.read("expired-session")
        self.assertIsNone(result)

    async def testReadExpiredRecordDeletesFile(self) -> None:
        """
        Remove the session file when an expired record is read.

        Validates that lazy eviction occurs so the storage directory
        does not accumulate stale session files indefinitely.
        """
        store = self._store()
        record = _make_record("stale-session", offset_seconds=-5)
        await store.write(record)
        await store.read("stale-session")
        path = store._path("stale-session")
        self.assertFalse(path.exists())

    async def testReadCorruptFileReturnsNone(self) -> None:
        """
        Return None when the session file contains invalid JSON.

        Validates that a corrupt file is treated as a cache miss and
        does not propagate a decode exception to the caller.
        """
        store = self._store()
        path = store._path("corrupt-session")
        store._writeFile(path, b"{{broken json")
        result = await store.read("corrupt-session")
        self.assertIsNone(result)

    async def testReadCorruptFileDeletesFile(self) -> None:
        """
        Delete the session file when it contains invalid JSON.

        Validates that corrupt files are removed during the lazy eviction
        triggered by a read attempt.
        """
        store = self._store()
        path = store._path("corrupt-del")
        store._writeFile(path, b"not json")
        await store.read("corrupt-del")
        self.assertFalse(path.exists())

    # ── write ────────────────────────────────────────────────────────────────

    async def testWriteCreatesSessionFile(self) -> None:
        """
        Persist a session record as a JSON file on disk.

        Validates that write() creates the expected file in the store
        directory so that a subsequent read() can retrieve it.
        """
        store = self._store()
        await store.write(_make_record("new-file"))
        path = store._path("new-file")
        self.assertTrue(path.exists())

    async def testWriteOverwritesExistingFile(self) -> None:
        """
        Replace the existing session file on a second write.

        Validates that writing the same session ID twice leaves only one
        file containing the latest data.
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
        """
        Delete the session file via the async delete() method.

        Validates that after delete() the file is absent from disk and
        subsequent reads return None.
        """
        store = self._store()
        await store.write(_make_record("to-delete"))
        await store.delete("to-delete")
        path = store._path("to-delete")
        self.assertFalse(path.exists())

    async def testDeleteAbsentSessionIsNoOp(self) -> None:
        """
        Silently ignore delete() when no file exists for the identifier.

        Validates that calling delete() on an unknown session ID does
        not raise a FileNotFoundError or any other exception.
        """
        store = self._store()
        await store.delete("nonexistent-session")

    async def testDeleteDoesNotAffectOtherSessions(self) -> None:
        """
        Preserve unrelated session files when one is deleted.

        Validates that delete() targets only the specified identifier
        and does not remove adjacent session files.
        """
        store = self._store()
        await store.write(_make_record("keep-me"))
        await store.write(_make_record("remove-me"))
        await store.delete("remove-me")
        result = await store.read("keep-me")
        self.assertIsNotNone(result)

    # ── gc ───────────────────────────────────────────────────────────────────

    async def testGcRemovesExpiredFiles(self) -> None:
        """
        Evict expired session files during the gc sweep.

        Validates that gc() identifies and deletes files whose
        expires_at timestamps are in the past.
        """
        store = self._store()
        await store.write(_make_record("live", offset_seconds=3600))
        await store.write(_make_record("dead", offset_seconds=-1))
        await store.gc()
        self.assertTrue(store._path("live").exists())
        self.assertFalse(store._path("dead").exists())

    async def testGcRemovesCorruptFiles(self) -> None:
        """
        Delete corrupt JSON files during the gc sweep.

        Validates that _gcSweep() removes files that cannot be decoded,
        preventing stale garbage from accumulating in the session directory.
        """
        store = self._store()
        corrupt_path = self._directory / "bad.json"
        corrupt_path.write_bytes(b"not-valid-json")
        await store.gc()
        self.assertFalse(corrupt_path.exists())

    async def testGcKeepsLiveFiles(self) -> None:
        """
        Leave valid, non-expired session files untouched during gc().

        Validates that the garbage-collection sweep does not evict
        sessions that are still within their lifetime.
        """
        store = self._store()
        await store.write(_make_record("session-a", offset_seconds=7200))
        await store.write(_make_record("session-b", offset_seconds=3600))
        await store.gc()
        self.assertTrue(store._path("session-a").exists())
        self.assertTrue(store._path("session-b").exists())

    async def testGcOnEmptyDirectoryIsNoOp(self) -> None:
        """
        Execute gc() on an empty directory without raising.

        Validates that the gc sweep handles the trivial case of no
        session files gracefully.
        """
        store = self._store()
        await store.gc()
        remaining = list(self._directory.iterdir())
        self.assertEqual(remaining, [])

    async def testGcIgnoresNonJsonFiles(self) -> None:
        """
        Leave non-JSON files untouched during the gc sweep.

        Validates that gc() only processes .json files and does not
        interfere with any other content in the session directory.
        """
        store = self._store()
        other_file = self._directory / "readme.txt"
        other_file.write_text("documentation", encoding="utf-8")
        await store.gc()
        self.assertTrue(other_file.exists())

    async def testGcIgnoresDirectories(self) -> None:
        """
        Leave sub-directories untouched during the gc sweep.

        Validates that a directory whose name ends in ``.json`` is
        skipped instead of being treated as a session file.
        """
        store = self._store()
        nested = self._directory / "nested.json"
        nested.mkdir()
        await store.gc()
        self.assertTrue(nested.is_dir())
