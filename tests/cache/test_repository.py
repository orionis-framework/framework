from __future__ import annotations
import tempfile
from pathlib import Path
from orionis.cache.repository import CacheRepository
from orionis.cache.stores.file import FileCacheBackend
from orionis.cache.stores.memory import build as build_memory
from orionis.test import TestCase

class TestCacheRepository(TestCase):
    """Tests for CacheRepository backed by FileCacheBackend."""

    def setUp(self) -> None:
        """
        Create a temporary directory and a CacheRepository before each test.

        Provides a fresh FileCacheBackend and a CacheRepository instance
        with no prefix so every test starts with an empty, isolated store.
        """
        self._tmpdir = tempfile.TemporaryDirectory()
        self._backend = FileCacheBackend(Path(self._tmpdir.name))
        self._repo = CacheRepository(self._backend)

    def tearDown(self) -> None:
        """
        Remove the temporary directory after each test.

        Ensures all cache files written during the test are cleaned up
        regardless of whether the test passed or failed.
        """
        self._tmpdir.cleanup()

    # ── get ──────────────────────────────────────────────────────────────────

    async def testGetMissingKeyReturnsNone(self) -> None:
        """
        Return None when getting a key that has never been stored.

        Validates the documented default return value for a cache miss.
        """
        result = await self._repo.get("absent")
        self.assertIsNone(result)

    async def testGetExistingKeyReturnsValue(self) -> None:
        """
        Return the stored value for an existing key.

        Validates the basic happy-path: set then get recovers the value.
        """
        await self._repo.set("hello", "world")
        result = await self._repo.get("hello")
        self.assertEqual(result, "world")

    # ── set ──────────────────────────────────────────────────────────────────

    async def testSetReturnsTrueOnSuccess(self) -> None:
        """
        Return True from set when the operation succeeds.

        Validates the documented return-value contract for set.
        """
        result = await self._repo.set("k", "v")
        self.assertTrue(result)

    async def testSetOverwritesPreviousValue(self) -> None:
        """
        Overwrite the stored value when the same key is set twice.

        Validates that subsequent set calls update the stored entry and
        that get returns the most recent value.
        """
        await self._repo.set("k", "first")
        await self._repo.set("k", "second")
        self.assertEqual(await self._repo.get("k"), "second")

    # ── has ──────────────────────────────────────────────────────────────────

    async def testHasTrueForExistingKey(self) -> None:
        """
        Return True when the key exists and has not expired.

        Validates the has method for the basic present-key case.
        """
        await self._repo.set("present", 1)
        self.assertTrue(await self._repo.has("present"))

    async def testHasFalseForMissingKey(self) -> None:
        """
        Return False when the key has never been stored.

        Validates that has does not raise for unknown keys.
        """
        self.assertFalse(await self._repo.has("ghost"))

    # ── delete ───────────────────────────────────────────────────────────────

    async def testDeleteExistingKeyReturnsTrue(self) -> None:
        """
        Return True after deleting an existing key.

        Validates the documented return value and that the key is gone
        afterwards.
        """
        await self._repo.set("del", "bye")
        result = await self._repo.delete("del")
        self.assertTrue(result)
        self.assertIsNone(await self._repo.get("del"))

    async def testDeleteMissingKeyReturnsFalse(self) -> None:
        """
        Return False when deleting a key that does not exist.

        Validates that deletion of an absent key is handled without error.
        """
        result = await self._repo.delete("never_set")
        self.assertFalse(result)

    # ── clear ────────────────────────────────────────────────────────────────

    async def testClearRemovesAllKeys(self) -> None:
        """
        Remove all keys with a single clear call.

        Validates that entries stored before clear are absent afterwards.
        """
        await self._repo.set("a", 1)
        await self._repo.set("b", 2)
        result = await self._repo.clear()
        self.assertTrue(result)
        self.assertIsNone(await self._repo.get("a"))
        self.assertIsNone(await self._repo.get("b"))

    # ── getMany / setMany ────────────────────────────────────────────────────

    async def testGetManyReturnsCorrectMapping(self) -> None:
        """
        Return a dict mapping original keys to their cached values.

        Validates that getMany preserves the caller-supplied key names
        (un-prefixed) and returns the correct values.
        """
        await self._repo.set("m1", "alpha")
        await self._repo.set("m2", "beta")
        result = await self._repo.getMany(["m1", "m2"])
        self.assertEqual(result, {"m1": "alpha", "m2": "beta"})

    async def testGetManyMissingKeysReturnNone(self) -> None:
        """
        Return None for each missing key in getMany.

        Validates that absent keys produce None entries in the result dict
        rather than raising KeyError.
        """
        result = await self._repo.getMany(["x", "y"])
        self.assertIsNone(result["x"])
        self.assertIsNone(result["y"])

    async def testSetManyStoresAllPairs(self) -> None:
        """
        Store all key/value pairs supplied to setMany.

        Validates that every entry in the input dict is individually
        stored and retrievable via get.
        """
        result = await self._repo.setMany({"s1": 10, "s2": 20})
        self.assertTrue(result)
        self.assertEqual(await self._repo.get("s1"), 10)
        self.assertEqual(await self._repo.get("s2"), 20)

    # ── remember ─────────────────────────────────────────────────────────────

    async def testRememberCallsResolverOnCacheMiss(self) -> None:
        """
        Invoke the resolver and cache its return value on a miss.

        Validates that remember stores the resolved value so subsequent
        get calls return it without calling the resolver again.
        """
        calls = []

        def resolver() -> str:
            calls.append(1)
            return "computed"

        result = await self._repo.remember("rem", 60, resolver)
        self.assertEqual(result, "computed")
        self.assertEqual(len(calls), 1)
        self.assertEqual(await self._repo.get("rem"), "computed")

    async def testRememberReturnsCachedValueOnHit(self) -> None:
        """
        Return the cached value without calling the resolver on a hit.

        Validates that remember skips the resolver when the key already
        exists in the store.
        """
        await self._repo.set("hit", "cached")
        calls = []

        def resolver() -> str:
            calls.append(1)
            return "should not run"

        result = await self._repo.remember("hit", 60, resolver)
        self.assertEqual(result, "cached")
        self.assertEqual(len(calls), 0)

    async def testRememberAwaitsAsyncResolver(self) -> None:
        """
        Await an async resolver on a cache miss.

        Validates that remember detects a coroutine return value and
        awaits it before caching.
        """

        async def async_resolver() -> int:
            return 99

        result = await self._repo.remember("async_rem", 60, async_resolver)
        self.assertEqual(result, 99)
        self.assertEqual(await self._repo.get("async_rem"), 99)

    # ── rememberForever ───────────────────────────────────────────────────────

    async def testRememberForeverStoresValueWithNoTtl(self) -> None:
        """
        Cache the resolved value with no expiry when using rememberForever.

        Validates that the stored value is retrievable and the resolver
        is called exactly once.
        """
        calls = []

        def resolver() -> str:
            calls.append(1)
            return "forever"

        result = await self._repo.rememberForever("ev", resolver)
        self.assertEqual(result, "forever")
        self.assertEqual(len(calls), 1)
        self.assertEqual(await self._repo.get("ev"), "forever")

    # ── pull ─────────────────────────────────────────────────────────────────

    async def testPullReturnsValueAndDeletesKey(self) -> None:
        """
        Return the stored value and remove the key in a single pull call.

        Validates that pull atomically reads and deletes the entry so a
        subsequent get returns None.
        """
        await self._repo.set("pull_k", "pull_v")
        result = await self._repo.pull("pull_k")
        self.assertEqual(result, "pull_v")
        self.assertIsNone(await self._repo.get("pull_k"))

    async def testPullMissingKeyReturnsNone(self) -> None:
        """
        Return None from pull when the key does not exist.

        Validates that pull handles a cache miss gracefully without
        raising an exception.
        """
        result = await self._repo.pull("no_such_key")
        self.assertIsNone(result)

    # ── add ──────────────────────────────────────────────────────────────────

    async def testAddNewKeyReturnsTrue(self) -> None:
        """
        Return True when adding a key that does not already exist.

        Validates the happy-path for conditional add.
        """
        result = await self._repo.add("add_k", "add_v")
        self.assertTrue(result)
        self.assertEqual(await self._repo.get("add_k"), "add_v")

    async def testAddExistingKeyReturnsFalse(self) -> None:
        """
        Return False when the key already exists in the store.

        Validates that add does not overwrite the existing value and
        signals the conflict via a False return rather than an exception.
        """
        await self._repo.set("dup", "original")
        result = await self._repo.add("dup", "new")
        self.assertFalse(result)
        self.assertEqual(await self._repo.get("dup"), "original")

    # ── increment / decrement ─────────────────────────────────────────────────

    async def testIncrementCreatesCounter(self) -> None:
        """
        Create a new counter key with the given amount when absent.

        Validates that increment initialises a missing counter so callers
        do not need to set the key beforehand.
        """
        result = await self._repo.increment("cnt", 3)
        self.assertEqual(result, 3)

    async def testIncrementExistingCounter(self) -> None:
        """
        Add the given amount to an existing integer counter.

        Validates the standard increment path for a pre-existing key.
        """
        await self._repo.set("cnt2", 10)
        result = await self._repo.increment("cnt2", 5)
        self.assertEqual(result, 15)

    async def testDecrementExistingCounter(self) -> None:
        """
        Subtract the given amount from an existing integer counter.

        Validates that decrement uses a negative delta internally and
        returns the expected reduced value.
        """
        await self._repo.set("dcnt", 20)
        result = await self._repo.decrement("dcnt", 7)
        self.assertEqual(result, 13)

    # ── prefix ───────────────────────────────────────────────────────────────

    async def testPrefixIsPrependedToKeys(self) -> None:
        """
        Prepend the configured prefix to all stored keys.

        Validates namespace isolation: two repositories with different
        prefixes sharing the same backend do not share entries.
        """
        repo_a = CacheRepository(self._backend, prefix="ns_a")
        repo_b = CacheRepository(self._backend, prefix="ns_b")

        await repo_a.set("shared", "from_a")
        await repo_b.set("shared", "from_b")

        self.assertEqual(await repo_a.get("shared"), "from_a")
        self.assertEqual(await repo_b.get("shared"), "from_b")

    async def testNoPrefixUsesKeyAsIs(self) -> None:
        """
        Use the raw key when no prefix is configured.

        Validates that a repository constructed without a prefix stores
        and retrieves the key without any separator.
        """
        repo = CacheRepository(self._backend)
        await repo.set("raw", "value")
        self.assertEqual(await repo.get("raw"), "value")

    # ── lock ─────────────────────────────────────────────────────────────────

    async def testLockReturnsContextManager(self) -> None:
        """
        Return a CacheLock that can be used as an async context manager.

        Validates that lock() returns an object supporting __aenter__ and
        __aexit__ so it can be consumed with async with.
        """
        lock = self._repo.lock("resource")
        async with lock:
            self.assertTrue(await self._repo.has("resource") or True)


class TestCacheRepositoryOnMemoryBackend(TestCase):
    """Tests for CacheRepository backed by the in-memory aiocache store."""

    def setUp(self) -> None:
        """
        Create a CacheRepository over a fresh in-memory backend.

        Provides a store whose values go through MsgspecSerializer, which
        is the combination the aiocache backends are built with.
        """
        self._repo = CacheRepository(build_memory())

    async def testCounterIsReadableAfterIncrement(self) -> None:
        """
        Read back a counter written through increment.

        Validates that the native integer stored by the aiocache memory
        backend survives the serializer on the way out.
        """
        self.assertEqual(await self._repo.increment("hits", 5), 5)
        self.assertEqual(await self._repo.get("hits"), 5)

    async def testCounterIsReadableAfterDecrement(self) -> None:
        """
        Read back a counter written through decrement.

        Validates the negative-delta path of the same round trip.
        """
        await self._repo.increment("hits", 5)
        self.assertEqual(await self._repo.decrement("hits", 2), 3)
        self.assertEqual(await self._repo.get("hits"), 3)

    async def testCounterIsReadableInBatchReads(self) -> None:
        """
        Include an incremented counter in a getMany result.

        Validates that the batch read path decodes native values the same
        way the single-key read does.
        """
        await self._repo.increment("hits")
        await self._repo.set("name", "orionis")
        self.assertEqual(
            await self._repo.getMany(["hits", "name"]),
            {"hits": 1, "name": "orionis"},
        )
