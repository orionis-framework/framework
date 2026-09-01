from __future__ import annotations
import inspect
import tempfile
from typing import ClassVar
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from orionis.console.core.loader import Loader
from orionis.console.core.contracts.loader import ILoader
from orionis.console.base.command import BaseCommand
from orionis.console.args.argument import Argument
from orionis.test import TestCase

class MockCommand(BaseCommand):
    """
    Mock command class for testing.

    This class serves as a test fixture for command-related tests,
    implementing the BaseCommand interface with predefined attributes
    and a simple handle method.

    Attributes
    ----------
    signature : str
        The command signature identifier.
    description : str
        The command description text.
    timestamps : bool
        Whether to include timestamps in output.
    arguments : list
        The list of command arguments.

    Returns
    -------
    str
        The string "mock handled" when handle method is invoked.
    """

    signature: str = "test:mock"
    description: str = "Test mock command"
    timestamps: bool = True
    arguments: list = None

    def handle(self) -> str:
        """
        Execute the mock command logic.

        Returns
        -------
        str
            A fixed string indicating successful mock execution.
        """
        return "mock handled"

class TestLoader(TestCase):

    def setUp(self) -> None:
        """
        Set up test fixtures.

        Creates a Loader instance and mock objects needed for testing.
        """
        # FileBasedCache creates this directory on disk, so it must point at a
        # writable temporary location instead of the filesystem root.
        compiled_dir = tempfile.TemporaryDirectory()
        self.addCleanup(compiled_dir.cleanup)

        self.mock_app = Mock()
        self.mock_app.compiled = False
        self.mock_app.basePath = Path("/mock/path")
        self.mock_app.path.return_value = Path("/mock/path/console")
        self.mock_app.routingPaths.return_value = [Path("/mock/path/routes.py")]
        self.mock_app.compiledPath = Path(compiled_dir.name) / "compiled"
        self.mock_app.compiledInvalidationPathsDirs = []
        self.mock_app.compiledInvalidationPathsFiles = []

    def testInheritsFromILoader(self) -> None:
        """
        Verify that Loader inherits from ILoader.

        Ensures that the implementation properly implements the
        abstract interface and follows the inheritance hierarchy.
        """
        loader = Loader(self.mock_app)
        self.assertTrue(issubclass(Loader, ILoader))
        self.assertIsInstance(loader, ILoader)

    def testCanBeInstantiated(self) -> None:
        """
        Verify that Loader can be instantiated.

        Tests that the loader implementation can be created
        without raising any exceptions, unlike the abstract interface.
        """
        loader = Loader(self.mock_app)
        self.assertIsInstance(loader, Loader)
        self.assertIsInstance(loader, ILoader)

    def testInitialization(self) -> None:
        """
        Verify that Loader initializes correctly.

        Tests that internal state is properly set up during
        construction with proper default values.
        """
        loader = Loader(self.mock_app)
        self.assertTrue(hasattr(loader, "_Loader__fluent_commands"))
        self.assertTrue(hasattr(loader, "_Loader__commands"))
        self.assertTrue(hasattr(loader, "_Loader__metadata"))
        self.assertTrue(hasattr(loader, "_Loader__imported_modules"))
        self.assertTrue(hasattr(loader, "_Loader__app"))
        self.assertTrue(hasattr(loader, "_Loader__use_cache"))
        self.assertTrue(hasattr(loader, "_Loader__persistence"))

    def testInitializationWithCache(self) -> None:
        """
        Verify that Loader initializes correctly with cache enabled.

        Tests that cache is properly set up when app.compiled is True.
        """
        self.mock_app.compiled = True
        loader = Loader(self.mock_app)
        self.assertTrue(loader._Loader__use_cache)

    def testInitializationWithoutCache(self) -> None:
        """
        Verify that Loader initializes correctly without cache.

        Tests that cache is disabled when app.compiled is False.
        """
        self.mock_app.compiled = False
        loader = Loader(self.mock_app)

        # Check that caching is disabled
        self.assertFalse(loader._Loader__use_cache)
        self.assertIsNone(loader._Loader__persistence)

    def testHasAllRequiredMethods(self) -> None:
        """
        Verify that Loader implements all required methods.

        Checks that all abstract methods from ILoader are implemented
        in the Loader class.
        """
        loader = Loader(self.mock_app)

        # Check that all required methods exist
        self.assertTrue(hasattr(loader, "get"))
        self.assertTrue(hasattr(loader, "all"))
        self.assertTrue(hasattr(loader, "addFluentCommand"))

    def testAllMethodsAreCallable(self) -> None:
        """
        Verify that all implemented methods are callable.

        Ensures that the Loader properly implements all methods
        as callable functions.
        """
        loader = Loader(self.mock_app)
        self.assertTrue(callable(loader.get))
        self.assertTrue(callable(loader.all))
        self.assertTrue(callable(loader.addFluentCommand))

    def testAsyncMethods(self) -> None:
        """
        Verify that async methods are correctly implemented.

        Checks that get and all methods are coroutine functions,
        matching the interface requirements.
        """
        loader = Loader(self.mock_app)
        self.assertTrue(inspect.iscoroutinefunction(loader.get))
        self.assertTrue(inspect.iscoroutinefunction(loader.all))
        self.assertFalse(inspect.iscoroutinefunction(loader.addFluentCommand))

    async def testGetMethodReturnsNoneForNonExistentCommand(self) -> None:
        """
        Verify that get method returns None for non-existent commands.

        Tests that the get method properly handles requests for
        commands that don't exist.
        """
        loader = Loader(self.mock_app)
        result = await loader.get("nonexistent:command")
        self.assertIsNone(result)

    async def testAllMethodReturnsDict(self) -> None:
        """
        Verify that all method returns a dictionary.

        Tests that the all method returns the proper data structure
        for containing command mappings.
        """
        loader = Loader(self.mock_app)
        with patch.object(loader, "_Loader__loadMetadata", new_callable=AsyncMock):
            result = await loader.all()
            self.assertIsInstance(result, dict)

    def testAddFluentCommandValidInput(self) -> None:
        """
        Verify that addFluentCommand works with valid input.

        Tests that fluent commands can be properly added with
        valid signature and handler.
        """
        loader = Loader(self.mock_app)

        # Mock handler
        handler = [MockCommand, "handle"]

        result = loader.addFluentCommand("test:fluent", handler)
        self.assertIsNotNone(result)

    def testAddFluentCommandInvalidHandlerEmpty(self) -> None:
        """
        Verify that addFluentCommand raises error with empty handler.

        Tests that proper validation is performed on handler input
        and empty handlers are rejected.
        """
        loader = Loader(self.mock_app)
        with self.assertRaises(ValueError) as context:
            loader.addFluentCommand("test:command", [])
        error_message = str(context.exception)
        self.assertIn("Handler must be a list with at least one element", error_message)

    def testAddFluentCommandInvalidHandlerNotList(self) -> None:
        """
        Verify that addFluentCommand raises error with non-list handler.

        Tests that handler validation properly rejects non-list inputs.
        """
        loader = Loader(self.mock_app)
        with self.assertRaises(ValueError):
            loader.addFluentCommand("test:command", "not_a_list")

    def testAddFluentCommandInvalidHandlerNotCallable(self) -> None:
        """
        Verify that addFluentCommand raises error with non-callable handler.

        Tests that the first element of handler must be a callable class.
        """
        loader = Loader(self.mock_app)

        with self.assertRaises(TypeError) as context:
            loader.addFluentCommand("test:command", ["not_callable"])

        error_message = str(context.exception)
        self.assertIn("The first element of handler must be a class", error_message)

    def testGetSignatureValidation(self) -> None:
        """
        Verify that signature validation works correctly.

        Tests the private __getSignature method with valid and invalid inputs.
        """
        loader = Loader(self.mock_app)
        signature = loader._Loader__getSignature(MockCommand)
        self.assertEqual(signature, "test:mock")

    def testGetSignatureInvalidMissing(self) -> None:
        """
        Verify that __getSignature raises error for missing signature.

        Tests that commands without signature attribute are properly
        rejected.

        Returns
        -------
        None
        """
        loader = Loader(self.mock_app)

        class NoSignatureCommand(BaseCommand):
            description = "Test command"
            timestamps = False

            def handle(self) -> str:
                return "handled"

        with self.assertRaises(ValueError) as context:
            loader._Loader__getSignature(NoSignatureCommand)

        error_msg = str(context.exception)
        self.assertIn("must have a 'signature' attribute", error_msg)

    def testGetSignatureInvalidType(self) -> None:
        """
        Verify that __getSignature raises error for non-string signature.

        Tests that signature validation rejects non-string types.

        Returns
        -------
        None
        """
        loader = Loader(self.mock_app)

        class InvalidSignatureCommand(BaseCommand):
            signature = 123  # Invalid type
            description = "Test command"
            timestamps = False

            def handle(self) -> str:
                return "handled"

        with self.assertRaises(TypeError) as context:
            loader._Loader__getSignature(InvalidSignatureCommand)

        error_msg = str(context.exception)
        self.assertIn("'signature' must be a string", error_msg)

    def testGetSignatureInvalidEmpty(self) -> None:
        """
        Validate that __getSignature rejects empty signatures.

        Tests that empty string signatures are properly rejected with
        appropriate error handling.

        Returns
        -------
        None
        """
        loader: Loader = Loader(self.mock_app)

        class EmptySignatureCommand(BaseCommand):
            signature: str = ""
            description: str = "Test command"
            timestamps: bool = False

            def handle(self) -> str:
                return "handled"

        # Verify that empty signature raises ValueError
        with self.assertRaises(ValueError) as context:
            loader._Loader__getSignature(EmptySignatureCommand)

        error_message: str = str(context.exception)
        self.assertIn("cannot be an empty string", error_message)

    def testGetSignatureInvalidPattern(self) -> None:
        """
        Validate that __getSignature enforces proper naming conventions.

        Tests that signatures must follow the proper naming pattern
        and rejects invalid formats.

        Returns
        -------
        None
        """
        loader: Loader = Loader(self.mock_app)

        class InvalidPatternCommand(BaseCommand):
            # Starts with number - invalid pattern
            signature: str = "123invalid"
            description: str = "Test command"
            timestamps: bool = False

            def handle(self) -> str:
                return "handled"

        # Verify that invalid pattern raises ValueError
        with self.assertRaises(ValueError) as context:
            loader._Loader__getSignature(InvalidPatternCommand)

        error_message: str = str(context.exception)
        self.assertIn(
            "must contain only alphanumeric characters", error_message,
        )

    def testGetDescriptionDefault(self) -> None:
        """
        Verify that __getDescription provides default for missing description.

        Tests that commands without a description attribute receive a
        sensible default value.

        Returns
        -------
        None
        """
        loader: Loader = Loader(self.mock_app)

        class NoDescriptionCommand(BaseCommand):
            signature: str = "test:nodesc"
            timestamps: bool = False

            def handle(self) -> str:
                return "handled"

        # Verify default description is returned for missing attribute
        description: str = loader._Loader__getDescription(
            NoDescriptionCommand,
        )
        self.assertEqual(description, "No description provided.")

    def testGetDescriptionInvalidType(self) -> None:
        """
        Verify that __getDescription raises error for non-string description.

        Tests that description validation properly rejects non-string types
        and raises appropriate TypeError.

        Returns
        -------
        None
        """
        loader: Loader = Loader(self.mock_app)

        class InvalidDescriptionCommand(BaseCommand):
            signature: str = "test:command"
            description: int = 123  # Invalid type
            timestamps: bool = False

            def handle(self) -> str:
                return "handled"

        # Verify TypeError is raised for non-string description
        with self.assertRaises(TypeError) as context:
            loader._Loader__getDescription(InvalidDescriptionCommand)

        error_msg: str = str(context.exception)
        self.assertIn("'description' must be a string", error_msg)

    def testGetDescriptionEmpty(self) -> None:
        """
        Verify that __getDescription rejects empty descriptions.

        Tests that empty string descriptions are properly rejected
        with appropriate error handling.

        Returns
        -------
        None
        """
        loader: Loader = Loader(self.mock_app)

        class EmptyDescriptionCommand(BaseCommand):
            signature: str = "test:command"
            description: str = ""
            timestamps: bool = False

            def handle(self) -> str:
                return "handled"

        # Verify that empty description raises ValueError
        with self.assertRaises(ValueError) as context:
            loader._Loader__getDescription(EmptyDescriptionCommand)

        error_message: str = str(context.exception)
        self.assertIn("cannot be an empty string", error_message)

    def testGetTimestampsDefault(self) -> None:
        """
        Verify that __getTimestamps returns default for missing attribute.

        Tests that commands without timestamps attribute receive
        the default boolean value.

        Returns
        -------
        None
        """
        loader: Loader = Loader(self.mock_app)

        class NoTimestampsCommand(BaseCommand):
            signature: str = "test:notimestamps"
            description: str = "Test command"

            def handle(self) -> str:
                return "handled"

        # Verify default timestamps value is returned
        timestamps: bool = loader._Loader__getTimestamps(
            NoTimestampsCommand,
        )
        self.assertTrue(timestamps)

    def testGetTimestampsInvalidType(self) -> None:
        """
        Verify that __getTimestamps raises error for non-boolean timestamps.

        Tests that timestamps validation rejects non-boolean types.

        Returns
        -------
        None
        """
        loader: Loader = Loader(self.mock_app)

        class InvalidTimestampsCommand(BaseCommand):
            signature: str = "test:command"
            description: str = "Test command"
            timestamps: str = "not_boolean"  # Invalid type

            def handle(self) -> str:
                return "handled"

        # Verify TypeError is raised for non-boolean timestamps
        with self.assertRaises(TypeError) as context:
            loader._Loader__getTimestamps(InvalidTimestampsCommand)

        error_message: str = str(context.exception)
        self.assertIn("'timestamps' must be a boolean", error_message)

    def testGetArgumentsEmpty(self) -> None:
        """
        Verify that __getArguments returns empty list for missing arguments.

        Tests that commands without arguments attribute receive an empty
        list as the default value.

        Returns
        -------
        None
        """
        loader: Loader = Loader(self.mock_app)

        class NoArgumentsCommand(BaseCommand):
            signature: str = "test:noargs"
            description: str = "Test command"
            timestamps: bool = False

            def handle(self) -> str:
                return "handled"

        # Verify empty list is returned for missing arguments
        arguments: list = loader._Loader__getArguments(
            NoArgumentsCommand,
        )
        self.assertEqual(arguments, [])

    def testGetArgumentsValidArguments(self) -> None:
        """
        Verify that __getArguments handles valid Argument instances.

        Tests that valid Argument instances are properly converted to
        dictionaries with correct structure.

        Returns
        -------
        None
        """
        loader: Loader = Loader(self.mock_app)

        # Create valid argument with correct parameters
        arg: Argument = Argument(
            name_or_flags="--test",
            help="Test argument",
            required=True,
            type_=str,
        )

        class ValidArgumentsCommand(BaseCommand):
            signature: str = "test:args"
            description: str = "Test command"
            timestamps: bool = False
            arguments: ClassVar[list[Argument]] = [arg]

            def handle(self) -> str:
                return "handled"

        # Retrieve and validate arguments list
        arguments: list = loader._Loader__getArguments(
            ValidArgumentsCommand,
        )
        self.assertIsInstance(arguments, list)
        self.assertEqual(len(arguments), 1)
        self.assertIsInstance(arguments[0], dict)

    def testGetArgumentsInvalidType(self) -> None:
        """
        Verify that __getArguments raises error for non-list arguments.

        Tests that arguments validation rejects non-list types.

        Returns
        -------
        None
        """
        loader: Loader = Loader(self.mock_app)

        class InvalidArgumentsCommand(BaseCommand):
            signature: str = "test:command"
            description: str = "Test command"
            timestamps: bool = False
            arguments: str = "not_a_list"  # Invalid type

            def handle(self) -> str:
                return "handled"

        # Verify TypeError is raised for non-list arguments
        with self.assertRaises(TypeError) as context:
            loader._Loader__getArguments(InvalidArgumentsCommand)

        error_msg: str = str(context.exception)
        self.assertIn("'inputs' must return a list", error_msg)

    def testGetArgumentsInvalidArgumentType(self) -> None:
        """
        Verify that __getArguments raises error for non-Argument instances.

        Tests that all elements in arguments list must be Argument
        instances.

        Returns
        -------
        None
        """
        loader: Loader = Loader(self.mock_app)

        class InvalidArgumentTypeCommand(BaseCommand):
            signature: str = "test:command"
            description: str = "Test command"
            timestamps: bool = False
            # Invalid element type - must be Argument instance
            arguments: ClassVar[list[str]] = ["not_an_argument"]

            def handle(self) -> str:
                return "handled"

        # Verify TypeError is raised for non-Argument elements
        with self.assertRaises(TypeError) as context:
            loader._Loader__getArguments(InvalidArgumentTypeCommand)

        error_msg: str = str(context.exception)
        self.assertIn("must contain only Argument instances", error_msg)

    def testBuildArgumentParserWithArguments(self) -> None:
        """
        Build argument parser with the provided arguments.

        Tests that ArgumentParser is properly constructed with given
        arguments and no exceptions are raised during parser creation.

        Returns
        -------
        None
        """
        loader: Loader = Loader(self.mock_app)

        # Test with empty arguments list - parser should still be created
        parser = loader._Loader__buildArgumentParser(
            [], "test:sig", "Test description",
        )

        self.assertIsNotNone(parser)

    def testClassIsNotAbstract(self) -> None:
        """
        Verify that Loader is not an abstract class.

        Ensures that Loader can be instantiated and does not have
        any remaining abstract methods.

        Returns
        -------
        None
        """
        self.assertFalse(inspect.isabstract(Loader))

    def testMethodsHaveProperDocstrings(self) -> None:
        """
        Verify that implemented methods have proper documentation.

        Checks that all public methods include proper docstrings
        following the project's documentation standards.

        Returns
        -------
        None
        """
        # Verify that methods have non-empty docstrings
        self.assertIsNotNone(Loader.__init__.__doc__)
        self.assertIsNotNone(Loader.get.__doc__)
        self.assertIsNotNone(Loader.all.__doc__)
        self.assertIsNotNone(Loader.addFluentCommand.__doc__)

        # Verify that docstrings are not just whitespace
        self.assertTrue(Loader.__init__.__doc__.strip())
        self.assertTrue(Loader.get.__doc__.strip())
        self.assertTrue(Loader.all.__doc__.strip())
        self.assertTrue(Loader.addFluentCommand.__doc__.strip())
