# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from __future__ import annotations
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch
from orionis.cache.locks.lock import _FILE_LOCKS, CacheLock
from orionis.cache.stores.database import DatabaseCacheBackend
from orionis.cache.stores.file import FileCacheBackend
from orionis.database.connection import Connection
from orionis.test import TestCase


class TestCacheLock(TestCase):
    def setUp(self) -> None:
        """Create a temporary directory and a FileCacheBackend before each test.

        Provides an isolated backend so every test operates without
        side effects from shared state.

        Returns
        -------
        None
            No return value.
        """
        self.enterContext(patch.dict(_FILE_LOCKS, clear=True))
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self._backend = FileCacheBackend(Path(self._tmpdir.name))

    # ── basic acquire / release ───────────────────────────────────────────────

    async def testFileLockReturnsContextManagerSelf(self) -> None:
        """Return self from __aenter__ so the as-clause works correctly.

        Validates that async with lock as l assigns the CacheLock instance
        to the bound variable.

        Returns
        -------
        None
            No return value.
        """
        lock = CacheLock(self._backend, "self_check")
        async with lock as acquired:
            self.assertIs(acquired, lock)

    async def testFileLockIsReleasedAfterContextExit(self) -> None:
        """Release the underlying asyncio.Lock after the context exits.

        Validates that the asyncio.Lock stored in _FILE_LOCKS for the key
        is no longer locked once the CacheLock context exits.

        Returns
        -------
        None
            No return value.
        """
        key = "release_check"
        lock = CacheLock(self._backend, key)
        async with lock:
            internal = lock._impl
        self.assertIsNotNone(internal)
        self.assertFalse(internal.locked())  # type: ignore[union-attr]

    async def testFileLockWithNoTimeoutAcquires(self) -> None:
        """Acquire a lock when timeout is None (no deadline).

        Validates that passing timeout=None uses a plain asyncio.Lock
        acquire without wrapping it in wait_for.

        Returns
        -------
        None
            No return value.
        """
        lock = CacheLock(self._backend, "no_timeout", timeout=None)
        async with lock:
            internal = lock._impl
            self.assertIsNotNone(internal)
            self.assertTrue(internal.locked())  # type: ignore[union-attr]

    async def testFileLockWithTimeoutAcquires(self) -> None:
        """Acquire a lock when a positive timeout is specified.

        Validates that passing a timeout wraps the acquire in
        asyncio.wait_for without raising when the lock is free.

        Returns
        -------
        None
            No return value.
        """
        lock = CacheLock(self._backend, "with_timeout", timeout=2.0)
        async with lock:
            pass

    # ── mutual exclusion ─────────────────────────────────────────────────────

    async def testTwoLocksOnSameKeyAreMutuallyExclusive(self) -> None:
        """Block a second caller until the current file-lock owner exits."""
        attempted = asyncio.Event()
        entered = asyncio.Event()

        async def acquire_second() -> None:
            """Signal the attempt and record successful acquisition."""
            attempted.set()
            async with CacheLock(self._backend, "exclusive"):
                entered.set()

        task = None
        try:
            async with CacheLock(self._backend, "exclusive"):
                task = asyncio.create_task(acquire_second())
                await asyncio.wait_for(attempted.wait(), 2)
                self.assertFalse(entered.is_set())
            await asyncio.wait_for(task, 2)
            self.assertTrue(entered.is_set())
        finally:
            if task is not None:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    async def testTwoLocksOnDifferentKeysAreIndependent(self) -> None:
        """Hold two different keys concurrently within one event loop."""
        async with (
            CacheLock(self._backend, "key_x") as first,
            CacheLock(self._backend, "key_y", timeout=1) as second,
        ):
            self.assertIsNot(first._impl, second._impl)
            self.assertTrue(first._impl.locked())
            self.assertTrue(second._impl.locked())

    # ── timeout expiry ────────────────────────────────────────────────────────

    async def testFileLockTimeoutRaisesWhenLockHeld(self) -> None:
        """Expire a waiter's acquisition deadline while the owner holds its lock."""
        async with CacheLock(self._backend, "tight_timeout"):
            with self.assertRaises(TimeoutError):
                async with CacheLock(self._backend, "tight_timeout", timeout=0.01):
                    self.fail("A waiter entered the held lock.")

    async def testSeparateDirectoriesHaveIndependentLocks(self) -> None:
        """
        Allow equal keys in separate cache directories to acquire together.

        Returns
        -------
        None
            No return value.
        """
        other = FileCacheBackend(Path(self._tmpdir.name) / "other")
        async with (
            CacheLock(self._backend, "shared") as first,
            CacheLock(other, "shared", timeout=0.1) as second,
        ):
            self.assertIsNot(first._impl, second._impl)

    async def testSameDirectorySharesLocksAcrossBackends(self) -> None:
        """
        Serialize backends that address the same cache directory.

        Returns
        -------
        None
            No return value.
        """
        other = FileCacheBackend(Path(self._tmpdir.name) / ".")
        async with CacheLock(self._backend, "shared"):
            with self.assertRaises(TimeoutError):
                async with CacheLock(other, "shared", timeout=0.01):
                    self.fail("The second backend acquired a held lock.")

    async def testReleasedLocksDoNotAccumulate(self) -> None:
        """
        Discard registry entries after their last holder and waiter leave.

        Returns
        -------
        None
            No return value.
        """
        for index in range(100):
            async with CacheLock(self._backend, str(index)):
                self.assertEqual(len(_FILE_LOCKS), 1)
        self.assertEqual(len(_FILE_LOCKS), 0)

    async def testCanceledWaiterPreservesHolder(self) -> None:
        """
        Keep the held lock registered when another task stops waiting.

        Returns
        -------
        None
            No return value.
        """
        async with CacheLock(self._backend, "shared") as holder:
            waiter = CacheLock(self._backend, "shared")
            task = asyncio.create_task(waiter.__aenter__())
            await asyncio.sleep(0)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertEqual(list(_FILE_LOCKS.values()), [holder._impl])
            with self.assertRaises(TimeoutError):
                async with CacheLock(self._backend, "shared", timeout=0.01):
                    self.fail("The canceled waiter replaced the held lock.")

    async def testDifferentEventLoopsHaveIndependentLocks(self) -> None:
        """
        Keep asyncio locks isolated between event loops.

        Returns
        -------
        None
            No return value.
        """

        async def acquire_lock() -> asyncio.Lock:
            """Acquire the key within the worker event loop.

            Returns
            -------
            asyncio.Lock
                Lock associated with the worker event loop.
            """
            async with CacheLock(self._backend, "shared", timeout=0.1) as lock:
                return lock._impl

        def run_probe() -> asyncio.Lock:
            """Run the acquisition in an independent event loop.

            Returns
            -------
            asyncio.Lock
                Lock acquired in the worker thread.
            """
            return asyncio.run(acquire_lock())

        async with CacheLock(self._backend, "shared") as holder:
            other = await asyncio.to_thread(run_probe)
            self.assertIsNot(holder._impl, other)


class TestDatabaseCacheLock(TestCase):
    async def asyncSetUp(self) -> None:
        """Create an in-memory SQLite connection and a database-backed lock.

        Provides an isolated backend so every test operates on its own
        state without side effects from shared rows. The backing tables
        are created eagerly here (instead of lazily on first use) so the
        timing-sensitive concurrency tests below are not affected by the
        one-time DDL bootstrap cost.

        Returns
        -------
        None
            No return value.
        """
        self._connection = Connection(
            "sqlite",
            {"driver": "sqlite", "database": ":memory:", "prefix": ""},
        )
        self.addAsyncCleanup(self._connection.disconnect)
        self._backend = DatabaseCacheBackend(
            connection=self._connection,
            table="cache",
            lock_table="cache_locks",
        )
        await self._backend._ensureSchema()

    async def testDatabaseLockRowIsRemovedAfterRelease(self) -> None:
        """Remove the underlying lock row once the context exits.

        Validates that __aexit__ calls releaseLock on the backend.

        Returns
        -------
        None
            No return value.
        """
        key = "db_release_check"
        lock = CacheLock(self._backend, key)
        async with lock:
            pass
        # The row should be gone, so a fresh acquire from any owner succeeds.
        acquired = await self._backend.acquireLock(key, "someone-else", lease=5)
        self.assertTrue(acquired)
        await self._backend.releaseLock(key, "someone-else")

    async def testTwoDatabaseLocksOnSameKeyAreMutuallyExclusive(self) -> None:
        """Block a database contender until its current owner releases the row."""
        blocked = asyncio.Event()
        entered = asyncio.Event()
        original = DatabaseCacheBackend.acquireLock

        async def observe_acquisition(
            backend: DatabaseCacheBackend,
            key: str,
            owner: str,
            lease: float,
        ) -> bool:
            """Record a real database rejection before allowing the owner to exit.

            Parameters
            ----------
            backend : DatabaseCacheBackend
                Real backend handling the contender's request.
            key : str
                Shared resource key.
            owner : str
                Token identifying the contender.
            lease : float
                Requested lease duration in seconds.

            Returns
            -------
            bool
                Whether the database granted the lease.
            """
            acquired = await original(backend, key, owner, lease=lease)
            if not acquired:
                blocked.set()
            return acquired

        self.enterContext(
            patch.object(DatabaseCacheBackend, "acquireLock", observe_acquisition),
        )

        async def acquire_second() -> None:
            """Signal the attempt and record successful database-lock acquisition."""
            async with CacheLock(self._backend, "db_exclusive", timeout=2):
                entered.set()

        task = None
        try:
            async with CacheLock(self._backend, "db_exclusive"):
                task = asyncio.create_task(acquire_second())
                await asyncio.wait_for(blocked.wait(), 2)
                self.assertFalse(entered.is_set())
            await asyncio.wait_for(task, 3)
            self.assertTrue(entered.is_set())
        finally:
            if task is not None:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    async def testDatabaseLockTimeoutRaisesWhenLockHeld(self) -> None:
        """Expire a database contender's deadline while the lock row is held."""
        async with CacheLock(self._backend, "db_tight_timeout"):
            with self.assertRaises(TimeoutError):
                async with CacheLock(self._backend, "db_tight_timeout", timeout=0.05):
                    self.fail("A database contender entered the held lock.")
