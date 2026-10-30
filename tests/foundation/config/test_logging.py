from datetime import time
from typing import Self
from config.logging import BootstrapLogging
from orionis.foundation.config.logging import (
    Chunked,
    Daily,
    Hourly,
    Level,
    Logging,
    Monthly,
    Stack,
    Weekly,
)
from orionis.foundation.config.logging.validators import IsValidLevel, IsValidPath
from tests.foundation.config.test_environment import ConfigurationTestCase

class TestLoggingConfiguration(ConfigurationTestCase):

    def testQueueCapacityIsExplicitAndValidatedInBothLayers(self: Self) -> None:
        """Read queue capacity lazily and reject invalid admission limits.

        Returns
        -------
        None
            Verify opt-in defaults and strict environment-backed configuration.
        """
        for entity in (Logging, BootstrapLogging):
            self.assertEqual(entity().queue_capacity, 0)
        self.environment.values["LOG_QUEUE_CAPACITY"] = 128
        for entity in (Logging, BootstrapLogging):
            self.assertEqual(entity().queue_capacity, 128)
            for value in (-1, True, "128", None):
                with self.assertRaises(ValueError):
                    entity(queue_capacity=value)

    def testCallableLevelValidationStillReturnsNone(self: Self) -> None:
        """Keep validation-only calls distinct from numeric normalization.

        Returns
        -------
        None
            Validation returns None while normalization returns the numeric level.
        """
        for value in (Level.INFO, Level.INFO.value, " info "):
            self.assertIsNone(IsValidLevel(value))
            self.assertEqual(IsValidLevel.normalize(value), Level.INFO.value)

    def testStatelessValidatorsDoNotHaveInstanceDictionaries(self: Self) -> None:
        """Keep shared logging validators free of mutable instance attributes.

        Returns
        -------
        None
            Both validator singletons use empty slots.
        """
        self.assertFalse(hasattr(IsValidLevel, "__dict__"))
        self.assertFalse(hasattr(IsValidPath, "__dict__"))

    def testAllChannelsNormalizeTheSameLevelRepresentations(self: Self) -> None:
        """Match numeric, enum, and string log levels across every channel.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for cls in (Stack, Hourly, Daily, Weekly, Monthly, Chunked):
            for level in Level:
                for value in (level, level.value, level.name.lower()):
                    with self.subTest(channel=cls.__name__, level=value):
                        self.assertEqual(cls(level=value).level, level.value)

    def testInvalidLevelsAreRejectedConsistently(self: Self) -> None:
        """Reject unknown names and numeric levels without losing type errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for cls in (Stack, Hourly, Daily, Weekly, Monthly, Chunked):
            for value in (True, None, "invalid", -1):
                with (
                    self.subTest(channel=cls.__name__, level=value),
                    self.assertRaises((TypeError, ValueError)),
                ):
                    cls(level=value)

    def testDailyRotationTimeAcceptsItsDocumentedStringForm(self: Self) -> None:
        """Parse daily rotation strings and preserve validation exception causes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Daily(at="12:30:00").at, time(12, 30))
        with self.assertRaises(ValueError) as failure:
            Daily(at="25:00:00")
        self.assertIsInstance(failure.exception.__cause__, ValueError)
