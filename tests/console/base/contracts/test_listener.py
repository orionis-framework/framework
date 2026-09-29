from __future__ import annotations
import inspect
from abc import ABC
from orionis.console.base.contracts.listener import IBaseTaskListener
from orionis.test import TestCase

class TestIBaseTaskListener(TestCase):

    def testIsAbstractClass(self) -> None:
        """
        Verify that IBaseTaskListener is an abstract class.

        Checks if IBaseTaskListener has abstract methods and cannot be instantiated
        directly without implementation.

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        # Verify it's an abstract class
        self.assertTrue(inspect.isabstract(IBaseTaskListener))

    def testCannotBeInstantiatedDirectly(self) -> None:
        """
        Ensure IBaseTaskListener cannot be instantiated directly.

        Attempts to create an instance of the abstract class and expects a
        TypeError due to unimplemented abstract methods.

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        with self.assertRaises(TypeError) as context:
            IBaseTaskListener()
        error_msg = str(context.exception)
        self.assertIn("Can't instantiate abstract class", error_msg)
        self.assertIn("abstract method", error_msg)

    def testHasRequiredAbstractMethods(self) -> None:
        """
        Confirm that IBaseTaskListener defines all required abstract methods.

        Checks that the interface declares the core methods that concrete
        implementations must provide.

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        expected_methods = [
            "onTaskAdded",
            "onTaskRemoved",
            "onTaskExecuted",
            "onTaskError",
            "onTaskMissed",
            "onTaskSubmitted",
            "onTaskMaxInstances",
        ]

        # Get abstract methods from the class
        abstract_methods = getattr(IBaseTaskListener, "__abstractmethods__", set())

        # Convert to list for easier comparison
        abstract_method_list = list(abstract_methods)

        # Verify all expected methods are abstract
        for method_name in expected_methods:
            self.assertIn(method_name, abstract_method_list)

        # Verify the count matches
        self.assertEqual(len(expected_methods), len(abstract_method_list))

    def testMethodSignatures(self) -> None:
        """
        Verify all methods have correct basic signatures.

        Checks that method parameters are properly structured for all handler methods.

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        methods_to_test = [
            "onTaskAdded",
            "onTaskRemoved",
            "onTaskExecuted",
            "onTaskError",
            "onTaskMissed",
            "onTaskSubmitted",
            "onTaskMaxInstances",
        ]

        for method_name in methods_to_test:
            with self.subTest(method=method_name):
                # Verify method exists
                self.assertTrue(hasattr(IBaseTaskListener, method_name))

                # Verify method is callable
                method = getattr(IBaseTaskListener, method_name)
                self.assertTrue(callable(method))

                # Verify method is async
                self.assertTrue(inspect.iscoroutinefunction(method))

    def testAllMethodsAreAsync(self) -> None:
        """
        Verify all abstract methods are asynchronous.

        Checks that all abstract methods are defined as async functions.

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        async_methods = [
            "onTaskAdded",
            "onTaskRemoved",
            "onTaskExecuted",
            "onTaskError",
            "onTaskMissed",
            "onTaskSubmitted",
            "onTaskMaxInstances",
        ]

        for method_name in async_methods:
            method = getattr(IBaseTaskListener, method_name)
            self.assertTrue(inspect.iscoroutinefunction(method))

    def testInheritanceHierarchy(self) -> None:
        """
        Verify IBaseTaskListener inheritance hierarchy.

        Checks that the interface properly inherits from ABC (Abstract Base Class).

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        # Check that it inherits from ABC
        self.assertTrue(issubclass(IBaseTaskListener, ABC))

        # Check method resolution order
        mro = IBaseTaskListener.__mro__
        self.assertIn(ABC, mro)

    def testMethodsAcceptEventParameter(self) -> None:
        """
        Verify methods are structured to accept event parameters.

        Checks that all handler methods exist and are properly structured.

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        methods = [
            "onTaskAdded",
            "onTaskRemoved",
            "onTaskExecuted",
            "onTaskError",
            "onTaskMissed",
            "onTaskSubmitted",
            "onTaskMaxInstances",
        ]

        for method_name in methods:
            with self.subTest(method=method_name):
                # Verify method exists
                self.assertTrue(hasattr(IBaseTaskListener, method_name))
                # Verify method is in abstract methods
                abstract_methods = getattr(
                    IBaseTaskListener, "__abstractmethods__", set(),
                )
                self.assertIn(method_name, abstract_methods)
