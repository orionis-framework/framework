from __future__ import annotations
from orionis.test import TestCase
from orionis.container.exceptions.container import CircularDependencyException

_MESSAGE = "A -> B -> A"

class TestCircularDependencyException(TestCase):

    def testInheritsFromTheBuiltinException(self) -> None:
        """
        Derive from Exception so generic handlers can still catch it.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertTrue(issubclass(CircularDependencyException, Exception))

    def testCanBeBuiltWithoutAMessage(self) -> None:
        """
        Build the exception without arguments and keep ``args`` empty.

        Returns
        -------
        None
            This method does not return a value.
        """
        exc = CircularDependencyException()
        self.assertEqual(exc.args, ())
        self.assertEqual(str(exc), "")

    def testPreservesTheSuppliedMessage(self) -> None:
        """
        Preserve the supplied message in both ``args`` and ``str()``.

        Returns
        -------
        None
            This method does not return a value.
        """
        exc = CircularDependencyException(_MESSAGE)
        self.assertEqual(exc.args, (_MESSAGE,))
        self.assertEqual(str(exc), _MESSAGE)

    def testRaisedInstanceKeepsItsMessage(self) -> None:
        """
        Keep the message intact once the exception has been raised.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(CircularDependencyException) as ctx:
            raise CircularDependencyException(_MESSAGE)
        self.assertEqual(str(ctx.exception), _MESSAGE)

    def testSupportsExceptionChaining(self) -> None:
        """
        Keep the original error reachable through ``__cause__``.

        Returns
        -------
        None
            This method does not return a value.
        """
        original = ValueError("root cause")
        with self.assertRaises(CircularDependencyException) as ctx:
            try:
                raise original
            except ValueError as exc:
                raise CircularDependencyException(_MESSAGE) from exc
        self.assertIs(ctx.exception.__cause__, original)
