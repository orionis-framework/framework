# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import io
from datetime import datetime
from typing import get_type_hints
from orionis import storage
from orionis.storage.contracts.directory import IDirectory
from orionis.storage.contracts.disk import IDisk
from orionis.storage.contracts.driver import IStorageDriver
from orionis.storage.contracts.file import IFile
from orionis.storage.contracts.manager import IStorageManager
from orionis.storage.contracts.stream import IStorageStream
from orionis.storage.contracts.uploaded_file import IUploadedFile
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

# Abstract contracts implemented by the concrete classes.
_CONTRACTS: tuple[type, ...] = (
    IDirectory,
    IDisk,
    IFile,
    IStorageDriver,
    IStorageManager,
    IStorageStream,
    IUploadedFile,
)

# Classes whose instances must never carry an attribute dictionary.
_SLOTTED_CLASSES: tuple[type, ...] = (
    AsyncStream,
    AzureStorageDriver,
    Directory,
    Disk,
    File,
    FileInfo,
    GoogleStorageDriver,
    LocalStorageDriver,
    MemoryStorageDriver,
    S3StorageDriver,
    StorageManager,
    UploadedFile,
)


class TestStoragePackage(TestCase):
    def testMetadataAndDriverAnnotationsResolveAtRuntime(self) -> None:
        """Resolve file metadata and the public driver signatures at runtime."""
        with self.subTest(target="FileInfo"):
            self.assertIs(get_type_hints(FileInfo)["lastModified"], datetime)
        for name, method in vars(IStorageDriver).items():
            if name.startswith("_") or not callable(method):
                continue
            with self.subTest(target=name):
                self.assertIn("return", get_type_hints(method))

    def testAllDeclaresTheFullPublicSurface(self) -> None:
        """Declare every public symbol of the package in __all__.

        Validates that the export list never drifts from the code.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(
            list(storage.__all__),
            sorted(_EXPECTED_EXPORTS),
        )

    def testExportedSymbolsResolveToTheirImplementation(self) -> None:
        """Re-export the very objects defined by the submodules.

        Validates that shortcuts never shadow the real classes.

        Returns
        -------
        None
            No return value.
        """
        for name, expected in _EXPECTED_EXPORTS.items():
            self.assertIs(getattr(storage, name), expected)


class TestStorageSlots(TestCase):
    def testContractsDeclareEmptySlots(self) -> None:
        """Declare an empty ``__slots__`` on every storage contract.

        Validates that the ABCs never reintroduce ``__dict__`` in the
        concrete classes implementing them.

        Returns
        -------
        None
            No return value.
        """
        for contract in _CONTRACTS:
            self.assertEqual(contract.__slots__, (), contract.__name__)

    def testConcreteClassesExcludeInstanceDictionaries(self) -> None:
        """Exclude an instance dictionary from every concrete storage type.

        Inspect the resulting layout without constructing cloud clients or
        requiring each ancestor to repeat a particular slots declaration.
        """
        for klass in _SLOTTED_CLASSES:
            with self.subTest(klass=klass.__name__):
                self.assertEqual(klass.__dictoffset__, 0)

    def testInstancesCarryNoAttributeDictionary(self) -> None:
        """Build domain objects without an instance dictionary.

        Validates the memory footprint claimed by ``__slots__`` on the
        objects created on every listing or file operation.

        Returns
        -------
        None
            No return value.
        """
        driver = MemoryStorageDriver()
        instances = (
            driver,
            Disk(name="memory", driver=driver),
            File(driver, "a.txt"),
            Directory(driver, "a"),
            AsyncStream(io.BytesIO),
        )
        for instance in instances:
            self.assertFalse(
                hasattr(instance, "__dict__"),
                type(instance).__name__,
            )
