import asyncio
import inspect
import math
from contextlib import nullcontext
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Self
from weakref import WeakValueDictionary
from orionis.cache.contracts.repository import ICacheRepository
from orionis.cache.exceptions import CacheStoreException
from orionis.cache.locks.coalescing import resolver_lease
from orionis.cache.locks.lock import CacheLock

if TYPE_CHECKING:
    from collections.abc import Callable

# Sentinel that distinguishes a missing cache key from a stored None value.
_MISSING = object()

class _Flight:
    """Retain a completed result only while its concurrent waiters exist."""

    def __init__(self: Self) -> None:
        """
        Initialize the lock and unresolved value for concurrent cache callers.

        Returns
        -------
        None
            Complete the operation without returning a value.
        """
        self.lock = asyncio.Lock()
        self.value = _MISSING

_FLIGHTS: WeakValueDictionary[tuple, _Flight] = WeakValueDictionary()
_RESOLVING: ContextVar[frozenset[tuple]] = ContextVar(
    "orionis-cache-resolving",
    default=frozenset(),
)

class CacheRepository(ICacheRepository):
    """Async cache repository backed by a configurable storage backend.

    Wraps a low-level backend with optional key-prefix support and exposes
    a higher-level API (get, set, remember, lock, …).
    """

    # ruff: noqa: ANN401, PLC0415, SLF001

    __slots__ = ("_backend", "_prefix")

    def __init__(self: Self, backend: Any, prefix: str = "") -> None:
        """
        Initialise the repository with a backend and an optional key prefix.

        Parameters
        ----------
        backend : Any
            Storage backend implementing the low-level cache protocol.
        prefix : str, optional
            String prepended to every key, separated by ``:``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        # Store the backend and prefix for use in all subsequent operations.
        self._backend = backend
        self._prefix = prefix

    # ── Key helper ──────────────────────────────────────────────────────────

    def _k(self: Self, key: str) -> str:
        """
        Return the prefixed form of *key*.

        Parameters
        ----------
        key : str
            Raw cache key.

        Returns
        -------
        str
            Prefixed key, or the original key when no prefix is configured.
        """
        # Prepend the prefix only when one has been configured.
        return f"{self._prefix}:{key}" if self._prefix else key

    # ── Public API ──────────────────────────────────────────────────────────

    async def replace(
        self: Self, key: str, value: Any, ttl: float | None = None,
    ) -> bool:
        """Replace a live entry without resurrecting a deleted key.

        Parameters
        ----------
        key : str
            Existing cache key.
        value : Any
            Replacement value.
        ttl : float | None
            New lifetime in seconds, or None for no expiry.

        Returns
        -------
        bool
            True when the backend atomically accepted the replacement.

        Raises
        ------
        CacheStoreException
            If the backend has no atomic replacement primitive.
        """
        backend = self._backend
        prefixed = self._k(key)
        replace = getattr(backend, "replace", None)
        if callable(replace):
            return bool(await replace(prefixed, value, ttl=ttl))

        from aiocache import BaseCache
        from aiocache.lock import OptimisticLock, OptimisticLockError

        if not isinstance(backend, BaseCache):
            error_msg = "This cache backend does not support atomic replacement."
            raise CacheStoreException(error_msg)
        async with OptimisticLock(backend, prefixed) as lock:
            if lock._token is None:
                return False
            try:
                return await lock.cas(value, ttl=ttl)
            except OptimisticLockError:
                return False

    async def get(self: Self, key: str) -> Any:
        """
        Return the cached value for *key*, or ``None`` when absent.

        Parameters
        ----------
        key : str
            Cache key.

        Returns
        -------
        Any
            Cached value, or ``None`` when the key does not exist.
        """
        # Delegate the read to the backend using the prefixed key.
        return await self._backend.get(self._k(key))

    async def set(
        self: Self,
        key: str,
        value: Any,
        ttl: float | None = None,
    ) -> bool:
        """
        Store *value* under *key* with an optional time-to-live.

        Parameters
        ----------
        key : str
            Cache key.
        value : Any
            Value to store.
        ttl : float | None, optional
            Time-to-live in seconds.  ``None`` means no expiry.

        Returns
        -------
        bool
            ``True`` on success.
        """
        # Coerce the backend result to bool for a consistent return type.
        return bool(await self._backend.set(self._k(key), value, ttl=ttl))

    async def has(self: Self, key: str) -> bool:
        """
        Return ``True`` if *key* exists and has not expired.

        Parameters
        ----------
        key : str
            Cache key.

        Returns
        -------
        bool
            ``True`` when the key is present and still valid.
        """
        # Check existence without fetching the value.
        return bool(await self._backend.exists(self._k(key)))

    async def delete(self: Self, key: str) -> bool:
        """
        Remove *key* from the cache store.

        Parameters
        ----------
        key : str
            Cache key.

        Returns
        -------
        bool
            ``True`` if the key existed and was removed, ``False`` otherwise.
        """
        # Delegate deletion to the backend.
        return bool(await self._backend.delete(self._k(key)))

    async def clear(self: Self) -> bool:
        """
        Remove all entries from the cache store.

        Returns
        -------
        bool
            ``True`` on success.
        """
        # Flush the entire backend store.
        return bool(await self._backend.clear())

    async def getMany(self: Self, keys: list[str]) -> dict[str, Any]:
        """
        Return a mapping of key → value for all requested *keys*.

        Parameters
        ----------
        keys : list[str]
            Cache keys to fetch.

        Returns
        -------
        dict[str, Any]
            Mapping that preserves the original (un-prefixed) key names.
        """
        # Prefix all keys before the batch read.
        values = await self._backend.multi_get([self._k(k) for k in keys])
        # Re-associate results with their original unprefixed keys.
        return dict(zip(keys, values, strict=True))

    async def setMany(
        self: Self,
        values: dict[str, Any],
        ttl: float | None = None,
    ) -> bool:
        """
        Store multiple key/value pairs with an optional shared TTL.

        Parameters
        ----------
        values : dict[str, Any]
            Mapping of key → value to store.
        ttl : float | None, optional
            Shared time-to-live in seconds.  ``None`` means no expiry.

        Returns
        -------
        bool
            ``True`` on success.
        """
        # Build prefixed pairs before passing them to the backend.
        pairs = [(self._k(k), v) for k, v in values.items()]
        return bool(await self._backend.multi_set(pairs, ttl=ttl))

    async def remember(
        self: Self,
        key: str,
        ttl: float | None,
        resolver: Callable,
    ) -> Any:
        """
        Return the cached value for *key*, computing it on a cache miss.

        If the key is absent, call *resolver* (sync or async), persist the
        result for *ttl* seconds, and return it.

        Parameters
        ----------
        key : str
            Cache key.
        ttl : float | None
            TTL applied when storing the resolved value.  ``None`` means
            no expiry.
        resolver : Callable
            Zero-argument callable that produces the value.  May be async.

        Returns
        -------
        Any
            Cached value, or the freshly computed value on a miss.
        """
        # Use a sentinel so that a legitimately stored None is not treated
        # as a cache miss.
        cached = await self._backend.get(self._k(key), default=_MISSING)
        if cached is not _MISSING:
            return cached

        # Invoke the resolver; await the result when it is a coroutine.
        value = resolver()
        if inspect.isawaitable(value):
            value = await value

        # Persist the resolved value before returning it.
        await self.set(key, value, ttl=ttl)
        return value

    async def rememberOnce(
        self: Self,
        key: str,
        ttl: float | None,
        resolver: Callable,
        *,
        wait_timeout: float = 10,
        lease: float | None = None,
    ) -> Any:
        """
        Coalesce concurrent misses without changing ``remember`` semantics.

        Parameters
        ----------
        key : str
            Cache key within this repository's prefix.
        ttl : float | None
            Lifetime of the computed value, including a stored None.
        resolver : Callable
            Synchronous or asynchronous value producer.
        wait_timeout : float
            Maximum local or Redis admission wait in seconds, per phase.
        lease : float | None
            Optional backend lock lease for cross-process coalescing. Backend
            lock guarantees apply; a resolver must finish within the lease.

        Returns
        -------
        Any
            Cached or freshly resolved value. Failed or cancelled owners do
            not retain local locks; a later caller can retry.
        """
        if not math.isfinite(wait_timeout) or wait_timeout <= 0:
            error_msg = "Cache wait_timeout must be finite and positive."
            raise ValueError(error_msg)
        if lease is not None and (not math.isfinite(lease) or lease <= 0):
            error_msg = "Cache lease must be finite and positive."
            raise ValueError(error_msg)
        identity = (asyncio.get_running_loop(), id(self._backend), self._k(key))
        resolving = _RESOLVING.get()
        if identity in resolving:
            error_msg = "A coalesced cache resolver cannot recursively resolve its key."
            raise RuntimeError(error_msg)
        cached = await self._backend.get(self._k(key), default=_MISSING)
        if cached is not _MISSING:
            return cached
        flight = _FLIGHTS.get(identity)
        if flight is None:
            flight = _Flight()
            _FLIGHTS[identity] = flight
        async with asyncio.timeout(wait_timeout):
            await flight.lock.acquire()
        token = _RESOLVING.set(resolving | {identity})
        try:
            if flight.value is not _MISSING:
                return flight.value
            distributed = (
                resolver_lease(
                    self._backend,
                    self._k(f"remember:{key}"),
                    lease,
                    wait_timeout,
                )
                if lease
                else nullcontext()
            )
            async with distributed:
                flight.value = await self.remember(key, ttl, resolver)
                return flight.value
        finally:
            _RESOLVING.reset(token)
            flight.lock.release()

    async def rememberForever(self: Self, key: str, resolver: Callable) -> Any:
        """
        Cache the value for *key* indefinitely, resolving on a miss.

        Parameters
        ----------
        key : str
            Cache key.
        resolver : Callable
            Zero-argument callable that produces the value.  May be async.

        Returns
        -------
        Any
            Cached value, or the freshly computed value on a miss.
        """
        # Delegate to remember with no TTL so the entry never expires.
        return await self.remember(key, None, resolver)

    async def pull(self: Self, key: str) -> Any:
        """
        Return the cached value for *key* and immediately remove it.

        Parameters
        ----------
        key : str
            Cache key.

        Returns
        -------
        Any
            Cached value, or ``None`` when the key is absent.
        """
        # Use the sentinel to distinguish a missing key from a stored None.
        value = await self._backend.get(self._k(key), default=_MISSING)
        if value is _MISSING:
            return None
        # Remove the key after successfully reading it.
        await self.delete(key)
        return value

    async def add(
        self: Self,
        key: str,
        value: Any,
        ttl: float | None = None,
    ) -> bool:
        """
        Store *value* under *key* only when the key does not already exist.

        Parameters
        ----------
        key : str
            Cache key.
        value : Any
            Value to store.
        ttl : float | None, optional
            Optional time-to-live in seconds.

        Returns
        -------
        bool
            ``True`` on success, ``False`` when the key already exists.
        """
        try:
            # Attempt an atomic add; the backend raises ValueError on conflict.
            await self._backend.add(self._k(key), value, ttl=ttl)
            return True
        except ValueError:
            # Key already exists; report the conflict without re-raising.
            return False

    async def increment(self: Self, key: str, amount: int = 1) -> int:
        """
        Increment the integer stored at *key* by *amount*.

        Parameters
        ----------
        key : str
            Cache key.
        amount : int, optional
            Positive integer to add.  Defaults to ``1``.

        Returns
        -------
        int
            New value after the increment.
        """
        # Delegate the positive increment to the backend.
        return await self._backend.increment(self._k(key), amount)

    async def decrement(self: Self, key: str, amount: int = 1) -> int:
        """
        Decrement the integer stored at *key* by *amount*.

        Parameters
        ----------
        key : str
            Cache key.
        amount : int, optional
            Positive integer to subtract.  Defaults to ``1``.

        Returns
        -------
        int
            New value after the decrement.
        """
        # Negate the amount to reuse the backend's increment operation.
        return await self._backend.increment(self._k(key), -amount)

    def lock(self: Self, key: str, timeout: float | None = None) -> CacheLock:
        """
        Return an async context manager that acquires a distributed lock.

        Parameters
        ----------
        key : str
            Resource key to lock.
        timeout : float | None, optional
            Maximum lock duration in seconds.  ``None`` means no timeout.

        Returns
        -------
        CacheLock
            Async context manager for the requested lock.
        """
        # Build a CacheLock bound to the prefixed key and optional timeout.
        return CacheLock(self._backend, self._k(key), timeout)
