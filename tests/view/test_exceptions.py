# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify the view exception hierarchy, messages, and explicit causes."""

from orionis.test import TestCase
from orionis.view.exceptions import (
    ViewException,
    ViewRenderException,
    ViewRouteException,
    ViewTemplateNotFoundException,
)


class TestViewExceptions(TestCase):
    """Preserve specific errors and their common catch boundary."""

    def testExceptionHierarchy(self) -> None:
        """Derive every specialized view error from the shared exception base.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(issubclass(ViewException, Exception))
        for exception_type in (
            ViewRenderException,
            ViewTemplateNotFoundException,
            ViewRouteException,
        ):
            with self.subTest(exception=exception_type.__name__):
                self.assertTrue(issubclass(exception_type, ViewException))
                self.assertTrue(issubclass(exception_type, Exception))

    def testPreservesMessagesAtEachSpecificType(self) -> None:
        """Keep each original message when catching its specific error type.

        Returns
        -------
        None
            No return value.
        """
        cases = (
            (ViewException, "base view error"),
            (ViewRenderException, "render failed in template"),
            (ViewTemplateNotFoundException, "template not found: users/index.html"),
            (ViewRouteException, "route 'users.show' is not defined"),
        )
        for exception_type, message in cases:
            with self.subTest(exception=exception_type.__name__):
                with self.assertRaises(exception_type) as caught:
                    raise exception_type(message)
                self.assertEqual(str(caught.exception), message)
                self.assertEqual(caught.exception.args, (message,))

    def testCatchesEachSpecializedErrorAsViewException(self) -> None:
        """Catch all specialized errors through their common view boundary.

        Returns
        -------
        None
            No return value.
        """
        cases = (
            (ViewRenderException, "render error"),
            (ViewTemplateNotFoundException, "missing template"),
            (ViewRouteException, "missing route parameter"),
        )
        for exception_type, message in cases:
            with self.subTest(exception=exception_type.__name__):
                with self.assertRaises(ViewException) as caught:
                    raise exception_type(message)
                self.assertIs(type(caught.exception), exception_type)
                self.assertEqual(str(caught.exception), message)

    def testViewExceptionWithNoArgs(self) -> None:
        """Raise the base exception without constructing a message.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(ViewException) as caught:
            raise ViewException
        self.assertEqual(caught.exception.args, ())
        self.assertEqual(str(caught.exception), "")

    def testPreservesChainedCauses(self) -> None:
        """Preserve each original error as the explicitly chained cause.

        Returns
        -------
        None
            No return value.
        """
        cases = (
            (
                ViewRenderException,
                "wrapped render error",
                RuntimeError("original cause"),
            ),
            (
                ViewTemplateNotFoundException,
                "template missing",
                KeyError("missing-template"),
            ),
        )
        for exception_type, message, original in cases:
            with self.subTest(exception=exception_type.__name__):
                with self.assertRaises(exception_type) as caught:
                    raise exception_type(message) from original
                self.assertIs(caught.exception.__cause__, original)
                self.assertEqual(str(caught.exception), message)

    def testExceptionTypesAreDistinct(self) -> None:
        """Keep every specialized exception unrelated to its sibling types.

        Returns
        -------
        None
            No return value.
        """
        exception_types = (
            ViewRenderException,
            ViewTemplateNotFoundException,
            ViewRouteException,
        )
        for left in exception_types:
            for right in exception_types:
                if left is not right:
                    with self.subTest(left=left.__name__, right=right.__name__):
                        self.assertFalse(issubclass(left, right))
