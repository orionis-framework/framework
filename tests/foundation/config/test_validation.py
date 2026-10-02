from enum import Enum
from orionis.foundation.config.validation import normalize_enum
from orionis.test import TestCase

class _Mode(Enum):
    PRIMARY = "fast-mode"
    ALIAS = PRIMARY
    FAST_MODE = "other"
    NUMBER = 0
    EMPTY = ""

class TestEnumNormalization(TestCase):
    """Validate indexed enum lookups without changing accepted inputs."""

    def testNamesValuesAliasesAndWhitespaceRemainAccepted(self) -> None:
        """
        Normalize members, names, aliases and numeric string representations.

        Returns
        -------
        None
            Assertions preserve all supported input representations.
        """
        inputs = (
            (_Mode.PRIMARY, "fast-mode"),
            (" Primary ", "fast-mode"),
            ("ALIAS", "fast-mode"),
            (" FAST-MODE ", "fast-mode"),
            ("fast_mode", "other"),
            ("0", 0),
            ("empty", ""),
            ("", ""),
        )
        self.assertEqual(
            [normalize_enum(value, _Mode, "mode") for value, _ in inputs],
            [expected for _, expected in inputs],
        )

    def testFirstDeclaredMatchWinsNameValueCollisions(self) -> None:
        """
        Preserve declaration precedence when a value matches another member name.

        Returns
        -------
        None
            The earlier value takes precedence over the later name.
        """
        choices = Enum("Choices", {"FIRST": "second", "SECOND": "last"})
        self.assertEqual(normalize_enum("second", choices, "choice"), "second")

    def testDifferentEnumClassesKeepSeparateIndexes(self) -> None:
        """
        Resolve identical input names independently for each enum class.

        Returns
        -------
        None
            Cached tables never leak values between enum types.
        """
        first = Enum("Choices", {"VALUE": "first"})
        second = Enum("Choices", {"VALUE": "second"})
        self.assertEqual(normalize_enum("value", first, "choice"), "first")
        self.assertEqual(normalize_enum("value", second, "choice"), "second")

    def testAddedNameAliasesInvalidateTheIndex(self) -> None:
        """
        Recognize aliases added after the initial lookup on Python 3.14.

        Returns
        -------
        None
            A changed member count selects a fresh normalized table.
        """
        choices = Enum("Choices", {"FIRST": "value"})
        self.assertEqual(normalize_enum("first", choices, "choice"), "value")
        choices.FIRST._add_alias_("SECOND")
        self.assertEqual(normalize_enum("second", choices, "choice"), "value")

    def testInvalidInputsKeepTheirErrorTypesAndFieldNames(self) -> None:
        """
        Reject unsupported types and report the current field for invalid values.

        Returns
        -------
        None
            Errors retain their public types and contextual field names.
        """
        with self.assertRaisesRegex(TypeError, "'mode' must be a string"):
            normalize_enum(0, _Mode, "mode")
        with self.assertRaisesRegex(ValueError, "'first' must be one of"):
            normalize_enum("unknown", _Mode, "first")
        with self.assertRaisesRegex(ValueError, "'second' must be one of"):
            normalize_enum("unknown", _Mode, "second")

    def testMutableEnumValuesKeepTheirCurrentStringRepresentation(self) -> None:
        """
        Observe changed enum values instead of retaining stale string matches.

        Returns
        -------
        None
            Mutable values remain readable and obsolete representations fail.
        """
        choices = Enum("MutableChoices", {"VALUES": [1]})
        self.assertIs(normalize_enum("[1]", choices, "choice"), choices.VALUES.value)
        choices.VALUES.value.append(2)
        self.assertIs(
            normalize_enum("[1, 2]", choices, "choice"), choices.VALUES.value,
        )
        with self.assertRaises(ValueError):
            normalize_enum("[1]", choices, "choice")
