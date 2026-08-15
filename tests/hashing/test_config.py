from __future__ import annotations
from orionis.foundation.config.hashing.entities.argon2 import Argon2
from orionis.foundation.config.hashing.entities.bcrypt import Bcrypt
from orionis.foundation.config.hashing.entities.hashing import Hashing
from orionis.foundation.config.hashing.enums.drivers import Drivers
from orionis.foundation.core_config import CORE_CONFIG
from orionis.test import TestCase

class TestHashingDrivers(TestCase):
    """Tests for the hashing driver enumeration."""

    def testOnlyPasswordHashingAlgorithmsAreSupported(self) -> None:
        """
        Verify no general purpose digest is offered as a driver.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(
            sorted(driver.value for driver in Drivers),
            ["argon2", "bcrypt"],
        )

class TestHashingEntity(TestCase):
    """Tests for the hashing configuration entity."""

    def testDefaultDriverIsArgon2(self) -> None:
        """
        Verify Argon2id is the default driver for new installations.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(Hashing().driver, "argon2")

    def testEnumDriverIsNormalisedToString(self) -> None:
        """
        Verify a Drivers member is stored as its canonical string value.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(Hashing(driver=Drivers.BCRYPT).driver, "bcrypt")

    def testNestedOptionsAreConvertedToEntities(self) -> None:
        """
        Verify plain dictionaries become typed configuration entities.

        Returns
        -------
        None
            This method does not return a value.
        """
        config = Hashing(argon2={"time": 2}, bcrypt={"rounds": 10})
        self.assertIsInstance(config.argon2, Argon2)
        self.assertIsInstance(config.bcrypt, Bcrypt)
        self.assertEqual(config.argon2.time, 2)
        self.assertEqual(config.bcrypt.rounds, 10)

    def testUnknownDriverIsRejected(self) -> None:
        """
        Verify an unsupported driver name raises a validation error.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(ValueError):
            Hashing(driver="md5")

    def testNonStringDriverIsRejected(self) -> None:
        """
        Verify a driver of an invalid type raises a validation error.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(TypeError):
            Hashing(driver=123)

    def testIsRegisteredInCoreConfig(self) -> None:
        """
        Verify the hashing section ships with the framework defaults.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIn("hashing", CORE_CONFIG)
        self.assertEqual(CORE_CONFIG["hashing"]["driver"], "argon2")

class TestArgon2Entity(TestCase):
    """Tests for the Argon2id configuration entity."""

    def testDefaultsFollowRecommendedCosts(self) -> None:
        """
        Verify the default cost parameters match the recommended values.

        Returns
        -------
        None
            This method does not return a value.
        """
        options = Argon2()
        self.assertEqual(options.memory, 65536)
        self.assertEqual(options.threads, 4)
        self.assertEqual(options.time, 3)

    def testNonPositiveCostIsRejected(self) -> None:
        """
        Verify a cost parameter below one raises a validation error.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(ValueError):
            Argon2(time=0)

    def testNonIntegerCostIsRejected(self) -> None:
        """
        Verify a non-integer cost parameter raises a validation error.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(TypeError):
            Argon2(memory="65536")

class TestBcryptEntity(TestCase):
    """Tests for the bcrypt configuration entity."""

    def testDefaultRoundsMatchIndustryBaseline(self) -> None:
        """
        Verify the default cost factor is twelve rounds.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(Bcrypt().rounds, 12)

    def testRoundsOutOfRangeAreRejected(self) -> None:
        """
        Verify a cost factor outside the bcrypt range is rejected.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(ValueError):
            Bcrypt(rounds=3)
        with self.assertRaises(ValueError):
            Bcrypt(rounds=32)

    def testNonIntegerRoundsAreRejected(self) -> None:
        """
        Verify a non-integer cost factor raises a validation error.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(TypeError):
            Bcrypt(rounds="12")
