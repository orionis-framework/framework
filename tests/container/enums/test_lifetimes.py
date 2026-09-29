from __future__ import annotations
from enum import Enum
from orionis.test import TestCase
from orionis.container.enums.lifetimes import Lifetime

_EXPECTED_VALUES = {
    "TRANSIENT": 1,
    "SINGLETON": 2,
    "SCOPED": 3,
}

class TestLifetimeMembers(TestCase):

    def testEnumDeclaresExactlyTheExpectedMembers(self) -> None:
        """
        Declare exactly the three documented lifecycle members.

        Catches both silent removals and undocumented additions to the
        lifetime catalogue.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(
            set(Lifetime.__members__),
            set(_EXPECTED_VALUES),
        )

    def testMembersCarryTheirDeclaredAutoValues(self) -> None:
        """
        Assign the sequential ``auto()`` values expected by the container.

        Returns
        -------
        None
            This method does not return a value.
        """
        actual = {member.name: member.value for member in Lifetime}
        self.assertEqual(actual, _EXPECTED_VALUES)

    def testMembersAreEnumSingletons(self) -> None:
        """
        Expose every member as a hashable Enum singleton.

        Returns
        -------
        None
            This method does not return a value.
        """
        for member in Lifetime:
            self.assertIsInstance(member, Enum)
            self.assertIs(Lifetime[member.name], member)
            self.assertIs(Lifetime(member.value), member)
        self.assertEqual(len({member: member.name for member in Lifetime}), 3)

class TestLifetimeLookup(TestCase):

    def testUnknownValueRaisesValueError(self) -> None:
        """
        Raise ValueError when constructing a Lifetime from an unknown value.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(ValueError):
            Lifetime(0)

    def testUnknownNameRaisesKeyError(self) -> None:
        """
        Raise KeyError when looking a Lifetime up by an unknown name.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(KeyError):
            _ = Lifetime["UNKNOWN"]

class TestLifetimeRepresentation(TestCase):

    def testTextualFormsExposeTheMemberName(self) -> None:
        """
        Include the member name in both ``str()`` and ``repr()`` output.

        Returns
        -------
        None
            This method does not return a value.
        """
        for member in Lifetime:
            self.assertIn(member.name, str(member))
            self.assertIn(member.name, repr(member))
            self.assertIn(Lifetime.__name__, repr(member))
