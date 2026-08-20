from __future__ import annotations
import hashlib
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from orionis.storage.contracts.file import IFile
from orionis.storage.contracts.stream import IStorageStream
from orionis.storage.disk import Disk
from orionis.storage.drivers.memory import MemoryStorageDriver
from orionis.storage.entities.file_info import FileInfo
from orionis.storage.enums.visibility import Visibility
from orionis.storage.exceptions import (
    StorageFileNotFoundException,
    StoragePathException,
    UnsupportedStorageOperationException,
)
from orionis.storage.file import File
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

async def chunk_stream(chunks: tuple[bytes, ...]) -> AsyncIterator[bytes]:
    """
    Yield every chunk of *chunks* asynchronously.

    Parameters
    ----------
    chunks : tuple[bytes, ...]
        Consecutive byte chunks to emit.

    Yields
    ------
    bytes
        The next chunk of the sequence.
    """
    for chunk in chunks:
        yield chunk

class TestFilePath(TestCase):

    def setUp(self) -> None:
        """
        Build a driver-backed file factory before each test.

        Keeps every test isolated in its own in-memory store.
        """
        self._driver = MemoryStorageDriver()

    def testImplementsTheFileContract(self) -> None:
        """
        Expose the file through its published contract.

        Validates that disks can type their return values.
        """
        self.assertIsInstance(File(self._driver, "a.txt"), IFile)

    def testPathIsNormalizedOnIngestion(self) -> None:
        """
        Normalize the path supplied at construction time.

        Validates that separators and redundant segments collapse.
        """
        file = File(self._driver, "\\docs//sub/../a.txt")
        self.assertEqual(file.path(), "docs/a.txt")

    def testRootPathIsRejected(self) -> None:
        """
        Reject paths resolving to the disk root.

        Validates that a file always targets a concrete path.
        """
        with self.assertRaises(StoragePathException):
            File(self._driver, "/")

    def testEscapingPathIsRejected(self) -> None:
        """
        Reject paths escaping the disk root.

        Validates the traversal guard applied on ingestion.
        """
        with self.assertRaises(StoragePathException):
            File(self._driver, "../escape.txt")

class TestFileContent(TestCase):

    def setUp(self) -> None:
        """
        Build a disk over a fresh memory driver before each test.

        Keeps every test isolated in its own in-memory store.
        """
        self._disk = Disk(name="fake", driver=MemoryStorageDriver())

    async def testWriteIsFluentAndPersistsBytes(self) -> None:
        """
        Persist raw bytes and return the same file object.

        Validates fluent chaining on the write path.
        """
        file = self._disk.file("f.txt")
        self.assertIs(await file.write(b"data"), file)
        self.assertEqual(await file.read(), b"data")

    async def testWriteEncodesStringsAsUtf8(self) -> None:
        """
        Encode string contents before persisting them.

        Validates the string branch of the write path.
        """
        file = await self._disk.file("f.txt").write("año")
        self.assertEqual(await file.read(), "año".encode())

    async def testWriteAppliesTheRequestedVisibility(self) -> None:
        """
        Forward the visibility argument down to the driver.

        Validates the optional parameter of write().
        """
        file = await self._disk.file("f.txt").write(
            b"data", Visibility.PUBLIC.value,
        )
        self.assertEqual(await file.visibility(), Visibility.PUBLIC.value)

    async def testReadMissingFileRaises(self) -> None:
        """
        Reject reads targeting a missing file.

        Validates the failure contract of read().
        """
        with self.assertRaises(StorageFileNotFoundException):
            await self._disk.file("missing.txt").read()

    async def testReadStreamYieldsConsecutiveChunks(self) -> None:
        """
        Stream the contents in chunks of the requested size.

        Validates the chunk_size argument of readStream().
        """
        file = await self._disk.put("f.txt", b"abcde")
        chunks = [chunk async for chunk in file.readStream(2)]
        self.assertEqual(chunks, [b"ab", b"cd", b"e"])

    async def testWriteStreamIsFluentAndJoinsChunks(self) -> None:
        """
        Persist every chunk produced by an async iterable.

        Validates fluent chaining on the streamed write path.
        """
        file = self._disk.file("f.txt")
        written = await file.writeStream(chunk_stream((b"ab", b"cd")))
        self.assertIs(written, file)
        self.assertEqual(await file.read(), b"abcd")

    async def testWriteStreamAppliesTheRequestedVisibility(self) -> None:
        """
        Forward the visibility argument on the streamed write path.

        Validates the optional parameter of writeStream().
        """
        file = await self._disk.file("f.txt").writeStream(
            chunk_stream((b"ab",)), Visibility.PUBLIC.value,
        )
        self.assertEqual(await file.visibility(), Visibility.PUBLIC.value)

    async def testOpenReturnsAnAsyncStream(self) -> None:
        """
        Open a binary stream over the file through the driver.

        Validates the round trip between a write and a read stream.
        """
        file = self._disk.file("f.txt")
        stream = file.open("wb")
        self.assertIsInstance(stream, IStorageStream)
        async with stream:
            await stream.write(b"streamed")
        self.assertEqual(await file.read(), b"streamed")

    def testOpenRejectsTextModes(self) -> None:
        """
        Reject stream modes that are not binary.

        Validates the failure contract of open().
        """
        with self.assertRaises(UnsupportedStorageOperationException):
            self._disk.file("f.txt").open("r")

    async def testExistsReflectsTheStoredState(self) -> None:
        """
        Report whether the file is present on the disk.

        Validates the delegation of exists().
        """
        file = self._disk.file("f.txt")
        self.assertFalse(await file.exists())
        await file.write(b"data")
        self.assertTrue(await file.exists())

    async def testDeleteReportsWhetherTheFileExisted(self) -> None:
        """
        Remove the file and report whether it was present.

        Validates the delegation of delete().
        """
        file = await self._disk.put("f.txt", b"data")
        self.assertTrue(await file.delete())
        self.assertFalse(await file.delete())

class TestFileRelocation(TestCase):

    def setUp(self) -> None:
        """
        Build a disk over a fresh memory driver before each test.

        Keeps every test isolated in its own in-memory store.
        """
        self._disk = Disk(name="fake", driver=MemoryStorageDriver())

    async def testCopyToReturnsANewFileObject(self) -> None:
        """
        Copy the file and return an object for the duplicate.

        Validates copyTo() semantics and source preservation.
        """
        original = await self._disk.put("one.txt", b"data")
        clone = await original.copyTo("sub//two.txt")
        self.assertIsNot(clone, original)
        self.assertEqual(clone.path(), "sub/two.txt")
        self.assertEqual(await clone.read(), b"data")
        self.assertTrue(await original.exists())

    async def testCopyToMissingSourceRaises(self) -> None:
        """
        Reject copies whose source file does not exist.

        Validates the failure contract of copyTo().
        """
        with self.assertRaises(StorageFileNotFoundException):
            await self._disk.file("missing.txt").copyTo("two.txt")

    async def testMoveToReturnsANewFileObject(self) -> None:
        """
        Move the file and return an object for the new location.

        Validates moveTo() semantics and source removal.
        """
        original = await self._disk.put("one.txt", b"data")
        moved = await original.moveTo("sub/two.txt")
        self.assertEqual(moved.path(), "sub/two.txt")
        self.assertEqual(await moved.read(), b"data")
        self.assertFalse(await original.exists())

    async def testMoveToMissingSourceRaises(self) -> None:
        """
        Reject moves whose source file does not exist.

        Validates the failure contract of moveTo().
        """
        with self.assertRaises(StorageFileNotFoundException):
            await self._disk.file("missing.txt").moveTo("two.txt")

    async def testRenameKeepsTheParentDirectory(self) -> None:
        """
        Rename the file inside its current directory.

        Validates the parent-preserving path computation.
        """
        original = await self._disk.put("docs/old.txt", b"data")
        renamed = await original.rename("new.txt")
        self.assertEqual(renamed.path(), "docs/new.txt")
        self.assertEqual(await renamed.read(), b"data")

    async def testRenameWorksAtTheDiskRoot(self) -> None:
        """
        Rename a file stored directly at the disk root.

        Validates the branch without a parent directory.
        """
        original = await self._disk.put("old.txt", b"data")
        renamed = await original.rename("new.txt")
        self.assertEqual(renamed.path(), "new.txt")

    async def testRenameRejectsEmptyNames(self) -> None:
        """
        Reject empty names on rename.

        Validates the failure contract of rename().
        """
        file = await self._disk.put("docs/old.txt", b"data")
        with self.assertRaises(StoragePathException):
            await file.rename("")

    async def testRenameRejectsDirectorySeparators(self) -> None:
        """
        Reject names containing a directory separator.

        Validates that rename() never relocates the file.
        """
        file = await self._disk.put("docs/old.txt", b"data")
        with self.assertRaises(StoragePathException):
            await file.rename("sub/new.txt")
        with self.assertRaises(StoragePathException):
            await file.rename("sub\\new.txt")

class TestFileMetadata(TestCase):

    def setUp(self) -> None:
        """
        Build a public disk over a fresh memory driver.

        The base URL keeps URL-related assertions self-contained.
        """
        self._disk = Disk(
            name="fake",
            driver=MemoryStorageDriver(base_url="https://cdn.test"),
        )

    async def testSizeReturnsTheByteCount(self) -> None:
        """
        Return the size of the stored contents in bytes.

        Validates the delegation of size().
        """
        file = await self._disk.put("f.txt", b"abc")
        self.assertEqual(await file.size(), 3)

    async def testMimeTypeIsGuessedFromTheExtension(self) -> None:
        """
        Guess the MIME type from the file extension.

        Validates both the known and the unknown outcomes.
        """
        known = await self._disk.put("f.txt", b"abc")
        self.assertEqual(await known.mimeType(), "text/plain")
        unknown = await self._disk.put("f.unknownext", b"abc")
        self.assertIsNone(await unknown.mimeType())

    async def testLastModifiedIsTimezoneAware(self) -> None:
        """
        Return a timezone-aware modification timestamp.

        Validates the delegation of lastModified().
        """
        file = await self._disk.put("f.txt", b"abc")
        self.assertIsNotNone((await file.lastModified()).tzinfo)

    async def testUrlIsBuiltFromTheDiskBaseUrl(self) -> None:
        """
        Compose the public URL of the file.

        Validates the delegation of url().
        """
        file = await self._disk.put("img/a b.png", b"x")
        self.assertEqual(await file.url(), "https://cdn.test/img/a%20b.png")

    async def testTemporaryUrlSurfacesDriverLimitations(self) -> None:
        """
        Propagate the driver failure for unsupported signed URLs.

        Validates the delegation of temporaryUrl().
        """
        file = await self._disk.put("f.txt", b"abc")
        with self.assertRaises(UnsupportedStorageOperationException):
            await file.temporaryUrl(60)

    async def testVisibilityDefaultsToPrivate(self) -> None:
        """
        Report the visibility applied by the medium default.

        Validates the delegation of visibility().
        """
        file = await self._disk.put("f.txt", b"abc")
        self.assertEqual(await file.visibility(), Visibility.PRIVATE.value)

    async def testSetVisibilityIsFluent(self) -> None:
        """
        Change the visibility and return the same file object.

        Validates fluent chaining on setVisibility().
        """
        file = await self._disk.put("f.txt", b"abc")
        self.assertIs(await file.setVisibility(Visibility.PUBLIC.value), file)
        self.assertEqual(await file.visibility(), Visibility.PUBLIC.value)

    async def testSetVisibilityRejectsUnknownLevels(self) -> None:
        """
        Reject visibility levels the driver does not support.

        Validates the failure contract of setVisibility().
        """
        file = await self._disk.put("f.txt", b"abc")
        with self.assertRaises(UnsupportedStorageOperationException):
            await file.setVisibility("secret")

    async def testHashMatchesTheHashlibDigest(self) -> None:
        """
        Compute the content digest with the requested algorithm.

        Validates the default and an explicit algorithm.
        """
        file = await self._disk.put("f.txt", b"abc")
        self.assertEqual(await file.hash(), hashlib.sha256(b"abc").hexdigest())
        self.assertEqual(
            await file.hash("sha1"), hashlib.sha1(b"abc").hexdigest(),
        )

    async def testHashRejectsUnknownAlgorithms(self) -> None:
        """
        Reject digest algorithms unavailable in the runtime.

        Validates the failure contract of hash().
        """
        file = await self._disk.put("f.txt", b"abc")
        with self.assertRaises(UnsupportedStorageOperationException):
            await file.hash("not-an-algorithm")

    async def testDownloadCopiesTheFileLocally(self) -> None:
        """
        Copy the stored contents onto the local filesystem.

        Validates the delegation of download().
        """
        file = await self._disk.put("docs/report.pdf", b"pdf")
        with tempfile.TemporaryDirectory() as tmp:
            target = await file.download(Path(tmp))
            self.assertEqual(target.name, "report.pdf")
            self.assertEqual(target.read_bytes(), b"pdf")

    async def testInfoReturnsAMetadataSnapshot(self) -> None:
        """
        Collect the metadata snapshot produced by the driver.

        Validates the delegation of info() and its payload.
        """
        file = await self._disk.put("docs/f.txt", b"abc")
        info = await file.info()
        self.assertIsInstance(info, FileInfo)
        self.assertEqual(info.path, "docs/f.txt")
        self.assertEqual(info.size, 3)
        self.assertEqual(info.mimeType, "text/plain")
        self.assertEqual(info.url, "https://cdn.test/docs/f.txt")
        self.assertEqual(info.checksum, hashlib.sha256(b"abc").hexdigest())

    async def testMetadataOfMissingFilesRaises(self) -> None:
        """
        Reject metadata requests targeting a missing file.

        Validates the shared failure contract of the metadata API.
        """
        missing = self._disk.file("missing.txt")
        with self.assertRaises(StorageFileNotFoundException):
            await missing.size()
        with self.assertRaises(StorageFileNotFoundException):
            await missing.lastModified()
        with self.assertRaises(StorageFileNotFoundException):
            await missing.info()
