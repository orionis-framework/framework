from __future__ import annotations
import asyncio
import tempfile
from pathlib import Path
from orionis.cache.stores.database import DatabaseCacheBackend
from orionis.database.connection import Connection
from orionis.test import TestCase

class TestDatabaseCacheBackend(TestCase):

    async def asyncSetUp(self) -> None:
        """
        Create an in-memory SQLite connection and a fresh backend per test.

        Provides an isolated, writable database so every test operates
        on its own state without side effects. Tables are created lazily
        by the backend on first access.
        """
        self._connection = Connection(
            "sqlite",
            {"driver": "sqlite", "database": ":memory:", "prefix": ""},
        )
        self._backend = DatabaseCacheBackend(
            connection=self._connection,
            table="cache",
            lock_table="cache_locks",
        )

    async def asyncTearDown(self) -> None:
        """
        Dispose the in-memory engine after each test.

        Releases the pooled in-memory database.
        """
        await self._connection.disconnect()

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
        Remove an existing key and report it as deleted.

        Validates the documented int contract (1 for an existing key).
        """
        await self._backend.set("d", "v")
        result = await self._backend.delete("d")
        self.assertEqual(result, 1)
        self.assertFalse(await self._backend.exists("d"))

    async def testDeleteMissingKeyReturnsZero(self) -> None:
        """
        Report zero affected rows when deleting an absent key.

        Validates that deleting a non-existent key does not raise.
        """
        result = await self._backend.delete("missing")
        self.assertEqual(result, 0)

    # ── clear ────────────────────────────────────────────────────────────────

    async def testClearRemovesAllEntries(self) -> None:
        """
        Remove every stored entry from the table.

        Validates that clear wipes all rows regardless of key.
        """
        await self._backend.set("a", 1)
        await self._backend.set("b", 2)
        result = await self._backend.clear()
        self.assertTrue(result)
        self.assertFalse(await self._backend.exists("a"))
        self.assertFalse(await self._backend.exists("b"))

    # ── multi get/set ────────────────────────────────────────────────────────

    async def testMultiGetReturnsValuesInOrder(self) -> None:
        """
        Return values matching the order of the requested keys.

        Validates that missing keys map to None within the batch result.
        """
        await self._backend.set("m1", "one")
        await self._backend.set("m2", "two")
        result = await self._backend.multiGet(["m1", "m2", "missing"])
        self.assertEqual(result, ["one", "two", None])

    async def testMultiSetStoresAllPairs(self) -> None:
        """
        Store every key/value pair from a batch write.

        Validates that all pairs become individually retrievable.
        """
        result = await self._backend.multiSet([("s1", "a"), ("s2", "b")])
        self.assertTrue(result)
        self.assertEqual(await self._backend.get("s1"), "a")
        self.assertEqual(await self._backend.get("s2"), "b")

    async def testAiocacheAliasesDelegateToCamelCaseMethods(self) -> None:
        """
        Delegate the snake_case aliases to their camelCase counterparts.

        Validates the aiocache-compatible multi_get/multi_set aliases.
        """
        await self._backend.multi_set([("al1", "x")])
        result = await self._backend.multi_get(["al1"])
        self.assertEqual(result, ["x"])

    # ── add ──────────────────────────────────────────────────────────────────

    async def testAddStoresValueWhenKeyIsAbsent(self) -> None:
        """
        Store the value when the key does not already exist.

        Validates the happy path of the add operation.
        """
        result = await self._backend.add("new", "val")
        self.assertTrue(result)
        self.assertEqual(await self._backend.get("new"), "val")

    async def testAddRaisesWhenKeyAlreadyExists(self) -> None:
        """
        Raise ValueError when attempting to add an existing key.

        Validates the documented conflict behaviour of add.
        """
        await self._backend.set("dup", "existing")
        with self.assertRaises(ValueError):
            await self._backend.add("dup", "other")

    # ── increment ────────────────────────────────────────────────────────────

    async def testIncrementCreatesKeyWhenAbsent(self) -> None:
        """
        Create the key with the delta value when it does not exist.

        Validates the documented auto-creation behaviour of increment.
        """
        result = await self._backend.increment("counter")
        self.assertEqual(result, 1)

    async def testIncrementAddsDeltaToExistingValue(self) -> None:
        """
        Add the delta to an existing integer value.

        Validates the basic increment happy path.
        """
        await self._backend.set("counter2", 10)
        result = await self._backend.increment("counter2", delta=5)
        self.assertEqual(result, 15)
        self.assertEqual(await self._backend.get("counter2"), 15)

    async def testIncrementSupportsNegativeDelta(self) -> None:
        """
        Subtract from the stored value using a negative delta.

        Validates that increment doubles as decrement via sign inversion.
        """
        await self._backend.set("counter3", 10)
        result = await self._backend.increment("counter3", delta=-4)
        self.assertEqual(result, 6)

    async def testIncrementResetsAfterExpiry(self) -> None:
        """
        Restart the counter from the delta once the previous entry expired.

        Validates that increment treats an expired row as absent.
        """
        await self._backend.set("counter4", 10, ttl=0.05)
        await asyncio.sleep(0.1)
        result = await self._backend.increment("counter4")
        self.assertEqual(result, 1)

    # ── atomic locks ─────────────────────────────────────────────────────────

    async def testAcquireLockSucceedsWhenFree(self) -> None:
        """
        Acquire the lock when no row exists for the key yet.

        Validates the base case of the row-based lock.
        """
        acquired = await self._backend.acquireLock("res", "owner-a", lease=5)
        self.assertTrue(acquired)

    async def testAcquireLockFailsWhenHeldByAnotherOwner(self) -> None:
        """
        Refuse to grant the lock to a different owner while it is valid.

        Validates mutual exclusion between distinct owner tokens.
        """
        await self._backend.acquireLock("res2", "owner-a", lease=5)
        acquired = await self._backend.acquireLock("res2", "owner-b", lease=5)
        self.assertFalse(acquired)

    async def testAcquireLockSucceedsForSameOwner(self) -> None:
        """
        Allow the current owner to renew its own lock.

        Validates that re-acquiring with the same owner token succeeds.
        """
        await self._backend.acquireLock("res3", "owner-a", lease=5)
        acquired = await self._backend.acquireLock("res3", "owner-a", lease=5)
        self.assertTrue(acquired)

    async def testAcquireLockSucceedsAfterExpiry(self) -> None:
        """
        Steal an expired lock row on behalf of a new owner.

        Validates that a lease elapsing releases the lock automatically.
        """
        await self._backend.acquireLock("res4", "owner-a", lease=0.05)
        await asyncio.sleep(0.1)
        acquired = await self._backend.acquireLock("res4", "owner-b", lease=5)
        self.assertTrue(acquired)

    async def testReleaseLockAllowsReacquisitionByOtherOwner(self) -> None:
        """
        Free the lock row so another owner can acquire it immediately.

        Validates the explicit release path of the row-based lock.
        """
        await self._backend.acquireLock("res5", "owner-a", lease=5)
        await self._backend.releaseLock("res5", "owner-a")
        acquired = await self._backend.acquireLock("res5", "owner-b", lease=5)
        self.assertTrue(acquired)

    # ── expiration column ────────────────────────────────────────────────────

    async def testEntryExpirationKeepsSubSecondPrecision(self) -> None:
        """
        Store a fractional TTL without losing its decimals.

        Validates that the expiration column is wide enough for the
        floating point TTL the public API accepts, so an integer column
        can never silently round it.
        """
        await self._backend.set("fractional", "v", ttl=0.25)

        rows = await self._connection.select(
            "SELECT expiration FROM cache WHERE cache_key = :k",
            {"k": "fractional"},
        )
        stored = rows[0]["expiration"]

        self.assertIsInstance(stored, float)
        self.assertNotEqual(stored % 1, 0.0)

    async def testLockExpirationKeepsSubSecondPrecision(self) -> None:
        """
        Store a fractional lease without losing its decimals.

        Validates that a short lease is honoured with the granularity it
        was requested with, instead of being widened to a whole second.
        """
        await self._backend.acquireLock("res6", "owner-a", lease=0.25)

        rows = await self._connection.select(
            "SELECT expiration FROM cache_locks WHERE cache_key = :k",
            {"k": "res6"},
        )
        stored = rows[0]["expiration"]

        self.assertIsInstance(stored, float)
        self.assertNotEqual(stored % 1, 0.0)

class TestDatabaseCacheBackendConcurrency(TestCase):
    """Atomicity tests for the operations several callers may race on.

    These run against a file database on purpose: an in-memory SQLite
    database is served by a ``StaticPool``, so every task shares a single
    connection and one task's rollback undoes another task's insert,
    which hides the very behaviour under test.
    """

    async def asyncSetUp(self) -> None:
        """
        Create a file-backed database and a ready backend per test.

        Gives every concurrent task its own connection, so the database
        arbitrates the race instead of the pool.
        """
        self._tmpdir = tempfile.TemporaryDirectory()
        self._connection = Connection(
            "sqlite",
            {
                "driver": "sqlite",
                "database": str(Path(self._tmpdir.name) / "cache.sqlite"),
                "prefix": "",
            },
        )
        self._backend = DatabaseCacheBackend(
            connection=self._connection,
            table="cache",
        )
        await self._backend._ensureSchema()

    async def asyncTearDown(self) -> None:
        """
        Dispose the engine and remove the temporary database file.

        Releases the file handle before the directory is cleaned up.
        """
        await self._connection.disconnect()
        self._tmpdir.cleanup()

    async def testConcurrentAddGrantsASingleWinner(self) -> None:
        """
        Let exactly one concurrent caller create the key.

        Validates that add() decides the winner through the primary key
        instead of a check-then-act pair, which every caller could pass
        before any of them inserted.
        """
        results = await asyncio.gather(
            *(self._backend.add("race", f"value-{n}") for n in range(10)),
            return_exceptions=True,
        )

        granted = [r for r in results if r is True]
        rejected = [r for r in results if isinstance(r, ValueError)]

        self.assertEqual(len(granted), 1)
        self.assertEqual(len(rejected), 9)

    async def testConcurrentIncrementsAreNotLost(self) -> None:
        """
        Apply every concurrent increment to the same counter.

        Validates the compare-and-swap retry: a plain read-modify-write
        lets simultaneous writers overwrite each other and the counter
        ends far below the number of calls.
        """
        await self._backend.set("hits", 0)

        await asyncio.gather(
            *(self._backend.increment("hits") for _ in range(10)),
        )

        self.assertEqual(await self._backend.get("hits"), 10)

    async def testConcurrentIncrementsCreateTheCounterOnce(self) -> None:
        """
        Reach the exact total when the counter does not exist yet.

        Validates that the creation path is retried instead of letting
        two callers both believe they initialised the counter.
        """
        await asyncio.gather(
            *(self._backend.increment("fresh") for _ in range(10)),
        )

        self.assertEqual(await self._backend.get("fresh"), 10)

    async def testConcurrentLockAttemptsGrantASingleOwner(self) -> None:
        """
        Hand the lock row to one owner when several race for it.

        Validates that the row-based lock keeps mutual exclusion when
        every contender reaches the table at the same time.
        """
        results = await asyncio.gather(
            *(
                self._backend.acquireLock("hot", f"owner-{n}", lease=5)
                for n in range(10)
            ),
        )

        self.assertEqual(sum(1 for granted in results if granted), 1)
