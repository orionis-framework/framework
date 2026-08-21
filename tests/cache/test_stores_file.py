from __future__ import annotations
import asyncio
import tempfile
from pathlib import Path
from orionis.cache.stores.file import FileCacheBackend
from orionis.test import TestCase

class TestFileCacheBackend(TestCase):

    def setUp(self) -> None:
        """
        Create a temporary directory and a FileCacheBackend before each test.

        Provides an isolated, writable directory so every test operates on
        its own filesystem state without side effects.
        """
        self._tmpdir = tempfile.TemporaryDirectory()
        self._path = Path(self._tmpdir.name)
        self._backend = FileCacheBackend(self._path)

    def tearDown(self) -> None:
        """
        Remove the temporary directory after each test.

        Ensures all cache files created during the test are cleaned up
        regardless of whether the test passed or failed.
        """
        self._tmpdir.cleanup()

    # ── get ──────────────────────────────────────────────────────────────────

    async def testGetMissingKeyReturnsDefault(self) -> None:
        """
        Return the default value when a key does not exist.

        Validates that a missing key produces the caller-supplied default
        rather than raising an exception.
        """
        result = await self._backend.get("absent")
        self.assertIsNone(result)

    async def testGetMissingKeyReturnsCustomDefault(self) -> None:
        """
        Return a caller-supplied default for a missing key.

        Validates that the default parameter is forwarded correctly and
        not ignored when the key is absent.
        """
        result = await self._backend.get("absent", default="fallback")
        self.assertEqual(result, "fallback")

    async def testGetExistingKeyReturnsValue(self) -> None:
        """
        Return the stored value for an existing key.

        Validates the basic happy-path: set then get recovers the value.
        """
        await self._backend.set("k1", "hello")
        result = await self._backend.get("k1")
        self.assertEqual(result, "hello")

    async def testGetAfterTtlExpiryReturnsDefault(self) -> None:
        """
        Return the default value after a key's TTL has elapsed.

        Validates that expired entries are lazily evicted on first read
        and the default is returned instead.
        """
        await self._backend.set("ttl_key", "data", ttl=0.05)
        await asyncio.sleep(0.1)
        result = await self._backend.get("ttl_key")
        self.assertIsNone(result)

    # ── set ──────────────────────────────────────────────────────────────────

    async def testSetReturnsTrueOnSuccess(self) -> None:
        """
        Return True after a successful set operation.

        Validates the documented return value contract for set.
        """
        result = await self._backend.set("k", "v")
        self.assertTrue(result)

    async def testSetOverwritesExistingValue(self) -> None:
        """
        Overwrite an existing key with a new value.

        Validates that a second set replaces the previous value so get
        returns the latest data.
        """
        await self._backend.set("k", "first")
        await self._backend.set("k", "second")
        result = await self._backend.get("k")
        self.assertEqual(result, "second")

    async def testSetWithNoneTtlPersistsForever(self) -> None:
        """
        Persist a value with no TTL indefinitely.

        Validates that passing ttl=None stores the entry without an
        expiry timestamp, so it is always returned.
        """
        await self._backend.set("persist", 42, ttl=None)
        result = await self._backend.get("persist")
        self.assertEqual(result, 42)

    async def testSetStoresNoneValue(self) -> None:
        """
        Store and retrieve an explicit None value.

        Validates that None stored intentionally is recovered as None,
        not confused with a missing-key None.
        """
        await self._backend.set("null_key", None)
        result = await self._backend.get("null_key", default="missing")
        self.assertIsNone(result)

    # ── exists ───────────────────────────────────────────────────────────────

    async def testExistsTrueForExistingKey(self) -> None:
        """
        Return True when the key exists and has not expired.

        Validates the exists method for the basic present-key case.
        """
        await self._backend.set("ex", "val")
        self.assertTrue(await self._backend.exists("ex"))

    async def testExistsFalseForMissingKey(self) -> None:
        """
        Return False when the key has never been stored.

        Validates that exists does not raise for unknown keys.
        """
        self.assertFalse(await self._backend.exists("ghost"))

    async def testExistsFalseAfterExpiry(self) -> None:
        """
        Return False after a key's TTL has elapsed.

        Validates that exists uses the same lazy-eviction logic as get.
        """
        await self._backend.set("exp", "x", ttl=0.05)
        await asyncio.sleep(0.1)
        self.assertFalse(await self._backend.exists("exp"))

    # ── delete ───────────────────────────────────────────────────────────────

    async def testDeleteExistingKeyReturnsOne(self) -> None:
        """
        Return 1 when deleting an existing key.

        Validates the documented return value for a successful deletion.
        """
        await self._backend.set("del", "v")
        result = await self._backend.delete("del")
        self.assertEqual(result, 1)

    async def testDeleteMissingKeyReturnsZero(self) -> None:
        """
        Return 0 when deleting a key that does not exist.

        Validates that deletion of an absent key is handled without error.
        """
        result = await self._backend.delete("never_set")
        self.assertEqual(result, 0)

    async def testDeletedKeyIsNoLongerAccessible(self) -> None:
        """
        Confirm the key is gone after a delete call.

        Validates that get returns the default value after a successful
        deletion.
        """
        await self._backend.set("gone", "data")
        await self._backend.delete("gone")
        self.assertIsNone(await self._backend.get("gone"))

    # ── clear ────────────────────────────────────────────────────────────────

    async def testClearRemovesAllEntries(self) -> None:
        """
        Remove all cached entries with a single clear call.

        Validates that keys written before clear are all absent after it.
        """
        await self._backend.set("a", 1)
        await self._backend.set("b", 2)
        result = await self._backend.clear()
        self.assertTrue(result)
        self.assertIsNone(await self._backend.get("a"))
        self.assertIsNone(await self._backend.get("b"))

    async def testClearOnEmptyStoreReturnsTrueWithoutError(self) -> None:
        """
        Return True when clearing an already empty store.

        Validates that clear is idempotent and does not raise when there
        are no entries to remove.
        """
        result = await self._backend.clear()
        self.assertTrue(result)

    # ── multiGet / multi_get ─────────────────────────────────────────────────

    async def testMultiGetReturnsValuesInOrder(self) -> None:
        """
        Return values in the same order as the requested keys.

        Validates that multiGet preserves key ordering so callers can zip
        keys with values without reordering.
        """
        await self._backend.set("x", 10)
        await self._backend.set("y", 20)
        results = await self._backend.multiGet(["x", "y"])
        self.assertEqual(results, [10, 20])

    async def testMultiGetMissingKeysReturnDefault(self) -> None:
        """
        Return the default for each missing key in multiGet.

        Validates that absent keys produce the caller-supplied default
        rather than raising KeyError.
        """
        results = await self._backend.multiGet(["m1", "m2"], default=0)
        self.assertEqual(results, [0, 0])

    async def testMultiGetAliasMatchesMultiGet(self) -> None:
        """
        Confirm multi_get returns the same result as multiGet.

        Validates that the aiocache-compatible snake_case alias delegates
        correctly to the camelCase implementation.
        """
        await self._backend.set("p", "val")
        camel = await self._backend.multiGet(["p"])
        snake = await self._backend.multi_get(["p"])
        self.assertEqual(camel, snake)

    # ── multiSet / multi_set ─────────────────────────────────────────────────

    async def testMultiSetStoresAllPairs(self) -> None:
        """
        Store all key/value pairs provided to multiSet.

        Validates that every pair in the input list is individually
        stored and retrievable via get.
        """
        pairs = [("q1", "a"), ("q2", "b")]
        result = await self._backend.multiSet(pairs)
        self.assertTrue(result)
        self.assertEqual(await self._backend.get("q1"), "a")
        self.assertEqual(await self._backend.get("q2"), "b")

    async def testMultiSetAliasMatchesMultiSet(self) -> None:
        """
        Confirm multi_set stores entries accessible via get.

        Validates that the aiocache-compatible snake_case alias delegates
        correctly to the camelCase implementation.
        """
        result = await self._backend.multi_set([("alias_k", "alias_v")])
        self.assertTrue(result)
        self.assertEqual(await self._backend.get("alias_k"), "alias_v")

    # ── add ──────────────────────────────────────────────────────────────────

    async def testAddNewKeyReturnsTrue(self) -> None:
        """
        Return True when adding a key that does not exist.

        Validates the happy-path for add where no conflict occurs.
        """
        result = await self._backend.add("new_k", "new_v")
        self.assertTrue(result)
        self.assertEqual(await self._backend.get("new_k"), "new_v")

    async def testAddExistingKeyRaisesValueError(self) -> None:
        """
        Raise ValueError when adding a key that already exists.

        Validates the atomic-add contract: existing keys must not be
        silently overwritten.
        """
        await self._backend.set("dup", "original")
        with self.assertRaises(ValueError):
            await self._backend.add("dup", "conflict")

    async def testAddDoesNotOverwriteExistingValue(self) -> None:
        """
        Leave the existing value unchanged when add raises.

        Validates that the ValueError from add does not corrupt the
        previously stored entry.
        """
        import contextlib
        await self._backend.set("safe", "kept")
        with contextlib.suppress(ValueError):
            await self._backend.add("safe", "new")
        self.assertEqual(await self._backend.get("safe"), "kept")

    # ── increment ────────────────────────────────────────────────────────────

    async def testIncrementCreatesNewKeyWithDelta(self) -> None:
        """
        Create a new key with value equal to delta when the key is absent.

        Validates that increment initialises a missing counter from zero.
        """
        result = await self._backend.increment("cnt", 5)
        self.assertEqual(result, 5)

    async def testIncrementExistingKeyAddsAmount(self) -> None:
        """
        Add delta to an existing integer counter.

        Validates that increment updates the stored value atomically
        within a single call.
        """
        await self._backend.set("counter", 10)
        result = await self._backend.increment("counter", 3)
        self.assertEqual(result, 13)

    async def testIncrementByDefaultOneStep(self) -> None:
        """
        Increment by one when no delta is specified.

        Validates the default delta=1 documented in the method signature.
        """
        await self._backend.set("one", 0)
        result = await self._backend.increment("one")
        self.assertEqual(result, 1)

    async def testIncrementWithNegativeDeltaDecrements(self) -> None:
        """
        Decrement the counter when a negative delta is passed.

        Validates that increment accepts negative amounts to act as
        a decrement operation.
        """
        await self._backend.set("dec", 10)
        result = await self._backend.increment("dec", -4)
        self.assertEqual(result, 6)

    # ── misc ─────────────────────────────────────────────────────────────────

    async def testBackendCreatesDirectoryIfMissing(self) -> None:
        """
        Create the cache directory on initialisation if it does not exist.

        Validates that FileCacheBackend.mkdir(parents=True) is called so
        a nested path that does not yet exist is created.
        """
        nested = self._path / "deep" / "nested"
        FileCacheBackend(nested)
        self.assertTrue(nested.is_dir())

    async def testDifferentKeysAreIndependent(self) -> None:
        """
        Confirm separate keys do not share storage.

        Validates that writing to one key has no effect on a different key
        stored under the same backend instance.
        """
        await self._backend.set("kA", "A")
        await self._backend.set("kB", "B")
        self.assertEqual(await self._backend.get("kA"), "A")
        self.assertEqual(await self._backend.get("kB"), "B")


class TestFileCacheBackendConcurrency(TestCase):

    def setUp(self) -> None:
        """
        Create a temporary directory and a FileCacheBackend before each test.

        Provides an isolated directory so concurrent writes never touch
        files produced by another test.
        """
        self._tmpdir = tempfile.TemporaryDirectory()
        self._path = Path(self._tmpdir.name)
        self._backend = FileCacheBackend(self._path)

    def tearDown(self) -> None:
        """
        Remove the temporary directory after each test.

        Ensures every file written by the concurrent tasks is cleaned up.
        """
        self._tmpdir.cleanup()

    async def testConcurrentWritesToTheSamePathNeverMixPayloads(self) -> None:
        """
        Keep every concurrent write of one key internally consistent.

        Validates that the staging file is unique per write, so the entry
        published at the end is one complete payload and never a blend of
        two writers.
        """
        payloads = [{"writer": index, "data": "x" * 500} for index in range(20)]
        await asyncio.gather(
            *(self._backend.set("shared", payload) for payload in payloads),
        )

        stored = await self._backend.get("shared")
        self.assertIn(stored, payloads)
        self.assertEqual(list(self._path.glob("*.tmp")), [])

    async def testConcurrentAddElectsASingleWinner(self) -> None:
        """
        Allow exactly one caller to win a contended add.

        Validates that add is an exclusive create and therefore usable as
        a mutual-exclusion primitive.
        """
        async def attempt(index: int) -> bool:
            try:
                return await self._backend.add("only-once", index)
            except ValueError:
                return False

        results = await asyncio.gather(*(attempt(index) for index in range(10)))

        self.assertEqual(sum(results), 1)
        self.assertIn(await self._backend.get("only-once"), range(10))

    async def testConcurrentIncrementsDoNotLoseUpdates(self) -> None:
        """
        Apply every concurrent increment to the counter.

        Validates that the read-modify-write cycle is serialised, so no
        update is lost when tasks run interleaved on the same loop.
        """
        await asyncio.gather(*(self._backend.increment("hits") for _ in range(25)))
        self.assertEqual(await self._backend.get("hits"), 25)

    async def testIncrementPreservesTheExistingExpiry(self) -> None:
        """
        Keep the original TTL when a counter is incremented.

        Validates that increment updates only the value, so the entry
        still expires at the deadline set by the initial write.
        """
        await self._backend.set("ttl_counter", 1, ttl=0.05)
        self.assertEqual(await self._backend.increment("ttl_counter"), 2)

        await asyncio.sleep(0.1)
        self.assertIsNone(await self._backend.get("ttl_counter"))

    async def testIncrementOverAnExpiredKeyRestartsWithoutExpiry(self) -> None:
        """
        Restart the counter from zero once the previous entry expired.

        Validates that a stale deadline is dropped instead of being
        carried over to the fresh value.
        """
        await self._backend.set("stale", 7, ttl=0.05)
        await asyncio.sleep(0.1)

        self.assertEqual(await self._backend.increment("stale", 3), 3)
        await asyncio.sleep(0.1)
        self.assertEqual(await self._backend.get("stale"), 3)

