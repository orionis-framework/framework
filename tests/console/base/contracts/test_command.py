from __future__ import annotations
import inspect
from orionis.console.base.contracts.command import IBaseCommand
from orionis.test import TestCase

class TestIBaseCommand(TestCase):

    def testIsAbstractClass(self) -> None:
        """
        Verify that IBaseCommand is an abstract class.

        Checks if IBaseCommand has abstract methods and cannot be instantiated
        directly without implementation.

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        # Verify it's an abstract class
        self.assertTrue(inspect.isabstract(IBaseCommand))

    def testCannotBeInstantiatedDirectly(self) -> None:
        """
        Ensure IBaseCommand cannot be instantiated directly.

        Attempts to create an instance of the abstract class and expects a
        TypeError due to unimplemented abstract methods.

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        with self.assertRaises(TypeError) as context:
            IBaseCommand()
        error_msg = str(context.exception)
        self.assertIn("Can't instantiate abstract class", error_msg)
        self.assertIn("abstract method", error_msg)

    def testHasRequiredAbstractMethods(self) -> None:
        """
        Confirm that IBaseCommand defines all required abstract methods.

        Checks that the interface declares the core methods that concrete
        implementations must provide.

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        abstract_methods = IBaseCommand.__abstractmethods__
        expected_methods = {"handle", "getArgument", "getArguments", "setArguments"}
        self.assertEqual(abstract_methods, expected_methods)

    def testHasCorrectClassAttributes(self) -> None:
        """
        Verify that IBaseCommand defines required class-level attributes.

        Checks that the interface declares the expected class variables with
        proper type annotations.

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        # Check that class attributes are defined
        self.assertTrue(hasattr(IBaseCommand, "timestamps"))
        self.assertTrue("signature" in IBaseCommand.__annotations__)
        self.assertTrue("description" in IBaseCommand.__annotations__)
        self.assertTrue(hasattr(IBaseCommand, "arguments"))

    def testClassAttributeTypes(self) -> None:
        """
        Validate that class attributes have correct type annotations.

        Checks that the type hints for class attributes match the expected types
        as defined in the interface.

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        annotations = IBaseCommand.__annotations__
        expected_annotations = [
            "timestamps",
            "signature",
            "description",
            "arguments",
        ]
        for attr_name in expected_annotations:
            self.assertIn(attr_name, annotations)

    def testDefaultArgumentsList(self) -> None:
        """
        Check that the default arguments list is properly initialized.

        Verifies that the default arguments class variable is an empty list and
        can be safely used for inheritance.

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        self.assertEqual(IBaseCommand.arguments, [])
        self.assertIsInstance(IBaseCommand.arguments, list)

    def testDefaultTimestampsSetting(self) -> None:
        """
        Confirm that timestamps are enabled by default.

        Verifies that the default configuration enables timestamp display in
        console output.

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        self.assertTrue(IBaseCommand.timestamps)

    def testHandleMethodSignature(self) -> None:
        """
        Validate that the handle method has correct signature.

        Checks that the abstract handle method is properly defined with async
        support and no parameters except self.

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        handle_method = IBaseCommand.handle
        # Check it's an abstract method
        self.assertTrue(getattr(handle_method, "__isabstractmethod__", False))
        # Check method signature
        signature = inspect.signature(handle_method)
        self.assertEqual(len(signature.parameters), 1)  # Only 'self'
        # Should be async
        self.assertTrue(inspect.iscoroutinefunction(handle_method))

    def testGetArgumentMethodSignature(self) -> None:
        """
        Ensure getArgument method has correct signature.

        Checks that the abstract getArgument method accepts the expected
        parameters with proper type annotations.

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        method = IBaseCommand.getArgument
        # Check it's an abstract method
        self.assertTrue(getattr(method, "__isabstractmethod__", False))
        # Check method signature
        signature = inspect.signature(method)
        parameters = list(signature.parameters.keys())
        # Expected parameters: self, key, default
        self.assertEqual(len(parameters), 3)
        self.assertEqual(parameters[0], "self")
        self.assertEqual(parameters[1], "key")
        self.assertEqual(parameters[2], "default")

    def testGetArgumentsMethodSignature(self) -> None:
        """
        Confirm getArguments method has correct signature.

        Checks that the abstract getArguments method has the expected signature
        for returning all arguments.

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        method = IBaseCommand.getArguments
        # Check it's an abstract method
        self.assertTrue(getattr(method, "__isabstractmethod__", False))
        # Check method signature
        signature = inspect.signature(method)
        parameters = list(signature.parameters.keys())
        # Expected parameters: only self
        self.assertEqual(len(parameters), 1)
        self.assertEqual(parameters[0], "self")

    def testSetArgumentsMethodSignature(self) -> None:
        """
        Validate setArguments method has correct signature.

        Checks that the abstract setArguments method accepts the expected
        parameters for injecting parsed command-line arguments.

        Returns
        -------
        None
            No return value; asserts within the method.
        """
        method = IBaseCommand.setArguments
        # Check it's an abstract method
        self.assertTrue(getattr(method, "__isabstractmethod__", False))
        # Check method signature
        signature = inspect.signature(method)
        parameters = list(signature.parameters.keys())
        # Expected parameters: self, args
        self.assertEqual(len(parameters), 2)
        self.assertEqual(parameters[0], "self")
        self.assertEqual(parameters[1], "args")
