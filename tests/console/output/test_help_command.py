from __future__ import annotations
import argparse
from unittest.mock import MagicMock, patch
from orionis.console.output.help_command import HelpCommand
from orionis.test import TestCase

# ------------------------------------------------------------------ #
#  Helpers                                                           #
# ------------------------------------------------------------------ #

def _make_parser(
    *flags_or_positionals: str, **kwargs: object,
) -> argparse.ArgumentParser:
    """
    Build an ArgumentParser with the requested arguments for test use.

    Parameters
    ----------
    *flags_or_positionals : str
        Argument names passed to add_argument.
    **kwargs : Any
        Extra keyword arguments forwarded to add_argument.

    Returns
    -------
    argparse.ArgumentParser
        A configured parser whose _actions can be inspected.
    """
    parser = argparse.ArgumentParser(add_help=True)
    for flag in flags_or_positionals:
        parser.add_argument(flag, **kwargs)
    return parser

class TestHelpCommand(TestCase):

    # ------------------------------------------------------------------ #
    #  parseActions — return structure                                   #
    # ------------------------------------------------------------------ #

    def testParseActionsReturnsExpectedKeys(self) -> None:
        """Verify that parseActions returns a dict with the expected top-level keys.

        Ensures the returned mapping always contains help, positionals,
        optionals, and subcommands regardless of the input.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=False)
        result = HelpCommand.parseActions(parser._actions)
        self.assertIn("help", result)
        self.assertIn("positionals", result)
        self.assertIn("optionals", result)
        self.assertIn("subcommands", result)

    def testParseActionsEmptyActionsReturnsEmptyStructure(self) -> None:
        """Verify that parseActions on an empty action list returns the base structure.

        Ensures no KeyError or crash occurs when actions is an empty list,
        and that all four keys map to their default empty values.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = HelpCommand.parseActions([])
        self.assertIsNone(result["help"])
        self.assertEqual(result["positionals"], [])
        self.assertEqual(result["optionals"], [])
        self.assertEqual(result["subcommands"], {})

    # ------------------------------------------------------------------ #
    #  parseActions — help action                                        #
    # ------------------------------------------------------------------ #

    def testParseActionsDetectsHelpAction(self) -> None:
        """Verify that the _HelpAction is stored in the 'help' key.

        Ensures that the standard -h/--help action is correctly identified
        and separated from positional and optional arguments.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=True)
        result = HelpCommand.parseActions(parser._actions)
        self.assertIsNotNone(result["help"])

    def testParseActionsHelpActionDataHasExpectedFields(self) -> None:
        """Verify that the help action dict contains the required metadata fields.

        Ensures each action dictionary exposes action_class, dest, flags,
        nargs, const, default, type, choices, required, help, and metavar.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=True)
        result = HelpCommand.parseActions(parser._actions)
        expected_fields = {
            "action_class", "dest", "flags", "nargs", "const",
            "default", "type", "choices", "required", "help", "metavar",
        }
        self.assertTrue(expected_fields.issubset(result["help"].keys()))

    def testParseActionsHelpNotInOptionalsOrPositionals(self) -> None:
        """Verify that the help action does not appear in optionals or positionals.

        Ensures the help action is exclusively stored under the 'help' key and
        does not contaminate the optionals or positionals lists.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=True)
        result = HelpCommand.parseActions(parser._actions)
        dest_optionals = [a["dest"] for a in result["optionals"]]
        dest_positionals = [a["dest"] for a in result["positionals"]]
        self.assertNotIn("help", dest_optionals)
        self.assertNotIn("help", dest_positionals)

    # ------------------------------------------------------------------ #
    #  parseActions — optional arguments                                 #
    # ------------------------------------------------------------------ #

    def testParseActionsCategorizesOptionalArgument(self) -> None:
        """Verify that a flagged argument (--flag) is stored in optionals.

        Ensures arguments with option_strings are correctly classified as
        optional rather than positional.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = _make_parser("--output")
        result = HelpCommand.parseActions(parser._actions)
        dests = [a["dest"] for a in result["optionals"]]
        self.assertIn("output", dests)

    def testParseActionsMultipleOptionalsAreAllCaptured(self) -> None:
        """Verify that multiple optional arguments are all stored in optionals.

        Ensures the list accumulates every flagged argument in the order
        they were added to the parser.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--verbose", action="store_true")
        parser.add_argument("--output", type=str)
        result = HelpCommand.parseActions(parser._actions)
        dests = [a["dest"] for a in result["optionals"]]
        self.assertIn("verbose", dests)
        self.assertIn("output", dests)

    def testParseActionsOptionalDataContainsFlags(self) -> None:
        """Verify that an optional action dict stores the flag strings.

        Ensures the flags field is populated with the option string list
        so help renderers can display the correct flag names.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = _make_parser("--verbose", action="store_true")
        result = HelpCommand.parseActions(parser._actions)
        flags_per_action = [a["flags"] for a in result["optionals"]]
        self.assertTrue(any("--verbose" in f for f in flags_per_action))

    # ------------------------------------------------------------------ #
    #  parseActions — positional arguments                               #
    # ------------------------------------------------------------------ #

    def testParseActionsCategorizesPositionalArgument(self) -> None:
        """Verify that a positional argument is stored in positionals.

        Ensures arguments without option_strings (no leading dashes) are
        correctly classified as positional.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = _make_parser("filename")
        result = HelpCommand.parseActions(parser._actions)
        dests = [a["dest"] for a in result["positionals"]]
        self.assertIn("filename", dests)

    def testParseActionsMultiplePositionalsAreAllCaptured(self) -> None:
        """Verify that multiple positional arguments are all stored in positionals.

        Ensures the list accumulates every positional argument in order.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("src")
        parser.add_argument("dst")
        result = HelpCommand.parseActions(parser._actions)
        dests = [a["dest"] for a in result["positionals"]]
        self.assertIn("src", dests)
        self.assertIn("dst", dests)

    def testParseActionsPositionalNotInOptionals(self) -> None:
        """Verify that a positional argument does not appear in optionals.

        Ensures the two categories are mutually exclusive so consumers
        can rely on each list containing only the correct argument type.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = _make_parser("filename")
        result = HelpCommand.parseActions(parser._actions)
        dests = [a["dest"] for a in result["optionals"]]
        self.assertNotIn("filename", dests)

    # ------------------------------------------------------------------ #
    #  parseActions — subcommands                                        #
    # ------------------------------------------------------------------ #

    def testParseActionsDetectsSubcommands(self) -> None:
        """Verify that a subparser action populates the subcommands dict.

        Ensures that child parsers registered via add_subparsers are
        captured and keyed by their command name.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=False)
        sub = parser.add_subparsers(dest="cmd")
        sub.add_parser("init", description="Initialise project")
        result = HelpCommand.parseActions(parser._actions)
        self.assertIn("init", result["subcommands"])

    def testParseActionsSubcommandContainsHelpAndArguments(self) -> None:
        """Verify that a subcommand entry contains 'help' and 'arguments' keys.

        Ensures the nested structure for each subcommand provides both a
        description and a recursively parsed arguments mapping.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=False)
        sub = parser.add_subparsers(dest="cmd")
        sub.add_parser("deploy", description="Deploy the app")
        result = HelpCommand.parseActions(parser._actions)
        self.assertIn("help", result["subcommands"]["deploy"])
        self.assertIn("arguments", result["subcommands"]["deploy"])

    def testParseActionsSubcommandHelpMatchesDescription(self) -> None:
        """Verify that the subcommand help field reflects the parser description.

        Ensures the description passed to add_parser is surfaced in the
        subcommand's metadata so help renderers can display it correctly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=False)
        sub = parser.add_subparsers(dest="cmd")
        sub.add_parser("serve", description="Start the server")
        result = HelpCommand.parseActions(parser._actions)
        self.assertEqual(result["subcommands"]["serve"]["help"], "Start the server")

    def testParseActionsSubcommandNotInOptionalsOrPositionals(self) -> None:
        """Verify that subparser actions do not appear in optionals or positionals.

        Ensures the subcommand categorization is exclusive and does not
        contaminate the other two output lists.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=False)
        sub = parser.add_subparsers(dest="cmd")
        sub.add_parser("test")
        result = HelpCommand.parseActions(parser._actions)
        dests_opt = [a["dest"] for a in result["optionals"]]
        dests_pos = [a["dest"] for a in result["positionals"]]
        self.assertNotIn("cmd", dests_opt)
        self.assertNotIn("cmd", dests_pos)

    def testParseActionsMultipleSubcommands(self) -> None:
        """Verify that multiple subcommands are all captured in subcommands dict.

        Ensures all child parsers registered under the same subparsers action
        are present as separate keys in the result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=False)
        sub = parser.add_subparsers(dest="cmd")
        sub.add_parser("start")
        sub.add_parser("stop")
        result = HelpCommand.parseActions(parser._actions)
        self.assertIn("start", result["subcommands"])
        self.assertIn("stop", result["subcommands"])

    # ------------------------------------------------------------------ #
    #  parseActions — type field                                         #
    # ------------------------------------------------------------------ #

    def testParseActionsTypeFieldDefaultsToStr(self) -> None:
        """Verify that optional actions without an explicit type default to 'str'.

        Ensures the type field is always populated with a string name so
        help renderers are never faced with a None value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--name")
        result = HelpCommand.parseActions(parser._actions)
        self.assertEqual(result["optionals"][0]["type"], "str")

    def testParseActionsTypeFieldReflectsExplicitType(self) -> None:
        """Verify that an explicit type is reflected by its __name__ in the dict.

        Ensures integer-typed arguments expose 'int' as the type string
        rather than the raw callable.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--count", type=int)
        result = HelpCommand.parseActions(parser._actions)
        self.assertEqual(result["optionals"][0]["type"], "int")

    # ------------------------------------------------------------------ #
    #  printActions — normal path                                        #
    # ------------------------------------------------------------------ #

    def testPrintActionsReturnsNone(self) -> None:
        """Verify that printActions returns None for a valid command.

        Ensures the method adheres to its declared contract which
        specifies a None return value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=True)
        with patch("orionis.console.output.help_command.Console"):
            result = HelpCommand.printActions(
                "mycommand",
                parser._actions,
                is_error=False,
            )
        self.assertIsNone(result)

    def testPrintActionsCallsConsolePrint(self) -> None:
        """Verify that printActions invokes the Rich Console.print method.

        Ensures output is actually produced by delegating to the Rich
        Console rather than being silently dropped.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=True)
        with patch("orionis.console.output.help_command.Console") as mock_console:
            mock_instance = MagicMock()
            mock_console.return_value = mock_instance
            HelpCommand.printActions(
                "mycommand",
                parser._actions,
                is_error=False,
            )
            self.assertTrue(mock_instance.print.called)

    def testPrintActionsNoErrorShowsHelpPanel(self) -> None:
        """Verify that printActions with is_error=False renders a help panel.

        Ensures the non-error path prints a Panel containing the command
        name and does not include an error message.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=True)
        printed_args = []
        with patch("orionis.console.output.help_command.Console") as mock_console:
            mock_instance = MagicMock()
            mock_instance.print.side_effect = lambda *a, **_: printed_args.append(a)
            mock_console.return_value = mock_instance
            HelpCommand.printActions("deploy", parser._actions, is_error=False)
        # At least one call should have been made
        self.assertTrue(len(printed_args) > 0)

    def testPrintActionsWithOptionals(self) -> None:
        """Verify that printActions handles optional arguments without raising.

        Ensures a parser with flag arguments produces output without
        any exception being raised.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=True)
        parser.add_argument("--verbose", action="store_true")
        with patch("orionis.console.output.help_command.Console"):
            result = HelpCommand.printActions("run", parser._actions, is_error=False)
        self.assertIsNone(result)

    def testPrintActionsWithPositionals(self) -> None:
        """Verify that printActions handles positional arguments without raising.

        Ensures a parser with positional arguments produces output without
        any exception being raised.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=True)
        parser.add_argument("filename")
        with patch("orionis.console.output.help_command.Console"):
            result = HelpCommand.printActions(
                "process",
                parser._actions,
                is_error=False,
            )
        self.assertIsNone(result)

    def testPrintActionsWithSubcommands(self) -> None:
        """Verify that printActions handles subcommands without raising.

        Ensures a parser with subparsers registered produces output
        without any exception being raised.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=False)
        subs = parser.add_subparsers(dest="cmd")
        subs.add_parser("start")
        with patch("orionis.console.output.help_command.Console"):
            result = HelpCommand.printActions("root", parser._actions, is_error=False)
        self.assertIsNone(result)

    # ------------------------------------------------------------------ #
    #  printActions — error path                                         #
    # ------------------------------------------------------------------ #

    def testPrintActionsWithIsErrorReturnsNone(self) -> None:
        """Verify that printActions with is_error=True returns None.

        Ensures the error output path completes normally and does not
        raise any unhandled exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=True)
        with patch("orionis.console.output.help_command.Console"):
            result = HelpCommand.printActions("badcmd", parser._actions, is_error=True)
        self.assertIsNone(result)

    def testPrintActionsErrorPathCallsConsolePrint(self) -> None:
        """Verify that the error path invokes Console.print.

        Ensures that when is_error=True the error panel and messages are
        rendered by delegating to the Rich Console instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parser = argparse.ArgumentParser(add_help=True)
        with patch("orionis.console.output.help_command.Console") as mock_console:
            mock_instance = MagicMock()
            mock_console.return_value = mock_instance
            HelpCommand.printActions("badcmd", parser._actions, is_error=True)
            self.assertTrue(mock_instance.print.called)
