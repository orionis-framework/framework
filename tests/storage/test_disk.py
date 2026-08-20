from orionis.storage.contracts.directory import IDirectory
from orionis.storage.contracts.disk import IDisk
from orionis.storage.contracts.file import IFile
from orionis.storage.directory import Directory
from orionis.storage.disk import Disk
from orionis.storage.drivers.memory import MemoryStorageDriver
from orionis.storage.enums.visibility import Visibility
from orionis.storage.exceptions import (
    StorageFileNotFoundException,
    StoragePathException,
)
from orionis.storage.file import File
from orionis.test import TestCase

class TestDisk(TestCase):

    def setUp(self) -> None:
        """
        Build a disk over a fresh memory driver before each test.

        Keeps every test isolated in its own in-memory store.
        """
        self._driver = MemoryStorageDriver()
        self._disk = Disk(name="fake", driver=self._driver)

    def testImplementsTheDiskContract(self) -> None:
        """
        Expose the disk through its published contract.

        Validates that the manager can type its return values.
        """
        self.assertIsInstance(self._disk, IDisk)

    def testNameReturnsTheConfiguredName(self) -> None:
        """
        Return the configuration name assigned to the disk.

        Validates the accessor used to identify resolved disks.
        """
        self.assertEqual(self._disk.name(), "fake")

    def testFileFactoryBindsTheDiskDriver(self) -> None:
        """
        Build File objects bound to the driver of the disk.

        Validates the factory and its path normalization.
        """
        file = self._disk.file("avatars//user.png")
        self.assertIsInstance(file, File)
        self.assertEqual(file.path(), "avatars/user.png")
        self.assertIs(file._driver, self._driver)

    def testFileFactoryRejectsTheDiskRoot(self) -> None:
        """
        Reject file paths resolving to the disk root.

        Validates the failure contract of file().
        """
        with self.assertRaises(StoragePathException):
            self._disk.file("")

    def testDirectoryFactoryBindsTheDiskDriver(self) -> None:
        """
        Build Directory objects bound to the driver of the disk.

        Validates the factory and its path normalization.
        """
        directory = self._disk.directory("photos//2026")
        self.assertIsInstance(directory, Directory)
        self.assertEqual(directory.path(), "photos/2026")
        self.assertIs(directory._driver, self._driver)

    def testDirectoryFactoryDefaultsToTheDiskRoot(self) -> None:
        """
        Default the directory factory to the disk root.

        Validates the empty-string representation of the root.
        """
        self.assertEqual(self._disk.directory().path(), "")

    def testDirectoryFactoryRejectsEscapingPaths(self) -> None:
        """
        Reject directory paths escaping the disk root.

        Validates the failure contract of directory().
        """
        with self.assertRaises(StoragePathException):
            self._disk.directory("../outside")

    async def testPutWritesContentsAndReturnsAFile(self) -> None:
        """
        Persist contents and return the resulting file object.

        Validates the delegation of put() to File.write().
        """
        stored = await self._disk.put("docs/a.txt", b"data")
        self.assertIsInstance(stored, IFile)
        self.assertEqual(stored.path(), "docs/a.txt")
        self.assertEqual(await stored.read(), b"data")

    async def testPutForwardsTheRequestedVisibility(self) -> None:
        """
        Apply the visibility requested when writing contents.

        Validates that the optional argument reaches the driver.
        """
        stored = await self._disk.put(
            "a.txt", "text", Visibility.PUBLIC.value,
        )
        self.assertEqual(await stored.visibility(), Visibility.PUBLIC.value)

    async def testExistsReflectsTheStoredState(self) -> None:
        """
        Report whether a file exists on the disk.

        Validates the delegation of exists() to File.
        """
        self.assertFalse(await self._disk.exists("a.txt"))
        await self._disk.put("a.txt", b"data")
        self.assertTrue(await self._disk.exists("a.txt"))

    async def testDeleteReportsWhetherTheFileExisted(self) -> None:
        """
        Remove a file and report whether it was present.

        Validates the delegation of delete() to File.
        """
        await self._disk.put("a.txt", b"data")
        self.assertTrue(await self._disk.delete("a.txt"))
        self.assertFalse(await self._disk.delete("a.txt"))

    async def testCopyDuplicatesTheSourceFile(self) -> None:
        """
        Copy a file and keep the source in place.

        Validates the delegation of copy() to File.copyTo().
        """
        await self._disk.put("a.txt", b"data")
        copied = await self._disk.copy("a.txt", "b.txt")
        self.assertEqual(copied.path(), "b.txt")
        self.assertEqual(await copied.read(), b"data")
        self.assertTrue(await self._disk.exists("a.txt"))

    async def testCopyMissingSourceRaises(self) -> None:
        """
        Reject copies whose source file does not exist.

        Validates the failure contract of copy().
        """
        with self.assertRaises(StorageFileNotFoundException):
            await self._disk.copy("missing.txt", "b.txt")

    async def testMoveRelocatesTheSourceFile(self) -> None:
        """
        Move a file and drop the original location.

        Validates the delegation of move() to File.moveTo().
        """
        await self._disk.put("a.txt", b"data")
        moved = await self._disk.move("a.txt", "sub/b.txt")
        self.assertEqual(moved.path(), "sub/b.txt")
        self.assertEqual(await moved.read(), b"data")
        self.assertFalse(await self._disk.exists("a.txt"))

    async def testMoveMissingSourceRaises(self) -> None:
        """
        Reject moves whose source file does not exist.

        Validates the failure contract of move().
        """
        with self.assertRaises(StorageFileNotFoundException):
            await self._disk.move("missing.txt", "b.txt")

    async def testDirectoryObjectsSeeFilesWrittenThroughTheDisk(self) -> None:
        """
        Share the same medium between disk and directory objects.

        Validates that both factories are bound to one driver.
        """
        await self._disk.put("photos/a.png", b"1")
        listing = await self._disk.directory("photos").files()
        self.assertIsInstance(listing[0], IFile)
        self.assertEqual([file.path() for file in listing], ["photos/a.png"])

    async def testDirectoryFactoryProducesTheDirectoryContract(self) -> None:
        """
        Expose built directories through their published contract.

        Validates the type advertised by directory().
        """
        directory = self._disk.directory("photos")
        self.assertIsInstance(directory, IDirectory)
        self.assertIs(await directory.create(), directory)
