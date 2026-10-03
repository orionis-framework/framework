from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from orionis.http.layer.store import memory_rate_limit
from orionis.http.layer.store.memory_rate_limit import MemoryRateLimitStore
from orionis.test import TestCase
from tests.http.test_support import replace_attribute

class _Clock:
    """Expose an explicitly controlled monotonic time to the rate-limit store."""

    def __init__(self, now: float = 0.0) -> None:
        """Store the initial timestamp reported by the clock.

        Parameters
        ----------
        now : float
            Value supplied for ``now``.

        Returns
        -------
        None
            Store the initial controlled timestamp.
        """
        self.now = now

    def __call__(self) -> float:
        """Return the current controlled timestamp.

        Returns
        -------
        float
            Current controlled monotonic timestamp.
        """
        return self.now

def _thread_attempts(store: MemoryRateLimitStore, barrier: Barrier) -> int:
    """Submit requests from an independent event loop in a worker thread.

    Parameters
    ----------
    store : MemoryRateLimitStore
        Shared store receiving the attempts.
    barrier : Barrier
        Synchronize this worker with the other threads.

    Returns
    -------
    int
        Number of attempts accepted by this worker.
    """
    async def run() -> int:
        """Count the attempts accepted by this worker.

        Returns
        -------
        int
            Number of accepted attempts.
        """
        return sum([await store.hit("shared", 17, 60) for _ in range(100)])

    barrier.wait(timeout=10)
    return asyncio.run(run())

class TestMemoryRateLimitStore(TestCase):
    """Exercise quotas and incremental reclamation of inactive clients."""

    async def testExpiresAtTheSlidingWindowBoundary(self) -> None:
        """Allow a new attempt as soon as the oldest accepted attempt expires.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        store = MemoryRateLimitStore()
        timestamps = iter((0.0, 1.0, 9.0, 10.0, 10.5, 11.0))

        def next_timestamp() -> float:
            """Return the timestamp assigned to the next quota attempt.

            Returns
            -------
            float
                Timestamp assigned to the next attempt.
            """
            return next(timestamps)

        with replace_attribute(memory_rate_limit, "monotonic", next_timestamp):
            results = [await store.hit("client", 2, 10) for _ in range(6)]
        self.assertEqual(results, [True, True, False, True, False, True])

    async def testReclaimsClientsThatNeverReturn(self) -> None:
        """Remove expired buckets while unrelated requests continue arriving.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        store = MemoryRateLimitStore()
        clock = _Clock()
        with replace_attribute(memory_rate_limit, "monotonic", clock):
            for index in range(1024):
                await store.hit(str(index), 10, 10)
            clock.now = 20.0
            for _ in range(300):
                await store.hit("active", 1000, 10)
        self.assertEqual(set(store._MemoryRateLimitStore__storage), {"active"})
        self.assertEqual(list(store._MemoryRateLimitStore__keys), ["active"])

    async def testRejectedTrafficStillReclaimsExpiredClients(self) -> None:
        """Continue collecting short-lived clients when a busy client is denied.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        store = MemoryRateLimitStore()
        clock = _Clock()
        with replace_attribute(memory_rate_limit, "monotonic", clock):
            await store.hit("busy", 1, 1000)
            for index in range(256):
                await store.hit(str(index), 10, 10)
            clock.now = 20.0
            for _ in range(100):
                self.assertFalse(await store.hit("busy", 1, 1000))
        self.assertEqual(set(store._MemoryRateLimitStore__storage), {"busy"})

    async def testBoundsEachCollectionBatch(self) -> None:
        """Limit the number of keys inspected by one collection pass.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        store = MemoryRateLimitStore()
        with replace_attribute(memory_rate_limit, "monotonic", _Clock()):
            for index in range(1024):
                await store.hit(str(index), 10, 10)
        store._MemoryRateLimitStore__gc(20.0)
        self.assertEqual(
            len(store._MemoryRateLimitStore__storage),
            1024 - store._GC_BATCH_SIZE,
        )

    async def testConcurrentAttemptsRespectTheQuota(self) -> None:
        """Apply one shared quota to tasks running on the same event loop.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        store = MemoryRateLimitStore()
        with replace_attribute(memory_rate_limit, "monotonic", _Clock()):
            results = await asyncio.gather(*(
                store.hit("client", 10, 60) for _ in range(100)
            ))
        self.assertEqual(sum(results), 10)

    async def testZeroQuotaDoesNotRetainClients(self) -> None:
        """Reject a zero quota without retaining empty client buckets.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        store = MemoryRateLimitStore()
        self.assertFalse(await store.hit("client", 0, 60))
        self.assertFalse(store._MemoryRateLimitStore__storage)
        self.assertFalse(store._MemoryRateLimitStore__keys)

    async def testRejectsNewClientsAtCapacityWithoutResettingExistingQuotas(
        self,
    ) -> None:
        """Bound retained clients and preserve active clients' accepted history.

        Returns
        -------
        None
            Verify excess clients cannot evict active quotas.
        """
        store = MemoryRateLimitStore(max_keys=2)
        self.assertTrue(await store.hit("one", 2, 60))
        self.assertTrue(await store.hit("two", 2, 60))
        for index in range(1000):
            self.assertFalse(await store.hit(f"new-{index}", 2, 60))
        self.assertTrue(await store.hit("one", 2, 60))
        self.assertFalse(await store.hit("one", 2, 60))
        self.assertEqual(set(store._MemoryRateLimitStore__storage), {"one", "two"})

    async def testBoundsTotalAcceptedTimestampsAcrossClients(self) -> None:
        """Reject additions when aggregate timestamp capacity is reached.

        Returns
        -------
        None
            Verify the store bounds accepted timestamps across clients.
        """
        store = MemoryRateLimitStore(max_events=3)
        self.assertTrue(await store.hit("one", 100, 60))
        self.assertTrue(await store.hit("two", 100, 60))
        self.assertTrue(await store.hit("one", 100, 60))
        self.assertFalse(await store.hit("two", 100, 60))
        self.assertFalse(await store.hit("new", 100, 60))
        self.assertEqual(store._MemoryRateLimitStore__total_events, 3)
        self.assertEqual(len(store._MemoryRateLimitStore__storage), 2)

    async def testReusesCapacityAtExpirationBoundary(self) -> None:
        """Release client and timestamp capacity when a quota expires.

        Returns
        -------
        None
            Verify expired quotas free both configured capacity limits.
        """
        store = MemoryRateLimitStore(max_keys=1, max_events=1)
        clock = _Clock()
        with replace_attribute(memory_rate_limit, "monotonic", clock):
            self.assertTrue(await store.hit("old", 10, 10))
            self.assertFalse(await store.hit("new", 10, 10))
            clock.now = 10
            self.assertTrue(await store.hit("new", 10, 10))
        self.assertEqual(set(store._MemoryRateLimitStore__storage), {"new"})
        self.assertEqual(store._MemoryRateLimitStore__total_events, 1)

    async def testConcurrentThreadsAndEventLoopsRespectSharedQuota(self) -> None:
        """Share one store among independent worker-thread event loops.

        Returns
        -------
        None
            Verify threads collectively observe one quota and event count.
        """
        store = MemoryRateLimitStore()
        barrier = Barrier(8)
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = await asyncio.gather(*(
                loop.run_in_executor(executor, _thread_attempts, store, barrier)
                for _ in range(8)
            ))
        self.assertEqual(sum(results), 17)
        self.assertEqual(store._MemoryRateLimitStore__total_events, 17)

    def testRejectsInvalidCapacity(self) -> None:
        """Require finite, positive integer store capacities.

        Returns
        -------
        None
            Verify invalid values are rejected for each capacity setting.
        """
        for value in (0, -1, True, 1.5):
            for name in ("max_keys", "max_events"):
                with self.subTest(name=name, value=value), self.assertRaises(
                    (TypeError, ValueError),
                ):
                    MemoryRateLimitStore(**{name: value})
