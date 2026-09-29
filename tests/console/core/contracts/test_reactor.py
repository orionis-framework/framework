from __future__ import annotations
import inspect
from orionis.console.core.contracts.reactor import IReactor
from orionis.test import TestCase

class TestIReactor(TestCase):
    """Test suite for the IReactor abstract interface."""

    def testIsAbstractClass(self) -> None:
        """Verify that IReactor is an abstract class.

        Ensures that IReactor has abstract methods defined and cannot be
        instantiated directly without a concrete implementation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.isabstract(IReactor))

    def testCannotBeInstantiatedDirectly(self) -> None:
        """Ensure IReactor cannot be instantiated directly.

        Attempts to create an instance of the abstract class and expects a
        TypeError due to unimplemented abstract methods.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            IReactor()

    def testHasRequiredAbstractMethods(self) -> None:
        """Verify that all required abstract methods are defined on IReactor.

        Checks that the interface declares the expected abstract methods:
        command, info, and call.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        abstract_methods = IReactor.__abstractmethods__
        expected_methods = {"command", "info", "call"}
        self.assertEqual(abstract_methods, expected_methods)

    def testCommandMethodSignature(self) -> None:
        """Verify that the command method has the expected signature.

        Ensures the abstract method declares the correct parameters:
        self, signature, and handler.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IReactor.command)
        params = list(sig.parameters.keys())
        self.assertIn("signature", params)
        self.assertIn("handler", params)
        self.assertEqual(len(sig.parameters), 3)

    def testInfoMethodSignature(self) -> None:
        """Verify that the info method has the expected signature.

        Ensures the abstract method only declares self as its parameter,
        as no additional arguments are needed to retrieve command metadata.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IReactor.info)
        self.assertEqual(len(sig.parameters), 1)
        self.assertIn("self", sig.parameters)

    def testCallMethodSignature(self) -> None:
        """Verify that the call method has the expected signature.

        Ensures the abstract method declares the correct parameters:
        self, signature, and args with a default value of None.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IReactor.call)
        params = sig.parameters
        self.assertIn("signature", params)
        self.assertIn("args", params)
        self.assertEqual(len(params), 3)
        self.assertIsNone(params["args"].default)

    def testInfoIsAsyncMethod(self) -> None:
        """Verify that the info method is declared as a coroutine function.

        Ensures that info is defined as async to support non-blocking
        command metadata retrieval.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.iscoroutinefunction(IReactor.info))

    def testCallIsAsyncMethod(self) -> None:
        """Verify that the call method is declared as a coroutine function.

        Ensures that call is defined as async to support non-blocking
        command execution.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.iscoroutinefunction(IReactor.call))

    def testCommandIsNotAsyncMethod(self) -> None:
        """Verify that the command registration method is synchronous.

        Ensures that command is not a coroutine function, as command
        registration is a synchronous operation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(inspect.iscoroutinefunction(IReactor.command))

    def testConcreteSubclassMustImplementAllMethods(self) -> None:
        """Verify that a partial subclass cannot be instantiated.

        Ensures that any subclass that does not implement all abstract
        methods raises a TypeError on instantiation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        class PartialReactor(IReactor):
            def command(self, signature, handler): # NOSONAR
                """Accept command registration in the test double.

                Parameters
                ----------
                signature : object
                    Value supplied for ``signature``.
                handler : object
                    Value supplied for ``handler``.

                Returns
                -------
                None
                    Completes the operation described above.
                """

        with self.assertRaises(TypeError):
            PartialReactor()

    def testFullConcreteSubclassCanBeInstantiated(self) -> None:
        """Verify that a fully implemented subclass can be instantiated.

        Ensures that a class implementing all abstract methods of IReactor
        can be successfully instantiated without errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        class ConcreteReactor(IReactor):
            def command(self, signature, handler):
                """Accept a command registration in this contract double.

                Parameters
                ----------
                signature, handler : object
                    Command metadata required by the contract.

                Returns
                -------
                None
                    No registration is retained by this test double.
                """
                del signature, handler

            async def info(self):
                """Return the empty command registry.

                Returns
                -------
                list
                    Empty command metadata.
                """
                return []

            async def call(self, signature, args=None):
                """Accept a command invocation in this contract double.

                Parameters
                ----------
                signature : object
                    Command signature required by the contract.
                args : object, optional
                    Command arguments required by the contract.

                Returns
                -------
                int
                    Successful test result.
                """
                del signature, args
                return 0

        instance = ConcreteReactor()
        self.assertIsInstance(instance, IReactor)
