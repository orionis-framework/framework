from __future__ import annotations
from dataclasses import asdict
from orionis.foundation.config.hashing.entities.hashing import Hashing
from orionis.hashing.contracts.hash_manager import IHashManager
from orionis.hashing.exceptions import HashDriverNotSupportedException
from orionis.hashing.hash_manager import HashManager
from orionis.hashing.hashers.argon2_hasher import Argon2Hasher
from orionis.hashing.hashers.bcrypt_hasher import BcryptHasher
from orionis.test import TestCase

# Cheap cost parameters shared by every test in this module
_ARGON2 = {"memory": 8, "threads": 1, "time": 1}
_BCRYPT = {"rounds": 4}

class _FakeApp:
    """Minimal application stub exposing a hashing configuration."""

    def __init__(self, driver: str = "argon2") -> None:
        """
        Store the hashing configuration returned to the manager.

        Parameters
        ----------
        driver : str
            Driver name written into the configuration.
        """
        self._config = asdict(
            Hashing(driver=driver, argon2=_ARGON2, bcrypt=_BCRYPT),
        )

    def config(self, key: str) -> dict | None:
        """
        Return the stored configuration section.

        Parameters
        ----------
        key : str
            Configuration key requested by the manager.

        Returns
        -------
        dict | None
            Hashing configuration as a plain dictionary, or ``None`` when
            another section is requested.
        """
        return self._config if key == "hashing" else None

def _manager(driver: str = "argon2") -> HashManager:
    """
    Build a hash manager backed by the stub application.

    Parameters
    ----------
    driver : str
        Default driver used by the manager.

    Returns
    -------
    HashManager
        Manager configured with cheap cost parameters.
    """
    return HashManager(_FakeApp(driver))

class TestHashManagerContract(TestCase):
    """Tests for the contract implemented by HashManager."""

    def testImplementsManagerContract(self) -> None:
        """
        Verify HashManager implements the IHashManager contract.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIsInstance(_manager(), IHashManager)

class TestHashManagerDriverResolution(TestCase):
    """Tests for driver resolution and caching."""

    def testDefaultDriverIsArgon2(self) -> None:
        """
        Verify Argon2id is the driver used by default.

        Returns
        -------
        None
            This method does not return a value.
        """
        manager = _manager()
        self.assertEqual(manager.getDefaultDriver(), "argon2")
        self.assertIsInstance(manager.driver(), Argon2Hasher)

    def testNamedDriverIsResolved(self) -> None:
        """
        Verify a named driver is resolved regardless of the default.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIsInstance(_manager().driver("bcrypt"), BcryptHasher)

    def testConfiguredDriverIsHonored(self) -> None:
        """
        Verify the configured driver becomes the default one.

        Returns
        -------
        None
            This method does not return a value.
        """
        manager = _manager("bcrypt")
        self.assertEqual(manager.getAlgorithm(), "bcrypt")
        self.assertIsInstance(manager.driver(), BcryptHasher)

    def testDriverInstancesAreCached(self) -> None:
        """
        Verify repeated resolutions return the same driver instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        manager = _manager()
        self.assertIs(manager.driver(), manager.driver("argon2"))

    def testUnknownDriverRaises(self) -> None:
        """
        Verify an unsupported driver name is rejected.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(HashDriverNotSupportedException):
            _manager().driver("md5")

    def testConfiguredCostParametersAreApplied(self) -> None:
        """
        Verify the configured Argon2id cost parameters reach the hash.

        Returns
        -------
        None
            This method does not return a value.
        """
        hashed = _manager().make("secret")
        self.assertIn("m=8", hashed)
        self.assertIn("t=1", hashed)
        self.assertIn("p=1", hashed)

class TestHashManagerDelegation(TestCase):
    """Tests for the hashing API exposed by the manager."""

    def testMakeAndCheckRoundTrip(self) -> None:
        """
        Verify a hash produced by the manager validates the same value.

        Returns
        -------
        None
            This method does not return a value.
        """
        manager = _manager()
        hashed = manager.make("my-secret-password")
        self.assertTrue(manager.check("my-secret-password", hashed))
        self.assertFalse(manager.check("wrong-password", hashed))

    def testMakeUsesTheDefaultAlgorithm(self) -> None:
        """
        Verify the default driver produces an Argon2id hash.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertTrue(_manager().make("secret").startswith("$argon2id$"))

    def testMakeHonorsPerCallRounds(self) -> None:
        """
        Verify a per-call cost override reaches the active driver.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIn("t=2", _manager().make("secret", rounds=2))

    def testNeedsRehashFollowsConfiguration(self) -> None:
        """
        Verify rehash detection reflects the configured parameters.

        Returns
        -------
        None
            This method does not return a value.
        """
        manager = _manager()
        hashed = manager.make("secret")
        self.assertFalse(manager.needsRehash(hashed))

    def testNeedsRehashDetectsForeignAlgorithm(self) -> None:
        """
        Verify a hash from another driver requires a rehash.

        Returns
        -------
        None
            This method does not return a value.
        """
        manager = _manager()
        bcrypt_hash = manager.driver("bcrypt").make("secret")
        self.assertTrue(manager.needsRehash(bcrypt_hash))

    def testSetRoundsIsFluentAndAppliesToDefaultDriver(self) -> None:
        """
        Verify setRounds returns the manager and updates the driver.

        Returns
        -------
        None
            This method does not return a value.
        """
        manager = _manager()
        self.assertIs(manager.setRounds(2), manager)
        self.assertIn("t=2", manager.make("secret"))

    def testSetRoundsMarksPreviousHashesForRehash(self) -> None:
        """
        Verify hashes made before setRounds are flagged for regeneration.

        Returns
        -------
        None
            This method does not return a value.
        """
        manager = _manager()
        hashed = manager.make("secret")
        manager.setRounds(2)
        self.assertTrue(manager.needsRehash(hashed))
        self.assertTrue(manager.check("secret", hashed))
