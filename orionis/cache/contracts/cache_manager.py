from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from collections.abc import Callable
    from orionis.cache.contracts.repository import ICacheRepository

class ICacheManager(ABC):

    # ruff: noqa: ANN401

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
        Coalesce misses using the configured default store when supported.

        Parameters
        ----------
        key : str
            Cache or lease key to access.
        ttl : float | None
            Entry lifetime in seconds.
        resolver : Callable
            Callback that supplies the missing cache value.
        wait_timeout : float
            Maximum number of seconds to wait for ownership.
        lease : float | None
            Lease lifetime in seconds; use the store default when omitted.

        Returns
        -------
        Any
            Cached value or the result produced by the owning resolver.
        """
        return await self.store().rememberOnce(
            key,
            ttl,
            resolver,
            wait_timeout=wait_timeout,
            lease=lease,
        )

    @abstractmethod
    def store(self: Self, name: str | None = None) -> ICacheRepository:
        """
        Return the repository for the named (or default) store.

        Parameters
        ----------
        name : str | None
            Store name.  ``None`` selects the configured default.

        Returns
        -------
        ICacheRepository
            Repository bound to the requested store.
        """

    @abstractmethod
    async def get(self: Self, key: str) -> Any:
        """
        Retrieve the value for *key* from the default store.

        Parameters
        ----------
        key : str
            Cache key.

        Returns
        -------
        Any
            Cached value, or ``None`` when absent.
        """

    @abstractmethod
    async def set(self: Self, key: str, value: Any, ttl: float | None = None) -> bool:
        """
        Store *value* under *key* in the default store.

        Parameters
        ----------
        key : str
            Cache key.
        value : Any
            Value to cache.
        ttl : float | None
            Time-to-live in seconds.  ``None`` means no expiry.

        Returns
        -------
        bool
            ``True`` on success.
        """

    @abstractmethod
    async def has(self: Self, key: str) -> bool:
        """
        Check whether *key* exists in the default store.

        Parameters
        ----------
        key : str
            Cache key.

        Returns
        -------
        bool
            ``True`` if present and valid.
        """

    @abstractmethod
    async def delete(self: Self, key: str) -> bool:
        """
        Remove *key* from the default store.

        Parameters
        ----------
        key : str
            Cache key.

        Returns
        -------
        bool
            ``True`` if the key existed.
        """

    @abstractmethod
    async def clear(self: Self) -> bool:
        """
        Remove all entries from the default store.

        Returns
        -------
        bool
            ``True`` on success.
        """

    @abstractmethod
    async def getMany(self: Self, keys: list[str]) -> dict[str, Any]:
        """
        Retrieve multiple values from the default store.

        Parameters
        ----------
        keys : list[str]
            Cache keys.

        Returns
        -------
        dict[str, Any]
            Mapping of key → value.
        """

    @abstractmethod
    async def setMany(
        self: Self,
        values: dict[str, Any],
        ttl: float | None = None,
    ) -> bool:
        """
        Store multiple key/value pairs in the default store.

        Parameters
        ----------
        values : dict[str, Any]
            Mapping of key → value.
        ttl : float | None
            Shared TTL in seconds.

        Returns
        -------
        bool
            ``True`` on success.
        """

    @abstractmethod
    async def remember(
        self: Self,
        key: str,
        ttl: float | None,
        resolver: Callable,
    ) -> Any:
        """
        Return the cached value; resolve and cache if absent.

        Parameters
        ----------
        key : str
            Cache key.
        ttl : float | None
            TTL applied when caching the resolved value.
        resolver : Callable
            Zero-argument callable (sync or async) producing the value.

        Returns
        -------
        Any
            Cached or freshly computed value.
        """

    @abstractmethod
    async def rememberForever(self: Self, key: str, resolver: Callable) -> Any:
        """
        Return the cached value; resolve and cache forever if absent.

        Parameters
        ----------
        key : str
            Cache key.
        resolver : Callable
            Zero-argument callable (sync or async) producing the value.

        Returns
        -------
        Any
            Cached or freshly computed value.
        """

    @abstractmethod
    async def pull(self: Self, key: str) -> Any:
        """
        Return and immediately delete *key* from the default store.

        Parameters
        ----------
        key : str
            Cache key.

        Returns
        -------
        Any
            Cached value, or ``None`` when absent.
        """

    @abstractmethod
    async def add(self: Self, key: str, value: Any, ttl: float | None = None) -> bool:
        """
        Store *value* only if *key* is absent in the default store.

        Parameters
        ----------
        key : str
            Cache key.
        value : Any
            Value to store.
        ttl : float | None
            Optional TTL in seconds.

        Returns
        -------
        bool
            ``True`` on success, ``False`` when the key already exists.
        """

    @abstractmethod
    async def increment(self: Self, key: str, amount: int = 1) -> int:
        """
        Increment the integer at *key* in the default store.

        Parameters
        ----------
        key : str
            Cache key.
        amount : int
            Amount to add.

        Returns
        -------
        int
            New value after increment.
        """

    @abstractmethod
    async def decrement(self: Self, key: str, amount: int = 1) -> int:
        """
        Decrement the integer at *key* in the default store.

        Parameters
        ----------
        key : str
            Cache key.
        amount : int
            Amount to subtract.

        Returns
        -------
        int
            New value after decrement.
        """
