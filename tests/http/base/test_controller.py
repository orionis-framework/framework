from orionis.http.base.controller import BaseController
from orionis.test import TestCase

class TestBaseController(TestCase):
    """Unit tests for the BaseController marker class."""

    def testIsInstantiable(self) -> None:
        """
        Verify that BaseController can be instantiated without arguments.

        Confirms the class has no required constructor parameters and
        does not raise on creation.
        """
        instance = BaseController()
        self.assertIsInstance(instance, BaseController)

    def testSubclassInheritsFromBaseController(self) -> None:
        """
        Verify that a subclass of BaseController passes an issubclass check.

        Confirms that the inheritance hierarchy is correctly established.
        """

        class _MyController(BaseController):
            def index(self) -> str:
                """Return the controller action result."""
                return "ok"

        self.assertTrue(issubclass(_MyController, BaseController))
        instance = _MyController()
        self.assertIsInstance(instance, BaseController)

    def testBaseControllerHasNoPublicMethods(self) -> None:
        """
        Verify that BaseController exposes no public instance methods.

        Confirms the marker-class contract by asserting that no user-
        defined methods are present on the class.
        """
        public_methods = [
            name
            for name in dir(BaseController)
            if not name.startswith("_")
        ]
        self.assertEqual(public_methods, [])

    def testSubclassMethodsAreAccessible(self) -> None:
        """
        Verify that methods defined on a subclass are accessible.

        Confirms that extending BaseController does not interfere with
        method resolution in user-defined controllers.
        """

        class _UserController(BaseController):
            def show(self) -> str:
                """Return the user action result."""
                return "user"

        ctrl = _UserController()
        self.assertEqual(ctrl.show(), "user")
