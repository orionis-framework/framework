import asyncio
import threading
from types import SimpleNamespace
from typing import Self
from orionis.hashing.hashers.argon2_hasher import Argon2Hasher
from orionis.hashing.hashers.bcrypt_hasher import BcryptHasher
from orionis.support.concurrency import BoundedExecutor, WorkQueueFullError
from orionis.test import TestCase

class TestHashAdmission(TestCase):
    """Check shared algorithm admission without weakening cryptographic parameters."""

    async def testAlgorithmsShareDedicatedBudgetAndKeepLoopResponsive(
        self: Self,
    ) -> None:
        """
        Retain hashing capacity until native completion across algorithms.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        pool = BoundedExecutor(1, max_pending=0, name="hash-test")
        entered, released = threading.Event(), threading.Event()
        threads = []

        def native_hash(_password: str) -> str:
            """
            Record the worker thread and block until hashing is released.

            Parameters
            ----------
            _password : str
                Plaintext password supplied to the native hasher double.

            Returns
            -------
            str
                Fixed encoded hash used to exercise worker admission.
            """
            threads.append(threading.current_thread().name)
            entered.set()
            released.wait(5)
            return "encoded"

        argon = Argon2Hasher(executor=pool)
        bcrypt = BcryptHasher(executor=pool)
        backend = SimpleNamespace(
            hash=native_hash,
            verify=lambda _password, _hashed: True,
        )
        argon._backend = backend
        bcrypt._backend = backend
        running = asyncio.create_task(argon.make("test"))
        try:
            self.assertTrue(await asyncio.to_thread(entered.wait, 5))
            with self.assertRaises(WorkQueueFullError):
                await bcrypt.make("test")
            self.assertTrue(threads[0].startswith("hash-test"))
        finally:
            released.set()
            self.assertEqual(await running, "encoded")
            await pool.aclose()
