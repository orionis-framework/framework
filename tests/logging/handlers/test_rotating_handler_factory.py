import logging
from datetime import time
from logging import FileHandler, Handler
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.logging.handlers.advanced_rotating_file_handler import (
    AdvancedRotatingFileHandler,
)
from orionis.logging.handlers.chunked_suffix_resolver import ChunkedSuffixResolver
from orionis.logging.handlers.daily_suffix_resolver import DailySuffixResolver
from orionis.logging.handlers.hourly_suffix_resolver import HourlySuffixResolver
from orionis.logging.handlers.monthly_suffix_resolver import MonthlySuffixResolver
from orionis.logging.handlers.rotating_handler_factory import RotatingHandlerFactory
from orionis.logging.handlers.weekly_suffix_resolver import WeeklySuffixResolver
from orionis.test import TestCase

# Size unit used by the chunked channel configuration.
_MEGABYTE = 1024 * 1024

# Path fallback applied when the channel declares none.
_DEFAULT_PATH = "storage/logs/default.log"

class TestRotatingHandlerFactory(TestCase):

    def setUp(self) -> None:
        """Create a temporary application root and the handler registry."""
        self._tmp = TemporaryDirectory(ignore_cleanup_errors=True)
        self._handlers: list[Handler] = []

    def tearDown(self) -> None:
        """Close every built handler and delete the temporary root."""
        for handler in self._handlers:
            handler.close()
        self._tmp.cleanup()

    def _createHandler(self, channel: str, config: dict) -> Handler | None:
        """Build a handler through the factory and track it for teardown."""
        handler = RotatingHandlerFactory.createHandler(
            channel_name=channel,
            channel_config=config,
            app_root=self._tmp.name,
        )
        if handler is not None:
            self._handlers.append(handler)
        return handler

    def _createRotating(
        self,
        channel: str,
        config: dict,
    ) -> AdvancedRotatingFileHandler:
        """Build a rotating handler and fail when another type is produced."""
        handler = self._createHandler(channel, config)
        if not isinstance(handler, AdvancedRotatingFileHandler):
            self.fail(f"The '{channel}' channel did not build a rotating handler.")
        return handler

    def _createFile(self, config: dict) -> FileHandler:
        """Build the stack handler and fail when another type is produced."""
        handler = self._createHandler("stack", config)
        if not isinstance(handler, FileHandler):
            self.fail("The 'stack' channel did not build a plain file handler.")
        return handler

    def testStackChannelBuildsAPlainFileHandler(self) -> None:
        """
        Build a non rotating handler for the stack channel.

        Validates that the most common channel avoids the rotation machinery.
        """
        handler = self._createFile({"path": "storage/logs/stack.log"})
        self.assertNotIsInstance(handler, AdvancedRotatingFileHandler)

    def testStackChannelCreatesTheParentDirectory(self) -> None:
        """
        Create the directory tree required by the stack log file.

        Validates that a nested path never prevents the handler from opening
        its file later on.
        """
        self._createFile({"path": "storage/logs/nested/deep/stack.log"})
        expected = Path(self._tmp.name) / "storage" / "logs" / "nested" / "deep"
        self.assertTrue(expected.is_dir())

    def testStackChannelDelaysTheFileCreation(self) -> None:
        """
        Postpone the creation of the file until the first record.

        Validates that configuring a channel never produces an empty log file.
        """
        self._createFile({"path": "storage/logs/stack.log"})
        self.assertFalse((Path(self._tmp.name) / "storage/logs/stack.log").exists())

    def testStackChannelAppliesTheConfiguredLevel(self) -> None:
        """
        Apply the configured level to the stack handler.

        Validates that the channel threshold reaches the built handler.
        """
        handler = self._createFile(
            {"path": "storage/logs/stack.log", "level": logging.WARNING},
        )
        self.assertEqual(handler.level, logging.WARNING)

    def testDefaultPathIsUsedWhenTheChannelDeclaresNone(self) -> None:
        """
        Fall back to the default log path when none is configured.

        Validates the path applied to incomplete channel configurations.
        """
        self._createFile({})
        self.assertTrue((Path(self._tmp.name) / _DEFAULT_PATH).parent.is_dir())

    def testDefaultLevelIsInfoWhenTheChannelDeclaresNone(self) -> None:
        """
        Fall back to INFO when the channel declares no level.

        Validates the threshold applied to incomplete channel configurations.
        """
        self.assertEqual(self._createFile({}).level, logging.INFO)

    def testHourlyChannelUsesAnHourlyResolver(self) -> None:
        """
        Attach the hourly rotation strategy to the hourly channel.

        Validates the mapping between the channel name and its resolver.
        """
        handler = self._createRotating(
            "hourly",
            {"path": "storage/logs/hourly_{suffix}.log"},
        )
        self.assertIsInstance(handler.suffix_resolver, HourlySuffixResolver)

    def testHourlyChannelKeepsTheConfiguredRetention(self) -> None:
        """
        Keep as many files as the configured retention in hours.

        Validates that the retention option drives the backup count.
        """
        handler = self._createRotating(
            "hourly",
            {"path": "storage/logs/hourly_{suffix}.log", "retention_hours": 6},
        )
        self.assertEqual(handler.backup_count, 6)

    def testHourlyChannelDefaultsToADayOfRetention(self) -> None:
        """
        Keep a full day of files when no retention is configured.

        Validates the default retention of the hourly channel.
        """
        handler = self._createRotating(
            "hourly",
            {"path": "storage/logs/hourly_{suffix}.log"},
        )
        self.assertEqual(handler.backup_count, 24)

    def testDailyChannelUsesADailyResolver(self) -> None:
        """
        Attach the daily rotation strategy to the daily channel.

        Validates the mapping between the channel name and its resolver.
        """
        handler = self._createRotating(
            "daily",
            {"path": "storage/logs/daily_{suffix}.log"},
        )
        self.assertIsInstance(handler.suffix_resolver, DailySuffixResolver)

    def testDailyChannelForwardsTheRotationTime(self) -> None:
        """
        Forward the configured rotation time to the daily resolver.

        Validates that the moment of the day declared by the channel is
        honoured.
        """
        handler = self._createRotating(
            "daily",
            {"path": "storage/logs/daily_{suffix}.log", "at": time(3, 30)},
        )
        resolver = handler.suffix_resolver
        if not isinstance(resolver, DailySuffixResolver):
            self.fail("The 'daily' channel did not build a daily resolver.")
        self.assertEqual(resolver.at_time, time(3, 30))

    def testDailyChannelDefaultsToAWeekOfRetention(self) -> None:
        """
        Keep a full week of files when no retention is configured.

        Validates the default retention of the daily channel.
        """
        handler = self._createRotating(
            "daily",
            {"path": "storage/logs/daily_{suffix}.log"},
        )
        self.assertEqual(handler.backup_count, 7)

    def testWeeklyChannelUsesAWeeklyResolver(self) -> None:
        """
        Attach the weekly rotation strategy to the weekly channel.

        Validates the mapping between the channel name and its resolver.
        """
        handler = self._createRotating(
            "weekly",
            {"path": "storage/logs/weekly_{suffix}.log"},
        )
        self.assertIsInstance(handler.suffix_resolver, WeeklySuffixResolver)

    def testWeeklyChannelDefaultsToFourWeeksOfRetention(self) -> None:
        """
        Keep four weeks of files when no retention is configured.

        Validates the default retention of the weekly channel.
        """
        handler = self._createRotating(
            "weekly",
            {"path": "storage/logs/weekly_{suffix}.log"},
        )
        self.assertEqual(handler.backup_count, 4)

    def testMonthlyChannelUsesAMonthlyResolver(self) -> None:
        """
        Attach the monthly rotation strategy to the monthly channel.

        Validates the mapping between the channel name and its resolver.
        """
        handler = self._createRotating(
            "monthly",
            {"path": "storage/logs/monthly_{suffix}.log"},
        )
        self.assertIsInstance(handler.suffix_resolver, MonthlySuffixResolver)

    def testMonthlyChannelKeepsTheConfiguredRetention(self) -> None:
        """
        Keep as many files as the configured retention in months.

        Validates that the retention option drives the backup count.
        """
        handler = self._createRotating(
            "monthly",
            {"path": "storage/logs/monthly_{suffix}.log", "retention_months": 12},
        )
        self.assertEqual(handler.backup_count, 12)

    def testChunkedChannelUsesAChunkedResolver(self) -> None:
        """
        Attach the size based rotation strategy to the chunked channel.

        Validates the mapping between the channel name and its resolver.
        """
        handler = self._createRotating(
            "chunked",
            {"path": "storage/logs/chunked_{suffix}.log"},
        )
        self.assertIsInstance(handler.suffix_resolver, ChunkedSuffixResolver)

    def testChunkedChannelConvertsMegabytesIntoBytes(self) -> None:
        """
        Express the configured chunk size in bytes.

        Validates the unit conversion applied to the size threshold.
        """
        handler = self._createRotating(
            "chunked",
            {"path": "storage/logs/chunked_{suffix}.log", "mb_size": 3},
        )
        self.assertEqual(handler.max_bytes, 3 * _MEGABYTE)

    def testChunkedChannelDefaultsToTenMegabytes(self) -> None:
        """
        Rotate every ten megabytes when no size is configured.

        Validates the default chunk size of the channel.
        """
        handler = self._createRotating(
            "chunked",
            {"path": "storage/logs/chunked_{suffix}.log"},
        )
        self.assertEqual(handler.max_bytes, 10 * _MEGABYTE)

    def testChunkedChannelDefaultsToFiveFiles(self) -> None:
        """
        Keep five chunks when no file count is configured.

        Validates the default retention of the chunked channel.
        """
        handler = self._createRotating(
            "chunked",
            {"path": "storage/logs/chunked_{suffix}.log"},
        )
        self.assertEqual(handler.backup_count, 5)

    def testChunkedChannelCompressesRotatedFiles(self) -> None:
        """
        Compress every rotated chunk.

        Validates that size based rotation always archives the closed files.
        """
        handler = self._createRotating(
            "chunked",
            {"path": "storage/logs/chunked_{suffix}.log"},
        )
        self.assertTrue(handler.compress_rotated)

    def testRotatingChannelsReceiveTheApplicationRoot(self) -> None:
        """
        Resolve rotating log paths against the application root.

        Validates that relative paths configured by the channel are anchored
        to the project directory.
        """
        handler = self._createRotating(
            "daily",
            {"path": "storage/logs/daily_{suffix}.log"},
        )
        self.assertEqual(handler.app_root, Path(self._tmp.name))

    def testRotatingChannelsApplyTheConfiguredLevel(self) -> None:
        """
        Apply the configured level to rotating handlers.

        Validates that the channel threshold reaches every handler type.
        """
        handler = self._createRotating(
            "daily",
            {"path": "storage/logs/daily_{suffix}.log", "level": logging.ERROR},
        )
        self.assertEqual(handler.level, logging.ERROR)

    def testUnsupportedChannelBuildsNoHandler(self) -> None:
        """
        Build no handler for an unsupported channel name.

        Validates that the caller decides how to react to an unknown channel
        instead of receiving an exception.
        """
        self.assertIsNone(self._createHandler("unknown", {}))
