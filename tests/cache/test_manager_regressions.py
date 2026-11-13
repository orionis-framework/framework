# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect cache publication, nullable values and asynchronous ownership."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from pathlib import Path
from threading import Barrier, BrokenBarrierError
from types import SimpleNamespace
from typing import get_type_hints
from unittest.mock import patch

from aiocache.lock import RedLock

from orionis.cache.cache_manager import CacheManager
from orionis.cache.locks.coalescing import RedisResolverLease
from orionis.cache.locks.lock import CacheLock
from orionis.cache.repository import CacheRepository
from orionis.cache.stores.database import DatabaseCacheBackend
from orionis.cache.stores.memory import build as build_memory
from orionis.test import TestCase


class _RacingManager(CacheManager):
    """Coordinate concurrent store construction without replacing the backend."""

    def __init__(self) -> None:
        """Configure an isolated memory store and a construction barrier."""
        configuration = SimpleNamespace(
            default="memory",
            prefix="race",
            stores=SimpleNamespace(),
        )
        application = SimpleNamespace(
            basePath=Path.cwd(),
            config=lambda _section: configuration,
        )
        super().__init__(application)
        self.barrier = Barrier(2)

    def _buildBackend(self, name: str) -> object:
        """Expose a competing constructor before building the real store.

        Parameters
        ----------
        name : str
            Configured backend selected by the manager.

        Returns
        -------
        object
            Isolated memory backend with the standard serializer.
        """
        with suppress(BrokenBarrierError):
            self.barrier.wait(timeout=1)
        return super()._buildBackend(name)


class _UnconfirmedDatabaseLock(DatabaseCacheBackend):
    """Model a committed ownership write whose acknowledgement is cancelled."""

    def __init__(self) -> None:
        """Create controlled ownership state without opening a database."""
        self.owners = {}
        self.written = asyncio.Event()

    async def acquireLock(self, key: str, owner: str, lease: float) -> bool:
        """Persist ownership and wait until cancellation interrupts the reply.

        Parameters
        ----------
        key : str
            Resource key whose ownership is recorded.
        owner : str
            Caller token used by the owner-checked release.
        lease : float
            Lifetime supplied by the lock implementation.

        Returns
        -------
        bool
            True if the controlled acknowledgement is allowed to complete.
        """
        self.owners[key] = owner
        self.last_lease = lease
        self.written.set()
        await asyncio.Event().wait()
        return True

    async def releaseLock(self, key: str, owner: str) -> None:
        """Remove only the matching owner's committed write.

        Parameters
        ----------
        key : str
            Resource key to release.
        owner : str
            Token that must still own the resource.
        """
        if self.owners.get(key) == owner:
            del self.owners[key]


class TestCacheManagerRegressions(TestCase):
    """Preserve store identity and ownership across asynchronous boundaries."""

    async def testStoredNoneRemainsAHitAndCanBePulled(self) -> None:
        """Distinguish serialized null from absence across public operations."""
        backend = build_memory()
        self.addAsyncCleanup(backend.close)
        repository = CacheRepository(backend, "nullable")
        calls = []

        def resolve() -> None:
            """Record regeneration and return a cacheable null."""
            calls.append(True)

        for method_name in ("remember", "rememberOnce"):
            with self.subTest(method=method_name):
                calls.clear()
                method = getattr(repository, method_name)
                self.assertIsNone(await method(method_name, None, resolve))
                self.assertIsNone(await method(method_name, None, resolve))
                self.assertEqual(calls, [True])
        await repository.set("pull", None)
        self.assertIsNone(await repository.pull("pull"))
        self.assertFalse(await repository.has("pull"))

    async def testConcurrentStoreResolutionPublishesOneRepository(self) -> None:
        """Reuse one repository when multiple threads resolve the same store."""
        manager = _RacingManager()
        with ThreadPoolExecutor(max_workers=2) as executor:
            repositories = await asyncio.gather(
                *(
                    asyncio.wrap_future(executor.submit(manager.store))
                    for _ in range(2)
                ),
            )
        self.assertIs(repositories[0], repositories[1])
        await repositories[0].set("shared", 7)
        self.assertEqual(await repositories[1].get("shared"), 7)

    async def testCompletedResolverDoesNotPoisonItsChildContext(self) -> None:
        """Allow a child task to resolve after its inherited owner has finished."""
        backend = build_memory()
        self.addAsyncCleanup(backend.close)
        repository = CacheRepository(backend)
        release = asyncio.Event()
        children = []

        async def later() -> int:
            """Wait for the owning call to finish before resolving its key.

            Returns
            -------
            int
                Value produced by the new resolver after invalidation.
            """
            await release.wait()
            return await repository.rememberOnce("key", None, lambda: 2)

        async def resolve() -> int:
            """Spawn a deferred child and finish the current ownership.

            Returns
            -------
            int
                Initial cached value.
            """
            with self.assertRaisesRegex(RuntimeError, "recursively"):
                await asyncio.create_task(
                    repository.rememberOnce("key", None, lambda: 9),
                )
            children.append(asyncio.create_task(later()))
            return 1

        try:
            self.assertEqual(await repository.rememberOnce("key", None, resolve), 1)
            await repository.delete("key")
            release.set()
            self.assertEqual(await asyncio.wait_for(children[0], 2), 2)
        finally:
            release.set()
            for child in children:
                child.cancel()
            await asyncio.gather(*children, return_exceptions=True)

    async def testCancelledAcquisitionReleasesDatabaseOwnership(
        self,
    ) -> None:
        """Release a committed lease even when its acknowledgement is cancelled."""
        backend = _UnconfirmedDatabaseLock()
        lock = CacheLock(backend, "resource", timeout=1)
        acquiring = asyncio.create_task(lock.__aenter__())
        try:
            await asyncio.wait_for(backend.written.wait(), 2)
            acquiring.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(acquiring, 2)
            self.assertEqual(backend.owners, {})
        finally:
            acquiring.cancel()
            await asyncio.gather(acquiring, return_exceptions=True)

    async def testIndependentMemoryBackendsKeepSeparateLockEvents(self) -> None:
        """Release identical lock keys independently on separate memory stores."""
        first = build_memory()
        second = build_memory()
        self.addAsyncCleanup(first.close)
        self.addAsyncCleanup(second.close)
        async with CacheLock(first, "resource") as first_lock:
            first_key = first_lock._impl.key
            async with CacheLock(second, "resource") as second_lock:
                second_key = second_lock._impl.key
                self.assertTrue(await first.exists(first_key))
                self.assertTrue(await second.exists(second_key))
            self.assertFalse(await second.exists(second_key))
            self.assertTrue(await first.exists(first_key))
        self.assertFalse(await first.exists(first_key))
        waiting = asyncio.Event()
        entered = asyncio.Event()
        original_wait = RedLock._wait_for_release

        async def wait_for_release(lock: RedLock) -> None:
            """Signal contention and preserve the dependency's actual wait.

            Parameters
            ----------
            lock : RedLock
                Underlying lease waiting for its current owner.
            """
            waiting.set()
            await original_wait(lock)

        async def acquire() -> None:
            """Enter a second lease on the same backend after the holder leaves."""
            async with CacheLock(first, "resource"):
                entered.set()

        with patch.object(RedLock, "_wait_for_release", wait_for_release):
            async with CacheLock(first, "resource"):
                pending = asyncio.create_task(acquire())
                try:
                    await asyncio.wait_for(waiting.wait(), 2)
                    self.assertFalse(entered.is_set())
                except BaseException:
                    pending.cancel()
                    await asyncio.gather(pending, return_exceptions=True)
                    raise
            await asyncio.wait_for(pending, 2)
        self.assertTrue(entered.is_set())

    def testPublicAnnotationsResolveAtRuntime(self) -> None:
        """Resolve callable and traceback annotations used by extension APIs."""
        for method in (
            CacheManager.remember,
            CacheRepository.remember,
            CacheLock.__aexit__,
            RedisResolverLease.__aexit__,
        ):
            with self.subTest(method=method.__qualname__):
                self.assertIn("return", get_type_hints(method))
