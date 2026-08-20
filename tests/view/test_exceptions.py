from orionis.test import TestCase
from orionis.view.exceptions import (
    ViewException,
    ViewRenderException,
    ViewRouteException,
    ViewTemplateNotFoundException,
)

class TestViewExceptions(TestCase):

    def testViewExceptionInheritsFromException(self) -> None:
        """
        Verify ViewException is a subclass of Exception.

        Validates that ViewException fits the standard Python exception
        hierarchy and can be caught with a generic except clause.
        """
        self.assertTrue(issubclass(ViewException, Exception))

    def testViewRenderExceptionInheritsFromViewException(self) -> None:
        """
        Verify ViewRenderException is a subclass of ViewException.

        Validates the inheritance chain so callers can catch both the
        specific render error and the base view error type.
        """
        self.assertTrue(issubclass(ViewRenderException, ViewException))

    def testViewTemplateNotFoundInheritsFromViewException(self) -> None:
        """
        Verify ViewTemplateNotFoundException is a subclass of ViewException.

        Validates the inheritance chain so callers can catch both the
        specific not-found error and the base view error type.
        """
        self.assertTrue(issubclass(ViewTemplateNotFoundException, ViewException))

    def testViewRenderExceptionInheritsFromException(self) -> None:
        """
        Verify ViewRenderException is a subclass of Exception.

        Validates the full chain: ViewRenderException → ViewException
        → Exception.
        """
        self.assertTrue(issubclass(ViewRenderException, Exception))

    def testViewTemplateNotFoundInheritsFromException(self) -> None:
        """
        Verify ViewTemplateNotFoundException is a subclass of Exception.

        Validates the full chain: ViewTemplateNotFoundException
        → ViewException → Exception.
        """
        self.assertTrue(issubclass(ViewTemplateNotFoundException, Exception))

    def testRaiseViewExceptionWithMessage(self) -> None:
        """
        Raise ViewException and verify the message is preserved.

        Validates that the exception stores its message accessible via
        the standard str() conversion.
        """
        msg = "base view error"
        with self.assertRaises(ViewException) as ctx:
            raise ViewException(msg)
        self.assertEqual(str(ctx.exception), msg)

    def testRaiseViewRenderExceptionWithMessage(self) -> None:
        """
        Raise ViewRenderException and verify the message is preserved.

        Validates that ViewRenderException stores its message correctly
        and is catchable at its own type level.
        """
        msg = "render failed in template"
        with self.assertRaises(ViewRenderException) as ctx:
            raise ViewRenderException(msg)
        self.assertEqual(str(ctx.exception), msg)

    def testRaiseViewTemplateNotFoundWithMessage(self) -> None:
        """
        Raise ViewTemplateNotFoundException and verify the message.

        Validates that ViewTemplateNotFoundException stores its message
        and is catchable at its own type level.
        """
        msg = "template not found: users/index.html"
        with self.assertRaises(ViewTemplateNotFoundException) as ctx:
            raise ViewTemplateNotFoundException(msg)
        self.assertEqual(str(ctx.exception), msg)

    def testCatchViewRenderExceptionAsViewException(self) -> None:
        """
        Catch ViewRenderException using the ViewException base class.

        Validates polymorphic catching: callers handling ViewException
        will also intercept ViewRenderException without code changes.
        """
        msg = "render error"
        with self.assertRaises(ViewException):
            raise ViewRenderException(msg)

    def testCatchViewTemplateNotFoundAsViewException(self) -> None:
        """
        Catch ViewTemplateNotFoundException using the ViewException base.

        Validates polymorphic catching: callers handling ViewException
        will also intercept ViewTemplateNotFoundException.
        """
        msg = "missing template"
        with self.assertRaises(ViewException):
            raise ViewTemplateNotFoundException(msg)

    def testViewExceptionWithNoArgs(self) -> None:
        """
        Raise ViewException with no arguments.

        Validates that the exception can be raised without a message,
        matching the pattern used in bare re-raise scenarios.
        """
        with self.assertRaises(ViewException):
            raise ViewException

    def testViewRenderExceptionWithChainedCause(self) -> None:
        """
        Raise ViewRenderException chained from another exception.

        Validates that the __cause__ attribute preserves the original
        exception for debugging and logging purposes.
        """
        original = RuntimeError("original cause")
        msg = "wrapped render error"
        with self.assertRaises(ViewRenderException) as ctx:
            raise ViewRenderException(msg) from original
        self.assertIs(ctx.exception.__cause__, original)

    def testViewTemplateNotFoundWithChainedCause(self) -> None:
        """
        Raise ViewTemplateNotFoundException chained from another exception.

        Validates that the __cause__ attribute preserves the original
        exception when the not-found error wraps a Jinja2 cause.
        """
        original = KeyError("missing-template")
        msg = "template missing"
        with self.assertRaises(ViewTemplateNotFoundException) as ctx:
            raise ViewTemplateNotFoundException(msg) from original
        self.assertIs(ctx.exception.__cause__, original)

    def testViewRouteExceptionInheritsFromViewException(self) -> None:
        """
        Verify ViewRouteException is a subclass of ViewException.

        Validates the inheritance chain so callers can catch both the
        specific route error and the base view error type.
        """
        self.assertTrue(issubclass(ViewRouteException, ViewException))

    def testRaiseViewRouteExceptionWithMessage(self) -> None:
        """
        Raise ViewRouteException and verify the message is preserved.

        Validates that ViewRouteException stores its message correctly
        and is catchable at its own type level.
        """
        msg = "route 'users.show' is not defined"
        with self.assertRaises(ViewRouteException) as ctx:
            raise ViewRouteException(msg)
        self.assertEqual(str(ctx.exception), msg)

    def testCatchViewRouteExceptionAsViewException(self) -> None:
        """
        Catch ViewRouteException using the ViewException base class.

        Validates polymorphic catching: callers handling ViewException
        will also intercept ViewRouteException.
        """
        msg = "missing route parameter"
        with self.assertRaises(ViewException):
            raise ViewRouteException(msg)

    def testExceptionTypesAreDistinct(self) -> None:
        """
        Verify the specialised view errors are unrelated to each other.

        Validates that catching one specialised type never intercepts a
        sibling error type.
        """
        self.assertFalse(
            issubclass(ViewRouteException, ViewRenderException),
        )
        self.assertFalse(
            issubclass(ViewTemplateNotFoundException, ViewRenderException),
        )
