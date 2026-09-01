from orionis.hashing.exceptions import (
    HashConfigurationException,
    HashDriverNotSupportedException,
    HashException,
    MissingHashDependencyException,
)
from orionis.test import TestCase

# Every specialised failure published by the module.
_SPECIALISED_EXCEPTIONS: tuple[type[HashException], ...] = (
    HashConfigurationException,
    HashDriverNotSupportedException,
    MissingHashDependencyException,
)


class TestHashExceptionHierarchy(TestCase):

    def testBaseExceptionDerivesFromException(self) -> None:
        """
        Derive the module base failure from the builtin Exception.

        Validates that callers may catch it without reaching for
        BaseException.
        """
        self.assertTrue(issubclass(HashException, Exception))

    def testEverySpecialisedFailureDerivesFromTheBase(self) -> None:
        """
        Group every specialised failure under the module base class.

        Validates that a single ``except HashException`` covers all the
        errors the hashing module can raise.
        """
        for exception in _SPECIALISED_EXCEPTIONS:
            self.assertTrue(issubclass(exception, HashException))

    def testSpecialisedFailuresAreDistinctTypes(self) -> None:
        """
        Keep the specialised failures independent from each other.

        Validates that catching one of them never swallows another.
        """
        self.assertEqual(len(set(_SPECIALISED_EXCEPTIONS)), 3)

    def testCatchingTheBaseCatchesEverySpecialisedFailure(self) -> None:
        """
        Catch any specialised failure through the base class.

        Validates the behaviour application code relies on when it guards
        a hashing operation.
        """
        error_msg = "failure"
        for exception in _SPECIALISED_EXCEPTIONS:
            with self.assertRaises(HashException):
                raise exception(error_msg)


class TestHashExceptionInstances(TestCase):

    def testCarriesTheProvidedMessage(self) -> None:
        """
        Report the message handed to the constructor.

        Validates that the error text reaches the caller untouched.
        """
        error_msg = "invalid cost factor"
        self.assertEqual(str(HashConfigurationException(error_msg)), error_msg)

    def testPreservesTheOriginalCause(self) -> None:
        """
        Preserve the exception that triggered the failure.

        Validates that chaining with ``raise ... from`` keeps the original
        traceback reachable for diagnostics.
        """
        original = ImportError("pwdlib is missing")
        error_msg = "missing backend"
        try:
            raise MissingHashDependencyException(error_msg) from original
        except MissingHashDependencyException as exc:
            self.assertIs(exc.__cause__, original)
