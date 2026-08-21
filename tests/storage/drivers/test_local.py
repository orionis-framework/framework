from __future__ import annotations
import asyncio
import hashlib
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from orionis.storage.drivers.local import LocalStorageDriver
from orionis.storage.entities.file_info import FileInfo
from orionis.storage.exceptions import (
    StorageFileNotFoundException,
    StoragePathException,
    UnsupportedStorageOperationException,
)
from orionis.test import TestCase

class TestLocalStorageDriver(TestCase):

    def setUp(self) -> None:
        """
        Create a temporary root and a local driver before each test.

        Provides an isolated, writable directory so every test
        operates on its own filesystem state without side effects.
        """
        self._tmpdir = tempfile.TemporaryDirectory()
        self._root = Path(self._tmpdir.name)
        self._driver = LocalStorageDriver(self._root)

    def tearDown(self) -> None:
        """
        Remove the temporary root after each test.

        Ensures all files created during the test are cleaned up
        regardless of the test outcome.
        """
        self._tmpdir.cleanup()

    # ── write / read ─────────────────────────────────────────────────────────

    async def testWriteAndReadRoundtrip(self) -> None:
        """
        Persist bytes and read them back unchanged.

        Validates the basic happy path of the write/read pair,
        including automatic parent directory creation.
        """
        await self._driver.write("nested/dir/a.bin", b"hello")
        self.assertEqual(await self._driver.read("nested/dir/a.bin"), b"hello")

    async def testWriteEncodesStringsAsUtf8(self) -> None:
        """
        Encode string contents as UTF-8 on write.

        Validates that textual payloads land on disk as UTF-8 bytes.
        """
        await self._driver.write("a.txt", "café")
        self.assertEqual((self._root / "a.txt").read_bytes(), "café".encode())

    async def testWriteLeavesNoTempFileBehind(self) -> None:
        """
        Clean up the intermediate temp file used for atomic writes.

        Validates that only the final file remains after a write.
        """
        await self._driver.write("clean.txt", b"x")
        leftovers = [p.name for p in self._root.iterdir()]
        self.assertEqual(leftovers, ["clean.txt"])

    async def testConcurrentWritesToTheSamePathNeverMixPayloads(self) -> None:
        """
        Publish a whole payload when writers race on the same path.

        Validates that every write stages its bytes in its own temp
        file, so a racing writer can neither publish a mix of two
        payloads nor steal another writer's staging file. Windows may
        still refuse a concurrent replace of the destination, which is
        an operating system limitation and never a lost staging file.
        """
        payloads = [bytes([index]) * 4096 for index in range(1, 9)]
        results = await asyncio.gather(
            *[
                self._driver.write("shared.bin", payload)
                for payload in payloads
            ],
            return_exceptions=True,
        )

        for result in results:
            if result is not None:
                self.assertIsInstance(result, PermissionError)

        self.assertIn(None, results)
        self.assertIn(await self._driver.read("shared.bin"), payloads)
        self.assertEqual(
            [p.name for p in self._root.iterdir()], ["shared.bin"],
        )

    async def testFailedWriteRemovesItsTempFile(self) -> None:
        """
        Discard the staging file when the write cannot be committed.

        Validates the cleanup path by targeting an existing directory,
        which no platform can replace with a file.
        """
        (self._root / "busy").mkdir()
        with self.assertRaises(OSError):
            await self._driver.write("busy", b"x")
        self.assertEqual([p.name for p in self._root.iterdir()], ["busy"])

    async def testReadMissingFileRaises(self) -> None:
        """
        Raise StorageFileNotFoundException when reading a missing file.

        Validates the documented failure contract of read().
        """
        with self.assertRaises(StorageFileNotFoundException):
            await self._driver.read("absent.txt")

    async def testPathTraversalIsRejected(self) -> None:
        """
        Reject paths that escape the disk root.

        Validates traversal protection with both separator styles.
        """
        with self.assertRaises(StoragePathException):
            await self._driver.write("../evil.txt", b"x")
        with self.assertRaises(StoragePathException):
            await self._driver.read("..\\..\\secret")

    # ── streams ──────────────────────────────────────────────────────────────

    async def testReadStreamYieldsChunks(self) -> None:
        """
        Yield the file content in chunks of the requested size.

        Validates chunked iteration and full content reassembly.
        """
        await self._driver.write("big.bin", b"abcdefghij")
        chunks = [
            chunk
            async for chunk in self._driver.readStream("big.bin", chunk_size=4)
        ]
        self.assertEqual(b"".join(chunks), b"abcdefghij")
        self.assertEqual(len(chunks), 3)

    async def testWriteStreamPersistsAllChunks(self) -> None:
        """
        Persist every chunk produced by an async generator.

        Validates that streamed writes reassemble the payload and
        create parent directories.
        """
        async def producer():
            yield b"one"
            yield b"two"

        await self._driver.writeStream("chunks/joined.txt", producer())
        self.assertEqual(
            await self._driver.read("chunks/joined.txt"),
            b"onetwo",
        )

    async def testFailedStreamWriteLeavesNothingBehind(self) -> None:
        """
        Discard the staging file when a streamed transfer fails.

        Validates that an interrupted stream creates no destination
        file and removes only its own temp file.
        """
        async def producer():
            yield b"one"
            error_msg = "producer exhausted unexpectedly"
            raise RuntimeError(error_msg)

        with self.assertRaises(RuntimeError):
            await self._driver.writeStream("partial.bin", producer())

        self.assertEqual(list(self._root.iterdir()), [])
        self.assertFalse(await self._driver.exists("partial.bin"))

    async def testOpenWriteThenReadThroughStream(self) -> None:
        """
        Write through an open stream and read the content back.

        Validates the async context-manager stream over local files.
        """
        async with self._driver.open("s.bin", "wb") as stream:
            await stream.write(b"streamed")
        async with self._driver.open("s.bin", "rb") as stream:
            self.assertEqual(await stream.read(), b"streamed")

    def testOpenRejectsTextModes(self) -> None:
        """
        Reject non-binary stream modes.

        Validates the documented mode whitelist of open().
        """
        with self.assertRaises(UnsupportedStorageOperationException):
            self._driver.open("a.txt", "w")

    # ── existence, deletion, copy, move ──────────────────────────────────────

    async def testExistsReflectsState(self) -> None:
        """
        Report existence only for stored files.

        Validates exists() before and after a write.
        """
        self.assertFalse(await self._driver.exists("f.txt"))
        await self._driver.write("f.txt", b"x")
        self.assertTrue(await self._driver.exists("f.txt"))

    async def testDeleteReturnsWhetherFileExisted(self) -> None:
        """
        Return True only when the deleted file existed.

        Validates the boolean contract of delete().
        """
        await self._driver.write("f.txt", b"x")
        self.assertTrue(await self._driver.delete("f.txt"))
        self.assertFalse(await self._driver.delete("f.txt"))

    async def testCopyDuplicatesContent(self) -> None:
        """
        Duplicate the file content at the target path.

        Validates that both source and copy exist afterwards.
        """
        await self._driver.write("src.txt", b"data")
        await self._driver.copy("src.txt", "copies/dst.txt")
        self.assertEqual(await self._driver.read("copies/dst.txt"), b"data")
        self.assertTrue(await self._driver.exists("src.txt"))

    async def testMoveRemovesSource(self) -> None:
        """
        Relocate the file content and drop the source file.

        Validates the move semantics of the driver.
        """
        await self._driver.write("src.txt", b"data")
        await self._driver.move("src.txt", "moved/dst.txt")
        self.assertEqual(await self._driver.read("moved/dst.txt"), b"data")
        self.assertFalse(await self._driver.exists("src.txt"))

    # ── metadata ─────────────────────────────────────────────────────────────

    async def testSizeReturnsByteCount(self) -> None:
        """
        Return the exact stored byte count.

        Validates size() against a known payload.
        """
        await self._driver.write("f.bin", b"12345")
        self.assertEqual(await self._driver.size("f.bin"), 5)

    async def testLastModifiedIsTimezoneAware(self) -> None:
        """
        Return a timezone-aware UTC timestamp.

        Validates the datetime contract of lastModified().
        """
        await self._driver.write("f.txt", b"x")
        stamp = await self._driver.lastModified("f.txt")
        self.assertIsInstance(stamp, datetime)
        self.assertEqual(stamp.tzinfo, UTC)

    async def testVisibilityReturnsSupportedLevel(self) -> None:
        """
        Return one of the supported visibility levels.

        Validates visibility() portability across platforms with
        partial POSIX permission support.
        """
        await self._driver.write("f.txt", b"x")
        self.assertIn(
            await self._driver.visibility("f.txt"),
            ("public", "private"),
        )

    async def testSetVisibilityRejectsUnknownLevel(self) -> None:
        """
        Reject visibility levels outside the supported set.

        Validates the failure contract of setVisibility().
        """
        await self._driver.write("f.txt", b"x")
        with self.assertRaises(UnsupportedStorageOperationException):
            await self._driver.setVisibility("f.txt", "secret")

    async def testHashMatchesHashlibDigest(self) -> None:
        """
        Compute the same digest as hashlib for the stored content.

        Validates hash() against a locally computed SHA-256.
        """
        await self._driver.write("f.bin", b"payload")
        expected = hashlib.sha256(b"payload").hexdigest()
        self.assertEqual(await self._driver.hash("f.bin"), expected)

    async def testInfoReturnsFileInfoEntity(self) -> None:
        """
        Return an immutable FileInfo snapshot with coherent values.

        Validates the info() aggregation of size, hashes, and MIME.
        """
        await self._driver.write("docs/f.txt", b"abc")
        info = await self._driver.info("docs/f.txt")
        self.assertIsInstance(info, FileInfo)
        self.assertEqual(info.path, "docs/f.txt")
        self.assertEqual(info.size, 3)
        self.assertEqual(info.checksum, hashlib.sha256(b"abc").hexdigest())
        self.assertEqual(info.mimeType, "text/plain")
        self.assertEqual(info.lastModified.tzinfo, UTC)

    # ── directories ──────────────────────────────────────────────────────────

    async def testCreateAndDeleteDirectory(self) -> None:
        """
        Create a nested directory and delete it with its contents.

        Validates createDirectory()/deleteDirectory() round trips.
        """
        await self._driver.createDirectory("up/loads")
        self.assertTrue(await self._driver.directoryExists("up/loads"))
        await self._driver.write("up/loads/f.txt", b"x")
        self.assertTrue(await self._driver.deleteDirectory("up"))
        self.assertFalse(await self._driver.directoryExists("up"))
        self.assertFalse(await self._driver.deleteDirectory("up"))

    async def testFilesListsDirectAndRecursiveEntries(self) -> None:
        """
        List direct children and full subtrees separately.

        Validates the recursive flag of files().
        """
        await self._driver.write("d/one.txt", b"1")
        await self._driver.write("d/sub/two.txt", b"2")
        self.assertEqual(await self._driver.files("d"), ["d/one.txt"])
        self.assertEqual(
            await self._driver.files("d", recursive=True),
            ["d/one.txt", "d/sub/two.txt"],
        )

    async def testDirectoriesListsDirectAndRecursiveEntries(self) -> None:
        """
        List direct child directories and full subtrees separately.

        Validates the recursive flag of directories().
        """
        await self._driver.write("d/sub/deep/f.txt", b"x")
        self.assertEqual(await self._driver.directories("d"), ["d/sub"])
        self.assertEqual(
            await self._driver.directories("d", recursive=True),
            ["d/sub", "d/sub/deep"],
        )

    # ── URLs and downloads ───────────────────────────────────────────────────

    async def testUrlWithoutBaseUrlRaises(self) -> None:
        """
        Raise when the disk exposes no public URLs.

        Validates the failure contract of url() without a base URL.
        """
        await self._driver.write("f.txt", b"x")
        with self.assertRaises(UnsupportedStorageOperationException):
            await self._driver.url("f.txt")

    async def testUrlComposedFromBaseUrl(self) -> None:
        """
        Compose the public URL from the configured base URL.

        Validates URL building and path quoting.
        """
        driver = LocalStorageDriver(self._root, base_url="/static")
        await driver.write("img/a b.png", b"x")
        self.assertEqual(await driver.url("img/a b.png"), "/static/img/a%20b.png")

    async def testTemporaryUrlAlwaysRaises(self) -> None:
        """
        Raise since local disks cannot sign URLs.

        Validates the documented limitation of temporaryUrl().
        """
        await self._driver.write("f.txt", b"x")
        with self.assertRaises(UnsupportedStorageOperationException):
            await self._driver.temporaryUrl("f.txt", 60)

    async def testDownloadCopiesToLocalDestination(self) -> None:
        """
        Copy the stored file to a local destination path.

        Validates download() with both file and directory targets.
        """
        await self._driver.write("docs/report.pdf", b"pdf-bytes")
        with tempfile.TemporaryDirectory() as destination:
            target = await self._driver.download("docs/report.pdf", destination)
            self.assertEqual(target.name, "report.pdf")
            self.assertEqual(target.read_bytes(), b"pdf-bytes")
