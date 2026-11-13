# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect date configuration and formatting across invalid inputs and zones."""

from datetime import UTC, datetime
from unittest.mock import patch
import pendulum
from orionis.support.facades.datetime import DateTime
from orionis.test import TestCase


class TestDateTimeRegressions(TestCase):
    """Exercise configured date behavior without leaking process defaults."""

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
