import io
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

def ancestors_without_slots(klass: type) -> list[str]:
    """
    Return the ancestors of *klass* that would reintroduce ``__dict__``.

    Parameters
    ----------
    klass : type
        Class whose method resolution order is inspected.

    Returns
    -------
    list[str]
        Names of the ancestors not declaring ``__slots__``, excluding
        ``object``, which never adds an attribute dictionary.
    """
    return [
        base.__name__
        for base in klass.__mro__
        if base is not object and "__slots__" not in vars(base)
    ]

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

class TestStorageSlots(TestCase):

    def testContractsDeclareEmptySlots(self) -> None:
        """
        Declare an empty ``__slots__`` on every storage contract.

        Validates that the ABCs never reintroduce ``__dict__`` in the
        concrete classes implementing them.
        """
        for contract in _CONTRACTS:
            self.assertEqual(contract.__slots__, (), contract.__name__)

    def testWholeHierarchyDeclaresSlots(self) -> None:
        """
        Declare ``__slots__`` at every level of each class hierarchy.

        Validates the invariant for classes that cannot be built
        without external resources, such as the cloud drivers.
        """
        for klass in _SLOTTED_CLASSES:
            self.assertEqual(
                ancestors_without_slots(klass), [], klass.__name__,
            )

    def testInstancesCarryNoAttributeDictionary(self) -> None:
        """
        Build domain objects without an instance dictionary.

        Validates the memory footprint claimed by ``__slots__`` on the
        objects created on every listing or file operation.
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
                hasattr(instance, "__dict__"), type(instance).__name__,
            )
