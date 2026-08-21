from datetime import UTC, datetime, time, timedelta, timezone
from orionis.logging.handlers.weekly_suffix_resolver import WeeklySuffixResolver
from orionis.test import TestCase

# Extreme offsets used to prove the guard protecting the rotation schedule.
_FAR_EAST = timezone(timedelta(hours=14))
_FAR_WEST = timezone(timedelta(hours=-12))

def _make_resolver(
    at_time: time | None = None,
    tz: timezone = UTC,
) -> WeeklySuffixResolver:
    """Return a weekly resolver pinned to the given timezone."""
    resolver = WeeklySuffixResolver(at_time=at_time)
    resolver.tz = tz
    return resolver

class TestWeeklySuffixResolverSuffix(TestCase):

    def testSuffixUsesTheIsoWeekPattern(self) -> None:
        """
        Build the suffix from the ISO year and week of the given datetime.

        Validates the naming scheme applied to weekly log files.
        """
        moment = datetime(2025, 1, 6, 12, 0, 0, tzinfo=UTC)
        self.assertEqual(_make_resolver().getSuffix(dt=moment), "2025-week02")

    def testSuffixFollowsTheIsoYearOnTheYearBoundary(self) -> None:
        """
        Report the ISO year instead of the calendar year at the boundary.

        Validates that the last days of December belong to the first week of
        the following ISO year.
        """
        moment = datetime(2025, 12, 29, 12, 0, 0, tzinfo=UTC)
        self.assertEqual(_make_resolver().getSuffix(dt=moment), "2026-week01")

    def testSuffixDefaultsToTheCurrentWeek(self) -> None:
        """
        Resolve the current week when no datetime is supplied.

        Validates that the handler can request a suffix without tracking time
        by itself.
        """
        self.assertRegex(_make_resolver().getSuffix(), r"^\d{4}-week\d{2}$")

class TestWeeklySuffixResolverRotation(TestCase):

    def testDefaultRotationTimeIsMidnight(self) -> None:
        """
        Rotate at midnight when no time is configured.

        Validates the default applied to channels declaring no rotation time.
        """
        self.assertEqual(_make_resolver().at_time, time(0, 0, 0))

    def testNextRotationIsTheUpcomingMonday(self) -> None:
        """
        Schedule the next rotation on the upcoming Monday.

        Validates the weekly schedule computed from a mid week moment.
        """
        current = datetime(2025, 4, 9, 14, 0, 0, tzinfo=UTC)
        self.assertEqual(
            _make_resolver().getNextRotationTime(current),
            datetime(2025, 4, 14, 0, 0, 0, tzinfo=UTC),
        )

    def testNextRotationSkipsAFullWeekOnMonday(self) -> None:
        """
        Schedule the next rotation a full week ahead when already on Monday.

        Validates that the rotation of the current week is never repeated.
        """
        current = datetime(2025, 4, 14, 14, 0, 0, tzinfo=UTC)
        self.assertEqual(
            _make_resolver().getNextRotationTime(current),
            datetime(2025, 4, 21, 0, 0, 0, tzinfo=UTC),
        )

    def testNextRotationHonoursTheConfiguredTime(self) -> None:
        """
        Apply the configured rotation time to the upcoming Monday.

        Validates that a non midnight schedule is preserved.
        """
        current = datetime(2025, 4, 9, 3, 0, 0, tzinfo=UTC)
        self.assertEqual(
            _make_resolver(time(6, 0, 0)).getNextRotationTime(current),
            datetime(2025, 4, 14, 6, 0, 0, tzinfo=UTC),
        )

    def testNextRotationSkipsAWeekWhenTheTimezoneShiftsItBackwards(self) -> None:
        """
        Add a week when the computed rotation is not in the future.

        Validates the guard protecting a schedule built with a resolver
        timezone far ahead of the timezone of the supplied datetime.
        """
        resolver = _make_resolver(tz=_FAR_EAST)
        current = datetime(2025, 4, 13, 23, 0, 0, tzinfo=_FAR_WEST)
        result = resolver.getNextRotationTime(current)
        self.assertEqual(result, datetime(2025, 4, 21, 0, 0, 0, tzinfo=_FAR_EAST))
        self.assertGreater(result, current)
