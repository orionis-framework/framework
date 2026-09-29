from __future__ import annotations
from orionis.database.exceptions import (
    ConnectionNotFoundException,
    DatabaseException,
    MigrationNotFoundException,
    MissingDatabaseDependencyException,
    QueryException,
    TransactionException,
    UnsupportedDriverException,
)
from orionis.test import TestCase

# Every specific exception exposed by the database module.
_SPECIFIC_EXCEPTIONS = (
    ConnectionNotFoundException,
    MigrationNotFoundException,
    MissingDatabaseDependencyException,
    QueryException,
    TransactionException,
    UnsupportedDriverException,
)

class TestDatabaseExceptions(TestCase):

    def testDatabaseExceptionExtendsException(self) -> None:
        """Extend the built-in Exception type.

        Validates the root of the database exception hierarchy.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(DatabaseException, Exception))

    def testEverySpecificExceptionExtendsDatabaseException(self) -> None:
        """Extend DatabaseException for every specific exception type.

        Validates that catching DatabaseException also catches any
        specific database error raised across the module.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for exception_type in _SPECIFIC_EXCEPTIONS:
            self.assertTrue(issubclass(exception_type, DatabaseException))

    def testEachSpecificExceptionPreservesItsMessage(self) -> None:
        """Preserve the constructor message for every specific exception.

        Validates that every subclass behaves like a plain exception
        with respect to message handling.

        Returns
        -------
        None
            Assertions verify the behavior described above.

        Raises
        ------
        exception_type
            Raised by this helper to exercise the failure path.
        """
        for exception_type in _SPECIFIC_EXCEPTIONS:
            error_msg = f"{exception_type.__name__} failure."
            with self.assertRaises(exception_type) as ctx:
                raise exception_type(error_msg)
            self.assertEqual(str(ctx.exception), error_msg)

    def testCatchingBaseExceptionCatchesAnySubtype(self) -> None:
        """Catch a specific error through the DatabaseException base.

        Validates the polymorphic catch-all use case relied upon by
        callers that do not care which specific error occurred.

        Returns
        -------
        None
            Assertions verify the behavior described above.

        Raises
        ------
        QueryException
            Raised by this helper to exercise the failure path.
        """
        error_msg = "Query failed."
        with self.assertRaises(DatabaseException):
            raise QueryException(error_msg)

    def testUnrelatedExceptionIsNotCaughtAsDatabaseException(self) -> None:
        """Leave unrelated exceptions outside the database hierarchy.

        Validates that the hierarchy does not overreach into plain
        Python exceptions such as ValueError.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(issubclass(ValueError, DatabaseException))

    def testExceptionSupportsChainedCause(self) -> None:
        """Preserve the original cause when re-raised with ``from``.

        Validates the exception chaining convention used across the
        database module (``raise X(msg) from exc``).

        Returns
        -------
        None
            Assertions verify the behavior described above.

        Raises
        ------
        cause
            Raised by this helper to exercise the failure path.
        QueryException
            Raised by this helper to exercise the failure path.
        """
        cause = ValueError("root cause")
        try:
            try:
                raise cause
            except ValueError as exc:
                error_msg = "wrapped failure"
                raise QueryException(error_msg) from exc
        except QueryException as wrapped:
            self.assertIs(wrapped.__cause__, cause)
