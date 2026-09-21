import threading
from orionis.hashing.contracts.hasher import IHasher
from orionis.hashing.exceptions import HashConfigurationException
from orionis.hashing.hashers.argon2_hasher import (
    DEFAULT_MEMORY,
    DEFAULT_THREADS,
    DEFAULT_TIME,
    Argon2Hasher,
)
from orionis.test import TestCase

# Argon2 requires memory_cost >= 8 * parallelism, so 32 KiB leaves room
# for the tests raising the parallelism to two lanes.
_CHEAP_OPTIONS: dict[str, int] = {"memory": 32, "threads": 1, "time": 1}

# Encoded hash produced by another algorithm, used as a foreign input.
_FOREIGN_HASH: str = "$2b$04$" + "a" * 53


def cheap_hasher(**overrides: int) -> Argon2Hasher:
    """
    Build an Argon2 hasher with cost parameters fit for a test suite.

    Parameters
    ----------
    **overrides : int
        Cost parameters replacing the cheap defaults.

    Returns
    -------
    Argon2Hasher
        Hasher configured for fast execution.
    """
    options = dict(_CHEAP_OPTIONS)
    options.update(overrides)
    return Argon2Hasher(**options)


class _ThreadRecordingHasher(Argon2Hasher):
    """Record the thread that performs the blocking hashing work."""

    __slots__ = ("thread_ids",)

    def __init__(self, **options: int) -> None:
        """Start with an empty journal of worker threads."""
        super().__init__(**options)
        self.thread_ids: list[int] = []

    def _make(
        self,
        value: str,
        *,
        rounds: int | None = None,
        memory: int | None = None,
        threads: int | None = None,
    ) -> str:
        """Record the executing thread before hashing."""
        self.thread_ids.append(threading.get_ident())
        return super()._make(value, rounds=rounds, memory=memory, threads=threads)

    def _check(self, value: str, hashed: str) -> bool:
        """Record the executing thread before verifying."""
        self.thread_ids.append(threading.get_ident())
        return super()._check(value, hashed)


class TestArgon2HasherLayout(TestCase):

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
            Argon2Hasher.__dict__.get("__slots__"),
            ("_backend", "_backend_class", "_memory", "_threads", "_time"),
        )

    def testDoesNotExposeAnInstanceDictionary(self) -> None:
        """
        Keep instances free of an attribute dictionary.

        Validates that the empty slots of the contract propagate to the
        driver.
        """
        self.assertFalse(hasattr(cheap_hasher(), "__dict__"))

    def testReportsArgon2idAsItsAlgorithm(self) -> None:
        """
        Report Argon2id as the algorithm identifier of the driver.

        Validates the value exposed to callers inspecting the driver.
        """
        self.assertEqual(cheap_hasher().getAlgorithm(), "argon2id")


class TestArgon2HasherDefaults(TestCase):

    def testDeclaresTheRecommendedCostParameters(self) -> None:
        """
        Declare the cost parameters recommended for interactive logins.

        Validates the constants shared with the configuration entity.
        """
        self.assertEqual(DEFAULT_MEMORY, 65536)
        self.assertEqual(DEFAULT_THREADS, 4)
        self.assertEqual(DEFAULT_TIME, 3)

    def testAppliesTheDeclaredDefaultsWhenNoCostIsGiven(self) -> None:
        """
        Apply the declared defaults to a driver built without arguments.

        Validates that the recommended costs are the ones used when the
        application does not override them.
        """
        hasher = Argon2Hasher()
        self.assertEqual(hasher._memory, DEFAULT_MEMORY)
        self.assertEqual(hasher._threads, DEFAULT_THREADS)
        self.assertEqual(hasher._time, DEFAULT_TIME)


class TestArgon2HasherValidation(TestCase):

    def testRejectsCostParametersBelowOne(self) -> None:
        """
        Reject any cost parameter that is not strictly positive.

        Validates the guard protecting the backend from an unusable
        configuration.
        """
        with self.assertRaises(HashConfigurationException):
            Argon2Hasher(memory=0)
        with self.assertRaises(HashConfigurationException):
            Argon2Hasher(threads=0)
        with self.assertRaises(HashConfigurationException):
            Argon2Hasher(time=-1)

    def testRejectsNonIntegerCostParameters(self) -> None:
        """
        Reject cost parameters that are not integers.

        Validates that a textual or fractional value never reaches the
        backend.
        """
        with self.assertRaises(HashConfigurationException):
            Argon2Hasher(memory="32")  # type: ignore[arg-type]
        with self.assertRaises(HashConfigurationException):
            Argon2Hasher(time=1.5)  # type: ignore[arg-type]

    def testRejectsBooleanCostParameters(self) -> None:
        """
        Reject booleans even though they are integers in Python.

        Validates the explicit guard that keeps a flag from being read as
        a cost factor.
        """
        with self.assertRaises(HashConfigurationException):
            Argon2Hasher(threads=True)

    def testErrorMessageNamesTheRejectedOption(self) -> None:
        """
        Name the offending option and its value in the error message.

        Validates that the failure is actionable without a traceback.
        """
        with self.assertRaises(HashConfigurationException) as captured:
            Argon2Hasher(memory=0)
        message = str(captured.exception)
        self.assertIn("memory", message)
        self.assertIn("0", message)

    async def testRejectsInvalidOverridesAtCallTime(self) -> None:
        """
        Reject invalid per-call overrides before hashing anything.

        Validates that a bad override fails loudly instead of silently
        falling back to the configured cost.
        """
        hasher = cheap_hasher()
        with self.assertRaises(HashConfigurationException):
            await hasher.make("secret", rounds=0)
        with self.assertRaises(HashConfigurationException):
            await hasher.make("secret", memory=0)
        with self.assertRaises(HashConfigurationException):
            await hasher.make("secret", threads=0)

    def testRejectsInvalidFluentValues(self) -> None:
        """
        Reject invalid values handed to the fluent setters.

        Validates that the configured state can never become unusable.
        """
        hasher = cheap_hasher()
        with self.assertRaises(HashConfigurationException):
            hasher.setRounds(0)
        with self.assertRaises(HashConfigurationException):
            hasher.setMemory(0)
        with self.assertRaises(HashConfigurationException):
            hasher.setThreads(0)


class TestArgon2HasherBackend(TestCase):

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
        Reuse a single backend instance for the configured costs.

        Validates the caching that keeps hashing free of redundant
        allocations.
        """
        hasher = cheap_hasher()
        self.assertIs(hasher._default(), hasher._default())

    async def testMakeReusesTheCachedBackend(self) -> None:
        """
        Reuse the cached backend when no override is provided.

        Validates the fast path taken by the vast majority of calls.
        """
        hasher = cheap_hasher()
        await hasher.make("secret")
        cached = hasher._backend
        await hasher.make("secret")
        self.assertIs(hasher._backend, cached)

    async def testOverridesNeverReplaceTheCachedBackend(self) -> None:
        """
        Keep the cached backend untouched when a call overrides a cost.

        Validates that a per-call override stays scoped to that call.
        """
        hasher = cheap_hasher()
        await hasher.make("secret")
        cached = hasher._backend
        await hasher.make("secret", memory=16)
        self.assertIs(hasher._backend, cached)

    async def testForeignHashNeverReachesTheBackendInstance(self) -> None:
        """
        Reject a foreign hash without building the backend instance.

        Validates the identify guard shared by check and needsRehash, which
        only needs the backend class to recognise the encoding.
        """
        hasher = cheap_hasher()
        self.assertFalse(await hasher.check("secret", _FOREIGN_HASH))
        self.assertTrue(hasher.needsRehash(_FOREIGN_HASH))
        self.assertIsNone(hasher._backend)

    async def testHashingRunsOutsideTheEventLoopThread(self) -> None:
        """
        Burn the hashing cost on a worker thread instead of the loop.

        Validates that a login never stalls the other requests served by
        the same worker.
        """
        hasher = _ThreadRecordingHasher(**_CHEAP_OPTIONS)
        hashed = await hasher.make("secret")
        self.assertTrue(await hasher.check("secret", hashed))
        self.assertEqual(len(hasher.thread_ids), 2)
        self.assertNotIn(threading.get_ident(), hasher.thread_ids)


class TestArgon2HasherMake(TestCase):

    async def testProducesAnArgon2idHash(self) -> None:
        """
        Produce a hash carrying the Argon2id identifier.

        Validates that the driver never falls back to another variant.
        """
        hashed = await cheap_hasher().make("secret")
        self.assertTrue(hashed.startswith("$argon2id$"))

    async def testNeverReturnsThePlainValue(self) -> None:
        """
        Keep the plain value out of the produced hash.

        Validates the most basic guarantee expected from the driver.
        """
        self.assertNotIn("secret", await cheap_hasher().make("secret"))

    async def testIsSaltedPerCall(self) -> None:
        """
        Produce a different hash for every call on the same value.

        Validates that a random salt is generated per call.
        """
        hasher = cheap_hasher()
        self.assertNotEqual(await hasher.make("secret"), await hasher.make("secret"))

    async def testAppliesTheConfiguredCosts(self) -> None:
        """
        Encode the configured costs inside the produced hash.

        Validates that the driver configuration reaches the backend.
        """
        hashed = await cheap_hasher().make("secret")
        self.assertIn("m=32", hashed)
        self.assertIn("t=1", hashed)
        self.assertIn("p=1", hashed)

    async def testHonorsTheRoundsOverride(self) -> None:
        """
        Map the rounds override onto the Argon2id time cost.

        Validates the naming bridge between the shared contract and the
        Argon2id vocabulary.
        """
        self.assertIn("t=2", await cheap_hasher().make("secret", rounds=2))

    async def testHonorsTheMemoryOverride(self) -> None:
        """
        Apply the memory override to a single call.

        Validates the per-call tuning of the memory cost.
        """
        self.assertIn("m=16", await cheap_hasher().make("secret", memory=16))

    async def testHonorsTheThreadsOverride(self) -> None:
        """
        Apply the parallelism override to a single call.

        Validates the per-call tuning of the number of lanes.
        """
        self.assertIn("p=2", await cheap_hasher().make("secret", threads=2))

    async def testCombinesEveryOverrideInASingleCall(self) -> None:
        """
        Apply every override provided in the same call.

        Validates that the overrides are independent of each other.
        """
        hashed = await cheap_hasher().make("secret", rounds=2, memory=64, threads=2)
        self.assertIn("m=64", hashed)
        self.assertIn("t=2", hashed)
        self.assertIn("p=2", hashed)


class TestArgon2HasherCheck(TestCase):

    async def testAcceptsTheOriginalValue(self) -> None:
        """
        Accept the value the hash was produced from.

        Validates the round trip application code depends on.
        """
        hasher = cheap_hasher()
        self.assertTrue(await hasher.check("secret", await hasher.make("secret")))

    async def testRejectsADifferentValue(self) -> None:
        """
        Reject any value other than the hashed one.

        Validates that verification is not vulnerable to a partial match.
        """
        hasher = cheap_hasher()
        self.assertFalse(await hasher.check("other", await hasher.make("secret")))

    async def testAcceptsAHashCreatedWithOtherCosts(self) -> None:
        """
        Accept a hash produced with a different cost configuration.

        Validates that raising the costs never locks existing users out.
        """
        legacy = await cheap_hasher(time=1).make("secret")
        self.assertTrue(await cheap_hasher(time=2).check("secret", legacy))

    async def testRejectsAHashFromAnotherAlgorithm(self) -> None:
        """
        Reject a hash produced by another algorithm.

        Validates the guard that keeps the backend from parsing a foreign
        encoding.
        """
        self.assertFalse(await cheap_hasher().check("secret", _FOREIGN_HASH))

    async def testRejectsAMalformedHash(self) -> None:
        """
        Reject an input that is not an encoded hash at all.

        Validates that unparsable data never raises through the driver.
        """
        self.assertFalse(await cheap_hasher().check("secret", "not-a-hash"))

    async def testRejectsAnEmptyHash(self) -> None:
        """
        Reject an empty hash without touching the backend.

        Validates the guard protecting the verification path from a
        missing stored value.
        """
        self.assertFalse(await cheap_hasher().check("secret", ""))


class TestArgon2HasherNeedsRehash(TestCase):

    async def testFreshHashIsUpToDate(self) -> None:
        """
        Report a hash created with the current costs as up to date.

        Validates that no needless rehash is triggered on login.
        """
        hasher = cheap_hasher()
        self.assertFalse(hasher.needsRehash(await hasher.make("secret")))

    async def testOutdatedCostRequiresARehash(self) -> None:
        """
        Report a hash created with lower costs as outdated.

        Validates the upgrade path after raising the configured costs.
        """
        legacy = await cheap_hasher(time=1).make("secret")
        self.assertTrue(cheap_hasher(time=2).needsRehash(legacy))

    def testForeignAlgorithmRequiresARehash(self) -> None:
        """
        Report a hash from another algorithm as outdated.

        Validates the migration path from a legacy driver.
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


class TestArgon2HasherConfiguration(TestCase):

    def testFluentSettersReturnTheSameInstance(self) -> None:
        """
        Return the driver itself from every fluent setter.

        Validates the chaining style advertised by the contract.
        """
        hasher = cheap_hasher()
        self.assertIs(hasher.setRounds(2), hasher)
        self.assertIs(hasher.setMemory(64), hasher)
        self.assertIs(hasher.setThreads(2), hasher)

    async def testSetRoundsAppliesToLaterHashes(self) -> None:
        """
        Apply the new time cost to every subsequent hash.

        Validates that the cached backend is rebuilt after the change.
        """
        hasher = cheap_hasher(time=1)
        hasher.setRounds(3)
        self.assertIn("t=3", await hasher.make("secret"))

    async def testSetMemoryAppliesToLaterHashes(self) -> None:
        """
        Apply the new memory cost to every subsequent hash.

        Validates that the cached backend is rebuilt after the change.
        """
        hasher = cheap_hasher()
        hasher.setMemory(64)
        self.assertIn("m=64", await hasher.make("secret"))

    async def testSetThreadsAppliesToLaterHashes(self) -> None:
        """
        Apply the new parallelism to every subsequent hash.

        Validates that the cached backend is rebuilt after the change.
        """
        hasher = cheap_hasher()
        hasher.setThreads(2)
        self.assertIn("p=2", await hasher.make("secret"))

    def testEveryFluentSetterDropsTheCachedBackend(self) -> None:
        """
        Drop the cached backend whenever a cost parameter changes.

        Validates the invalidation that makes the new configuration
        effective.
        """
        for setter, value in (("setRounds", 2), ("setMemory", 64), ("setThreads", 2)):
            hasher = cheap_hasher()
            hasher._default()
            getattr(hasher, setter)(value)
            self.assertIsNone(hasher._backend, msg=setter)

    async def testEarlierHashesRemainVerifiable(self) -> None:
        """
        Keep verifying hashes produced before a configuration change.

        Validates that reconfiguring the driver never invalidates stored
        credentials.
        """
        hasher = cheap_hasher(time=1)
        hashed = await hasher.make("secret")
        hasher.setRounds(2)
        self.assertTrue(hasher.needsRehash(hashed))
        self.assertTrue(await hasher.check("secret", hashed))
