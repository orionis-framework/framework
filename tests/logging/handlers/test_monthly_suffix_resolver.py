from datetime import UTC, datetime, time
from orionis.logging.handlers.monthly_suffix_resolver import MonthlySuffixResolver
from orionis.test import TestCase

def _make_resolver(at_time: time | None = None) -> MonthlySuffixResolver:
    """Return a monthly resolver pinned to UTC."""
    resolver = MonthlySuffixResolver(at_time=at_time)
    resolver.tz = UTC
    return resolver

class TestMonthlySuffixResolverSuffix(TestCase):

    def testSuffixUsesTheMonthlyPattern(self) -> None:
        """
        Build the suffix from the year and month of the given datetime.

        Validates the naming scheme applied to monthly log files.
        """
        moment = datetime(2025, 3, 15, 10, 0, 0, tzinfo=UTC)
        self.assertEqual(_make_resolver().getSuffix(dt=moment), "2025-03")

    def testSuffixDefaultsToTheCurrentMonth(self) -> None:
        """
        Resolve the current month when no datetime is supplied.

        Validates that the handler can request a suffix without tracking time
        by itself.
        """
        self.assertRegex(_make_resolver().getSuffix(), r"^\d{4}-\d{2}$")

class TestMonthlySuffixResolverRotation(TestCase):

    def testDefaultRotationTimeIsMidnight(self) -> None:
        """
        Rotate at midnight when no time is configured.

        Validates the default applied to channels declaring no rotation time.
        """
        self.assertEqual(_make_resolver().at_time, time(0, 0, 0))

    def testNextRotationIsTheFirstDayOfTheFollowingMonth(self) -> None:
        """
        Schedule the next rotation on the first day of the next month.

        Validates the monthly schedule computed from a mid month moment.
        """
        current = datetime(2025, 3, 15, 12, 0, 0, tzinfo=UTC)
        self.assertEqual(
            _make_resolver().getNextRotationTime(current),
            datetime(2025, 4, 1, 0, 0, 0, tzinfo=UTC),
        )

    def testNextRotationWrapsDecemberToJanuary(self) -> None:
        """
        Schedule the next rotation on the first day of the following year.

        Validates the year boundary handled separately from the other months.
        """
        current = datetime(2025, 12, 20, 8, 0, 0, tzinfo=UTC)
        self.assertEqual(
            _make_resolver().getNextRotationTime(current),
            datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
        )

    def testNextRotationHonoursTheConfiguredTime(self) -> None:
        """
        Apply the configured rotation time to the first day of the month.

        Validates that a non midnight schedule is preserved.
        """
        current = datetime(2025, 5, 10, 0, 0, 0, tzinfo=UTC)
        self.assertEqual(
            _make_resolver(time(3, 30, 0)).getNextRotationTime(current),
            datetime(2025, 6, 1, 3, 30, 0, tzinfo=UTC),
        )

    def testNextRotationIsAlwaysInTheFuture(self) -> None:
        """
        Schedule the next rotation after the supplied moment.

        Validates the invariant on the last instant of a long month.
        """
        current = datetime(2025, 8, 31, 23, 59, 59, tzinfo=UTC)
        self.assertGreater(_make_resolver().getNextRotationTime(current), current)
