from __future__ import annotations
from enum import Enum
from orionis.console.enums.actions import ArgumentAction
from orionis.test import TestCase

class TestArgumentAction(TestCase):

    # ------------------------------------------------------------------ #
    #  Type & membership                                                 #
    # ------------------------------------------------------------------ #

    def testIsEnumSubclass(self) -> None:
        """Verify that ArgumentAction is a subclass of Enum.

        Ensures the class participates in Python's standard enum
        machinery and supports membership, iteration, and value lookup.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(ArgumentAction, Enum))

    def testHasExpectedMemberCount(self) -> None:
        """Verify that ArgumentAction defines exactly nine members.

        Ensures no members have been accidentally added or removed from
        the enum definition.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(len(ArgumentAction), 9)

    def testAllMembersHaveStringValues(self) -> None:
        """Verify that every member value is a string.

        Ensures the enum can be passed directly to argparse without
        type conversion.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for member in ArgumentAction:
            self.assertIsInstance(member.value, str)

    # ------------------------------------------------------------------ #
    #  Individual member values                                          #
    # ------------------------------------------------------------------ #

    def testStoreMemberValue(self) -> None:
        """Verify that STORE has the value 'store'.

        Ensures the string passed to argparse for the store action
        is correct.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ArgumentAction.STORE.value, "store")

    def testStoreConstMemberValue(self) -> None:
        """Verify that STORE_CONST has the value 'store_const'.

        Ensures the string passed to argparse for the store_const action
        is correct.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ArgumentAction.STORE_CONST.value, "store_const")

    def testStoreTrueMemberValue(self) -> None:
        """Verify that STORE_TRUE has the value 'store_true'.

        Ensures the string passed to argparse for the store_true action
        is correct.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ArgumentAction.STORE_TRUE.value, "store_true")

    def testStoreFalseMemberValue(self) -> None:
        """Verify that STORE_FALSE has the value 'store_false'.

        Ensures the string passed to argparse for the store_false action
        is correct.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ArgumentAction.STORE_FALSE.value, "store_false")

    def testAppendMemberValue(self) -> None:
        """Verify that APPEND has the value 'append'.

        Ensures the string passed to argparse for the append action
        is correct.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ArgumentAction.APPEND.value, "append")

    def testAppendConstMemberValue(self) -> None:
        """Verify that APPEND_CONST has the value 'append_const'.

        Ensures the string passed to argparse for the append_const action
        is correct.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ArgumentAction.APPEND_CONST.value, "append_const")

    def testCountMemberValue(self) -> None:
        """Verify that COUNT has the value 'count'.

        Ensures the string passed to argparse for the count action
        is correct.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ArgumentAction.COUNT.value, "count")

    def testHelpMemberValue(self) -> None:
        """Verify that HELP has the value 'help'.

        Ensures the string passed to argparse for the help action
        is correct.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ArgumentAction.HELP.value, "help")

    def testVersionMemberValue(self) -> None:
        """Verify that VERSION has the value 'version'.

        Ensures the string passed to argparse for the version action
        is correct.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ArgumentAction.VERSION.value, "version")

    # ------------------------------------------------------------------ #
    #  Lookup                                                            #
    # ------------------------------------------------------------------ #

    def testLookupByValue(self) -> None:
        """Verify that members can be retrieved by their string value.

        Ensures ArgumentAction('store') returns ArgumentAction.STORE,
        enabling reverse lookup from argparse action strings.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIs(ArgumentAction("store"), ArgumentAction.STORE)

    def testLookupInvalidValueRaisesValueError(self) -> None:
        """Verify that looking up an unknown value raises ValueError.

        Ensures the enum rejects any string not defined as a member
        value, preventing silent misconfigurations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            ArgumentAction("not_an_action")

    # ------------------------------------------------------------------ #
    #  Uniqueness                                                        #
    # ------------------------------------------------------------------ #

    def testAllValuesAreUnique(self) -> None:
        """Verify that no two members share the same string value.

        Ensures each argparse action string maps to exactly one enum
        member, avoiding ambiguity in lookups.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        values = [m.value for m in ArgumentAction]
        self.assertEqual(len(values), len(set(values)))

    def testAllNamesAreUnique(self) -> None:
        """Verify that no two members share the same name.

        Ensures the enum definition is self-consistent and no accidental
        aliasing has been introduced.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        names = [m.name for m in ArgumentAction]
        self.assertEqual(len(names), len(set(names)))
