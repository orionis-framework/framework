from orionis.auth import exceptions
from orionis.auth.exceptions import (
    AuthConfigurationException,
    AuthenticationException,
    AuthException,
    AuthorizationException,
    GuardNotFoundException,
    IdentityProviderException,
    PolicyNotFoundException,
    TokenException,
)
from orionis.failure.base.handler import _HTTP_STATUS_MAP
from orionis.http.enums.status import HTTPStatus
from orionis.test import TestCase

# Every concrete failure the module declares, excluding the shared base.
_SPECIALISED = (
    AuthConfigurationException,
    AuthenticationException,
    AuthorizationException,
    GuardNotFoundException,
    IdentityProviderException,
    PolicyNotFoundException,
    TokenException,
)


class TestExceptionHierarchy(TestCase):
    """Validate the exception hierarchy exposed by the module."""

    def testTheBaseIsAPlainException(self) -> None:
        """Inspect the ancestry of the module base class.

        Validates that a caller may still fall back to a generic
        ``except Exception`` handler.
        """
        self.assertTrue(issubclass(AuthException, Exception))

    def testEverySpecialisedFailureSharesTheModuleBase(self) -> None:
        """Walk the specialised failures looking for the shared base.

        Validates that a single ``except AuthException`` covers every
        failure the module can raise.
        """
        for exception in _SPECIALISED:
            self.assertTrue(issubclass(exception, AuthException), exception)

    def testEachFailureKeepsItsOwnType(self) -> None:
        """Compare the specialised failures against each other.

        Validates that callers can tell one failure from another without
        parsing messages.
        """
        self.assertEqual(len(set(_SPECIALISED)), len(_SPECIALISED))
        for exception in _SPECIALISED:
            others = [other for other in _SPECIALISED if other is not exception]
            for other in others:
                self.assertFalse(issubclass(exception, other), exception)

    def testAuthorizationIsNeverConfusedWithAuthentication(self) -> None:
        """Compare the two failures the HTTP layer maps to a status.

        Validates that "not logged in" and "not allowed" stay two
        independent branches of the hierarchy.
        """
        self.assertFalse(
            issubclass(AuthorizationException, AuthenticationException),
        )
        self.assertFalse(
            issubclass(AuthenticationException, AuthorizationException),
        )


class TestExceptionModuleSurface(TestCase):
    """Validate what the exception module publishes."""

    def testTheModuleOnlyPublishesItsOwnFailures(self) -> None:
        """Compare the public attributes of the module with the expected set.

        Validates that no helper or leaked import becomes part of the
        published surface.
        """
        published = {
            name for name in vars(exceptions) if not name.startswith("_")
        }
        expected = {AuthException.__name__} | {
            exception.__name__ for exception in _SPECIALISED
        }
        self.assertEqual(published, expected)

    def testEveryFailureDocumentsWhenItIsRaised(self) -> None:
        """Read the docstring declared by each failure.

        Validates that the module stays self describing, which matters
        because the classes carry no behaviour of their own.
        """
        for exception in (AuthException, *_SPECIALISED):
            docstring = exception.__doc__ or ""
            self.assertTrue(docstring.strip(), exception.__name__)


class TestExceptionBehaviour(TestCase):
    """Validate how the failures behave once raised."""

    def testEachFailureCarriesItsMessage(self) -> None:
        """Raise every failure with a message and read it back.

        Validates that the classes add no formatting of their own to the
        message the framework assigns.
        """
        for exception in (AuthException, *_SPECIALISED):
            error_msg = f"Failure raised by {exception.__name__}."
            with self.assertRaises(exception) as captured:
                raise exception(error_msg)
            self.assertEqual(str(captured.exception), error_msg)

    def testEachFailurePreservesItsCause(self) -> None:
        """Re-raise every failure from an underlying error.

        Validates that chaining keeps the original traceback reachable
        for the exception renderer.
        """
        for exception in (AuthException, *_SPECIALISED):
            cause = ValueError("underlying failure")
            error_msg = "Wrapped failure."
            with self.assertRaises(exception) as captured:
                try:
                    raise cause
                except ValueError as error:
                    raise exception(error_msg) from error
            self.assertIs(captured.exception.__cause__, cause)

    def testTheBaseCatchesEverySpecialisedFailure(self) -> None:
        """Catch each specialised failure through the shared base.

        Validates the single ``except`` clause application code relies on.
        """
        for exception in _SPECIALISED:
            error_msg = "Caught through the module base."
            with self.assertRaises(AuthException) as captured:
                raise exception(error_msg)
            self.assertIsInstance(captured.exception, exception)


class TestHttpStatusMapping(TestCase):
    """Validate how the failures become HTTP responses."""

    def testUnauthenticatedRequestsMapToFourZeroOne(self) -> None:
        """Read the status registered for a missing identity.

        Validates that ``401`` keeps meaning "no valid authenticated
        identity".
        """
        status, _ = _HTTP_STATUS_MAP[AuthenticationException]
        self.assertEqual(status, HTTPStatus.UNAUTHORIZED)

    def testForbiddenRequestsMapToFourZeroThree(self) -> None:
        """Read the status registered for a missing authorization.

        Validates that ``403`` keeps meaning "authenticated but not
        allowed".
        """
        status, _ = _HTTP_STATUS_MAP[AuthorizationException]
        self.assertEqual(status, HTTPStatus.FORBIDDEN)

    def testBothFailuresStayDistinguishable(self) -> None:
        """Compare the two registered mappings.

        Validates that collapsing them would never hide why a request was
        rejected.
        """
        self.assertNotEqual(
            _HTTP_STATUS_MAP[AuthenticationException],
            _HTTP_STATUS_MAP[AuthorizationException],
        )
