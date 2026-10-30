from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from collections.abc import Callable

class ICacheRepository(ABC):

    # ruff: noqa: ANN401

    __slots__ = ()

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
        Coalesce overlapping misses, or explicitly reject unsupported stores.

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
        raise NotImplementedError

    @abstractmethod
    async def replace(
        self: Self, key: str, value: Any, ttl: float | None = None,
    ) -> bool:
        """Replace a live entry atomically without creating a missing key.

        Parameters
        ----------
        key : str
            Cache key that must already exist.
        value : Any
            Replacement value.
        ttl : float | None
            New lifetime in seconds, or None for no expiry.

        Returns
        -------
        bool
            True when replaced; False when missing, expired or superseded.
        """

    @abstractmethod
    async def get(self: Self, key: str) -> Any:
        """
        Retrieve the cached value for *key*.

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
        Store *value* under *key* with an optional TTL.

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
        Check whether *key* exists and has not expired.

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
        Remove *key* from the store.

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
        Remove all entries from the store.

        Returns
        -------
        bool
            ``True`` on success.
        """

    @abstractmethod
    async def getMany(self: Self, keys: list[str]) -> dict[str, Any]:
        """
        Retrieve multiple values at once.

        Parameters
        ----------
        keys : list[str]
            Cache keys.

        Returns
        -------
        dict[str, Any]
            Mapping of key → value; missing keys map to ``None``.
        """

    @abstractmethod
    async def setMany(
        self: Self,
        values: dict[str, Any],
        ttl: float | None = None,
    ) -> bool:
        """
        Store multiple key/value pairs with an optional TTL.

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
        Return and immediately delete *key* from the store.

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
        Store *value* only if *key* does not already exist.

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
        Increment the integer stored at *key* by *amount*.

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
        Decrement the integer stored at *key* by *amount*.

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
