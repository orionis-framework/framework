# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect size rotation and timezone-aware calendar boundaries."""

import gzip
import logging
from datetime import UTC, datetime, time, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from orionis.logging.handlers.advanced_rotating_file_handler import (
    AdvancedRotatingFileHandler,
)
from orionis.logging.handlers.chunked_suffix_resolver import ChunkedSuffixResolver
from orionis.logging.handlers.daily_suffix_resolver import DailySuffixResolver
from orionis.logging.handlers.monthly_suffix_resolver import MonthlySuffixResolver
from orionis.logging.handlers.weekly_suffix_resolver import WeeklySuffixResolver
from orionis.test import TestCase


class TestRotationRegressions(TestCase):
    """Exercise real handlers and resolvers with controlled input times."""

    def testChunkedFilesRotateOnlyAfterReachingTheSizeLimit(self) -> None:
        """Retain one chunk until its recorded bytes reach the configured limit."""
        directory = Path(self.enterContext(TemporaryDirectory()))
        moment = datetime(2025, 4, 9, 14, 30, tzinfo=UTC)
        clock = self.enterContext(
            patch("orionis.logging.handlers.chunked_suffix_resolver.datetime"),
        )
        clock.now.return_value = moment
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
            """Deliver a real record through the handler's public entry point.

            Parameters
            ----------
            message : str
                Text whose encoded bytes contribute to chunk size.
            """
            handler.handle(
                logging.LogRecord("rotation", logging.INFO, "", 1, message, (), None),
            )

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
