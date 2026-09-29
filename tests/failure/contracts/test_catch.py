from __future__ import annotations
import inspect
from orionis.failure.contracts.catch import ICatch
from orionis.test import TestCase

class TestICatchIsAbstract(TestCase):

    def testIsAbstractClass(self) -> None:
        """Verify that ICatch is recognised as an abstract class.

        Validates that the interface declares at least one abstract method
        so Python prevents direct instantiation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.isabstract(ICatch))

    def testCannotBeInstantiatedDirectly(self) -> None:
        """Verify that ICatch raises TypeError on direct instantiation.

        Validates that attempting to create a bare ICatch object fails
        due to unimplemented abstract methods.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            ICatch()  # type: ignore[abstract]

    def testExceptionMethodIsAbstract(self) -> None:
        """Confirm that the exception method is declared abstract on ICatch.

        Validates that any concrete subclass is forced to implement the
        exception-handling entry point.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("exception", ICatch.__abstractmethods__)

    def testExactlyOneAbstractMethod(self) -> None:
        """Verify that ICatch declares exactly one abstract method.

        Validates that the interface surface area is stable and that no
        methods have been silently added or removed without updating
        consumers.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(len(ICatch.__abstractmethods__), 1)

class TestICatchConcreteSubclass(TestCase):

    def testConcreteSubclassCanBeInstantiated(self) -> None:
        """Instantiate a minimal concrete subclass of ICatch without error.

        Validates that a class providing the required exception method
        satisfies the abstract interface and can be created normally.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """

        class _ConcreteICatch(ICatch):
            async def exception(self, _exception, _request=None):
                """Accept exception dispatch in the contract test double.

                Parameters
                ----------
                _exception : object
                    Value supplied for ``_exception``.
                _request : object
                    Value supplied for ``_request``.

                Returns
                -------
                object
                    Value produced by the helper.
                """
                return

        instance = _ConcreteICatch()
        self.assertIsInstance(instance, ICatch)

    def testIncompleteSubclassRaisesTypeError(self) -> None:
        """Raise TypeError when a subclass omits the exception method.

        Validates that Python's ABC machinery enforces implementation of
        all abstract methods before an instance can be created.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """

        class _IncompleteICatch(ICatch):
            pass

        with self.assertRaises(TypeError):
            _IncompleteICatch()  # type: ignore[abstract]
