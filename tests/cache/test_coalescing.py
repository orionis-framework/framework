import asyncio
import gc
import tempfile
from pathlib import Path
from typing import Never, Self
from unittest.mock import patch
from aiocache import SimpleMemoryCache
from orionis.cache.repository import _FLIGHTS, CacheRepository
from orionis.cache.stores.file import FileCacheBackend
from orionis.test import TestCase

class TestCacheCoalescing(TestCase):
    """Verify opt-in miss coalescing and ordered file batches."""

    async def testOneResolverForConcurrentMissesIncludingNone(self: Self) -> None:
        """
        Coalesce 500 misses and retain a legitimate None value.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        backend = SimpleMemoryCache()
        repositories = [CacheRepository(backend, "same") for _ in range(2)]
        calls = 0

        async def resolve() -> None:
            """
            Count one resolver invocation and return a cacheable null value.

            Returns
            -------
            None
                Complete the operation without returning a value.
            """
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.01)

        result = await asyncio.gather(
            *(
                repositories[index % 2].rememberOnce(
                    "key",
                    None,
                    resolve,
                    wait_timeout=60,
                )
                for index in range(500)
            ),
        )
        self.assertEqual(result, [None] * 500)
        self.assertEqual(calls, 1)
        gc.collect()
        self.assertEqual(len(_FLIGHTS), 0)

    async def testCancelledOwnerAndFailuresReleaseTheKey(self: Self) -> None:
        """
        Allow retries after a failed or cancelled owner without stale locks.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        repository = CacheRepository(SimpleMemoryCache())
        entered = asyncio.Event()

        async def blocked() -> None:
            """
            Signal resolver entry and wait for cancellation.

            Returns
            -------
            None
                Complete the operation without returning a value.
            """
            entered.set()
            await asyncio.Event().wait()

        owner = asyncio.create_task(repository.rememberOnce("key", None, blocked))
        await entered.wait()
        with self.assertRaises(TimeoutError):
            await repository.rememberOnce("key", None, lambda: 2, wait_timeout=0.001)
        self.assertEqual(await repository.rememberOnce("other", None, lambda: 3), 3)
        owner.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await owner

        def fail() -> Never:
            """
            Raise a resolver failure to exercise ownership cleanup.

            Returns
            -------
            Never
                Never return normally; raise the configured failure.
            """
            error_msg = "resolver failed"
            raise ValueError(error_msg)

        with self.assertRaises(ValueError):
            await repository.rememberOnce("key", None, fail)
        self.assertEqual(await repository.rememberOnce("key", None, lambda: 4), 4)

    async def testRecursiveResolutionFailsWithoutDeadlock(self: Self) -> None:
        """
        Reject recursive ownership of the same key.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        repository = CacheRepository(SimpleMemoryCache())

        async def recursive() -> int:
            """
            Attempt to resolve a key already owned by this task.

            Returns
            -------
            int
                Resolved integer if the ownership guard allows the recursive call.
            """
            return await repository.rememberOnce("key", None, lambda: 1)

        with self.assertRaisesRegex(RuntimeError, "recursively"):
            await repository.rememberOnce("key", None, recursive)

    async def testFileBatchPreservesDuplicatesDefaultsAndExpiry(self: Self) -> None:
        """
        Use one worker transition per batch without changing file semantics.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        with tempfile.TemporaryDirectory() as directory:
            backend = FileCacheBackend(Path(directory))
            with patch(
                "orionis.cache.stores.file.asyncio.to_thread",
                wraps=asyncio.to_thread,
            ) as run:
                await backend.multiSet([("a", 1), ("a", None), ("b", 2)])
                self.assertEqual(run.call_count, 1)
            missing = object()
            with patch(
                "orionis.cache.stores.file.asyncio.to_thread",
                wraps=asyncio.to_thread,
            ) as run:
                self.assertEqual(
                    await backend.multiGet(["b", "a", "b", "missing"], missing),
                    [2, None, 2, missing],
                )
                self.assertEqual(run.call_count, 1)
            await backend.multiSet([("expired", 1)], ttl=-1)
            self.assertEqual(await backend.multiGet(["expired"]), [None])
