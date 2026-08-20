from __future__ import annotations
import hashlib
from datetime import UTC, datetime
from orionis.storage.drivers.memory import MemoryStorageDriver
from orionis.storage.entities.file_info import FileInfo
from orionis.storage.exceptions import (
    StorageFileNotFoundException,
    StoragePathException,
    UnsupportedStorageOperationException,
)
from orionis.test import TestCase

class TestMemoryStorageDriver(TestCase):

    def setUp(self) -> None:
        """
        Create a fresh in-memory driver before each test.

        Guarantees complete isolation between tests since all state
        lives in plain dictionaries inside the driver instance.
        """
        self._driver = MemoryStorageDriver()

    # ── write / read ─────────────────────────────────────────────────────────

    async def testWriteAndReadRoundtrip(self) -> None:
        """
        Persist bytes and read them back unchanged.

        Validates the basic happy path of the write/read pair.
        """
        await self._driver.write("docs/a.txt", b"hello")
        self.assertEqual(await self._driver.read("docs/a.txt"), b"hello")

    async def testWriteEncodesStringsAsUtf8(self) -> None:
        """
        Encode string contents as UTF-8 on write.

        Validates that textual payloads are stored as their UTF-8
        byte representation.
        """
        await self._driver.write("a.txt", "ñandú")
        self.assertEqual(await self._driver.read("a.txt"), "ñandú".encode())

    async def testReadMissingFileRaises(self) -> None:
        """
        Raise StorageFileNotFoundException when reading a missing file.

        Validates the documented failure contract of read().
        """
        with self.assertRaises(StorageFileNotFoundException):
            await self._driver.read("absent.txt")

    async def testWriteRejectsRootEscape(self) -> None:
        """
        Reject paths that escape the disk root.

        Validates the path-traversal protection applied to every
        operation.
        """
        with self.assertRaises(StoragePathException):
            await self._driver.write("../evil.txt", b"x")

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
        self.assertEqual(chunks, [b"abcd", b"efgh", b"ij"])

    async def testWriteStreamPersistsAllChunks(self) -> None:
        """
        Persist every chunk produced by an async generator.

        Validates that streamed writes reassemble the payload.
        """
        async def producer():
            yield b"one"
            yield b"two"

        await self._driver.writeStream("joined.txt", producer())
        self.assertEqual(await self._driver.read("joined.txt"), b"onetwo")

    async def testOpenWriteThenReadThroughStream(self) -> None:
        """
        Write through an open stream and read the persisted content.

        Validates that the stream flushes back into the store on
        close.
        """
        async with self._driver.open("s.txt", "wb") as stream:
            await stream.write(b"streamed")
        self.assertEqual(await self._driver.read("s.txt"), b"streamed")

    async def testOpenReadMissingFileRaises(self) -> None:
        """
        Raise StorageFileNotFoundException when opening a missing file.

        Validates the failure contract of read-mode streams.
        """
        stream = self._driver.open("missing.txt", "rb")
        with self.assertRaises(StorageFileNotFoundException):
            await stream.read()

    async def testOpenRejectsTextModes(self) -> None:
        """
        Reject non-binary stream modes.

        Validates the documented mode whitelist of open().
        """
        with self.assertRaises(UnsupportedStorageOperationException):
            self._driver.open("a.txt", "r")

    # ── existence and deletion ───────────────────────────────────────────────

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

    # ── copy / move ──────────────────────────────────────────────────────────

    async def testCopyDuplicatesContent(self) -> None:
        """
        Duplicate the file content at the target path.

        Validates that both source and copy exist afterwards.
        """
        await self._driver.write("src.txt", b"data")
        await self._driver.copy("src.txt", "dst.txt")
        self.assertEqual(await self._driver.read("dst.txt"), b"data")
        self.assertTrue(await self._driver.exists("src.txt"))

    async def testMoveRemovesSource(self) -> None:
        """
        Relocate the file content and drop the source entry.

        Validates the move semantics of the driver.
        """
        await self._driver.write("src.txt", b"data")
        await self._driver.move("src.txt", "dst.txt")
        self.assertEqual(await self._driver.read("dst.txt"), b"data")
        self.assertFalse(await self._driver.exists("src.txt"))

    async def testCopyMissingSourceRaises(self) -> None:
        """
        Raise StorageFileNotFoundException when copying a missing file.

        Validates the documented failure contract of copy().
        """
        with self.assertRaises(StorageFileNotFoundException):
            await self._driver.copy("nope.txt", "dst.txt")

    # ── metadata ─────────────────────────────────────────────────────────────

    async def testSizeReturnsByteCount(self) -> None:
        """
        Return the exact stored byte count.

        Validates size() against a known payload.
        """
        await self._driver.write("f.bin", b"12345")
        self.assertEqual(await self._driver.size("f.bin"), 5)

    async def testMimeTypeGuessedFromExtension(self) -> None:
        """
        Guess the MIME type from the file extension.

        Validates mimeType() for a well-known extension.
        """
        self.assertEqual(await self._driver.mimeType("photo.png"), "image/png")

    async def testLastModifiedIsTimezoneAware(self) -> None:
        """
        Return a timezone-aware UTC timestamp.

        Validates the datetime contract of lastModified().
        """
        await self._driver.write("f.txt", b"x")
        stamp = await self._driver.lastModified("f.txt")
        self.assertIsInstance(stamp, datetime)
        self.assertEqual(stamp.tzinfo, UTC)

    async def testVisibilityDefaultsToPrivate(self) -> None:
        """
        Store files as private when no visibility is given.

        Validates the default visibility of the memory driver.
        """
        await self._driver.write("f.txt", b"x")
        self.assertEqual(await self._driver.visibility("f.txt"), "private")

    async def testSetVisibilityUpdatesEntry(self) -> None:
        """
        Update the stored visibility level.

        Validates the setVisibility()/visibility() pair.
        """
        await self._driver.write("f.txt", b"x")
        await self._driver.setVisibility("f.txt", "public")
        self.assertEqual(await self._driver.visibility("f.txt"), "public")

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
        await self._driver.write("docs/f.txt", b"abc", visibility="public")
        info = await self._driver.info("docs/f.txt")
        self.assertIsInstance(info, FileInfo)
        self.assertEqual(info.path, "docs/f.txt")
        self.assertEqual(info.size, 3)
        self.assertEqual(info.visibility, "public")
        self.assertEqual(info.checksum, hashlib.sha256(b"abc").hexdigest())
        self.assertEqual(info.mimeType, "text/plain")

    # ── directories ──────────────────────────────────────────────────────────

    async def testDirectoryExistsForImplicitParents(self) -> None:
        """
        Report directories implied by stored file paths.

        Validates implicit directory semantics of the memory driver.
        """
        await self._driver.write("a/b/c.txt", b"x")
        self.assertTrue(await self._driver.directoryExists("a"))
        self.assertTrue(await self._driver.directoryExists("a/b"))
        self.assertFalse(await self._driver.directoryExists("z"))

    async def testCreateAndDeleteDirectory(self) -> None:
        """
        Create an explicit directory and delete it with its contents.

        Validates createDirectory()/deleteDirectory() round trips.
        """
        await self._driver.createDirectory("uploads")
        self.assertTrue(await self._driver.directoryExists("uploads"))
        await self._driver.write("uploads/f.txt", b"x")
        self.assertTrue(await self._driver.deleteDirectory("uploads"))
        self.assertFalse(await self._driver.exists("uploads/f.txt"))
        self.assertFalse(await self._driver.directoryExists("uploads"))

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

    # ── URLs ─────────────────────────────────────────────────────────────────

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
        driver = MemoryStorageDriver(base_url="/static/")
        await driver.write("img/a b.png", b"x")
        self.assertEqual(await driver.url("img/a b.png"), "/static/img/a%20b.png")

    async def testTemporaryUrlAlwaysRaises(self) -> None:
        """
        Raise since memory disks cannot sign URLs.

        Validates the documented limitation of temporaryUrl().
        """
        await self._driver.write("f.txt", b"x")
        with self.assertRaises(UnsupportedStorageOperationException):
            await self._driver.temporaryUrl("f.txt", 60)
