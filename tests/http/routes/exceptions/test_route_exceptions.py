from orionis.http.routes.exceptions.fallback_route_already_registered import (
    FallbackRouteAlreadyRegisteredException,
)
from orionis.http.routes.exceptions.method_not_allowed import MethodNotAllowed
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.test import TestCase

class TestRouteExceptions(TestCase):
    """Unit tests for HTTP route exception classes."""

    def testRouteNotFoundIsException(self) -> None:
        """Verify that RouteNotFound derives from Exception.

        Confirms the class hierarchy so it can be caught with a
        bare ``except Exception`` guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(RouteNotFound, Exception))

    def testRouteNotFoundCanBeRaised(self) -> None:
        """Verify that RouteNotFound can be raised and caught by type.

        Raises the exception with a message and confirms it is caught
        as the correct exception type.

        Returns
        -------
        None
            Assertions verify the behavior described above.

        Raises
        ------
        RouteNotFound
            Raised by this helper to exercise the failure path.
        """
        error_msg = "no route for /missing"
        with self.assertRaises(RouteNotFound):
            raise RouteNotFound(error_msg)

    def testRouteNotFoundMessage(self) -> None:
        """Verify that RouteNotFound preserves the exception message.

        Confirms that the string passed to the constructor is stored
        and accessible via str().

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        msg = "path /x not found"
        exc = RouteNotFound(msg)
        self.assertIn(msg, str(exc))

    def testMethodNotAllowedIsException(self) -> None:
        """Verify that MethodNotAllowed derives from Exception.

        Confirms the class hierarchy so it can be caught with a
        bare ``except Exception`` guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(MethodNotAllowed, Exception))

    def testMethodNotAllowedCanBeRaised(self) -> None:
        """Verify that MethodNotAllowed can be raised and caught by type.

        Raises the exception with a message and confirms it is caught
        as the correct exception type.

        Returns
        -------
        None
            Assertions verify the behavior described above.

        Raises
        ------
        MethodNotAllowed
            Raised by this helper to exercise the failure path.
        """
        error_msg = "DELETE not allowed on /users"
        with self.assertRaises(MethodNotAllowed):
            raise MethodNotAllowed(error_msg)

    def testMethodNotAllowedMessage(self) -> None:
        """Verify that MethodNotAllowed preserves the exception message.

        Confirms that the string passed to the constructor is stored
        and accessible via str().

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        msg = "method PUT not allowed"
        exc = MethodNotAllowed(msg)
        self.assertIn(msg, str(exc))

    def testFallbackAlreadyRegisteredIsException(self) -> None:
        """Verify that FallbackRouteAlreadyRegisteredException is an Exception.

        Confirms the class hierarchy so it can be caught with a
        bare ``except Exception`` guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(
            issubclass(FallbackRouteAlreadyRegisteredException, Exception),
        )

    def testFallbackAlreadyRegisteredCanBeRaised(self) -> None:
        """Verify FallbackRouteAlreadyRegisteredException can be raised.

        Raises the exception and confirms it is caught as the correct
        exception type.

        Returns
        -------
        None
            Assertions verify the behavior described above.

        Raises
        ------
        FallbackRouteAlreadyRegisteredException
            Raised by this helper to exercise the failure path.
        """
        error_msg = "fallback already set"
        with self.assertRaises(FallbackRouteAlreadyRegisteredException):
            raise FallbackRouteAlreadyRegisteredException(error_msg)

    def testFallbackAlreadyRegisteredMessage(self) -> None:
        """Verify FallbackRouteAlreadyRegisteredException preserves the message.

        Confirms that the string passed to the constructor is accessible
        via str().

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        msg = "only one fallback allowed"
        exc = FallbackRouteAlreadyRegisteredException(msg)
        self.assertIn(msg, str(exc))
