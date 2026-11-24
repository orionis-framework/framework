# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect size rotation and timezone-aware calendar boundaries."""

import gzip
import logging
from datetime import UTC, datetime, time, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zoneinfo import ZoneInfo

from orionis.logging.handlers.advanced_rotating_file_handler import (
    AdvancedRotatingFileHandler,
)
from orionis.logging.handlers.chunked_suffix_resolver import ChunkedSuffixResolver
from orionis.logging.handlers.daily_suffix_resolver import DailySuffixResolver
from orionis.logging.handlers.hourly_suffix_resolver import HourlySuffixResolver
from orionis.logging.handlers.monthly_suffix_resolver import MonthlySuffixResolver
from orionis.logging.handlers.weekly_suffix_resolver import WeeklySuffixResolver
from orionis.support.facades.datetime import DateTime
from orionis.test import TestCase


class TestRotationRegressions(TestCase):
    """
    Verify log rotation at size and local calendar boundaries.

    Exercise the file handler and its built-in suffix resolvers with fixed instants.
    """

    def testDelayedRecordsPreserveEarlierCompressedDays(self) -> None:
        """
        Verify that a late record can reopen an archived day.

        Read both days after a second rotation to confirm their full contents.
        """
        directory = Path(self.enterContext(TemporaryDirectory()))
        resolver = DailySuffixResolver()
        resolver.tz = UTC
        handler = AdvancedRotatingFileHandler(
            "day_{suffix}.log",
            resolver,
            compress_rotated=True,
            app_root=str(directory),
        )
        self.addCleanup(handler.close)
        for index, day in enumerate((1, 2, 1, 2)):
            record = logging.makeLogRecord({"msg": str(index)})
            record.created = datetime(2026, 6, day, 12, tzinfo=UTC).timestamp()
            handler.handle(record)
        with gzip.open(
            directory / "day_2026-06-01.log.gz", "rt", encoding="utf-8",
        ) as archived:
            self.assertEqual(archived.read(), "0\n2\n")
        second_day = directory / "day_2026-06-02.log"
        self.assertEqual(second_day.read_text(encoding="utf-8"), "1\n3\n")

    def testSuffixesFollowAppTimezoneAndKeepBothRepeatedHours(self) -> None:
        """
        Verify that each resolver converts explicit instants to the application zone.

        Check that the repeated local hour receives two distinct filenames.
        """
        utc = datetime(2026, 6, 1, 2, tzinfo=UTC)
        resolvers = (
            (HourlySuffixResolver(), "2026-05-31_21"),
            (DailySuffixResolver(), "2026-05-31"),
            (WeeklySuffixResolver(), "2026-week22"),
            (MonthlySuffixResolver(), "2026-05"),
            (ChunkedSuffixResolver(), "20260531_210000_0001"),
        )
        with patch.object(
            DateTime, "getZoneInfo", return_value=ZoneInfo("America/Bogota"),
        ):
            for resolver, suffix in resolvers:
                with self.subTest(resolver=type(resolver).__name__):
                    self.assertEqual(resolver.getSuffix(utc), suffix)

        hourly = resolvers[0][0]
        with patch.object(
            DateTime, "getZoneInfo", return_value=ZoneInfo("America/New_York"),
        ):
            first = datetime(2026, 11, 1, 5, 30, tzinfo=UTC)
            second = first + timedelta(hours=1)
            self.assertEqual(hourly.getSuffix(first), "2026-11-01_01")
            self.assertEqual(hourly.getSuffix(second), "2026-11-01_01_-0500")
            self.assertEqual(
                hourly.getNextRotationTime(first).astimezone(UTC),
                second.replace(minute=0),
            )

    def testChunkedFilesRotateOnlyAfterReachingTheSizeLimit(self) -> None:
        """
        Verify that a size-based log chunk stays open until it reaches its limit.

        Check the byte count and archived lines after the following record rotates it.
        """
        directory = Path(self.enterContext(TemporaryDirectory()))
        moment = datetime(2025, 4, 9, 14, 30, tzinfo=UTC)
        handler = AdvancedRotatingFileHandler(
            "chunk_{suffix}.log",
            ChunkedSuffixResolver(),
            max_bytes=20,
            backup_count=5,
            compress_rotated=True,
            app_root=str(directory),
        )
        self.addCleanup(handler.close)

        def emit(message: str) -> None:
            """
            Write one record with a fixed creation timestamp.

            Parameters
            ----------
            message : str
                Text whose encoded bytes contribute to the chunk size.
            """
            record = logging.LogRecord(
                "rotation", logging.INFO, "", 1, message, (), None,
            )
            record.created = moment.timestamp()
            handler.handle(record)

        emit("first")
        initial = Path(handler.current_path)
        emit("second")
        self.assertEqual(Path(handler.current_path), initial)
        self.assertEqual(list(directory.glob("*.gz")), [])
        emit("1234567")
        self.assertEqual(handler.file_size, 21)
        self.assertEqual(Path(handler.current_path), initial)
        emit("next")
        self.assertNotEqual(Path(handler.current_path), initial)
        self.assertFalse(initial.exists())
        with gzip.open(str(initial) + ".gz", "rt", encoding="utf-8") as archive:
            self.assertEqual(archive.read(), "first\nsecond\n1234567\n")

    def testCalendarRotationUsesAnUpcomingTimeInTheCurrentPeriod(self) -> None:
        """Use today's scheduled boundary before advancing a full week or month."""
        for resolver_type, current, expected in (
            (
                DailySuffixResolver,
                datetime(2025, 4, 14, 8, tzinfo=UTC),
                datetime(2025, 4, 14, 10, tzinfo=UTC),
            ),
            (
                WeeklySuffixResolver,
                datetime(2025, 4, 14, 8, tzinfo=UTC),
                datetime(2025, 4, 14, 10, tzinfo=UTC),
            ),
            (
                MonthlySuffixResolver,
                datetime(2025, 4, 1, 8, tzinfo=UTC),
                datetime(2025, 4, 1, 10, tzinfo=UTC),
            ),
        ):
            for value in (current, current.replace(tzinfo=None)):
                with self.subTest(resolver=resolver_type.__name__, current=value):
                    resolver = resolver_type(at_time=time(10))
                    resolver.tz = UTC
                    self.assertEqual(resolver.getNextRotationTime(value), expected)
        resolver = DailySuffixResolver(at_time=time(22))
        resolver.tz = UTC
        current = datetime(2025, 4, 14, 1, tzinfo=timezone(timedelta(hours=5)))
        with self.subTest(resolver="DailySuffixResolver", current=current):
            self.assertEqual(
                resolver.getNextRotationTime(current),
                datetime(2025, 4, 13, 22, tzinfo=UTC),
            )
