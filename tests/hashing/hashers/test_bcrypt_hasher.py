from orionis.hashing.contracts.hasher import IHasher
from orionis.hashing.exceptions import HashConfigurationException
from orionis.hashing.hashers.bcrypt_hasher import (
    DEFAULT_ROUNDS,
    MAX_ROUNDS,
    MIN_ROUNDS,
    BcryptHasher,
)
from orionis.test import TestCase

# Cheapest cost factor accepted by bcrypt, keeps the suite fast.
_ROUNDS: int = 4

# Encoded hash produced by another algorithm, used as a foreign input.
_FOREIGN_HASH: str = "$argon2id$v=19$m=8,t=1,p=1$c2FsdHNhbHQ$ZGlnZXN0"


def cheap_hasher(rounds: int = _ROUNDS) -> BcryptHasher:
    """
    Build a bcrypt hasher with a cost factor fit for a test suite.

    Parameters
    ----------
    rounds : int
        Cost factor applied by the driver.

    Returns
    -------
    BcryptHasher
        Hasher configured for fast execution.
    """
    return BcryptHasher(rounds=rounds)


class TestBcryptHasherLayout(TestCase):

    def testImplementsTheHasherContract(self) -> None:
        """
        Register the driver as an implementation of the hashing contract.

        Validates that the manager can resolve it as an IHasher.
        """
        self.assertIsInstance(cheap_hasher(), IHasher)

    def testDeclaresTheExpectedSlots(self) -> None:
        """
        Declare the state of the driver as explicit slots.

        Validates the memory layout required by the framework conventions.
        """
        self.assertEqual(
            BcryptHasher.__dict__.get("__slots__"),
            ("_backend", "_backend_class", "_rounds"),
        )

    def testDoesNotExposeAnInstanceDictionary(self) -> None:
        """
        Keep instances free of an attribute dictionary.

        Validates that the empty slots of the contract propagate to the
        driver.
        """
        self.assertFalse(hasattr(cheap_hasher(), "__dict__"))

    def testReportsBcryptAsItsAlgorithm(self) -> None:
        """
        Report bcrypt as the algorithm identifier of the driver.

        Validates the value exposed to callers inspecting the driver.
        """
        self.assertEqual(cheap_hasher().getAlgorithm(), "bcrypt")


class TestBcryptHasherDefaults(TestCase):

    def testDeclaresTheBoundsImposedByTheAlgorithm(self) -> None:
        """
        Declare the cost range supported by bcrypt itself.

        Validates the constants guarding the configuration.
        """
        self.assertEqual(MIN_ROUNDS, 4)
        self.assertEqual(MAX_ROUNDS, 31)
        self.assertEqual(DEFAULT_ROUNDS, 12)

    def testAppliesTheDeclaredDefaultWhenNoCostIsGiven(self) -> None:
        """
        Apply the declared default to a driver built without arguments.

        Validates the industry baseline used when the application does
        not override it.
        """
        self.assertEqual(BcryptHasher()._rounds, DEFAULT_ROUNDS)


class TestBcryptHasherValidation(TestCase):

    def testRejectsACostBelowTheMinimum(self) -> None:
        """
        Reject a cost factor under the bcrypt lower bound.

        Validates the guard protecting the backend from an unsupported
        configuration.
        """
        with self.assertRaises(HashConfigurationException):
            BcryptHasher(rounds=MIN_ROUNDS - 1)

    def testRejectsACostAboveTheMaximum(self) -> None:
        """
        Reject a cost factor over the bcrypt upper bound.

        Validates the guard protecting the application from an
        unaffordable configuration.
        """
        with self.assertRaises(HashConfigurationException):
            BcryptHasher(rounds=MAX_ROUNDS + 1)

    def testAcceptsBothEndsOfTheSupportedRange(self) -> None:
        """
        Accept the two boundary values of the supported range.

        Validates that the guard is inclusive on both ends.
        """
        self.assertEqual(BcryptHasher(rounds=MIN_ROUNDS)._rounds, MIN_ROUNDS)
        self.assertEqual(BcryptHasher(rounds=MAX_ROUNDS)._rounds, MAX_ROUNDS)

    def testRejectsNonIntegerCostFactors(self) -> None:
        """
        Reject cost factors that are not integers.

        Validates that a textual or fractional value never reaches the
        backend.
        """
        with self.assertRaises(HashConfigurationException):
            BcryptHasher(rounds="12")  # type: ignore[arg-type]
        with self.assertRaises(HashConfigurationException):
            BcryptHasher(rounds=10.5)  # type: ignore[arg-type]

    def testRejectsBooleanCostFactors(self) -> None:
        """
        Reject booleans even though they are integers in Python.

        Validates the explicit guard that keeps a flag from being read as
        a cost factor.
        """
        with self.assertRaises(HashConfigurationException):
            BcryptHasher(rounds=True)

    def testErrorMessageNamesTheSupportedRange(self) -> None:
        """
        Report the supported range and the rejected value.

        Validates that the failure is actionable without a traceback.
        """
        with self.assertRaises(HashConfigurationException) as captured:
            BcryptHasher(rounds=99)
        message = str(captured.exception)
        self.assertIn(str(MIN_ROUNDS), message)
        self.assertIn(str(MAX_ROUNDS), message)
        self.assertIn("99", message)

    def testRejectsAnInvalidOverrideAtCallTime(self) -> None:
        """
        Reject an out of range override before hashing anything.

        Validates that a bad override fails loudly instead of silently
        falling back to the configured cost.
        """
        with self.assertRaises(HashConfigurationException):
            cheap_hasher().make("secret", rounds=99)

    def testRejectsAnInvalidFluentValue(self) -> None:
        """
        Reject an out of range value handed to the fluent setter.

        Validates that the configured state can never become unusable.
        """
        with self.assertRaises(HashConfigurationException):
            cheap_hasher().setRounds(MIN_ROUNDS - 1)


class TestBcryptHasherBackend(TestCase):

    def testConstructionNeverTouchesTheBackend(self) -> None:
        """
        Build the driver without importing its backend package.

        Validates that the driver stays constructible when the optional
        dependency is absent.
        """
        hasher = cheap_hasher()
        self.assertIsNone(hasher._backend_class)
        self.assertIsNone(hasher._backend)

    def testImportsTheBackendClassOnlyOnce(self) -> None:
        """
        Cache the backend class after the first import.

        Validates that repeated operations do not pay the import cost
        again.
        """
        hasher = cheap_hasher()
        self.assertIs(hasher._backendClass(), hasher._backendClass())

    def testCachesTheDefaultBackendInstance(self) -> None:
        """
        Reuse a single backend instance for the configured cost.

        Validates the caching that keeps hashing free of redundant
        allocations.
        """
        hasher = cheap_hasher()
        self.assertIs(hasher._default(), hasher._default())

    def testMakeReusesTheCachedBackend(self) -> None:
        """
        Reuse the cached backend when no override is provided.

        Validates the fast path taken by the vast majority of calls.
        """
        hasher = cheap_hasher()
        hasher.make("secret")
        cached = hasher._backend
        hasher.make("secret")
        self.assertIs(hasher._backend, cached)

    def testOverridesNeverReplaceTheCachedBackend(self) -> None:
        """
        Keep the cached backend untouched when a call overrides the cost.

        Validates that a per-call override stays scoped to that call.
        """
        hasher = cheap_hasher()
        hasher.make("secret")
        cached = hasher._backend
        hasher.make("secret", rounds=5)
        self.assertIs(hasher._backend, cached)

    def testForeignHashNeverReachesTheBackendInstance(self) -> None:
        """
        Reject a foreign hash without building the backend instance.

        Validates the identify guard shared by check and needsRehash, which
        only needs the backend class to recognise the encoding.
        """
        hasher = cheap_hasher()
        self.assertFalse(hasher.check("secret", _FOREIGN_HASH))
        self.assertTrue(hasher.needsRehash(_FOREIGN_HASH))
        self.assertIsNone(hasher._backend)


class TestBcryptHasherMake(TestCase):

    def testProducesABcryptHash(self) -> None:
        """
        Produce a hash carrying the bcrypt prefix and cost factor.

        Validates that the configured cost reaches the backend.
        """
        self.assertTrue(cheap_hasher().make("secret").startswith("$2b$04$"))

    def testNeverReturnsThePlainValue(self) -> None:
        """
        Keep the plain value out of the produced hash.

        Validates the most basic guarantee expected from the driver.
        """
        self.assertNotIn("secret", cheap_hasher().make("secret"))

    def testIsSaltedPerCall(self) -> None:
        """
        Produce a different hash for every call on the same value.

        Validates that a random salt is generated per call.
        """
        hasher = cheap_hasher()
        self.assertNotEqual(hasher.make("secret"), hasher.make("secret"))

    def testHonorsTheRoundsOverride(self) -> None:
        """
        Apply the cost override to a single call.

        Validates the per-call tuning of the cost factor.
        """
        self.assertTrue(cheap_hasher().make("secret", rounds=5).startswith("$2b$05$"))

    def testIgnoresTheOptionsOfOtherAlgorithms(self) -> None:
        """
        Ignore the memory and parallelism overrides.

        Validates that the shared contract stays usable even though
        bcrypt has no such parameters.
        """
        hashed = cheap_hasher().make("secret", memory=1024, threads=8)
        self.assertTrue(hashed.startswith("$2b$04$"))


class TestBcryptHasherCheck(TestCase):

    def testAcceptsTheOriginalValue(self) -> None:
        """
        Accept the value the hash was produced from.

        Validates the round trip application code depends on.
        """
        hasher = cheap_hasher()
        self.assertTrue(hasher.check("secret", hasher.make("secret")))

    def testRejectsADifferentValue(self) -> None:
        """
        Reject any value other than the hashed one.

        Validates that verification is not vulnerable to a partial match.
        """
        hasher = cheap_hasher()
        self.assertFalse(hasher.check("other", hasher.make("secret")))

    def testAcceptsAHashCreatedWithAnotherCost(self) -> None:
        """
        Accept a hash produced with a different cost factor.

        Validates that raising the cost never locks existing users out.
        """
        legacy = cheap_hasher().make("secret")
        self.assertTrue(cheap_hasher(rounds=5).check("secret", legacy))

    def testRejectsAHashFromAnotherAlgorithm(self) -> None:
        """
        Reject a hash produced by another algorithm.

        Validates the guard that keeps the backend from parsing a foreign
        encoding.
        """
        self.assertFalse(cheap_hasher().check("secret", _FOREIGN_HASH))

    def testRejectsAMalformedHash(self) -> None:
        """
        Reject an input that is not an encoded hash at all.

        Validates that unparsable data never raises through the driver.
        """
        self.assertFalse(cheap_hasher().check("secret", "not-a-hash"))

    def testRejectsAnEmptyHash(self) -> None:
        """
        Reject an empty hash without touching the backend.

        Validates the guard protecting the verification path from a
        missing stored value.
        """
        self.assertFalse(cheap_hasher().check("secret", ""))


class TestBcryptHasherNeedsRehash(TestCase):

    def testFreshHashIsUpToDate(self) -> None:
        """
        Report a hash created with the current cost as up to date.

        Validates that no needless rehash is triggered on login.
        """
        hasher = cheap_hasher()
        self.assertFalse(hasher.needsRehash(hasher.make("secret")))

    def testOutdatedCostRequiresARehash(self) -> None:
        """
        Report a hash created with a lower cost as outdated.

        Validates the upgrade path after raising the configured cost.
        """
        legacy = cheap_hasher().make("secret")
        self.assertTrue(cheap_hasher(rounds=5).needsRehash(legacy))

    def testForeignAlgorithmRequiresARehash(self) -> None:
        """
        Report a hash from another algorithm as outdated.

        Validates the migration path from another driver.
        """
        self.assertTrue(cheap_hasher().needsRehash(_FOREIGN_HASH))

    def testMalformedHashRequiresARehash(self) -> None:
        """
        Report an unparsable hash as outdated.

        Validates that corrupted data is regenerated instead of raising.
        """
        self.assertTrue(cheap_hasher().needsRehash("not-a-hash"))

    def testEmptyHashRequiresARehash(self) -> None:
        """
        Report an empty hash as outdated without touching the backend.

        Validates the guard covering a missing stored value.
        """
        self.assertTrue(cheap_hasher().needsRehash(""))


class TestBcryptHasherConfiguration(TestCase):

    def testSetRoundsReturnsTheSameInstance(self) -> None:
        """
        Return the driver itself from the fluent setter.

        Validates the chaining style advertised by the contract.
        """
        hasher = cheap_hasher()
        self.assertIs(hasher.setRounds(5), hasher)

    def testSetRoundsAppliesToLaterHashes(self) -> None:
        """
        Apply the new cost factor to every subsequent hash.

        Validates that the cached backend is rebuilt after the change.
        """
        hasher = cheap_hasher()
        hasher.setRounds(5)
        self.assertTrue(hasher.make("secret").startswith("$2b$05$"))

    def testSetRoundsDropsTheCachedBackend(self) -> None:
        """
        Drop the cached backend whenever the cost factor changes.

        Validates the invalidation that makes the new configuration
        effective.
        """
        hasher = cheap_hasher()
        hasher._default()
        hasher.setRounds(5)
        self.assertIsNone(hasher._backend)

    def testEarlierHashesRemainVerifiable(self) -> None:
        """
        Keep verifying hashes produced before a configuration change.

        Validates that reconfiguring the driver never invalidates stored
        credentials.
        """
        hasher = cheap_hasher()
        hashed = hasher.make("secret")
        hasher.setRounds(5)
        self.assertTrue(hasher.needsRehash(hashed))
        self.assertTrue(hasher.check("secret", hashed))
