from orionis.storage.contracts.directory import IDirectory
from orionis.storage.contracts.file import IFile
from orionis.storage.directory import Directory
from orionis.storage.disk import Disk
from orionis.storage.drivers.memory import MemoryStorageDriver
from orionis.storage.exceptions import StoragePathException
from orionis.test import TestCase

class TestDirectoryPath(TestCase):

    def setUp(self) -> None:
        """
        Build a fresh memory driver before each test.

        Keeps every test isolated in its own in-memory store.
        """
        self._driver = MemoryStorageDriver()

    def testImplementsTheDirectoryContract(self) -> None:
        """
        Expose the directory through its published contract.

        Validates that disks can type their return values.
        """
        self.assertIsInstance(Directory(self._driver), IDirectory)

    def testPathDefaultsToTheDiskRoot(self) -> None:
        """
        Default the directory path to the disk root.

        Validates the empty-string representation of the root.
        """
        self.assertEqual(Directory(self._driver).path(), "")

    def testPathIsNormalizedOnIngestion(self) -> None:
        """
        Normalize the path supplied at construction time.

        Validates that separators and redundant segments collapse.
        """
        directory = Directory(self._driver, "\\photos//2026/../2025/")
        self.assertEqual(directory.path(), "photos/2025")

    def testEscapingPathIsRejected(self) -> None:
        """
        Reject paths escaping the disk root.

        Validates the traversal guard applied on ingestion.
        """
        with self.assertRaises(StoragePathException):
            Directory(self._driver, "../outside")

class TestDirectoryLifecycle(TestCase):

    def setUp(self) -> None:
        """
        Build a disk over a fresh memory driver before each test.

        Keeps every test isolated in its own in-memory store.
        """
        self._disk = Disk(name="fake", driver=MemoryStorageDriver())

    async def testCreateIsFluent(self) -> None:
        """
        Create the directory and return the same object.

        Validates fluent chaining on create().
        """
        directory = self._disk.directory("uploads")
        self.assertIs(await directory.create(), directory)

    async def testLifecycleCreateExistsDelete(self) -> None:
        """
        Create, detect, and delete a directory.

        Validates the directory lifecycle end to end.
        """
        directory = self._disk.directory("uploads")
        self.assertFalse(await directory.exists())
        await directory.create()
        self.assertTrue(await directory.exists())
        self.assertTrue(await directory.delete())
        self.assertFalse(await directory.exists())

    async def testDeleteReportsWhetherTheDirectoryExisted(self) -> None:
        """
        Report whether the deleted directory was present.

        Validates the boolean contract of delete().
        """
        self.assertFalse(await self._disk.directory("ghost").delete())

    async def testDeleteRemovesNestedContents(self) -> None:
        """
        Remove the whole subtree of the directory.

        Validates the recursive nature of delete().
        """
        await self._disk.put("root/a/deep/f.txt", b"x")
        self.assertTrue(await self._disk.directory("root").delete())
        self.assertFalse(await self._disk.exists("root/a/deep/f.txt"))

    async def testRootDirectoryAlwaysExists(self) -> None:
        """
        Report the disk root as always present.

        Validates the special case of the empty path.
        """
        self.assertTrue(await self._disk.directory().exists())

class TestDirectoryListing(TestCase):

    def setUp(self) -> None:
        """
        Build a disk over a fresh memory driver before each test.

        Keeps every test isolated in its own in-memory store.
        """
        self._disk = Disk(name="fake", driver=MemoryStorageDriver())

    async def testFilesListsDirectChildrenOnly(self) -> None:
        """
        List the files directly contained in the directory.

        Validates that nested files are excluded from files().
        """
        await self._disk.put("photos/a.png", b"1")
        await self._disk.put("photos/nested/b.png", b"2")

        listing = await self._disk.directory("photos").files()
        self.assertIsInstance(listing[0], IFile)
        self.assertEqual([file.path() for file in listing], ["photos/a.png"])

    async def testAllFilesWalksTheWholeSubtree(self) -> None:
        """
        List every file contained in the directory tree.

        Validates the recursive listing and its ordering.
        """
        await self._disk.put("photos/a.png", b"1")
        await self._disk.put("photos/nested/b.png", b"2")

        listing = await self._disk.directory("photos").allFiles()
        self.assertEqual(
            [file.path() for file in listing],
            ["photos/a.png", "photos/nested/b.png"],
        )

    async def testDirectoriesListsDirectChildrenOnly(self) -> None:
        """
        List the directories directly contained in the directory.

        Validates that nested directories are excluded.
        """
        await self._disk.put("root/a/deep/f.txt", b"x")

        listing = await self._disk.directory("root").directories()
        self.assertIsInstance(listing[0], IDirectory)
        self.assertEqual(
            [directory.path() for directory in listing], ["root/a"],
        )

    async def testAllDirectoriesWalksTheWholeSubtree(self) -> None:
        """
        List every directory contained in the directory tree.

        Validates the recursive listing and its ordering.
        """
        await self._disk.put("root/a/deep/f.txt", b"x")

        listing = await self._disk.directory("root").allDirectories()
        self.assertEqual(
            [directory.path() for directory in listing],
            ["root/a", "root/a/deep"],
        )

    async def testListingsAreEmptyForUntouchedDirectories(self) -> None:
        """
        Return empty listings for directories without contents.

        Validates the empty-collection contract of the listing API.
        """
        directory = await self._disk.directory("empty").create()
        self.assertEqual(await directory.files(), [])
        self.assertEqual(await directory.allFiles(), [])
        self.assertEqual(await directory.directories(), [])
        self.assertEqual(await directory.allDirectories(), [])
