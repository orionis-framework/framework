from datetime import UTC, datetime, timedelta, timezone
from orionis.logging.handlers.hourly_suffix_resolver import HourlySuffixResolver
from orionis.test import TestCase

# Fixed offset used to prove the resolver normalises the timezone.
_AHEAD = timezone(timedelta(hours=5))

def _make_resolver() -> HourlySuffixResolver:
    """Return an hourly resolver pinned to UTC."""
    resolver = HourlySuffixResolver()
    resolver.tz = UTC
    return resolver

class TestHourlySuffixResolverSuffix(TestCase):

    def testSuffixUsesTheHourlyPattern(self) -> None:
        """
        Build the suffix from the date and the hour of the given datetime.

        Validates the naming scheme applied to hourly log files.
        """
        moment = datetime(2025, 4, 9, 14, 30, 45, tzinfo=UTC)
        self.assertEqual(_make_resolver().getSuffix(dt=moment), "2025-04-09_14")

    def testSuffixDefaultsToTheCurrentHour(self) -> None:
        """
        Resolve the current hour when no datetime is supplied.

        Validates that the handler can request a suffix without tracking time
        by itself.
        """
        self.assertRegex(
            _make_resolver().getSuffix(),
            r"^\d{4}-\d{2}-\d{2}_\d{2}$",
        )

class TestHourlySuffixResolverRotation(TestCase):

    def testNextRotationIsTheStartOfTheFollowingHour(self) -> None:
        """
        Schedule the next rotation at the top of the next hour.

        Validates that minutes, seconds and microseconds are discarded.
        """
        current = datetime(2025, 4, 9, 14, 30, 45, tzinfo=UTC)
        self.assertEqual(
            _make_resolver().getNextRotationTime(current),
            datetime(2025, 4, 9, 15, 0, 0, tzinfo=UTC),
        )

    def testNextRotationCrossesTheDayBoundary(self) -> None:
        """
        Move to the next day when rotating during the last hour.

        Validates the boundary between two consecutive days.
        """
        current = datetime(2025, 4, 9, 23, 59, 59, tzinfo=UTC)
        self.assertEqual(
            _make_resolver().getNextRotationTime(current),
            datetime(2025, 4, 10, 0, 0, 0, tzinfo=UTC),
        )

    def testNextRotationAdoptsTheResolverTimezone(self) -> None:
        """
        Express the next rotation in the timezone of the resolver.

        Validates that a datetime built in another timezone is relabelled
        instead of being converted.
        """
        current = datetime(2025, 4, 9, 14, 30, 0, tzinfo=_AHEAD)
        self.assertEqual(
            _make_resolver().getNextRotationTime(current),
            datetime(2025, 4, 9, 15, 0, 0, tzinfo=UTC),
        )
