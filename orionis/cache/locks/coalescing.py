import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Self
from uuid import uuid4
from orionis.cache.locks.lock import CacheLock, _is_backend
from orionis.support.concurrency import complete_on_cancel

if TYPE_CHECKING:
    from types import TracebackType

# Low-level aiocache methods deliberately avoid reserializing the ownership token.
# ruff: noqa: ANN401, SLF001

class RedisResolverLease:
    """Poll a Redis NX lease rather than relying on process-local waiter events."""

    def __init__(
        self: Self,
        backend: Any,
        key: str,
        lease: float,
        wait_timeout: float,
    ) -> None:
        """
        Retain bounded acquisition settings and a unique release token.

        Parameters
        ----------
        backend : Any
            Storage backend implementing the cache operations.
        key : str
            Cache or lease key to access.
        lease : float
            Lease lifetime in seconds; use the store default when omitted.
        wait_timeout : float
            Maximum number of seconds to wait for ownership.

        Returns
        -------
        None
            Complete the operation without returning a value.
        """
        self._backend = backend
        self._key = backend.build_key(key + "-lock")
        self._lease = lease
        self._wait = wait_timeout
        self._owner = uuid4().hex

    async def _acquire(self: Self) -> None:
        """
        Poll atomic acquisition until cancellation or the outer timeout.

        Returns
        -------
        None
            Complete the operation without returning a value.
        """
        while True:
            try:
                await self._backend._add(self._key, self._owner, ttl=self._lease)
                return
            except ValueError:
                await asyncio.sleep(0.05)

    async def _release(self: Self) -> None:
        """
        Delete only this owner's lease, including after an uncertain acquisition.

        Returns
        -------
        None
            Complete the operation without returning a value.
        """
        async with asyncio.timeout(self._wait):
            await self._backend._redlock_release(self._key, self._owner)

    async def __aenter__(self: Self) -> Self:
        """
        Acquire a distributed lease with a finite waiting budget.

        Returns
        -------
        Self
            This lease after successful ownership acquisition.
        """
        try:
            async with asyncio.timeout(self._wait):
                await self._acquire()
        except BaseException:
            # SET may have succeeded when its reply was cancelled. Compare/delete
            # is safe even if another owner now holds the key. TTL is the fallback.
            with suppress(Exception):
                await complete_on_cancel(self._release())
            raise
        return self

    async def __aexit__(
        self: Self,
        _type: type[BaseException] | None,
        _value: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        """
        Finish bounded ownership cleanup before propagating cancellation.

        Parameters
        ----------
        _type : type[BaseException] | None
            Exception type raised by the context body, if any.
        _value : BaseException | None
            Exception raised by the context body, if any.
        _traceback : TracebackType | None
            Traceback attached to the context exception, if any.

        Returns
        -------
        None
            Complete the operation without returning a value.
        """
        await complete_on_cancel(self._release())

def resolver_lease(
    backend: Any,
    key: str,
    lease: float,
    wait_timeout: float,
) -> CacheLock | RedisResolverLease:
    """Choose Redis polling or preserve the native lock of another backend.

    Parameters
    ----------
    backend : Any
        Repository backend, including aiocache Redis subclasses.
    key : str
        Repository-prefixed lock key.
    lease : float
        Positive ownership lifetime in seconds.
    wait_timeout : float
        Maximum Redis acquisition wait and cleanup budget.

    Returns
    -------
    CacheLock | RedisResolverLease
        Context manager with backend-specific lease guarantees.
    """
    if _is_backend(backend, "aiocache.backends.redis", "RedisBackend"):
        return RedisResolverLease(backend, key, lease, wait_timeout)
    return CacheLock(backend, key, lease)
