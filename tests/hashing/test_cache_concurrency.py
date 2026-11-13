# ruff: noqa: PT009, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Keep configuration changes from being overwritten by lazy worker construction."""

import asyncio
import threading
from unittest.mock import patch
from orionis.hashing import Argon2Hasher, BcryptHasher
from orionis.support.concurrency import BoundedExecutor
from orionis.test import TestCase


class TestHashCacheConcurrency(TestCase):
    """Exercise a setter while a real worker is constructing its first backend."""

    async def testSettersCannotRestoreAnOutdatedBackend(self) -> None:
        """Publish no stale cache after a concurrent configuration change.

        Returns
        -------
        None
            No return value.
        """
        pool = BoundedExecutor(1, max_pending=0, name="hash-cache-regression")
        cases = (
            (BcryptHasher(rounds=4, executor=pool), "setRounds", 5),
            (Argon2Hasher(memory=32, threads=1, time=1, executor=pool), "setRounds", 2),
            (
                Argon2Hasher(memory=32, threads=1, time=1, executor=pool),
                "setMemory",
                64,
            ),
            (
                Argon2Hasher(memory=32, threads=1, time=1, executor=pool),
                "setThreads",
                2,
            ),
        )
        loop = asyncio.get_running_loop()
        try:
            for hasher, setter, value in cases:
                with self.subTest(driver=hasher.getAlgorithm(), setter=setter):
                    entered, release = asyncio.Event(), threading.Event()
                    original = type(hasher)._build

                    def build(
                        instance: object,
                        *args: object,
                        builder: object = original,
                        ready: asyncio.Event = entered,
                        gate: threading.Event = release,
                    ) -> object:
                        """Pause a completed backend before its cache publication.

                        Parameters
                        ----------
                        instance : object
                            Driver whose backend is being constructed.
                        *args : object
                            Captured cost parameters forwarded to the real backend.
                        builder : object
                            Original construction method for this driver.
                        ready : asyncio.Event
                            Notification delivered when construction has finished.
                        gate : threading.Event
                            Release signal controlled by the setter's caller.

                        Returns
                        -------
                        object
                            Real backend configured before the concurrent setter.
                        """
                        backend = builder(instance, *args)
                        loop.call_soon_threadsafe(ready.set)
                        gate.wait()
                        return backend

                    with patch.object(type(hasher), "_build", build):
                        running = asyncio.create_task(hasher.make("cache regression"))
                        try:
                            await asyncio.wait_for(entered.wait(), timeout=5)
                            getattr(hasher, setter)(value)
                        finally:
                            release.set()
                            previous = await running
                    self.assertTrue(hasher.needsRehash(previous))
                    current = await hasher.make("cache regression")
                    self.assertFalse(hasher.needsRehash(current))
                    self.assertTrue(await hasher.check("cache regression", previous))
        finally:
            await pool.aclose()
