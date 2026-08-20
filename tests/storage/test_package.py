from orionis import storage
from orionis.storage.directory import Directory
from orionis.storage.disk import Disk
from orionis.storage.drivers.azure import AzureStorageDriver
from orionis.storage.drivers.gcs import GoogleStorageDriver
from orionis.storage.drivers.local import LocalStorageDriver
from orionis.storage.drivers.memory import MemoryStorageDriver
from orionis.storage.drivers.s3 import S3StorageDriver
from orionis.storage.entities.file_info import FileInfo
from orionis.storage.enums.visibility import Visibility
from orionis.storage.file import File
from orionis.storage.manager import StorageManager
from orionis.storage.stream import AsyncStream
from orionis.storage.uploaded_file import UploadedFile
from orionis.test import TestCase

# Public surface published by the storage package.
_EXPECTED_EXPORTS: dict[str, type] = {
    "AsyncStream": AsyncStream,
    "AzureStorageDriver": AzureStorageDriver,
    "Directory": Directory,
    "Disk": Disk,
    "File": File,
    "FileInfo": FileInfo,
    "GoogleStorageDriver": GoogleStorageDriver,
    "LocalStorageDriver": LocalStorageDriver,
    "MemoryStorageDriver": MemoryStorageDriver,
    "S3StorageDriver": S3StorageDriver,
    "StorageManager": StorageManager,
    "UploadedFile": UploadedFile,
    "Visibility": Visibility,
}

class TestStoragePackage(TestCase):

    def testAllDeclaresTheFullPublicSurface(self) -> None:
        """
        Declare every public symbol of the package in __all__.

        Validates that the export list never drifts from the code.
        """
        self.assertEqual(
            sorted(storage.__all__), sorted(_EXPECTED_EXPORTS),
        )

    def testAllIsAlphabeticallySorted(self) -> None:
        """
        Keep the export list alphabetically sorted.

        Validates the convention followed by the framework packages.
        """
        self.assertEqual(list(storage.__all__), sorted(storage.__all__))

    def testAllNamesAreUnique(self) -> None:
        """
        List every exported name exactly once.

        Validates that __all__ contains no duplicated entry.
        """
        self.assertEqual(len(set(storage.__all__)), len(storage.__all__))

    def testExportedSymbolsResolveToTheirImplementation(self) -> None:
        """
        Re-export the very objects defined by the submodules.

        Validates that shortcuts never shadow the real classes.
        """
        for name, expected in _EXPECTED_EXPORTS.items():
            self.assertIs(getattr(storage, name), expected)
