from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
from orionis.console.base.command import BaseCommand
from orionis.console.base.contracts.command import IBaseCommand
from orionis.console.output.console import Console
from orionis.test import TestCase

if TYPE_CHECKING:
    from orionis.console.args.argument import Argument

class ConcreteTestCommand(BaseCommand):
    """
    Implement a concrete test command for BaseCommand.

    This class is used to test the BaseCommand interface.
    """

    signature: str = "test-command"
    description: str = "A test command implementation"
    arguments: ClassVar[list[Argument]] = []

    async def handle(self) -> None:
        """
        Execute the test command handler.

        Returns
        -------
        None
            This method does not return a value.
        """

class TestBaseCommand(TestCase):
    """Test suite for the BaseCommand implementation."""

    def setUp(self) -> None:
        """
        Set up test fixtures before each test method.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Create a new instance of the test command for each test
        self.command = ConcreteTestCommand()

    def testInheritsFromExpectedClasses(self) -> None:
        """
        Verify BaseCommand inherits from Console and IBaseCommand.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Check inheritance and interface implementation
        self.assertIsInstance(self.command, Console)
        self.assertIsInstance(self.command, IBaseCommand)
        self.assertTrue(issubclass(BaseCommand, Console))
        self.assertTrue(issubclass(BaseCommand, IBaseCommand))

    def testDefaultTimestampsValue(self) -> None:
        """
        Check that timestamps are enabled by default.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertTrue(BaseCommand.timestamps)

    def testDefaultEmptyArguments(self) -> None:
        """
        Ensure the default arguments list is empty.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(BaseCommand.arguments, [])
        self.assertIsInstance(BaseCommand.arguments, list)

    def testDefaultEmptyInternalArguments(self) -> None:
        """
        Ensure the internal arguments dictionary is empty by default.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(BaseCommand().getArguments(), {})
        self.assertIsInstance(BaseCommand().getArguments(), dict)

    async def testHandleRaisesNotImplementedError(self) -> None:
        """
        Confirm handle method raises NotImplementedError in base class.

        Returns
        -------
        None
            This method does not return a value.
        """
        base_command = BaseCommand()
        # The base handle method should raise NotImplementedError
        with self.assertRaises(NotImplementedError) as context:
            await base_command.handle()
        error_message = str(context.exception)
        expected_message = (
            "The 'handle' method must be implemented in the subclass."
        )
        self.assertEqual(error_message, expected_message)

    def testGetArgumentWithValidKey(self) -> None:
        """
        Retrieve argument with a valid string key.

        Returns
        -------
        None
            This method does not return a value.
        """
        test_args = {"test_key": "test_value", "number_key": 42}
        self.command.setArguments(test_args)
        # Retrieve and check argument values
        result = self.command.getArgument("test_key")
        self.assertEqual(result, "test_value")
        result = self.command.getArgument("number_key")
        self.assertEqual(result, 42)

    def testGetArgumentWithDefaultValue(self) -> None:
        """
        Retrieve argument with a default value for missing key.

        Returns
        -------
        None
            This method does not return a value.
        """
        test_args = {"existing_key": "value"}
        self.command.setArguments(test_args)
        # Test with explicit default
        result = self.command.getArgument("missing_key", "default_value")
        self.assertEqual(result, "default_value")
        # Test with None default
        result = self.command.getArgument("missing_key")
        self.assertIsNone(result)

    def testGetArgumentWithInvalidKeyType(self) -> None:
        """
        Ensure getArgument raises TypeError for non-string key.

        Returns
        -------
        None
            This method does not return a value.
        """
        test_args = {"valid_key": "value"}
        self.command.setArguments(test_args)
        # Attempt to retrieve argument with invalid key type
        with self.assertRaises(TypeError) as context:
            self.command.getArgument(123)
        error_message = str(context.exception)
        self.assertEqual(error_message, "Argument key must be a string.")

    def testGetArgumentWithNoneKey(self) -> None:
        """
        Ensure getArgument raises TypeError for None key.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(TypeError) as context:
            self.command.getArgument(None)
        error_message = str(context.exception)
        self.assertEqual(error_message, "Argument key must be a string.")

    def testGetArgumentsReturnsCorrectData(self) -> None:
        """
        Ensure getArguments returns all stored arguments.

        Returns
        -------
        None
            This method does not return a value.
        """
        test_args = {
            "arg1": "value1",
            "arg2": 42,
            "arg3": True,
            "nested": {"key": "value"},
        }
        self.command.setArguments(test_args)
        result = self.command.getArguments()
        self.assertEqual(result, test_args)

    def testGetArgumentsReturnsCopy(self) -> None:
        """
        Ensure getArguments returns a copy of internal arguments.

        Returns
        -------
        None
            This method does not return a value.
        """
        test_args = {"original_key": "original_value"}
        self.command.setArguments(test_args)
        result = self.command.getArguments()
        result["modified_key"] = "modified_value"
        # The internal state should remain unchanged
        internal_args = self.command.getArguments()
        self.assertNotEqual(result, internal_args)
        self.assertNotIn("modified_key", internal_args)
        self.assertEqual(internal_args, {"original_key": "original_value"})

    def testGetArgumentsWithEmptyArguments(self) -> None:
        """
        Check getArguments behavior with no arguments set.

        Returns
        -------
        None
            This method does not return a value.
        """
        result = self.command.getArguments()
        self.assertEqual(result, {})
        self.assertIsInstance(result, dict)

    def testSetArgumentsWithValidDictionary(self) -> None:
        """
        Set arguments with a valid dictionary input.

        Returns
        -------
        None
            This method does not return a value.
        """
        test_args = {"key1": "value1", "key2": 42, "key3": True}
        self.command.setArguments(test_args)
        # Verify internal state was updated
        self.assertEqual(self.command.getArguments(), test_args)

    def testSetArgumentsWithEmptyDictionary(self) -> None:
        """
        Set arguments with an empty dictionary.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.command.setArguments({})
        self.assertEqual(self.command.getArguments(), {})

    def testSetArgumentsUpdatesExistingArguments(self) -> None:
        """
        Update existing arguments with setArguments.

        Returns
        -------
        None
            This method does not return a value.
        """
        # First set
        initial_args = {"arg1": "value1", "arg2": "value2"}
        self.command.setArguments(initial_args)
        # Second set with overlapping and new keys
        additional_args = {"arg2": "updated_value2", "arg3": "value3"}
        self.command.setArguments(additional_args)
        expected = {
            "arg1": "value1",
            "arg2": "updated_value2",
            "arg3": "value3",
        }
        self.assertEqual(self.command.getArguments(), expected)

    def testSetArgumentsRaisesTypeErrorForNonDict(self) -> None:
        """
        Ensure setArguments raises TypeError for non-dictionary input.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Test with string input
        with self.assertRaises(TypeError) as context:
            self.command.setArguments("invalid_string")
        error_message = str(context.exception)
        self.assertEqual(error_message, "Arguments must be provided as a dictionary.")

    def testSetArgumentsRaisesTypeErrorForNoneInput(self) -> None:
        """
        Ensure setArguments raises TypeError for None input.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(TypeError) as context:
            self.command.setArguments(None)
        error_message = str(context.exception)
        self.assertEqual(error_message, "Arguments must be provided as a dictionary.")

    def testSetArgumentsRaisesTypeErrorForListInput(self) -> None:
        """
        Ensure setArguments raises TypeError for list input.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(TypeError) as context:
            self.command.setArguments(["item1", "item2"])
        error_message = str(context.exception)
        self.assertEqual(error_message, "Arguments must be provided as a dictionary.")

    def testCompleteWorkflowWithArgumentHandling(self) -> None:
        """
        Test complete workflow of argument injection and retrieval.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Prepare test arguments
        test_args = {
            "input_file": "/path/to/file.txt",
            "verbose": True,
            "count": 10,
            "config": {"debug": True, "log_level": "INFO"},
        }
        # Inject arguments
        self.command.setArguments(test_args)
        # Test individual argument retrieval
        self.assertEqual(
            self.command.getArgument("input_file"), "/path/to/file.txt",
        )
        self.assertTrue(self.command.getArgument("verbose"))
        self.assertEqual(self.command.getArgument("count"), 10)
        # Test retrieval with default
        self.assertEqual(
            self.command.getArgument("missing", "default"), "default",
        )
        # Test complete arguments retrieval
        all_args = self.command.getArguments()
        self.assertEqual(all_args, test_args)
        # Verify independence of copies
        all_args["new_key"] = "new_value"
        self.assertNotIn("new_key", self.command.getArguments())

    def testArgumentsWithComplexDataTypes(self) -> None:
        """
        Handle arguments with complex data types.

        Returns
        -------
        None
            This method does not return a value.
        """
        complex_args = {
            "string": "text",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "none_value": None,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "tuple": (1, "two", 3.0),
        }
        self.command.setArguments(complex_args)
        # Verify each data type is preserved
        self.assertEqual(self.command.getArgument("string"), "text")
        self.assertEqual(self.command.getArgument("integer"), 42)
        self.assertEqual(self.command.getArgument("float"), 3.14)
        self.assertTrue(self.command.getArgument("boolean"))
        self.assertIsNone(self.command.getArgument("none_value"))
        self.assertEqual(self.command.getArgument("list"), [1, 2, 3])
        self.assertEqual(self.command.getArgument("dict"), {"nested": "value"})
        self.assertEqual(self.command.getArgument("tuple"), (1, "two", 3.0))

    def testInitialStateConsistency(self) -> None:
        """
        Ensure initial command state is consistent and predictable.

        Returns
        -------
        None
            This method does not return a value.
        """
        fresh_command = ConcreteTestCommand()
        # Check initial argument state
        self.assertEqual(fresh_command.getArguments(), {})
        self.assertIsNone(fresh_command.getArgument("any_key"))
        self.assertEqual(
            fresh_command.getArgument("any_key", "default"), "default",
        )
        # Check class attributes
        self.assertTrue(fresh_command.timestamps)
        self.assertEqual(fresh_command.signature, "test-command")
        self.assertEqual(
            fresh_command.description, "A test command implementation",
        )
        self.assertEqual(fresh_command.arguments, [])

    def testEdgeCaseEmptyStringKey(self) -> None:
        """
        Retrieve argument with an empty string key.

        Returns
        -------
        None
            This method does not return a value.
        """
        test_args = {"": "empty_key_value", "normal": "normal_value"}
        self.command.setArguments(test_args)
        result = self.command.getArgument("")
        self.assertEqual(result, "empty_key_value")

    def testArgumentKeyWithSpecialCharacters(self) -> None:
        """
        Handle argument keys with special characters.

        Returns
        -------
        None
            This method does not return a value.
        """
        test_args = {
            "key-with-dashes": "value1",
            "key_with_underscores": "value2",
            "key.with.dots": "value3",
            "key with spaces": "value4",
        }
        self.command.setArguments(test_args)
        self.assertEqual(self.command.getArgument("key-with-dashes"), "value1")
        self.assertEqual(self.command.getArgument("key_with_underscores"), "value2")
        self.assertEqual(self.command.getArgument("key.with.dots"), "value3")
        self.assertEqual(self.command.getArgument("key with spaces"), "value4")
