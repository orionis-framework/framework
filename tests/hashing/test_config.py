from orionis.foundation.config.hashing.entities.argon2 import Argon2
from orionis.foundation.config.hashing.entities.bcrypt import Bcrypt
from orionis.foundation.config.hashing.entities.hashing import Hashing
from orionis.foundation.config.hashing.enums.drivers import Drivers
from orionis.foundation.core_config import CORE_CONFIG
from orionis.hashing.hashers.argon2_hasher import (
    DEFAULT_MEMORY,
    DEFAULT_THREADS,
    DEFAULT_TIME,
)
from orionis.hashing.hashers.bcrypt_hasher import DEFAULT_ROUNDS
from orionis.test import TestCase


class TestHashingDrivers(TestCase):

    def testOnlyPasswordHashingAlgorithmsAreSupported(self) -> None:
        """
        Offer password hashing algorithms exclusively.

        Validates that no general purpose digest can be selected as a
        driver.
        """
        self.assertEqual(
            sorted(driver.value for driver in Drivers),
            ["argon2", "bcrypt"],
        )


class TestHashingEntity(TestCase):

    def testDefaultDriverIsArgon2(self) -> None:
        """
        Select Argon2id for new installations.

        Validates the default the framework ships with.
        """
        self.assertEqual(Hashing().driver, "argon2")

    def testEnumDriverIsNormalisedToString(self) -> None:
        """
        Store a Drivers member as its canonical string value.

        Validates the normalisation the manager relies on to resolve a
        driver by name.
        """
        self.assertEqual(Hashing(driver=Drivers.BCRYPT).driver, "bcrypt")

    def testNestedOptionsAreConvertedToEntities(self) -> None:
        """
        Convert plain dictionaries into typed configuration entities.

        Validates the shape the manager reads its cost parameters from.
        """
        config = Hashing(argon2={"time": 2}, bcrypt={"rounds": 10})
        self.assertIsInstance(config.argon2, Argon2)
        self.assertIsInstance(config.bcrypt, Bcrypt)
        self.assertEqual(config.argon2.time, 2)
        self.assertEqual(config.bcrypt.rounds, 10)

    def testUnknownDriverIsRejected(self) -> None:
        """
        Reject a driver name without an implementation.

        Validates that an invalid configuration fails at boot instead of
        at the first hashing call.
        """
        with self.assertRaises(ValueError):
            Hashing(driver="md5")

    def testNonStringDriverIsRejected(self) -> None:
        """
        Reject a driver declared with an unsupported type.

        Validates the type guard of the configuration entity.
        """
        with self.assertRaises(TypeError):
            Hashing(driver=123)

    def testIsRegisteredInCoreConfig(self) -> None:
        """
        Ship the hashing section with the framework defaults.

        Validates that the manager always finds its configuration.
        """
        self.assertIn("hashing", CORE_CONFIG)
        self.assertEqual(CORE_CONFIG["hashing"]["driver"], "argon2")


class TestArgon2Entity(TestCase):

    def testDefaultsFollowRecommendedCosts(self) -> None:
        """
        Declare the cost parameters recommended for interactive logins.

        Validates the defaults applied when nothing is configured.
        """
        options = Argon2()
        self.assertEqual(options.memory, 65536)
        self.assertEqual(options.threads, 4)
        self.assertEqual(options.time, 3)

    def testDefaultsMatchTheDriverConstants(self) -> None:
        """
        Keep the configuration defaults aligned with the driver ones.

        Validates that configuring nothing and instantiating the driver
        directly produce the same cost parameters.
        """
        options = Argon2()
        self.assertEqual(options.memory, DEFAULT_MEMORY)
        self.assertEqual(options.threads, DEFAULT_THREADS)
        self.assertEqual(options.time, DEFAULT_TIME)

    def testNonPositiveCostIsRejected(self) -> None:
        """
        Reject a cost parameter below one.

        Validates the guard mirroring the one applied by the driver.
        """
        with self.assertRaises(ValueError):
            Argon2(time=0)

    def testNonIntegerCostIsRejected(self) -> None:
        """
        Reject a cost parameter that is not an integer.

        Validates the type guard of the configuration entity.
        """
        with self.assertRaises(TypeError):
            Argon2(memory="65536")


class TestBcryptEntity(TestCase):

    def testDefaultRoundsMatchTheDriverConstant(self) -> None:
        """
        Declare twelve rounds as the default cost factor.

        Validates that the configuration and the driver agree on the
        industry baseline.
        """
        self.assertEqual(Bcrypt().rounds, 12)
        self.assertEqual(Bcrypt().rounds, DEFAULT_ROUNDS)

    def testRoundsOutOfRangeAreRejected(self) -> None:
        """
        Reject a cost factor outside the range supported by bcrypt.

        Validates the guard mirroring the one applied by the driver.
        """
        with self.assertRaises(ValueError):
            Bcrypt(rounds=3)
        with self.assertRaises(ValueError):
            Bcrypt(rounds=32)

    def testNonIntegerRoundsAreRejected(self) -> None:
        """
        Reject a cost factor that is not an integer.

        Validates the type guard of the configuration entity.
        """
        with self.assertRaises(TypeError):
            Bcrypt(rounds="12")
