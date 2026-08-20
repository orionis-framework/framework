from __future__ import annotations
from orionis.session.exceptions import SessionException, SessionStorageException
from orionis.test import TestCase

class TestSessionException(TestCase):
    """Unit tests for the base SessionException."""

    def testIsBuiltinException(self) -> None:
        """
        Confirm SessionException inherits from the built-in Exception.

        Validates that session errors can be caught using the generic
        Exception handler.
        """
        self.assertIsInstance(SessionException("base error"), Exception)

    def testPreservesMessage(self) -> None:
        """
        Preserve the error message string in the exception args.

        Validates that the message supplied to the constructor is
        accessible through the standard string representation.
        """
        message = "something went wrong"
        self.assertIn(message, str(SessionException(message)))

    def testCanBeRaised(self) -> None:
        """
        Raise and catch SessionException correctly.

        Validates that the exception integrates with the standard Python
        exception-handling machinery.
        """
        error_msg = "test raise"
        with self.assertRaises(SessionException):
            raise SessionException(error_msg)

class TestSessionStorageException(TestCase):
    """Unit tests for the storage-specific session exception."""

    def testIsSessionException(self) -> None:
        """
        Confirm SessionStorageException inherits from SessionException.

        Validates that storage-specific errors are catchable through the
        base session handler.
        """
        exc = SessionStorageException("store error")
        self.assertIsInstance(exc, SessionException)

    def testIsBuiltinException(self) -> None:
        """
        Confirm SessionStorageException also inherits from Exception.

        Validates the full inheritance chain so callers can catch any
        session error with a single broad handler.
        """
        self.assertIsInstance(SessionStorageException("store error"), Exception)

    def testPreservesMessage(self) -> None:
        """
        Preserve the error message in SessionStorageException.

        Validates that the message supplied at construction survives in
        the standard string representation.
        """
        message = "disk write failed"
        self.assertIn(message, str(SessionStorageException(message)))

    def testCaughtAsSessionException(self) -> None:
        """
        Catch SessionStorageException via the SessionException handler.

        Validates the polymorphic catch behaviour expected from the
        exception hierarchy.
        """
        error_msg = "hierarchy test"
        with self.assertRaises(SessionException):
            raise SessionStorageException(error_msg)
