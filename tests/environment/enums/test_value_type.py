from enum import Enum
from orionis.environment.enums import EnvironmentValueType
from orionis.environment.enums.value_type import (
    EnvironmentValueType as DirectEnvironmentValueType,
)
from orionis.test import TestCase

# Canonical member name to value mapping expected by the caster.
_EXPECTED_MEMBERS: dict[str, str] = {
    "BASE64": "base64",
    "PATH": "path",
    "STR": "str",
    "INT": "int",
    "FLOAT": "float",
    "BOOL": "bool",
    "LIST": "list",
    "DICT": "dict",
    "TUPLE": "tuple",
    "SET": "set",
}

# ---------------------------------------------------------------------------
# TestEnvironmentValueTypeMembers
# ---------------------------------------------------------------------------

class TestEnvironmentValueTypeMembers(TestCase):

    def testIsAnEnumeration(self) -> None:
        """Expose the supported value types as a standard enumeration.

        Validates that the type catalogue can be iterated and compared
        with the ordinary ``Enum`` semantics used across the framework.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(EnvironmentValueType, Enum))

    def testDeclaresExactlyTheDocumentedMembers(self) -> None:
        """Declare exactly the documented member name to value mapping.

        Validates that the ``"<type>:<value>"`` convention understood by
        the caster never drifts from the enumeration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        actual = {
            member.name: member.value for member in EnvironmentValueType
        }
        self.assertEqual(actual, _EXPECTED_MEMBERS)

    def testEveryValueIsAUniqueLowercaseString(self) -> None:
        """Keep every member value a unique lowercase string.

        Validates the prefix contract relied upon when parsing typed
        entries such as ``int:42`` from a ``.env`` file.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        values = [member.value for member in EnvironmentValueType]
        self.assertEqual(len(values), len(set(values)))
        for value in values:
            self.assertEqual(value, value.lower())

    def testIsReExportedByThePackage(self) -> None:
        """Re-export the enumeration from the enums package root.

        Validates that both documented import paths resolve to the very
        same object.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIs(EnvironmentValueType, DirectEnvironmentValueType)

# ---------------------------------------------------------------------------
# TestEnvironmentValueTypeLookup
# ---------------------------------------------------------------------------

class TestEnvironmentValueTypeLookup(TestCase):

    def testResolvesEveryMemberByValue(self) -> None:
        """Resolve every member through its canonical string value.

        Validates the call-style lookup used when a type hint arrives as
        a plain string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for name, value in _EXPECTED_MEMBERS.items():
            self.assertIs(
                EnvironmentValueType(value),
                EnvironmentValueType[name],
            )

    def testRejectsAnUnknownValue(self) -> None:
        """Raise ValueError when the requested value is unknown.

        Validates that an unsupported type hint cannot be silently
        coerced into a valid member.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            EnvironmentValueType("decimal")

    def testRejectsAnUnknownName(self) -> None:
        """Raise KeyError when the requested member name is unknown.

        Validates the name-based lookup used by the type validator when
        normalising uppercase hints.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(KeyError):
            EnvironmentValueType["DECIMAL"]

    def testLookupIsCaseSensitiveForValues(self) -> None:
        """Reject uppercase spellings of a member value.

        Validates that only the canonical lowercase form is accepted, so
        callers must normalise hints before the lookup.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            EnvironmentValueType("INT")
