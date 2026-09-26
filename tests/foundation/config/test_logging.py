from datetime import time

from orionis.foundation.config.logging import (
    Chunked,
    Daily,
    Hourly,
    Level,
    Monthly,
    Stack,
    Weekly,
)
from tests.foundation.config.support import ConfigurationTestCase


class TestLoggingConfiguration(ConfigurationTestCase):
    def testAllChannelsNormalizeTheSameLevelRepresentations(self) -> None:
        """Match numeric, enum, and string log levels across every channel."""
        for cls in (Stack, Hourly, Daily, Weekly, Monthly, Chunked):
            for level in Level:
                for value in (level, level.value, level.name.lower()):
                    with self.subTest(channel=cls.__name__, level=value):
                        self.assertEqual(cls(level=value).level, level.value)

    def testInvalidLevelsAreRejectedConsistently(self) -> None:
        """Reject unknown names and numeric levels without losing type errors."""
        for cls in (Stack, Hourly, Daily, Weekly, Monthly, Chunked):
            for value in (True, None, "invalid", -1):
                with (
                    self.subTest(channel=cls.__name__, level=value),
                    self.assertRaises((TypeError, ValueError)),
                ):
                    cls(level=value)

    def testDailyRotationTimeAcceptsItsDocumentedStringForm(self) -> None:
        """Parse daily rotation strings and preserve validation exception causes."""
        self.assertEqual(Daily(at="12:30:00").at, time(12, 30))
        with self.assertRaises(ValueError) as failure:
            Daily(at="25:00:00")
        self.assertIsInstance(failure.exception.__cause__, ValueError)
