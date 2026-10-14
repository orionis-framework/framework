from __future__ import annotations
import asyncio
import sys
import uuid
from typing import TYPE_CHECKING, Any, Self
from weakref import WeakValueDictionary

if TYPE_CHECKING:
    import types
    from aiocache.lock import RedLock
    from pathlib import Path

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
    tuple[asyncio.AbstractEventLoop, Path, str], asyncio.Lock,
] = WeakValueDictionary()

# Default lease applied when no timeout is given, matching the Redis branch.
_DEFAULT_LEASE: float = 10

# Delay between acquisition attempts while polling the database backend.
_POLL_INTERVAL: float = 0.05

class CacheLock:

    # ruff: noqa: ANN401, PLC0415

    __slots__ = ("_backend", "_impl", "_key", "_owner", "_timeout")

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
        backend : Any
            Raw cache backend.
        key : str
            Cache key to lock on.
        timeout : float | None
            Lock timeout in seconds.  ``None`` means no timeout.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self._backend = backend
        self._key = key
        self._timeout = timeout
        self._impl: asyncio.Lock | RedLock | None = None
        self._owner: str | None = None

    async def __aenter__(self) -> Self:
        """
        Acquire the lock before entering the protected block.

        Returns
        -------
        Self
            This ``CacheLock`` instance.
        """
        if _is_backend(
            self._backend, "orionis.cache.stores.file", "FileCacheBackend",
        ):
            identity = (
                asyncio.get_running_loop(), self._backend.lockNamespace, self._key,
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
            self._backend, "orionis.cache.stores.database", "DatabaseCacheBackend",
        ):
            await self.__acquireDatabaseLock()
        else:
            from aiocache.lock import RedLock

            self._impl = RedLock(
                self._backend,
                self._key,
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
            This method does not return a value.

        Raises
        ------
        TimeoutError
            If the lock cannot be acquired before *timeout* elapses.
        """
        owner = uuid.uuid4().hex
        lease = self._timeout or _DEFAULT_LEASE
        loop = asyncio.get_running_loop()
        deadline = None if self._timeout is None else loop.time() + self._timeout

        while not await self._backend.acquireLock(self._key, owner, lease):
            if deadline is not None and loop.time() >= deadline:
                msg = f"Timed out waiting for lock on {self._key!r}."
                raise TimeoutError(msg)
            await asyncio.sleep(_POLL_INTERVAL)

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
            Complete the documented operation without returning a value.
        """
        if _is_backend(
            self._backend, "orionis.cache.stores.file", "FileCacheBackend",
        ):
            if isinstance(self._impl, asyncio.Lock):
                self._impl.release()
                self._impl = None
        elif _is_backend(
            self._backend, "orionis.cache.stores.database", "DatabaseCacheBackend",
        ):
            if self._owner is not None:
                await self._backend.releaseLock(self._key, self._owner)
        elif self._impl is not None:
            await self._impl.__aexit__(exc_type, exc_val, exc_tb)
