from __future__ import annotations
import inspect
from abc import ABC
from orionis.console.base.contracts.scheduler import IBaseScheduler
from orionis.test import TestCase

class TestIBaseScheduler(TestCase):

    def testIsAbstractClass(self) -> None:
        """Verify that IBaseScheduler is an abstract class.

        Checks if IBaseScheduler has abstract methods and cannot be instantiated
        directly without implementation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        # Verify it's an abstract class
        self.assertTrue(inspect.isabstract(IBaseScheduler))

    def testCannotBeInstantiatedDirectly(self) -> None:
        """Ensure IBaseScheduler cannot be instantiated directly.

        Attempts to create an instance of the abstract class and expects a
        TypeError due to unimplemented abstract methods.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        # Attempt to instantiate the abstract class should raise TypeError
        with self.assertRaises(TypeError):
            IBaseScheduler()

    def testHasRequiredAbstractMethods(self) -> None:
        """Verify that all required abstract methods are defined.

        Checks that the interface declares the expected abstract methods:
        tasks, onStarted, onPaused, onResumed, and onShutdown.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        abstract_methods = IBaseScheduler.__abstractmethods__

        expected_methods = {
            "tasks",
            "onStarted",
            "onPaused",
            "onResumed",
            "onShutdown",
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
        tasks_sig = inspect.signature(IBaseScheduler.tasks)
        onstarted_sig = inspect.signature(IBaseScheduler.onStarted)
        onpaused_sig = inspect.signature(IBaseScheduler.onPaused)
        onresumed_sig = inspect.signature(IBaseScheduler.onResumed)
        onshutdown_sig = inspect.signature(IBaseScheduler.onShutdown)

        # Verify tasks method signature
        self.assertEqual(len(tasks_sig.parameters), 2)  # self + schedule
        self.assertIn("schedule", tasks_sig.parameters)

        # Verify event handler method signatures
        for sig in [onstarted_sig, onpaused_sig, onresumed_sig, onshutdown_sig]:
            self.assertEqual(len(sig.parameters), 2)  # self + event
            self.assertIn("event", sig.parameters)

    def testAllMethodsAreAsync(self) -> None:
        """Verify that all abstract methods are asynchronous.

        Ensures that the interface defines all methods as coroutine functions,
        which is required for proper async scheduling functionality.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        # Check that all abstract methods are coroutine functions
        self.assertTrue(inspect.iscoroutinefunction(IBaseScheduler.tasks))
        self.assertTrue(inspect.iscoroutinefunction(IBaseScheduler.onStarted))
        self.assertTrue(inspect.iscoroutinefunction(IBaseScheduler.onPaused))
        self.assertTrue(inspect.iscoroutinefunction(IBaseScheduler.onResumed))
        self.assertTrue(inspect.iscoroutinefunction(IBaseScheduler.onShutdown))

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
            class PartialScheduler(IBaseScheduler):
                async def tasks(self, schedule):
                    """Leave task access unimplemented in the partial scheduler.

                    Parameters
                    ----------
                    schedule : object
                        Value supplied for ``schedule``.

                    Returns
                    -------
                    None
                        Completes the operation described above.
                    """
                # Missing other abstract methods
            PartialScheduler()

    def testInheritsFromABC(self) -> None:
        """Verify that IBaseScheduler inherits from ABC.

        Ensures that the interface properly inherits from ABC to provide
        abstract method functionality.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(IBaseScheduler, ABC))

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
        self.assertTrue(hasattr(IBaseScheduler.tasks, "__annotations__"))
        self.assertTrue(hasattr(IBaseScheduler.onStarted, "__annotations__"))

        # Get annotations safely
        tasks_annotations = getattr(IBaseScheduler.tasks, "__annotations__", {})
        onstarted_annotations = getattr(IBaseScheduler.onStarted, "__annotations__", {})

        # Verify annotations exist (even if empty dicts)
        self.assertIsInstance(tasks_annotations, dict)
        self.assertIsInstance(onstarted_annotations, dict)
