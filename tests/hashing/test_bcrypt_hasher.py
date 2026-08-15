from __future__ import annotations
from orionis.hashing.contracts.hasher import IHasher
from orionis.hashing.exceptions import HashConfigurationException
from orionis.hashing.hashers.bcrypt_hasher import BcryptHasher
from orionis.test import TestCase

# Cheapest cost factor accepted by bcrypt, keeps the suite fast
_ROUNDS = 4

class TestBcryptHasherContract(TestCase):
    """Tests for the contract implemented by BcryptHasher."""

    def testImplementsHasherContract(self) -> None:
        """
        Verify BcryptHasher implements the IHasher contract.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIsInstance(BcryptHasher(rounds=_ROUNDS), IHasher)

    def testAlgorithmIsBcrypt(self) -> None:
        """
        Verify the reported algorithm is bcrypt.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(BcryptHasher(rounds=_ROUNDS).getAlgorithm(), "bcrypt")

class TestBcryptHasherMake(TestCase):
    """Tests for hash generation with bcrypt."""

    def testMakeProducesBcryptHash(self) -> None:
        """
        Verify the generated hash carries the bcrypt prefix and cost.

        Returns
        -------
        None
            This method does not return a value.
        """
        hashed = BcryptHasher(rounds=_ROUNDS).make("secret")
        self.assertTrue(hashed.startswith("$2b$04$"))

    def testMakeNeverReturnsPlainText(self) -> None:
        """
        Verify the plain value is never present in the produced hash.

        Returns
        -------
        None
            This method does not return a value.
        """
        hashed = BcryptHasher(rounds=_ROUNDS).make("secret")
        self.assertNotIn("secret", hashed)

    def testMakeIsSaltedPerCall(self) -> None:
        """
        Verify two hashes of the same value differ because of the salt.

        Returns
        -------
        None
            This method does not return a value.
        """
        hasher = BcryptHasher(rounds=_ROUNDS)
        self.assertNotEqual(hasher.make("secret"), hasher.make("secret"))

    def testMakeHonorsRoundsOverride(self) -> None:
        """
        Verify the rounds override changes the encoded cost factor.

        Returns
        -------
        None
            This method does not return a value.
        """
        hashed = BcryptHasher(rounds=_ROUNDS).make("secret", rounds=5)
        self.assertTrue(hashed.startswith("$2b$05$"))

    def testMakeIgnoresArgon2OnlyOptions(self) -> None:
        """
        Verify memory and threads overrides are ignored by bcrypt.

        Returns
        -------
        None
            This method does not return a value.
        """
        hashed = BcryptHasher(rounds=_ROUNDS).make(
            "secret",
            memory=1024,
            threads=8,
        )
        self.assertTrue(hashed.startswith("$2b$04$"))

    def testMakeRejectsOutOfRangeOverride(self) -> None:
        """
        Verify a cost factor outside the bcrypt range is rejected.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(HashConfigurationException):
            BcryptHasher(rounds=_ROUNDS).make("secret", rounds=99)

class TestBcryptHasherCheck(TestCase):
    """Tests for password verification with bcrypt."""

    def testCheckAcceptsMatchingValue(self) -> None:
        """
        Verify the original value matches its own hash.

        Returns
        -------
        None
            This method does not return a value.
        """
        hasher = BcryptHasher(rounds=_ROUNDS)
        self.assertTrue(hasher.check("secret", hasher.make("secret")))

    def testCheckRejectsDifferentValue(self) -> None:
        """
        Verify a different value does not match the hash.

        Returns
        -------
        None
            This method does not return a value.
        """
        hasher = BcryptHasher(rounds=_ROUNDS)
        self.assertFalse(hasher.check("other", hasher.make("secret")))

    def testCheckAcceptsHashWithDifferentCost(self) -> None:
        """
        Verify a hash created with another cost factor still verifies.

        Returns
        -------
        None
            This method does not return a value.
        """
        legacy = BcryptHasher(rounds=_ROUNDS).make("secret")
        self.assertTrue(BcryptHasher(rounds=5).check("secret", legacy))

    def testCheckRejectsForeignAlgorithm(self) -> None:
        """
        Verify an Argon2id hash is rejected by the bcrypt driver.

        Returns
        -------
        None
            This method does not return a value.
        """
        argon_hash = "$argon2id$v=19$m=8,t=1,p=1$c2FsdHNhbHQ$ZGlnZXN0"
        self.assertFalse(BcryptHasher(rounds=_ROUNDS).check("secret", argon_hash))

    def testCheckRejectsEmptyHash(self) -> None:
        """
        Verify an empty hash never validates.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertFalse(BcryptHasher(rounds=_ROUNDS).check("secret", ""))

class TestBcryptHasherNeedsRehash(TestCase):
    """Tests for rehash detection with bcrypt."""

    def testFreshHashDoesNotNeedRehash(self) -> None:
        """
        Verify a hash created with the current cost is up to date.

        Returns
        -------
        None
            This method does not return a value.
        """
        hasher = BcryptHasher(rounds=_ROUNDS)
        self.assertFalse(hasher.needsRehash(hasher.make("secret")))

    def testOutdatedCostNeedsRehash(self) -> None:
        """
        Verify a hash created with a lower cost requires a rehash.

        Returns
        -------
        None
            This method does not return a value.
        """
        legacy = BcryptHasher(rounds=_ROUNDS).make("secret")
        self.assertTrue(BcryptHasher(rounds=5).needsRehash(legacy))

    def testForeignAlgorithmNeedsRehash(self) -> None:
        """
        Verify a hash from another algorithm requires a rehash.

        Returns
        -------
        None
            This method does not return a value.
        """
        argon_hash = "$argon2id$v=19$m=8,t=1,p=1$c2FsdHNhbHQ$ZGlnZXN0"
        self.assertTrue(BcryptHasher(rounds=_ROUNDS).needsRehash(argon_hash))

    def testEmptyHashNeedsRehash(self) -> None:
        """
        Verify an empty hash requires a rehash.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertTrue(BcryptHasher(rounds=_ROUNDS).needsRehash(""))

class TestBcryptHasherConfiguration(TestCase):
    """Tests for the fluent configuration of the bcrypt driver."""

    def testSetRoundsReturnsSameInstance(self) -> None:
        """
        Verify setRounds is fluent and returns the same hasher.

        Returns
        -------
        None
            This method does not return a value.
        """
        hasher = BcryptHasher(rounds=_ROUNDS)
        self.assertIs(hasher.setRounds(5), hasher)

    def testSetRoundsAppliesToNewHashes(self) -> None:
        """
        Verify the new cost factor is applied to subsequent hashes.

        Returns
        -------
        None
            This method does not return a value.
        """
        hasher = BcryptHasher(rounds=_ROUNDS)
        hasher.setRounds(5)
        self.assertTrue(hasher.make("secret").startswith("$2b$05$"))

    def testRoundsBelowMinimumAreRejected(self) -> None:
        """
        Verify a cost factor below the bcrypt minimum is rejected.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(HashConfigurationException):
            BcryptHasher(rounds=3)

    def testRoundsAboveMaximumAreRejected(self) -> None:
        """
        Verify a cost factor above the bcrypt maximum is rejected.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(HashConfigurationException):
            BcryptHasher(rounds=32)

    def testBooleanRoundsAreRejected(self) -> None:
        """
        Verify a boolean is not accepted as a cost factor.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(HashConfigurationException):
            BcryptHasher(rounds=True)
