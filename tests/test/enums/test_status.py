from orionis.test import TestCase
from orionis.test.enums.status import TestStatus

# Canonical catalogue of statuses published by the enumeration.
_EXPECTED_MEMBERS: frozenset[str] = frozenset({
    "PASSED",
    "FAILED",
    "ERRORED",
    "SKIPPED",
})

class TestTestStatusMembers(TestCase):

    def testPassedMemberExists(self) -> None:
        """
        Confirm the PASSED member belongs to the enumeration.

        Validates that the successful outcome is published as a
        first-class member of TestStatus.
        """
        self.assertIn(TestStatus.PASSED, TestStatus)

    def testFailedMemberExists(self) -> None:
        """
        Confirm the FAILED member belongs to the enumeration.

        Validates that the assertion-failure outcome is published as a
        first-class member of TestStatus.
        """
        self.assertIn(TestStatus.FAILED, TestStatus)

    def testErroredMemberExists(self) -> None:
        """
        Confirm the ERRORED member belongs to the enumeration.

        Validates that the unexpected-exception outcome is published as
        a first-class member of TestStatus.
        """
        self.assertIn(TestStatus.ERRORED, TestStatus)

    def testSkippedMemberExists(self) -> None:
        """
        Confirm the SKIPPED member belongs to the enumeration.

        Validates that the intentionally-not-executed outcome is
        published as a first-class member of TestStatus.
        """
        self.assertIn(TestStatus.SKIPPED, TestStatus)

    def testEnumerationExposesExactlyFourMembers(self) -> None:
        """
        Confirm the enumeration publishes exactly four members.

        Validates that no undocumented status has been added to the
        public contract consumed by the result processor.
        """
        self.assertEqual({member.name for member in TestStatus}, _EXPECTED_MEMBERS)

class TestTestStatusValues(TestCase):

    def testMemberNamesMatchValues(self) -> None:
        """
        Confirm every member name equals its underlying string value.

        Validates the naming contract relied upon when statuses are
        serialised into cached JSON reports.
        """
        for member in TestStatus:
            self.assertEqual(member.name, member.value)

    def testMembersAreStringInstances(self) -> None:
        """
        Confirm every member is also a plain string instance.

        Validates that TestStatus derives from StrEnum so members can be
        rendered directly by the console reporter.
        """
        for member in TestStatus:
            self.assertIsInstance(member, str)

    def testMemberComparesEqualToPlainString(self) -> None:
        """
        Compare a member with its equivalent plain string successfully.

        Validates the StrEnum equality contract used by dictionary
        lookups keyed by status.
        """
        self.assertEqual(TestStatus.PASSED, "PASSED")

    def testMemberRendersAsPlainString(self) -> None:
        """
        Render a member as its bare value when converted to text.

        Validates that formatting a status never leaks the enumeration
        prefix into console output.
        """
        self.assertEqual(f"{TestStatus.ERRORED}", "ERRORED")

    def testMemberSupportsStringMethods(self) -> None:
        """
        Apply a string method directly to an enumeration member.

        Validates that members behave like strings, which the reporter
        relies on when centring status labels.
        """
        self.assertEqual(TestStatus.FAILED.center(8), " FAILED ")

class TestTestStatusLookup(TestCase):

    def testLookupByValueReturnsMember(self) -> None:
        """
        Retrieve a member from its string value.

        Validates the standard enumeration value lookup used when
        rebuilding statuses from persisted reports.
        """
        self.assertIs(TestStatus("FAILED"), TestStatus.FAILED)

    def testLookupByUnknownValueRaisesValueError(self) -> None:
        """
        Raise ValueError when the requested value is unknown.

        Validates that an unsupported status cannot be silently
        materialised from arbitrary text.
        """
        with self.assertRaises(ValueError):
            TestStatus("UNKNOWN")

    def testLookupByNameReturnsMember(self) -> None:
        """
        Retrieve a member through the name-based access syntax.

        Validates that statuses can be resolved by identifier as well as
        by value.
        """
        self.assertIs(TestStatus["SKIPPED"], TestStatus.SKIPPED)

    def testLookupByUnknownNameRaisesKeyError(self) -> None:
        """
        Raise KeyError when the requested member name is unknown.

        Validates that name-based access does not fabricate members for
        undefined identifiers.
        """
        with self.assertRaises(KeyError):
            TestStatus["UNKNOWN"]

    def testMembersUsableAsDictionaryKeys(self) -> None:
        """
        Use members as dictionary keys interchangeably with strings.

        Validates the hashing contract exploited by the summary panel,
        which counts results in a status-keyed dictionary.
        """
        counters: dict[str, int] = {TestStatus.PASSED: 1}
        self.assertEqual(counters["PASSED"], 1)
