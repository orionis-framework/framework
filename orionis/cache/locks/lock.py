# ruff: noqa: ANN401, BLE001, PLC0415, TC003
# Keep traceback annotations available and preserve body failures during cleanup.
"""Coordinate cache access through local locks or distributed leases."""

from __future__ import annotations
import asyncio
import sys
import types
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self
from weakref import WeakValueDictionary
from orionis.support.concurrency import complete_on_cancel

if TYPE_CHECKING:
    from aiocache.lock import RedLock


def _is_backend(backend: object, module_name: str, class_name: str) -> bool:
    """
    Check backend identity without importing an unused store.

    Parameters
    ----------
    backend : object
        Backend instance, including subclasses of built-in stores.
    module_name : str
        Defining module already loaded when its backend instance exists.
    class_name : str
        Backend class exported by the defining module.

    Returns
    -------
    bool
        Whether the instance belongs to the loaded backend class.
    """
    module = sys.modules.get(module_name)
    return module is not None and isinstance(backend, getattr(module, class_name))


# Share active file-cache locks within each event loop and storage directory.
_FILE_LOCKS: WeakValueDictionary[
    tuple[asyncio.AbstractEventLoop, Path, str],
    asyncio.Lock,
] = WeakValueDictionary()
"""Share active file-cache locks within each event loop and storage directory."""

# Default lease applied when no timeout is given, matching the Redis branch.
_DEFAULT_LEASE: float = 10
"""Default lease applied when no timeout is given, matching the Redis branch."""

# Delay between acquisition attempts while polling the database backend.
_POLL_INTERVAL: float = 0.05
"""Delay between acquisition attempts while polling the database backend."""


class CacheLock:
    """Coordinate cache access through local locks or distributed leases."""

    __slots__ = ("_backend", "_impl", "_key", "_owner", "_timeout")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self,
        backend: Any,
        key: str,
        timeout: float | None = None,
    ) -> None:
        """
        Initialize the lock for *key* on *backend*.

        Parameters
        ----------
        backend : typing.Any
            Raw cache backend.
        key : str
            Cache key to lock on.
        timeout : float | None
            File acquisition deadline, database acquisition deadline and lease,
            or aiocache lease, in seconds. None leaves file/database acquisition
            unbounded and uses the default lease where a lease applies.

        Returns
        -------
        None
            No return value.
        """
        self._backend = backend
        """Raw cache backend."""
        self._key = key
        """Cache key to lock on."""
        self._timeout = timeout
        """Store-specific acquisition timeout or lease duration in seconds."""
        self._impl: asyncio.Lock | RedLock | None = None
        """Underlying lock implementation selected for the cache backend."""
        self._owner: str | None = None
        """Ownership token used to identify the current holder."""

    async def __aenter__(self) -> Self:
        """
        Acquire the lock before entering the protected block.

        Returns
        -------
        typing.Self
            This ``CacheLock`` instance.
        """
        if _is_backend(
            self._backend,
            "orionis.cache.stores.file",
            "FileCacheBackend",
        ):
            identity = (
                asyncio.get_running_loop(),
                self._backend.lockNamespace,
                self._key,
            )
            lock = _FILE_LOCKS.get(identity)
            if lock is None:
                lock = asyncio.Lock()
                _FILE_LOCKS[identity] = lock
            if self._timeout is not None:
                await asyncio.wait_for(lock.acquire(), timeout=self._timeout)
            else:
                await lock.acquire()
            self._impl = lock
        elif _is_backend(
            self._backend,
            "orionis.cache.stores.database",
            "DatabaseCacheBackend",
        ):
            await self.__acquireDatabaseLock()
        else:
            from aiocache.lock import RedLock

            key = self._key
            if _is_backend(
                self._backend,
                "aiocache.backends.memory",
                "SimpleMemoryBackend",
            ):
                # RedLock's waiter events are global even for isolated memory stores.
                key = f"{id(self._backend)}:{key}"
            self._impl = RedLock(
                self._backend,
                key,
                lease=self._timeout or _DEFAULT_LEASE,
            )
            await self._impl.__aenter__()

        return self

    async def __acquireDatabaseLock(self) -> None:
        """
        Acquire the row-based database lock, polling until available.

        Mirrors the blocking semantics of the other branches: it waits
        until the lock is free, raising once *timeout* elapses.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        TimeoutError
            If the lock cannot be acquired before *timeout* elapses.
        """
        owner = uuid.uuid4().hex
        lease = self._timeout or _DEFAULT_LEASE
        loop = asyncio.get_running_loop()
        deadline = None if self._timeout is None else loop.time() + self._timeout

        try:
            while not await self._backend.acquireLock(self._key, owner, lease):
                if deadline is not None and loop.time() >= deadline:
                    msg = f"Timed out waiting for lock on {self._key!r}."
                    raise TimeoutError(msg)
                await asyncio.sleep(_POLL_INTERVAL)
        except BaseException:
            try:
                await complete_on_cancel(self._backend.releaseLock(self._key, owner))
            except Exception as cleanup_error:
                from orionis.failure.runtime import capture

                await capture(
                    cleanup_error,
                    flow="cache",
                    phase="cleanup",
                    operation="lock.release",
                )
            raise

        self._owner = owner

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """
        Release the lock after leaving the protected block.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            Exception type, if any.
        exc_val : BaseException | None
            Exception instance, if any.
        exc_tb : types.TracebackType | None
            Traceback object, if any.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        Exception
            If release fails without an earlier protected-operation failure.
        """
        try:
            if _is_backend(
                self._backend,
                "orionis.cache.stores.file",
                "FileCacheBackend",
            ):
                if isinstance(self._impl, asyncio.Lock):
                    self._impl.release()
                    self._impl = None
            elif _is_backend(
                self._backend,
                "orionis.cache.stores.database",
                "DatabaseCacheBackend",
            ):
                if self._owner is not None:
                    await complete_on_cancel(
                        self._backend.releaseLock(self._key, self._owner),
                    )
            elif self._impl is not None:
                await complete_on_cancel(
                    self._impl.__aexit__(exc_type, exc_val, exc_tb),
                )
        except Exception as cleanup_error:
            if exc_val is None:
                raise
            from orionis.failure.runtime import capture

            await capture(exc_val, flow="cache", phase="execution")
            await capture(
                cleanup_error,
                flow="cache",
                phase="cleanup",
                operation="lock.release",
            )
