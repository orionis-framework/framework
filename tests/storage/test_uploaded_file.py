from typing import TYPE_CHECKING
from orionis.storage.contracts.uploaded_file import IUploadedFile
from orionis.storage.disk import Disk
from orionis.storage.drivers.memory import MemoryStorageDriver
from orionis.storage.enums.visibility import Visibility
from orionis.storage.exceptions import StoragePathException
from orionis.storage.uploaded_file import UploadedFile
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import Iterator

class _FakeUpload:
    """Duck-typed multipart payload produced by the HTTP layer."""

    __slots__ = ("closed", "content_type", "extension", "filename", "payload")

    def __init__(self, filename: str, data: bytes) -> None:
        self.filename = filename
        self.content_type = "image/png"
        self.closed = False
        self.payload = data
        dot = filename.rfind(".")
        self.extension = filename[dot:].lower() if dot > 0 else ""

    @property
    def size(self) -> int:
        """
        Return the payload size in bytes.

        Returns
        -------
        int
            Byte count of the buffered data.
        """
        return len(self.payload)

    def read(self) -> bytes:
        """
        Return the full buffered payload.

        Returns
        -------
        bytes
            Buffered content.
        """
        return self.payload

    def chunks(self, size: int = 4) -> Iterator[bytes]:
        """
        Yield the payload in fixed-size chunks.

        Parameters
        ----------
        size : int
            Maximum number of bytes per yielded chunk.

        Yields
        ------
        bytes
            The next chunk of the buffered payload.
        """
        for start in range(0, len(self.payload), size):
            yield self.payload[start:start + size]

    def close(self) -> None:
        """Mark the buffered payload as released."""
        self.closed = True

class _RecordingManager:
    """Manager double handing out a single disk and recording lookups."""

    __slots__ = ("disk_names", "target")

    def __init__(self, target: Disk) -> None:
        self.target = target
        self.disk_names: list[str | None] = []

    def disk(self, name: str | None = None) -> Disk:
        """
        Return the stubbed disk and record the requested name.

        Parameters
        ----------
        name : str | None
            Disk name requested by the uploaded file.

        Returns
        -------
        Disk
            The disk supplied at construction time.
        """
        self.disk_names.append(name)
        return self.target

class TestUploadedFileMetadata(TestCase):

    def setUp(self) -> None:
        """
        Build an uploaded file over a memory-backed disk.

        Provides a fake payload and a recording manager so tests run
        without a booted application.
        """
        self._disk = Disk(name="fake", driver=MemoryStorageDriver())
        self._source = _FakeUpload("Profile Photo.png", b"png-payload")
        self._manager = _RecordingManager(self._disk)
        self._upload = UploadedFile(
            source=self._source,  # type: ignore[arg-type]
            manager=self._manager,  # type: ignore[arg-type]
        )

    def testImplementsTheUploadedFileContract(self) -> None:
        """
        Expose the upload through its published contract.

        Validates that the manager can type its return values.
        """
        self.assertIsInstance(self._upload, IUploadedFile)

    def testExposesTheClientSuppliedMetadata(self) -> None:
        """
        Expose the payload metadata through camelCase accessors.

        Validates originalName, extension, size, and mimeType.
        """
        self.assertEqual(self._upload.originalName(), "Profile Photo.png")
        self.assertEqual(self._upload.extension(), ".png")
        self.assertEqual(self._upload.size(), len(b"png-payload"))
        self.assertEqual(self._upload.mimeType(), "image/png")

    def testHashNameKeepsTheOriginalExtension(self) -> None:
        """
        Append the original extension to the generated name.

        Validates the format of hashName().
        """
        self.assertTrue(self._upload.hashName().endswith(".png"))

    def testHashNameIsGeneratedOnlyOnce(self) -> None:
        """
        Cache the generated name for the lifetime of the object.

        Validates the memoization of hashName().
        """
        self.assertEqual(self._upload.hashName(), self._upload.hashName())

    def testHashNameHandlesExtensionlessUploads(self) -> None:
        """
        Generate a bare name when the upload has no extension.

        Validates the empty-extension branch of hashName().
        """
        upload = UploadedFile(
            source=_FakeUpload("archive", b"data"),  # type: ignore[arg-type]
            manager=self._manager,  # type: ignore[arg-type]
        )
        self.assertNotIn(".", upload.hashName())

    async def testReadReturnsTheFullPayload(self) -> None:
        """
        Return the complete buffered payload.

        Validates the delegation of read() to the source.
        """
        self.assertEqual(await self._upload.read(), b"png-payload")

class TestUploadedFilePersistence(TestCase):

    def setUp(self) -> None:
        """
        Build an uploaded file over a memory-backed disk.

        Provides a fake payload and a recording manager so tests run
        without a booted application.
        """
        self._disk = Disk(name="fake", driver=MemoryStorageDriver())
        self._source = _FakeUpload("photo.png", b"png-payload")
        self._manager = _RecordingManager(self._disk)
        self._upload = UploadedFile(
            source=self._source,  # type: ignore[arg-type]
            manager=self._manager,  # type: ignore[arg-type]
        )

    async def testStorePersistsUnderTheGeneratedName(self) -> None:
        """
        Persist the payload under the generated hash name.

        Validates the delegation of store() to storeAs().
        """
        stored = await self._upload.store("avatars")
        self.assertEqual(stored.path(), f"avatars/{self._upload.hashName()}")
        self.assertEqual(await stored.read(), b"png-payload")

    async def testStoreDefaultsToTheDiskRoot(self) -> None:
        """
        Persist at the disk root when no directory is supplied.

        Validates the default directory of store().
        """
        stored = await self._upload.store()
        self.assertEqual(stored.path(), self._upload.hashName())

    async def testStoreForwardsDiskAndVisibility(self) -> None:
        """
        Forward the disk name and visibility down the write path.

        Validates the optional arguments of store().
        """
        stored = await self._upload.store(
            "avatars", "public", Visibility.PUBLIC.value,
        )
        self.assertEqual(self._manager.disk_names, ["public"])
        self.assertEqual(await stored.visibility(), Visibility.PUBLIC.value)

    async def testStoreAsPersistsUnderAnExplicitName(self) -> None:
        """
        Persist the payload under the requested file name.

        Validates storeAs() and the streamed content.
        """
        stored = await self._upload.storeAs("avatars", "user.png")
        self.assertEqual(stored.path(), "avatars/user.png")
        self.assertEqual(await stored.read(), b"png-payload")

    async def testStoreAsWithoutDirectoryWritesAtTheRoot(self) -> None:
        """
        Persist at the disk root when the directory is empty.

        Validates the target-path composition of storeAs().
        """
        stored = await self._upload.storeAs("", "user.png")
        self.assertEqual(stored.path(), "user.png")

    async def testStoreAsRejectsEmptyNames(self) -> None:
        """
        Reject empty file names on explicit persistence.

        Validates the failure contract of storeAs().
        """
        with self.assertRaises(StoragePathException):
            await self._upload.storeAs("avatars", "")

    async def testStoreAsRejectsDirectorySeparators(self) -> None:
        """
        Reject file names carrying a directory separator.

        Validates that the name is always a single path segment.
        """
        with self.assertRaises(StoragePathException):
            await self._upload.storeAs("avatars", "../user.png")
        with self.assertRaises(StoragePathException):
            await self._upload.storeAs("avatars", "sub\\user.png")

    async def testMoveReleasesTheUploadBuffer(self) -> None:
        """
        Release the temporary buffer after persisting the payload.

        Validates the buffer lifecycle of move().
        """
        stored = await self._upload.move("avatars", "moved.png")
        self.assertEqual(stored.path(), "avatars/moved.png")
        self.assertTrue(self._source.closed)

    async def testMoveDefaultsToTheGeneratedName(self) -> None:
        """
        Fall back to the generated name when none is supplied.

        Validates the optional name argument of move().
        """
        stored = await self._upload.move("avatars")
        self.assertEqual(stored.path(), f"avatars/{self._upload.hashName()}")

    async def testCopyKeepsTheUploadBufferUsable(self) -> None:
        """
        Keep the temporary buffer open after persisting.

        Validates the lifecycle difference between copy() and move().
        """
        stored = await self._upload.copy("avatars", "kept.png")
        self.assertEqual(stored.path(), "avatars/kept.png")
        self.assertFalse(self._source.closed)

    async def testCopyDefaultsToTheGeneratedName(self) -> None:
        """
        Fall back to the generated name when none is supplied.

        Validates the optional name argument of copy().
        """
        stored = await self._upload.copy("avatars")
        self.assertEqual(stored.path(), f"avatars/{self._upload.hashName()}")

    async def testPayloadIsStreamedInChunks(self) -> None:
        """
        Persist multi-chunk payloads without loading them at once.

        Validates the internal chunked stream used on every write.
        """
        upload = UploadedFile(
            source=_FakeUpload("big.bin", b"0123456789"),  # type: ignore[arg-type]
            manager=self._manager,  # type: ignore[arg-type]
        )
        stored = await upload.storeAs("bulk", "big.bin")
        self.assertEqual(await stored.read(), b"0123456789")

    async def testEmptyPayloadIsPersisted(self) -> None:
        """
        Persist uploads whose buffer produces no chunk at all.

        Validates the immediate termination of the chunk loop.
        """
        upload = UploadedFile(
            source=_FakeUpload("empty.bin", b""),  # type: ignore[arg-type]
            manager=self._manager,  # type: ignore[arg-type]
        )
        stored = await upload.storeAs("bulk", "empty.bin")
        self.assertEqual(await stored.read(), b"")
