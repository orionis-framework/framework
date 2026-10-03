from __future__ import annotations
import asyncio
import tempfile
from pathlib import Path
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
            Completes the operation described above.
        """
        self._tmpdir = tempfile.TemporaryDirectory()
        self._backend = FileCacheBackend(Path(self._tmpdir.name))

    def tearDown(self) -> None:
        """Remove the temporary directory and purge per-key asyncio locks.

        Ensures filesystem resources and the global _FILE_LOCKS dict are
        cleaned up after each test to prevent cross-test contamination.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self._tmpdir.cleanup()
        _FILE_LOCKS.clear()

    # ── basic acquire / release ───────────────────────────────────────────────

    async def testFileLockAcquireAndRelease(self) -> None:
        """Acquire and release a file-based lock without error.

        Validates that the happy-path async context manager usage does
        not raise and the lock is released on exit.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        lock = CacheLock(self._backend, "resource_a")
        async with lock:
            pass  # Lock is held here; no assertion needed beyond no-raise.

    async def testFileLockReturnsContextManagerSelf(self) -> None:
        """Return self from __aenter__ so the as-clause works correctly.

        Validates that async with lock as l assigns the CacheLock instance
        to the bound variable.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
            Assertions verify the behavior described above.
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
            Assertions verify the behavior described above.
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
            Assertions verify the behavior described above.
        """
        lock = CacheLock(self._backend, "with_timeout", timeout=2.0)
        async with lock:
            pass

    # ── mutual exclusion ─────────────────────────────────────────────────────

    async def testTwoLocksOnSameKeyAreMutuallyExclusive(self) -> None:
        """Prevent two coroutines from holding the same key lock simultaneously.

        Validates mutual exclusion by checking that the second acquire
        cannot enter the critical section while the first is still held.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        key = "exclusive"
        lock_a = CacheLock(self._backend, key)
        lock_b = CacheLock(self._backend, key)

        inside = []

        async def coroutine_a() -> None:
            """Hold the first lock while recording its execution order.

            Returns
            -------
            None
                Completes the operation described above.
            """
            async with lock_a:
                inside.append("a_start")
                await asyncio.sleep(0.05)
                inside.append("a_end")

        async def coroutine_b() -> None:
            """Wait for the first task to acquire its lock.

            Returns
            -------
            None
                Completes the operation described above.
            """
            await asyncio.sleep(0.01)  # Let A acquire first.
            async with lock_b:
                inside.append("b_start")

        await asyncio.gather(coroutine_a(), coroutine_b())
        # A must complete before B enters.
        self.assertEqual(inside.index("a_end"), inside.index("b_start") - 1)

    async def testTwoLocksOnDifferentKeysAreIndependent(self) -> None:
        """Allow two coroutines to hold locks on different keys simultaneously.

        Validates that namespace isolation prevents lock contention
        between unrelated resources.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        lock_x = CacheLock(self._backend, "key_x")
        lock_y = CacheLock(self._backend, "key_y")

        acquired = []

        async def hold_x() -> None:
            """Hold the lock for key x while recording acquisition.

            Returns
            -------
            None
                Completes the operation described above.
            """
            async with lock_x:
                acquired.append("x")
                await asyncio.sleep(0.05)

        async def hold_y() -> None:
            """Hold the lock for key y while recording acquisition.

            Returns
            -------
            None
                Completes the operation described above.
            """
            async with lock_y:
                acquired.append("y")
                await asyncio.sleep(0.05)

        await asyncio.gather(hold_x(), hold_y())
        # Both should have been acquired (in whichever order).
        self.assertIn("x", acquired)
        self.assertIn("y", acquired)

    # ── timeout expiry ────────────────────────────────────────────────────────

    async def testFileLockTimeoutRaisesWhenLockHeld(self) -> None:
        """Raise asyncio.TimeoutError when the lock cannot be acquired in time.

        Validates that a very short timeout expires while another coroutine
        holds the lock, propagating TimeoutError to the waiting caller.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        key = "tight_timeout"
        holder = CacheLock(self._backend, key)
        waiter = CacheLock(self._backend, key, timeout=0.01)

        async def hold() -> None:
            """Hold the cache lock until the timeout is observed.

            Returns
            -------
            None
                Completes the operation described above.
            """
            async with holder:
                await asyncio.sleep(0.2)

        holder_task = asyncio.create_task(hold())
        await asyncio.sleep(0.02)  # Let the holder acquire first.

        with self.assertRaises(asyncio.TimeoutError):
            async with waiter:
                pass  # Should not reach here.

        await holder_task

    async def testSeparateDirectoriesHaveIndependentLocks(self) -> None:
        """Allow equal keys in separate cache directories to acquire together."""
        other = FileCacheBackend(Path(self._tmpdir.name) / "other")
        async with (
            CacheLock(self._backend, "shared") as first,
            CacheLock(other, "shared", timeout=0.1) as second,
        ):
            self.assertIsNot(first._impl, second._impl)

    async def testSameDirectorySharesLocksAcrossBackends(self) -> None:
        """Serialize backends that address the same cache directory."""
        other = FileCacheBackend(Path(self._tmpdir.name) / ".")
        async with CacheLock(self._backend, "shared"):
            with self.assertRaises(TimeoutError):
                async with CacheLock(other, "shared", timeout=0.01):
                    self.fail("The second backend acquired a held lock.")

    async def testReleasedLocksDoNotAccumulate(self) -> None:
        """Discard registry entries after their last holder and waiter leave."""
        for index in range(100):
            async with CacheLock(self._backend, str(index)):
                self.assertEqual(len(_FILE_LOCKS), 1)
        self.assertEqual(len(_FILE_LOCKS), 0)

    async def testCanceledWaiterPreservesHolder(self) -> None:
        """Keep the held lock registered when another task stops waiting."""
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
        """Keep asyncio locks isolated between event loops."""
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
            Completes the operation described above.
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
        await self._backend._ensureSchema()

    async def asyncTearDown(self) -> None:
        """Dispose the in-memory engine after each test.

        Releases the pooled in-memory database.

        Returns
        -------
        None
            Completes the operation described above.
        """
        await self._connection.disconnect()

    async def testDatabaseLockAcquireAndRelease(self) -> None:
        """Acquire and release a database-backed lock without error.

        Validates the happy-path async context manager usage.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        lock = CacheLock(self._backend, "db_resource_a")
        async with lock:
            pass  # Lock is held here; no assertion needed beyond no-raise.

    async def testDatabaseLockRowIsRemovedAfterRelease(self) -> None:
        """Remove the underlying lock row once the context exits.

        Validates that __aexit__ calls releaseLock on the backend.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
        """Prevent two coroutines from holding the same key lock simultaneously.

        Validates mutual exclusion (never more than one concurrent holder)
        without assuming a specific acquisition order: unlike the
        asyncio.Lock-backed file lock, the row-based database lock does
        not guarantee FIFO fairness between owners racing to acquire it.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        key = "db_exclusive"
        lock_a = CacheLock(self._backend, key)
        lock_b = CacheLock(self._backend, key)
        state = {"concurrent": 0, "max_concurrent": 0}

        async def hold(lock: CacheLock) -> None:
            """Hold the cache lock until the timeout is observed.

            Parameters
            ----------
            lock : CacheLock
                Value supplied for ``lock``.

            Returns
            -------
            None
                Completes the operation described above.
            """
            async with lock:
                state["concurrent"] += 1
                state["max_concurrent"] = max(
                    state["max_concurrent"],
                    state["concurrent"],
                )
                await asyncio.sleep(0.05)
                state["concurrent"] -= 1

        await asyncio.gather(hold(lock_a), hold(lock_b))
        self.assertEqual(state["max_concurrent"], 1)

    async def testDatabaseLockTimeoutRaisesWhenLockHeld(self) -> None:
        """Raise TimeoutError when the lock cannot be acquired in time.

        Validates that a very short timeout expires while another
        coroutine holds the lock, propagating TimeoutError to the caller.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        key = "db_tight_timeout"
        holder = CacheLock(self._backend, key)
        waiter = CacheLock(self._backend, key, timeout=0.05)

        async def hold() -> None:
            """Hold the cache lock until the timeout is observed.

            Returns
            -------
            None
                Completes the operation described above.
            """
            async with holder:
                await asyncio.sleep(0.3)

        holder_task = asyncio.create_task(hold())
        await asyncio.sleep(0.02)  # Let the holder acquire first.

        with self.assertRaises(TimeoutError):
            async with waiter:
                pass  # Should not reach here.

        await holder_task
