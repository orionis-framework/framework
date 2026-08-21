from datetime import UTC, datetime, time
from orionis.logging.handlers.daily_suffix_resolver import DailySuffixResolver
from orionis.test import TestCase

def _make_resolver(at_time: time | None = None) -> DailySuffixResolver:
    """Return a daily resolver pinned to UTC."""
    resolver = DailySuffixResolver(at_time=at_time)
    resolver.tz = UTC
    return resolver

class TestDailySuffixResolverSuffix(TestCase):

    def testSuffixUsesTheDailyPattern(self) -> None:
        """
        Build the suffix from the date of the given datetime.

        Validates the naming scheme applied to daily log files.
        """
        moment = datetime(2025, 3, 31, 10, 0, 0, tzinfo=UTC)
        self.assertEqual(_make_resolver().getSuffix(dt=moment), "2025-03-31")

    def testSuffixDefaultsToTheCurrentDate(self) -> None:
        """
        Resolve the current date when no datetime is supplied.

        Validates that the handler can request a suffix without tracking time
        by itself.
        """
        self.assertRegex(_make_resolver().getSuffix(), r"^\d{4}-\d{2}-\d{2}$")

class TestDailySuffixResolverRotation(TestCase):

    def testDefaultRotationTimeIsMidnight(self) -> None:
        """
        Rotate at midnight when no time is configured.

        Validates the default applied to channels declaring no rotation time.
        """
        self.assertEqual(_make_resolver().at_time, time(0, 0, 0))

    def testConfiguredRotationTimeIsPreserved(self) -> None:
        """
        Keep the rotation time declared by the channel.

        Validates that the configured moment of the day drives the schedule.
        """
        self.assertEqual(_make_resolver(time(18, 0, 0)).at_time, time(18, 0, 0))

    def testNextRotationStaysOnTheSameDayWhenTheTimeIsAhead(self) -> None:
        """
        Schedule the rotation later on the same day when it is still ahead.

        Validates that no extra day is added when the configured time has not
        been reached yet.
        """
        current = datetime(2025, 4, 9, 14, 30, 0, tzinfo=UTC)
        self.assertEqual(
            _make_resolver(time(18, 0, 0)).getNextRotationTime(current),
            datetime(2025, 4, 9, 18, 0, 0, tzinfo=UTC),
        )

    def testNextRotationMovesToTheNextDayWhenTheTimePassed(self) -> None:
        """
        Schedule the rotation on the following day once the time passed.

        Validates the shift applied when the configured moment is already
        behind.
        """
        current = datetime(2025, 4, 9, 14, 30, 0, tzinfo=UTC)
        self.assertEqual(
            _make_resolver().getNextRotationTime(current),
            datetime(2025, 4, 10, 0, 0, 0, tzinfo=UTC),
        )

    def testNextRotationMovesToTheNextDayOnAnExactMatch(self) -> None:
        """
        Schedule the rotation on the following day at the exact boundary.

        Validates that a rotation happening right now is never scheduled
        twice.
        """
        current = datetime(2025, 4, 9, 0, 0, 0, tzinfo=UTC)
        self.assertEqual(
            _make_resolver().getNextRotationTime(current),
            datetime(2025, 4, 10, 0, 0, 0, tzinfo=UTC),
        )
