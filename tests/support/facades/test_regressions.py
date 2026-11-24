# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect date configuration and formatting across invalid inputs and zones."""

from datetime import UTC, datetime
from unittest.mock import patch
import pendulum
from orionis.support.facades.datetime import DateTime
from orionis.test import TestCase


class TestDateTimeRegressions(TestCase):
    """
    Exercise date parsing, conversion, and formatting across timezones.

    Each test restores the facade settings it changes.
    """

    def setUp(self) -> None:
        """Restore facade and Pendulum defaults after each scenario."""
        self.addCleanup(pendulum.set_locale, pendulum.get_locale())
        for name in ("_timezone", "_locale", "_zoneinfo_cache"):
            value = getattr(DateTime, name)
            self.addCleanup(setattr, DateTime, name, value)
        DateTime._zoneinfo_cache = {}
        DateTime._loadConfig(timezone_name="America/Bogota", locale="es")

    def testInvalidTimezonePreservesConfiguration(self) -> None:
        """Reject an unknown zone with the documented error and retain state."""
        zone = DateTime.getZoneInfo()
        with self.assertRaisesRegex(ValueError, "Invalid timezone"):
            DateTime._setTimezone("Invalid/Timezone_XXXX")
        self.assertEqual(DateTime.getTimezone(), "America/Bogota")
        self.assertIs(DateTime.getZoneInfo(), zone)

    def testInvalidLocalePreservesConfiguration(self) -> None:
        """Keep both locale settings when Pendulum rejects a new locale."""
        with self.assertRaises(ValueError):
            DateTime._setLocale("invalid_locale_xxxx")
        self.assertEqual(DateTime.getLocale(), "es")
        self.assertEqual(pendulum.get_locale(), "es")

    def testIsTodayUsesConfiguredCalendarDay(self) -> None:
        """Compare timezone-aware values against today's configured calendar date."""
        today = pendulum.datetime(2026, 1, 1, tz="America/Bogota")
        with patch(
            "orionis.support.facades.datetime.pendulum.today",
            return_value=today,
        ):
            self.assertTrue(
                DateTime.isToday(pendulum.datetime(2026, 1, 2, 2, tz="UTC")),
            )
            self.assertFalse(
                DateTime.isToday(pendulum.datetime(2026, 1, 2, 6, tz="UTC")),
            )

    def testFormatLocalConvertsZoneAndUsesConfiguredLocale(self) -> None:
        """Format equivalent inputs in the configured zone and locale."""
        instant = pendulum.datetime(2026, 1, 2, 2, tz="UTC")
        pendulum.set_locale("en")
        for value in (instant, datetime(2026, 1, 2, 2, tzinfo=UTC)):
            with self.subTest(value=value):
                self.assertEqual(
                    DateTime.formatLocal(value, "YYYY-MM-DD HH:mm MMMM"),
                    "2026-01-01 21:00 enero",
                )
        with patch.object(
            DateTime,
            "now",
            return_value=instant.in_timezone(
                "America/Bogota",
            ),
        ):
            self.assertEqual(DateTime.formatLocal(format_string="MMMM"), "enero")

    def testLocalInputAndExplicitOffsetsAcrossConstructors(self) -> None:
        """
        Check local input and explicit offsets across constructors.

        Returns
        -------
        None
            Verify wall times in Bogotá, offset conversion, and duration rejection.
        """
        wall_time = "2026-01-15T00:30:00"
        for value in (
            DateTime.parse(wall_time),
            DateTime.fromFormat(wall_time, "YYYY-MM-DDTHH:mm:ss"),
            DateTime.convertToLocal(wall_time),
            DateTime.convertToLocal(datetime.fromisoformat(wall_time)),
        ):
            self.assertEqual(value.isoformat(), "2026-01-15T00:30:00-05:00")
        for value in (
            DateTime.parse(wall_time + "Z"),
            DateTime.fromFormat(wall_time + "+00:00", "YYYY-MM-DDTHH:mm:ssZ"),
        ):
            self.assertEqual(value.isoformat(), "2026-01-14T19:30:00-05:00")
        with self.assertRaises(TypeError):
            DateTime.parse("P2D")

    def testPartialDatesUseLocalCalendarAndKeepTimeOffsets(self) -> None:
        """
        Check how partial dates use a fixed local reference.

        Returns
        -------
        None
            Verify the calendar date and UTC offset for ISO and flexible inputs.
        """
        reference = pendulum.datetime(2030, 1, 1, 10, tz="America/Bogota")
        with patch.object(DateTime, "now", return_value=reference):
            self.assertEqual(
                DateTime.parse("01:30:00Z").isoformat(), "2029-12-31T20:30:00-05:00",
            )
            self.assertEqual(
                DateTime.parse("8:30 PM", strict=False).isoformat(),
                "2030-01-01T20:30:00-05:00",
            )
            self.assertEqual(DateTime.parse("January 7", strict=False).year, 2030)

    def testUnixFormatTokensAreAbsoluteAndNaiveFoldsArePreserved(self) -> None:
        """
        Check Unix timestamps and repeated wall times.

        Returns
        -------
        None
            Verify epoch units, explicit folds, and the default first occurrence.
        """
        for text, fmt in (("1", "X"), ("1000", "x")):
            self.assertEqual(DateTime.fromFormat(text, fmt).timestamp(), 1)
        timezone = "America/New_York"
        for fold, offset in ((0, "-04:00"), (1, "-05:00")):
            moment = pendulum.naive(2026, 11, 1, 1, 30, fold=fold)
            local = DateTime.fromDatetime(moment, timezone)
            self.assertTrue(local.isoformat().endswith(offset))
        for moment in (
            DateTime.fromFormat("2026-11-01 01:30", "YYYY-MM-DD HH:mm", timezone),
            DateTime.parse("2026-11-01T01:30", timezone),
            DateTime.datetime(2026, 11, 1, 1, 30, tz=timezone),
            DateTime.fromDatetime(DateTime.naive(2026, 11, 1, 1, 30), timezone),
        ):
            self.assertEqual(moment.isoformat(), "2026-11-01T01:30:00-04:00")

    def testBoundariesUseSelectedCalendarForAnExplicitInstant(self) -> None:
        """
        Check calendar boundaries for an explicit instant.

        Returns
        -------
        None
            Verify each boundary and the weekend predicate in the selected zone.
        """
        instant = pendulum.datetime(2026, 1, 1, 2, tz="UTC")
        for unit in ("day", "week", "month", "year"):
            for direction in ("start", "end"):
                boundary = getattr(DateTime, direction + "Of" + unit.title())
                for tz in (None, "Asia/Tokyo"):
                    local = instant.in_timezone(tz or "America/Bogota")
                    expected = getattr(local, direction + "_of")(unit)
                    with self.subTest(unit=unit, direction=direction, tz=tz):
                        self.assertEqual(
                            boundary(instant, tz).isoformat(), expected.isoformat(),
                        )
        saturday = pendulum.datetime(2026, 1, 17, 2, tz="UTC")
        self.assertFalse(DateTime.isWeekend(saturday))

    def testPastAndFutureOrderRepeatedWallHoursByInstant(self) -> None:
        """
        Check past and future predicates during a repeated hour.

        Returns
        -------
        None
            Verify that the two offsets of the same wall time retain their order.
        """
        DateTime._setTimezone("America/New_York")
        first = DateTime.parse("2026-11-01T01:30:00-04:00")
        second = DateTime.parse("2026-11-01T01:30:00-05:00")
        with patch.object(DateTime, "now", return_value=first.in_timezone("UTC")):
            self.assertTrue(DateTime.isFuture(second))
        with patch.object(DateTime, "now", return_value=second.in_timezone("UTC")):
            self.assertTrue(DateTime.isPast(first))
