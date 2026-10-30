import asyncio
from typing import Self
from orionis.cache.locks.coalescing import RedisResolverLease
from orionis.test import TestCase

class _Backend:
    """Model atomic NX and owner-checked release without local waiter events."""

    def __init__(self: Self) -> None:
        """
        Initialize the lease storage and acquisition controls.

        Returns
        -------
        None
            Complete the operation without returning a value.
        """
        self.values = {}
        self.entered = asyncio.Event()
        self.block = False

    def build_key(self: Self, key: str) -> str:
        """
        Return the unprefixed key used by the test backend.

        Parameters
        ----------
        key : str
            Cache or lease key to access.

        Returns
        -------
        str
            The supplied key without an additional prefix.
        """
        return key

    async def _add(self: Self, key: str, value: str, *, ttl: float) -> None:
        """
        Store an unclaimed key and optionally pause acquisition.

        Parameters
        ----------
        key : str
            Cache or lease key to access.
        value : str
            Value supplied for ``value``.
        ttl : float
            Entry lifetime in seconds.

        Returns
        -------
        None
            Complete the operation without returning a value.
        """
        self.last_ttl = ttl
        if key in self.values:
            error_msg = "occupied"
            raise ValueError(error_msg)
        self.values[key] = value
        self.entered.set()
        if self.block:
            await asyncio.Event().wait()

    async def _redlock_release(self: Self, key: str, owner: str) -> int:
        """
        Delete a lease only when its stored owner matches.

        Parameters
        ----------
        key : str
            Cache or lease key to access.
        owner : str
            Ownership token required to delete the lease.

        Returns
        -------
        int
            One when the owned key was deleted, otherwise zero.
        """
        if self.values.get(key) == owner:
            del self.values[key]
            return 1
        return 0


class TestResolverLease(TestCase):
    """Check acquisition timeout and ownership cleanup across cancellation races."""

    async def testWaiterTimeoutCannotReleaseAnotherOwner(self: Self) -> None:
        """
        Preserve the active owner's lease when a contender times out.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        backend = _Backend()
        async with RedisResolverLease(backend, "key", 10, 0.1):
            owner = backend.values.copy()
            with self.assertRaises(TimeoutError):
                async with RedisResolverLease(backend, "key", 10, 0.01):
                    self.fail("A contender must not enter the owned lease.")
            self.assertEqual(backend.values, owner)
        self.assertEqual(backend.values, {})

    async def testCancelledAcquisitionCleansItsUnconfirmedWrite(self: Self) -> None:
        """
        Clean an acquired key even when cancellation loses the SET response.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        backend = _Backend()
        backend.block = True
        lease = RedisResolverLease(backend, "key", 10, 0.1)
        acquiring = asyncio.create_task(lease.__aenter__())
        await backend.entered.wait()
        acquiring.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await acquiring
        self.assertEqual(backend.values, {})

    async def testExpiredOwnerCannotDeleteReplacement(self: Self) -> None:
        """
        Preserve a replacement lease after the previous owner expires.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        backend = _Backend()
        async with RedisResolverLease(backend, "key", 10, 0.1):
            backend.values["key-lock"] = "replacement"
        self.assertEqual(backend.values, {"key-lock": "replacement"})
