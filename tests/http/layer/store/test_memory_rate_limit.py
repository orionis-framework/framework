from __future__ import annotations
import asyncio
from orionis.http.layer.store import memory_rate_limit
from orionis.http.layer.store.memory_rate_limit import MemoryRateLimitStore
from orionis.test import TestCase
from tests.http._support import replace_attribute

class _Clock:
    """Expose an explicitly controlled monotonic time to the rate-limit store."""

    def __init__(self, now: float = 0.0) -> None:
        """Store the initial timestamp reported by the clock."""
        self.now = now

    def __call__(self) -> float:
        """Return the current controlled timestamp."""
        return self.now


class TestMemoryRateLimitStore(TestCase):
    """Exercise quotas and incremental reclamation of inactive clients."""

    async def testExpiresAtTheSlidingWindowBoundary(self) -> None:
        """Allow a new attempt as soon as the oldest accepted attempt expires."""
        store = MemoryRateLimitStore()
        timestamps = iter((0.0, 1.0, 9.0, 10.0, 10.5, 11.0))

        def next_timestamp() -> float:
            """Return the timestamp assigned to the next quota attempt."""
            return next(timestamps)

        with replace_attribute(memory_rate_limit, "monotonic", next_timestamp):
            results = [await store.hit("client", 2, 10) for _ in range(6)]
        self.assertEqual(results, [True, True, False, True, False, True])

    async def testReclaimsClientsThatNeverReturn(self) -> None:
        """Remove expired buckets while unrelated requests continue arriving."""
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
        """Continue collecting short-lived clients when a busy client is denied."""
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
        """Limit the number of keys inspected by one collection pass."""
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
        """Apply one shared quota to tasks running on the same event loop."""
        store = MemoryRateLimitStore()
        with replace_attribute(memory_rate_limit, "monotonic", _Clock()):
            results = await asyncio.gather(*(
                store.hit("client", 10, 60) for _ in range(100)
            ))
        self.assertEqual(sum(results), 10)

    async def testZeroQuotaDoesNotRetainClients(self) -> None:
        """Reject a zero quota without retaining empty client buckets."""
        store = MemoryRateLimitStore()
        self.assertFalse(await store.hit("client", 0, 60))
        self.assertFalse(store._MemoryRateLimitStore__storage)
        self.assertFalse(store._MemoryRateLimitStore__keys)
