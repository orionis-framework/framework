from orionis.storage.exceptions import (
    DiskNotFoundException,
    DriverNotSupportedException,
    MissingStorageDependencyException,
    StorageException,
    StorageFileNotFoundException,
    StoragePathException,
    UnsupportedStorageOperationException,
)
from orionis.test import TestCase

# Every concrete exception published by the storage component.
_STORAGE_EXCEPTIONS: tuple[type[StorageException], ...] = (
    DiskNotFoundException,
    DriverNotSupportedException,
    MissingStorageDependencyException,
    StorageFileNotFoundException,
    StoragePathException,
    UnsupportedStorageOperationException,
)

class TestStorageExceptions(TestCase):

    def __raiseChained(self) -> None:
        """
        Raise a storage error caused by a lower-level failure.

        Returns
        -------
        None

        Raises
        ------
        StorageFileNotFoundException
            Always, chained to the originating ``OSError``.
        """
        origin_msg = "backend failure"
        error_msg = "File does not exist at path [a.txt]."
        try:
            raise OSError(origin_msg)
        except OSError as exc:
            raise StorageFileNotFoundException(error_msg) from exc

    def testBaseExceptionDerivesFromException(self) -> None:
        """
        Derive the storage base error from the built-in Exception.

        Validates that storage errors participate in standard
        exception handling.
        """
        self.assertTrue(issubclass(StorageException, Exception))

    def testEveryErrorDerivesFromTheStorageBase(self) -> None:
        """
        Derive every concrete error from the storage base class.

        Validates that a single except clause can catch them all.
        """
        for exception in _STORAGE_EXCEPTIONS:
            self.assertTrue(issubclass(exception, StorageException))

    def testConcreteErrorsAreDistinctTypes(self) -> None:
        """
        Keep every concrete error as its own distinct type.

        Validates that callers can discriminate failure causes.
        """
        self.assertEqual(len(set(_STORAGE_EXCEPTIONS)), len(_STORAGE_EXCEPTIONS))

    def testMessageIsPreserved(self) -> None:
        """
        Preserve the message supplied at construction time.

        Validates the string representation of storage errors.
        """
        error_msg = "Disk [dropbox] is not defined."
        self.assertEqual(str(DiskNotFoundException(error_msg)), error_msg)

    def testBaseClauseCatchesConcreteErrors(self) -> None:
        """
        Catch a concrete error through the storage base class.

        Validates the practical benefit of the shared hierarchy.
        """
        error_msg = "Driver [dropbox] has no implementation."
        with self.assertRaises(StorageException):
            raise DriverNotSupportedException(error_msg)

    def testChainingPreservesTheOriginalCause(self) -> None:
        """
        Preserve the originating error when re-raising.

        Validates that tracebacks keep the low-level failure.
        """
        with self.assertRaises(StorageFileNotFoundException) as ctx:
            self.__raiseChained()
        self.assertIsInstance(ctx.exception.__cause__, OSError)
