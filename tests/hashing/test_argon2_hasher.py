from __future__ import annotations
from orionis.hashing.contracts.hasher import IHasher
from orionis.hashing.exceptions import HashConfigurationException
from orionis.hashing.hashers.argon2_hasher import Argon2Hasher
from orionis.test import TestCase

def _hasher(**overrides: int) -> Argon2Hasher:
    """
    Build an Argon2 hasher with cheap cost parameters.

    Parameters
    ----------
    **overrides : int
        Cost parameters replacing the cheap defaults used by the tests.

    Returns
    -------
    Argon2Hasher
        Hasher configured for fast execution inside the test suite.
    """
    # Argon2 requires memory_cost >= 8 * parallelism, so 32 KiB leaves
    # room for the tests that raise the parallelism to two lanes.
    options = {"memory": 32, "threads": 1, "time": 1}
    options.update(overrides)
    return Argon2Hasher(**options)

class TestArgon2HasherContract(TestCase):
    """Tests for the contract implemented by Argon2Hasher."""

    def testImplementsHasherContract(self) -> None:
        """
        Verify Argon2Hasher implements the IHasher contract.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIsInstance(_hasher(), IHasher)

    def testAlgorithmIsArgon2id(self) -> None:
        """
        Verify the reported algorithm is Argon2id.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(_hasher().getAlgorithm(), "argon2id")

class TestArgon2HasherMake(TestCase):
    """Tests for hash generation with Argon2id."""

    def testMakeProducesArgon2idHash(self) -> None:
        """
        Verify the generated hash carries the Argon2id identifier.

        Returns
        -------
        None
            This method does not return a value.
        """
        hashed = _hasher().make("secret")
        self.assertTrue(hashed.startswith("$argon2id$"))

    def testMakeNeverReturnsPlainText(self) -> None:
        """
        Verify the plain value is never present in the produced hash.

        Returns
        -------
        None
            This method does not return a value.
        """
        hashed = _hasher().make("secret")
        self.assertNotIn("secret", hashed)

    def testMakeIsSaltedPerCall(self) -> None:
        """
        Verify two hashes of the same value differ because of the salt.

        Returns
        -------
        None
            This method does not return a value.
        """
        hasher = _hasher()
        self.assertNotEqual(hasher.make("secret"), hasher.make("secret"))

    def testMakeHonorsRoundsOverride(self) -> None:
        """
        Verify the rounds override changes the encoded time cost.

        Returns
        -------
        None
            This method does not return a value.
        """
        hashed = _hasher(time=1).make("secret", rounds=2)
        self.assertIn("t=2", hashed)

    def testMakeHonorsMemoryOverride(self) -> None:
        """
        Verify the memory override changes the encoded memory cost.

        Returns
        -------
        None
            This method does not return a value.
        """
        hashed = _hasher().make("secret", memory=16)
        self.assertIn("m=16", hashed)

    def testMakeHonorsThreadsOverride(self) -> None:
        """
        Verify the threads override changes the encoded parallelism.

        Returns
        -------
        None
            This method does not return a value.
        """
        hashed = _hasher().make("secret", threads=2)
        self.assertIn("p=2", hashed)

    def testMakeRejectsInvalidOverride(self) -> None:
        """
        Verify a non-positive override is rejected.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(HashConfigurationException):
            _hasher().make("secret", rounds=0)

class TestArgon2HasherCheck(TestCase):
    """Tests for password verification with Argon2id."""

    def testCheckAcceptsMatchingValue(self) -> None:
        """
        Verify the original value matches its own hash.

        Returns
        -------
        None
            This method does not return a value.
        """
        hasher = _hasher()
        self.assertTrue(hasher.check("secret", hasher.make("secret")))

    def testCheckRejectsDifferentValue(self) -> None:
        """
        Verify a different value does not match the hash.

        Returns
        -------
        None
            This method does not return a value.
        """
        hasher = _hasher()
        self.assertFalse(hasher.check("other", hasher.make("secret")))

    def testCheckAcceptsHashWithDifferentCost(self) -> None:
        """
        Verify a hash created with other cost parameters still verifies.

        Returns
        -------
        None
            This method does not return a value.
        """
        legacy = _hasher(time=1).make("secret")
        self.assertTrue(_hasher(time=2).check("secret", legacy))

    def testCheckRejectsForeignAlgorithm(self) -> None:
        """
        Verify a bcrypt hash is rejected by the Argon2id driver.

        Returns
        -------
        None
            This method does not return a value.
        """
        bcrypt_hash = "$2b$04$" + "a" * 53
        self.assertFalse(_hasher().check("secret", bcrypt_hash))

    def testCheckRejectsEmptyHash(self) -> None:
        """
        Verify an empty hash never validates.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertFalse(_hasher().check("secret", ""))

class TestArgon2HasherNeedsRehash(TestCase):
    """Tests for rehash detection with Argon2id."""

    def testFreshHashDoesNotNeedRehash(self) -> None:
        """
        Verify a hash created with the current parameters is up to date.

        Returns
        -------
        None
            This method does not return a value.
        """
        hasher = _hasher()
        self.assertFalse(hasher.needsRehash(hasher.make("secret")))

    def testOutdatedCostNeedsRehash(self) -> None:
        """
        Verify a hash created with a lower cost requires a rehash.

        Returns
        -------
        None
            This method does not return a value.
        """
        legacy = _hasher(time=1).make("secret")
        self.assertTrue(_hasher(time=2).needsRehash(legacy))

    def testForeignAlgorithmNeedsRehash(self) -> None:
        """
        Verify a hash from another algorithm requires a rehash.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertTrue(_hasher().needsRehash("$2b$04$" + "a" * 53))

    def testInvalidHashNeedsRehash(self) -> None:
        """
        Verify an unparsable hash requires a rehash.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertTrue(_hasher().needsRehash("not-a-hash"))

class TestArgon2HasherConfiguration(TestCase):
    """Tests for the fluent configuration of the Argon2id driver."""

    def testSetRoundsReturnsSameInstance(self) -> None:
        """
        Verify setRounds is fluent and returns the same hasher.

        Returns
        -------
        None
            This method does not return a value.
        """
        hasher = _hasher()
        self.assertIs(hasher.setRounds(2), hasher)

    def testSetRoundsAppliesToNewHashes(self) -> None:
        """
        Verify the new time cost is applied to subsequent hashes.

        Returns
        -------
        None
            This method does not return a value.
        """
        hasher = _hasher(time=1)
        hasher.setRounds(3)
        self.assertIn("t=3", hasher.make("secret"))

    def testSetMemoryAppliesToNewHashes(self) -> None:
        """
        Verify the new memory cost is applied to subsequent hashes.

        Returns
        -------
        None
            This method does not return a value.
        """
        hasher = _hasher()
        hasher.setMemory(32)
        self.assertIn("m=32", hasher.make("secret"))

    def testSetThreadsAppliesToNewHashes(self) -> None:
        """
        Verify the new parallelism is applied to subsequent hashes.

        Returns
        -------
        None
            This method does not return a value.
        """
        hasher = _hasher()
        hasher.setThreads(2)
        self.assertIn("p=2", hasher.make("secret"))

    def testInvalidConstructorParameterIsRejected(self) -> None:
        """
        Verify a negative cost parameter is rejected on construction.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(HashConfigurationException):
            Argon2Hasher(memory=0)

    def testBooleanCostParameterIsRejected(self) -> None:
        """
        Verify a boolean is not accepted as a cost parameter.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(HashConfigurationException):
            _hasher().setRounds(True)
