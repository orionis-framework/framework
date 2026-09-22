from orionis.http.routes.enums.route_types import RouteType
from orionis.test import TestCase

class TestRouteType(TestCase):
    """Unit tests for the RouteType string enumeration."""

    def testControllerValue(self) -> None:
        """
        Confirm that the CONTROLLER member has value 'controller'.

        Validates the string used to tag controller-based route handlers.
        """
        self.assertEqual(RouteType.CONTROLLER, "controller")

    def testFunctionValue(self) -> None:
        """
        Confirm that the FUNCTION member has value 'function'.

        Validates the string used to tag plain-function route handlers.
        """
        self.assertEqual(RouteType.FUNCTION, "function")

    def testInvokableValue(self) -> None:
        """
        Confirm that the INVOKABLE member has value 'invokable'.

        Validates the string used to tag invokable-class route handlers.
        """
        self.assertEqual(RouteType.INVOKABLE, "invokable")

    def testViewValue(self) -> None:
        """
        Confirm that the VIEW member has value 'view'.

        Validates the string used to tag template-only route handlers.
        """
        self.assertEqual(RouteType.VIEW, "view")

    def testIsStrEnum(self) -> None:
        """
        Verify that RouteType members behave as plain strings.

        Confirms that each member passes an isinstance check against
        str and supports direct string comparison.
        """
        for member in RouteType:
            self.assertIsInstance(str(member), str)

    def testMemberCount(self) -> None:
        """
        Verify that exactly four route types are defined.

        Validates that no undocumented member has been introduced.
        """
        self.assertEqual(len(list(RouteType)), 4)
