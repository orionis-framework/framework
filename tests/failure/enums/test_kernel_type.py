# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from __future__ import annotations

from orionis.failure.enums.kernel_type import KernelContext
from orionis.test import TestCase


class TestKernelContextMembers(TestCase):
    def testConsoleMemberExists(self) -> None:
        """Confirm that CONSOLE is a member of KernelContext.

        Validates that the enumeration exposes the CONSOLE variant,
        which identifies command-line execution contexts.

        Returns
        -------
        None
            No return value.
        """
        self.assertIn("CONSOLE", KernelContext.__members__)

    def testHttpMemberExists(self) -> None:
        """Confirm that HTTP is a member of KernelContext.

        Validates that the enumeration exposes the HTTP variant,
        which identifies web-server execution contexts.

        Returns
        -------
        None
            No return value.
        """
        self.assertIn("HTTP", KernelContext.__members__)

    def testExactlyTwoMembers(self) -> None:
        """Verify exactly two members.

        KernelContext defines exactly two members.

        Validates that no variants have been silently added or removed,
        keeping the enumeration surface stable.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(len(KernelContext), 2)

    def testMembersAreDistinct(self) -> None:
        """Confirm that CONSOLE and HTTP have different values.

        Validates that auto() assigns a unique integer to each member
        so identity comparisons behave correctly.

        Returns
        -------
        None
            No return value.
        """
        self.assertNotEqual(KernelContext.CONSOLE, KernelContext.HTTP)

    def testMembersAreKernelContextInstances(self) -> None:
        """Confirm that each member is an instance of KernelContext.

        Validates that the enumeration members belong to the correct
        class, which is required for isinstance checks at runtime.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsInstance(KernelContext.CONSOLE, KernelContext)
        self.assertIsInstance(KernelContext.HTTP, KernelContext)


class TestKernelContextLookup(TestCase):
    def testLookupConsoleByName(self) -> None:
        """Retrieve CONSOLE via name-based enum lookup.

        Validates that ``KernelContext['CONSOLE']`` returns the expected
        member, exercising the standard enum subscript interface.

        Returns
        -------
        None
            No return value.
        """
        member = KernelContext["CONSOLE"]
        self.assertIs(member, KernelContext.CONSOLE)

    def testLookupHttpByName(self) -> None:
        """Retrieve HTTP via name-based enum lookup.

        Validates that ``KernelContext['HTTP']`` returns the expected
        member, exercising the standard enum subscript interface.

        Returns
        -------
        None
            No return value.
        """
        member = KernelContext["HTTP"]
        self.assertIs(member, KernelContext.HTTP)

    def testInvalidNameRaisesKeyError(self) -> None:
        """Raise KeyError for an unrecognised name lookup.

        Validates that subscripting KernelContext with a non-existent
        name signals the error rather than returning a fallback value.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(KeyError):
            _ = KernelContext["UNKNOWN"]

    def testNameAttribute(self) -> None:
        """Expose the correct name string on each member.

        Validates that the .name property on CONSOLE and HTTP matches
        the identifier used in source code.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(KernelContext.CONSOLE.name, "CONSOLE")
        self.assertEqual(KernelContext.HTTP.name, "HTTP")

    def testValueAttributeIsInt(self) -> None:
        """Expose integer values via auto() for each member.

        Validates that the .value attribute of every member is an integer,
        as expected from the enum.auto() assignment.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsInstance(KernelContext.CONSOLE.value, int)
        self.assertIsInstance(KernelContext.HTTP.value, int)
