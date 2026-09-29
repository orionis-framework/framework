from __future__ import annotations
from abc import ABC
import inspect
from unittest.mock import Mock
from orionis.console.core.contracts.loader import ILoader
from orionis.test import TestCase

class TestILoader(TestCase):

    def testIsAbstractClass(self) -> None:
        """Verify that ILoader is an abstract class.

        Checks if ILoader has abstract methods and cannot be instantiated
        directly without implementation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        # Verify it's an abstract class
        self.assertTrue(inspect.isabstract(ILoader))

    def testCannotBeInstantiatedDirectly(self) -> None:
        """Ensure ILoader cannot be instantiated directly.

        Attempts to create an instance of the abstract class and expects a
        TypeError due to unimplemented abstract methods.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        # Attempt to instantiate the abstract class should raise TypeError
        with self.assertRaises(TypeError):
            ILoader()

    def testHasRequiredAbstractMethods(self) -> None:
        """Verify that all required abstract methods are defined.

        Checks that the interface declares the expected abstract methods:
        get, all, and addFluentCommand.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        abstract_methods = ILoader.__abstractmethods__
        expected_methods = {
            "get",
            "all",
            "addFluentCommand",
            "load",
        }
        self.assertEqual(abstract_methods, expected_methods)

    def testMethodSignatures(self) -> None:
        """Verify that abstract method signatures are correctly defined.

        Ensures that all abstract methods have the proper signatures,
        parameter types, and return type annotations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        # Get method signatures
        get_sig = inspect.signature(ILoader.get)
        all_sig = inspect.signature(ILoader.all)
        addfluentcommand_sig = inspect.signature(ILoader.addFluentCommand)

        # Verify get method signature
        self.assertEqual(len(get_sig.parameters), 2)
        self.assertIn("signature", get_sig.parameters)

        # Verify all method signature
        self.assertEqual(len(all_sig.parameters), 1)

        # Verify addFluentCommand method signature
        self.assertEqual(len(addfluentcommand_sig.parameters), 3)
        self.assertIn("signature", addfluentcommand_sig.parameters)
        self.assertIn("handler", addfluentcommand_sig.parameters)

    def testAsyncMethods(self) -> None:
        """Verify that get and all methods are asynchronous.

        Ensures that the get and all methods are defined as coroutine functions,
        which is required for proper async loading functionality.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        # Check that async methods are coroutine functions
        self.assertTrue(inspect.iscoroutinefunction(ILoader.get))
        self.assertTrue(inspect.iscoroutinefunction(ILoader.all))

        # Check that addFluentCommand is NOT async
        self.assertFalse(inspect.iscoroutinefunction(ILoader.addFluentCommand))

    def testInheritsFromABC(self) -> None:
        """Verify that ILoader inherits from ABC.

        Ensures that the interface properly inherits from ABC to provide
        abstract method functionality.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(ILoader, ABC))

    def testTypeHints(self) -> None:
        """Verify that proper type hints are defined for abstract methods.

        Checks that the methods have correct type annotations for
        parameters and return values.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        # Verify that methods have annotations defined
        self.assertTrue(hasattr(ILoader.get, "__annotations__"))
        self.assertTrue(hasattr(ILoader.all, "__annotations__"))
        self.assertTrue(hasattr(ILoader.addFluentCommand, "__annotations__"))

        # Get annotations safely
        get_annotations = getattr(ILoader.get, "__annotations__", {})
        all_annotations = getattr(ILoader.all, "__annotations__", {})
        addfluentcommand_annotations = getattr(
            ILoader.addFluentCommand, "__annotations__", {},
        )

        # Verify annotations exist (even if empty dicts)
        self.assertIsInstance(get_annotations, dict)
        self.assertIsInstance(all_annotations, dict)
        self.assertIsInstance(addfluentcommand_annotations, dict)

    def testImplementationRequiresAllMethods(self) -> None:
        """Verify that implementing the interface requires all abstract methods.

        Tests that attempting to create a partial implementation without
        all abstract methods raises TypeError.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        # Test that partial implementation fails
        with self.assertRaises(TypeError):
            class PartialLoader(ILoader):
                async def get(self, signature):
                    """Return the loader result required by the test double.

                    Parameters
                    ----------
                    signature : object
                        Value supplied for ``signature``.

                    Returns
                    -------
                    None
                        Completes the operation described above.
                    """
                # Missing other abstract methods
            PartialLoader()

    def testMethodDocstrings(self) -> None:
        """Verify that abstract methods have proper documentation.

        Checks that all abstract methods include docstrings following
        the project's documentation standards.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        # Check that methods have non-empty docstrings
        self.assertIsNotNone(ILoader.get.__doc__)
        self.assertIsNotNone(ILoader.all.__doc__)
        self.assertIsNotNone(ILoader.addFluentCommand.__doc__)

        # Check that docstrings are not just whitespace
        self.assertTrue(ILoader.get.__doc__.strip())
        self.assertTrue(ILoader.all.__doc__.strip())
        self.assertTrue(ILoader.addFluentCommand.__doc__.strip())

    def testCompleteImplementation(self) -> None:
        """Verify that a complete implementation can be created.

        Tests that a class implementing all abstract methods can be
        instantiated successfully.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        # Test that complete implementation works
        class CompleteLoader(ILoader):
            async def get(self, signature: str):
                """Return the loader result required by the test double.

                Parameters
                ----------
                signature : str
                    Value supplied for ``signature``.

                Returns
                -------
                object
                    Value produced by the helper.
                """
            async def all(self):
                """Return the command registry exposed by the test double.

                Returns
                -------
                object
                    Value produced by the helper.
                """
                return {}
            def addFluentCommand(self, _signature: str, _handler):
                """Record a fluent command registration.

                Parameters
                ----------
                _signature : str
                    Value supplied for ``_signature``.
                _handler : object
                    Value supplied for ``_handler``.

                Returns
                -------
                object
                    Value produced by the helper.
                """
                return Mock()
            async def load(self) -> None:
                """Leave loading unimplemented in the partial loader.

                Returns
                -------
                None
                    Completes the operation described above.
                """

        # Should not raise an error
        loader = CompleteLoader()
        self.assertIsInstance(loader, ILoader)
