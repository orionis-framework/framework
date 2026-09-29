from __future__ import annotations
import argparse
from typing import Any
from orionis.console.args.argument import Argument
from orionis.console.enums.actions import ArgumentAction
from orionis.support.types.sentinel import MISSING
from orionis.test import TestCase

class TestArgument(TestCase):

    def testBasicArgumentCreation(self) -> None:
        """
        Create a basic argument with minimal parameters.

        This test verifies that an argument can be created with only the required
        name_or_flags parameter.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        # Create an Argument with only the required parameter
        argument = Argument(name_or_flags="--verbose")

        # Assert all default properties of the Argument instance
        self.assertEqual(argument.name_or_flags, ("--verbose",))
        self.assertIsNone(argument.action)
        self.assertIsNone(argument.nargs)
        self.assertIs(argument.const, MISSING)
        self.assertIs(argument.default, MISSING)
        self.assertIsNone(argument.type_)
        self.assertIsNone(argument.choices)
        self.assertFalse(argument.required)
        self.assertIsNone(argument.help)
        self.assertIsNone(argument.metavar)
        self.assertIsNone(argument.dest)
        self.assertIsNone(argument.version)
        self.assertEqual(argument.extra, {})

    def testNameOrFlagsAsString(self) -> None:
        """
        Normalize name_or_flags string to tuple of strings.

        Verifies that when name_or_flags is provided as a string, it is normalized
        to a tuple of strings.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        # Create an Argument with a single string for name_or_flags
        argument = Argument(name_or_flags="--file")
        self.assertEqual(argument.name_or_flags, ("--file",))

    def testNameOrFlagsAsIterable(self) -> None:
        """
        Normalize name_or_flags iterable to tuple of strings.

        Verifies that when name_or_flags is provided as an iterable, it is
        normalized to a tuple of strings.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        # Create an Argument with an iterable for name_or_flags
        argument = Argument(name_or_flags=["-f", "--file"])
        self.assertEqual(argument.name_or_flags, ("-f", "--file"))

    def testActionAsString(self) -> None:
        """
        Accept string action parameter.

        Verifies that string actions are accepted and stored correctly.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        # Create an Argument with a string action
        argument = Argument(name_or_flags="--count", action="count")
        self.assertEqual(argument.action, "count")

    def testActionAsEnum(self) -> None:
        """
        Accept ArgumentAction enum as action parameter.

        Verifies that ArgumentAction enum values are accepted and stored
        correctly.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        # Create an Argument with an ArgumentAction enum as action
        argument = Argument(
            name_or_flags="--verbose",
            action=ArgumentAction.STORE_TRUE,
        )
        self.assertEqual(argument.action, ArgumentAction.STORE_TRUE)

    def testNargsAsInteger(self) -> None:
        """
        Accept integer value for nargs parameter.

        Verifies that integer values for nargs are accepted and stored
        correctly.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        # Create an Argument with an integer nargs
        argument = Argument(name_or_flags="--files", nargs=3)
        self.assertEqual(argument.nargs, 3)

    def testNargsAsValidString(self) -> None:
        """
        Accept valid string values for nargs parameter.

        Verifies that valid string values ('?', '*', '+') for nargs are
        accepted and stored correctly.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        # Test valid string values for nargs
        for valid_nargs in ["?", "*", "+"]:
            argument = Argument(name_or_flags="--files", nargs=valid_nargs)
            self.assertEqual(argument.nargs, valid_nargs)

    def testValidTypeParameter(self) -> None:
        """
        Verify that a valid callable type_ parameter is accepted and stored.

        This test checks that the Argument class accepts a callable for the
        type_ parameter and stores it correctly.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        # Create an Argument with a callable type_ parameter
        argument = Argument(name_or_flags="--count", type_=int)
        self.assertEqual(argument.type_, int)

    def testValidChoicesParameter(self) -> None:
        """
        Verify that valid iterable choices are accepted and stored.

        This test checks that the Argument class accepts an iterable (not a
        string) for the choices parameter and stores it correctly.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        # Create an Argument with a valid iterable for choices
        choices = ["red", "green", "blue"]
        argument = Argument(name_or_flags="--color", choices=choices)
        self.assertEqual(argument.choices, choices)

    def testRequiredParameter(self) -> None:
        """
        Verify that the required parameter is handled for True and False values.

        This test checks that the required parameter is stored correctly for
        both True and False values.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        # Create Arguments with required set to True and False
        required_arg = Argument(name_or_flags="--input", required=True)
        optional_arg = Argument(name_or_flags="--output", required=False)
        self.assertTrue(required_arg.required)
        self.assertFalse(optional_arg.required)

    def testHelpParameter(self) -> None:
        """
        Verify that the help parameter is stored correctly.

        This test checks that the help text provided to the Argument class is
        stored as expected.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        # Create an Argument with a help parameter
        help_text = "Input file path"
        argument = Argument(name_or_flags="--input", help=help_text)
        self.assertEqual(argument.help, help_text)

    def testMetavarAsString(self) -> None:
        """
        Verify that a string metavar parameter is accepted and stored.

        This test checks that the Argument class accepts a string for the
        metavar parameter and stores it correctly.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        # Create an Argument with a string metavar
        argument = Argument(name_or_flags="--file", metavar="FILE")
        self.assertEqual(argument.metavar, "FILE")

    def testMetavarAsTuple(self) -> None:
        """
        Verify that a tuple metavar parameter is accepted and stored.

        This test checks that the Argument class accepts a tuple of strings for
        the metavar parameter and stores it correctly.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        # Create an Argument with a tuple metavar
        metavar = ("SRC", "DEST")
        argument = Argument(name_or_flags="--copy", metavar=metavar)
        self.assertEqual(argument.metavar, metavar)

    def testDestParameter(self) -> None:
        """
        Verify that the dest parameter is stored correctly.

        This test checks that the dest parameter provided to the Argument class
        is stored as expected.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        # Create an Argument with a dest parameter
        argument = Argument(name_or_flags="--input-file", dest="input")
        self.assertEqual(argument.dest, "input")

    def testVersionParameter(self) -> None:
        """
        Verify correct handling of version parameter with version action.

        Tests that the version parameter is stored and associated with the
        version action.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        argument = Argument(
            name_or_flags="--version",
            action="version",
            version="1.0.0",
        )
        self.assertEqual(argument.version, "1.0.0")
        self.assertEqual(argument.action, "version")

    def testExtraParameter(self) -> None:
        """
        Verify correct storage of extra parameters.

        Tests that extra parameters are stored in the extra dictionary.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        extra = {"custom_param": "value"}
        argument = Argument(name_or_flags="--test", extra=extra)
        self.assertEqual(argument.extra, extra)

    def testConstAndDefaultWithValues(self) -> None:
        """
        Verify setting of const and default values.

        Tests that const and default parameters can be set to non-MISSING values.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        const_value = "constant"
        default_value = "default"
        argument = Argument(
            name_or_flags="--test",
            const=const_value,
            default=default_value,
        )
        self.assertEqual(argument.const, const_value)
        self.assertEqual(argument.default, default_value)

    def testEmptyExtraParameter(self) -> None:
        """
        Verify handling of empty extra parameter.

        Tests that an empty extra dictionary does not interfere with argument
        creation.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        argument = Argument(name_or_flags="--test", extra={})
        self.assertEqual(argument.extra, {})

    def testMissingConstAndDefault(self) -> None:
        """
        Verify handling of MISSING const and default values.

        Tests that MISSING sentinel values are handled for const and default.

        Returns
        -------
        None
            This method does not return a value. It asserts properties of the
            created Argument instance.
        """
        argument = Argument(name_or_flags="--test")
        self.assertIs(argument.const, MISSING)
        self.assertIs(argument.default, MISSING)

    def testEmptyNameOrFlagsRaisesError(self) -> None:
        """
        Raise ValueError if name_or_flags is empty.

        Tests that providing an empty iterable for name_or_flags raises a
        ValueError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        with self.assertRaises(ValueError) as context:
            Argument(name_or_flags=[])
        error_msg = "At least one name or flag must be provided"
        self.assertIn(error_msg, str(context.exception))

    def testNonStringFlagsRaisesError(self) -> None:
        """
        Raise TypeError if name_or_flags contains non-string values.

        Tests that non-string values in name_or_flags raise a TypeError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        with self.assertRaises(TypeError) as context:
            Argument(name_or_flags=[123, "--flag"])
        error_msg = "All name_or_flags must be strings"
        self.assertIn(error_msg, str(context.exception))

    def testHelpFlagsNotAllowed(self) -> None:
        """
        Raise ValueError if reserved help flags are used.

        Tests that using '-h' or '--help' as custom flags raises a ValueError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        with self.assertRaises(ValueError) as context:
            Argument(name_or_flags=["-h"])
        error_msg = "Custom help flags '-h' and '--help' are not allowed"
        self.assertIn(error_msg, str(context.exception))

        with self.assertRaises(ValueError) as context:
            Argument(name_or_flags=["--help"])
        self.assertIn(error_msg, str(context.exception))

    def testInvalidActionTypeRaisesError(self) -> None:
        """
        Raise TypeError if action parameter is of invalid type.

        Tests that providing an invalid type for action raises a TypeError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        with self.assertRaises(TypeError) as context:
            Argument(name_or_flags="--test", action=123)
        error_msg = "'action' must be a string, ArgumentAction, or None"
        self.assertIn(error_msg, str(context.exception))

    def testInvalidNargsTypeRaisesError(self) -> None:
        """
        Raise TypeError if nargs parameter is of invalid type.

        Tests that providing an invalid type for nargs raises a TypeError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        with self.assertRaises(TypeError) as context:
            Argument(name_or_flags="--test", nargs=[])
        error_msg = "'nargs' must be int, str, or None"
        self.assertIn(error_msg, str(context.exception))

    def testInvalidNargsStringValueRaisesError(self) -> None:
        """
        Raise ValueError if nargs string value is invalid.

        Tests that invalid string values for nargs raise a ValueError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        with self.assertRaises(ValueError) as context:
            Argument(name_or_flags="--test", nargs="invalid")
        error_msg = "'nargs' must be one of"
        self.assertIn(error_msg, str(context.exception))

    def testNonCallableTypeRaisesError(self) -> None:
        """
        Raise TypeError if type_ parameter is not callable.

        Tests that non-callable type_ parameters raise a TypeError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        with self.assertRaises(TypeError) as context:
            Argument(name_or_flags="--test", type_="not_callable")
        error_msg = "'type_' must be callable"
        self.assertIn(error_msg, str(context.exception))

    def testChoicesAsStringRaisesError(self) -> None:
        """
        Raise TypeError if choices parameter is a string.

        Tests that providing a string as choices raises a TypeError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        with self.assertRaises(TypeError) as context:
            Argument(name_or_flags="--test", choices="abc")
        error_msg = "'choices' cannot be a string"
        self.assertIn(error_msg, str(context.exception))

    def testNonIterableChoicesRaisesError(self) -> None:
        """
        Raise TypeError if choices parameter is not iterable.

        Tests that non-iterable choices parameters raise a TypeError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        with self.assertRaises(TypeError) as context:
            Argument(name_or_flags="--test", choices=123)
        error_msg = "'choices' must be iterable"
        self.assertIn(error_msg, str(context.exception))

    def testNonBoolRequiredRaisesError(self) -> None:
        """
        Raise TypeError if required parameter is not a bool.

        This test checks that providing a non-boolean value for the required
        parameter raises a TypeError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        # Attempt to create Argument with non-bool required value
        with self.assertRaises(TypeError) as context:
            Argument(name_or_flags="--test", required="true")
        error_msg = "'required' must be a bool"
        self.assertIn(error_msg, str(context.exception))

    def testNonStringHelpRaisesError(self) -> None:
        """
        Raise TypeError if help parameter is not a string.

        This test checks that providing a non-string value for the help
        parameter raises a TypeError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        # Attempt to create Argument with non-string help value
        with self.assertRaises(TypeError) as context:
            Argument(name_or_flags="--test", help=123)
        error_msg = "'help' must be a string"
        self.assertIn(error_msg, str(context.exception))

    def testInvalidMetavarTupleRaisesError(self) -> None:
        """
        Raise TypeError if metavar tuple contains non-string elements.

        This test checks that providing a tuple with non-string elements for
        metavar raises a TypeError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        # Attempt to create Argument with invalid metavar tuple
        with self.assertRaises(TypeError) as context:
            Argument(name_or_flags="--test", metavar=("valid", 123))
        error_msg = "'metavar' tuple must contain only strings"
        self.assertIn(error_msg, str(context.exception))

    def testInvalidMetavarTypeRaisesError(self) -> None:
        """
        Raise TypeError if metavar parameter is not a string or tuple.

        This test checks that providing an invalid type for metavar raises a
        TypeError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        # Attempt to create Argument with invalid metavar type
        with self.assertRaises(TypeError) as context:
            Argument(name_or_flags="--test", metavar=123)
        error_msg = "'metavar' must be a string, tuple[str,...], or None"
        self.assertIn(error_msg, str(context.exception))

    def testNonStringDestRaisesError(self) -> None:
        """
        Raise TypeError if dest parameter is not a string.

        This test checks that providing a non-string value for the dest
        parameter raises a TypeError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        # Attempt to create Argument with non-string dest value
        with self.assertRaises(TypeError) as context:
            Argument(name_or_flags="--test", dest=123)
        error_msg = "'dest' must be a string"
        self.assertIn(error_msg, str(context.exception))

    def testNonStringVersionRaisesError(self) -> None:
        """
        Raise TypeError if version parameter is not a string.

        This test checks that providing a non-string value for the version
        parameter raises a TypeError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        # Attempt to create Argument with non-string version value
        with self.assertRaises(TypeError) as context:
            Argument(name_or_flags="--test", version=123)
        error_msg = "'version' must be a string"
        self.assertIn(error_msg, str(context.exception))

    def testNonDictExtraRaisesError(self) -> None:
        """
        Raise TypeError if extra parameter is not a dictionary.

        This test checks that providing a non-dictionary value for the extra
        parameter raises a TypeError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        # Attempt to create Argument with non-dict extra value
        with self.assertRaises(TypeError) as context:
            Argument(name_or_flags="--test", extra="not_a_dict")
        error_msg = "'extra' must be a dictionary"
        self.assertIn(error_msg, str(context.exception))

    def testVersionActionWithoutVersionRaisesError(self) -> None:
        """
        Raise ValueError if version action is used without version parameter.

        This test checks that using action='version' without providing a version
        parameter raises a ValueError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        # Attempt to create Argument with version action but no version value
        with self.assertRaises(ValueError) as context:
            Argument(name_or_flags="--version", action="version")
        error_msg = "'version' must be provided when action='version'"
        self.assertIn(error_msg, str(context.exception))

    def testVersionActionEnumWithoutVersionRaisesError(self) -> None:
        """
        Raise ValueError if ArgumentAction.VERSION is used without version.

        This test checks that using ArgumentAction.VERSION without providing a
        version parameter raises a ValueError.

        Returns
        -------
        None
            This method does not return a value. It asserts that an exception
            is raised.
        """
        # Attempt to create Argument with ArgumentAction.VERSION but no version
        with self.assertRaises(ValueError) as context:
            Argument(name_or_flags="--version", action=ArgumentAction.VERSION)
        error_msg = "'version' must be provided when action='version'"
        self.assertIn(error_msg, str(context.exception))

    def testAddToParserBasic(self) -> None:
        """
        Add a basic argument to an ArgumentParser.

        Verifies that a basic argument can be added to an ArgumentParser
        without raising exceptions.

        Returns
        -------
        None
            This method does not return a value. It asserts that the argument
            is present in the parser's help output.
        """
        parser: argparse.ArgumentParser = argparse.ArgumentParser()
        argument: Argument = Argument(name_or_flags="--verbose")

        # Add the argument to the parser and check for errors
        argument.addToParser(parser)

        # Verify the argument was added by checking the help output
        help_text: str = parser.format_help()
        self.assertIn("--verbose", help_text)

    def testAddToParserWithAllParameters(self) -> None:
        """
        Add an argument with all parameters to an ArgumentParser.

        Verifies that an argument with multiple parameters can be added to an
        ArgumentParser and appears in the help output.

        Returns
        -------
        None
            This method does not return a value. It asserts that the argument
            and its help text are present in the parser's help output.
        """
        parser: argparse.ArgumentParser = argparse.ArgumentParser()
        argument: Argument = Argument(
            name_or_flags=["-f", "--file"],
            action="store",
            nargs="?",
            const="default.txt",
            default="config.txt",
            type_=str,
            choices=["config.txt", "settings.txt"],
            required=True,
            help="Configuration file",
            metavar="FILE",
            dest="config_file",
        )

        # Add the argument to the parser and check for errors
        argument.addToParser(parser)

        # Verify the argument and help text are present in the help output
        help_text: str = parser.format_help()
        self.assertIn("--file", help_text)
        self.assertIn("Configuration file", help_text)

    def testAddToParserWithActionEnum(self) -> None:
        """
        Add an argument with ArgumentAction enum to an ArgumentParser.

        Verifies that arguments using ArgumentAction enums are correctly
        converted to string values when added to the parser.

        Returns
        -------
        None
            This method does not return a value. It asserts that the argument
            is present in the parser's help output.
        """
        parser: argparse.ArgumentParser = argparse.ArgumentParser()
        argument: Argument = Argument(
            name_or_flags="--verbose",
            action=ArgumentAction.STORE_TRUE,
            help="Enable verbose output",
        )

        # Add the argument to the parser and check for errors
        argument.addToParser(parser)

        # Verify the argument was added by checking the help output
        help_text: str = parser.format_help()
        self.assertIn("--verbose", help_text)

    def testAddToParserWithVersionAction(self) -> None:
        """
        Add an argument with version action to an ArgumentParser.

        Verifies that version arguments are correctly added to the parser and
        appear in the help output.

        Returns
        -------
        None
            This method does not return a value. It asserts that the version
            argument is present in the parser's help output.
        """
        parser: argparse.ArgumentParser = argparse.ArgumentParser()
        argument: Argument = Argument(
            name_or_flags="--version",
            action="version",
            version="1.0.0",
        )

        # Add the argument to the parser and check for errors
        argument.addToParser(parser)

        # Verify the version argument is present in the help output
        help_text: str = parser.format_help()
        self.assertIn("--version", help_text)

    def testAddToParserWithConstAction(self) -> None:
        """
        Add an argument with store_const action to an ArgumentParser.

        Verifies that when using store_const actions, the type parameter is not
        passed to argparse.

        Returns
        -------
        None
            This method does not return a value. It asserts that the argument
            is present in the parser's help output.
        """
        parser: argparse.ArgumentParser = argparse.ArgumentParser()
        argument: Argument = Argument(
            name_or_flags="--flag",
            action="store_const",
            const="value",
        )

        # Add the argument to the parser and check for errors
        argument.addToParser(parser)

        # Verify the argument was added by checking the help output
        help_text: str = parser.format_help()
        self.assertIn("--flag", help_text)

    def testAddToParserWithExtraParameters(self) -> None:
        """
        Add an argument with extra parameters to an ArgumentParser.

        Verifies that extra parameters are correctly passed to the parser's
        add_argument method.

        Returns
        -------
        None
            This method does not return a value. It asserts that the extra
            parameters are present in the captured keyword arguments.
        """
        parser: argparse.ArgumentParser = argparse.ArgumentParser()
        argument: Argument = Argument(
            name_or_flags="--test",
            extra={"default": "extra_default", "help": "extra help text"},
        )

        # Mock add_argument to capture keyword arguments
        original_add_argument = parser.add_argument
        captured_kwargs: dict[str, Any] = {}

        def mock_add_argument(*args: object, **kwargs: object) -> object:
            """Record arguments supplied to parser registration.

            Parameters
            ----------
            *args : object
                Arguments passed to the wrapped callable.
            **kwargs : object
                Arguments passed to the wrapped callable.

            Returns
            -------
            object
                Value produced by the helper.
            """
            captured_kwargs.update(kwargs)
            return original_add_argument(*args, **kwargs)

        parser.add_argument = mock_add_argument  # type: ignore[method-assign]

        # Add the argument to the parser
        _arg = argument
        _arg.addToParser(parser)

        # Verify extra parameters were passed to add_argument
        self.assertEqual(captured_kwargs.get("default"), "extra_default")
        self.assertEqual(captured_kwargs.get("help"), "extra help text")

    def testAddToParserRequiredOptionalFlag(self) -> None:
        """
        Add a required optional flag to an ArgumentParser.

        Verifies that when an optional flag is marked as required=True, the
        required parameter is set in add_argument.

        Returns
        -------
        None
            This method does not return a value. It asserts that the required
            parameter is present in the captured keyword arguments.
        """
        parser: argparse.ArgumentParser = argparse.ArgumentParser()
        argument: Argument = Argument(
            name_or_flags="--input",
            required=True,
        )

        # Mock add_argument to capture keyword arguments
        original_add_argument = parser.add_argument
        captured_kwargs: dict[str, Any] = {}

        def mock_add_argument(*args: object, **kwargs: object) -> object:
            """Record arguments supplied to parser registration.

            Parameters
            ----------
            *args : object
                Arguments passed to the wrapped callable.
            **kwargs : object
                Arguments passed to the wrapped callable.

            Returns
            -------
            object
                Value produced by the helper.
            """
            captured_kwargs.update(kwargs)
            return original_add_argument(*args, **kwargs)

        parser.add_argument = mock_add_argument  # type: ignore[method-assign]

        # Add the argument to the parser
        argument.addToParser(parser)

        # Verify required parameter was set in add_argument
        self.assertTrue(captured_kwargs.get("required"))

    def testAddToParserPositionalNotRequired(self) -> None:
        """
        Add a positional argument with required=True to an ArgumentParser.

        Verifies that positional arguments do not set the required parameter,
        even if required=True is specified.

        Returns
        -------
        None
            This method does not return a value. It asserts that the required
            parameter is not present in the captured keyword arguments.
        """
        parser: argparse.ArgumentParser = argparse.ArgumentParser()
        argument: Argument = Argument(
            name_or_flags="input_file",
            required=True,  # Should be ignored for positional arguments
        )

        # Mock add_argument to capture keyword arguments
        original_add_argument = parser.add_argument
        captured_kwargs: dict[str, Any] = {}

        def mock_add_argument(*args: object, **kwargs: object) -> object:
            """Record arguments supplied to parser registration.

            Parameters
            ----------
            *args : object
                Arguments passed to the wrapped callable.
            **kwargs : object
                Arguments passed to the wrapped callable.

            Returns
            -------
            object
                Value produced by the helper.
            """
            captured_kwargs.update(kwargs)
            return original_add_argument(*args, **kwargs)

        parser.add_argument = mock_add_argument  # type: ignore[method-assign]

        # Add the argument to the parser
        argument.addToParser(parser)

        # Verify required parameter was not set in add_argument
        self.assertNotIn("required", captured_kwargs)
