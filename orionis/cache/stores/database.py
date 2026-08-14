from __future__ import annotations
import asyncio
import time
from typing import TYPE_CHECKING, Any
import msgspec
import msgspec.json as _msgjson
from orionis.database.exceptions import QueryException
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, String, Text

if TYPE_CHECKING:
    from orionis.database.contracts.connection import IConnection

# Sentinel object to distinguish "key not found" from a stored None value.
_MISSING = object()

# Default lock table used when the config does not declare one explicitly.
_DEFAULT_LOCK_TABLE = "cache_locks"


def _buildEntriesTable(table: str) -> TableDefinition:
    """
    Build the table definition for the cache entries table.

    Parameters
    ----------
    table : str
        Logical table name for cache entries.

    Returns
    -------
    TableDefinition
        Definition with ``cache_key`` (primary key), ``cache_value``
        (JSON payload) and ``expiration`` (epoch seconds, nullable)
        columns.
    """
    key_column = String(255).primary()
    key_column.name = "cache_key"

    value_column = Text().nullable()
    value_column.name = "cache_value"

    expiration_column = BigInteger().nullable()
    expiration_column.name = "expiration"

    return TableDefinition(
        name=table,
        columns={
            "cache_key": key_column,
            "cache_value": value_column,
            "expiration": expiration_column,
        },
        primary_key="cache_key",
    )


def _buildLocksTable(table: str) -> TableDefinition:
    """
    Build the table definition for the atomic-locks table.

    Parameters
    ----------
    table : str
        Logical table name for cache locks.

    Returns
    -------
    TableDefinition
        Definition with ``cache_key`` (primary key), ``owner`` and
        ``expiration`` (epoch seconds) columns.
    """
    key_column = String(255).primary()
    key_column.name = "cache_key"

    owner_column = String(255).nullable()
    owner_column.name = "owner"

    expiration_column = BigInteger().nullable()
    expiration_column.name = "expiration"

    return TableDefinition(
        name=table,
        columns={
            "cache_key": key_column,
            "owner": owner_column,
            "expiration": expiration_column,
        },
        primary_key="cache_key",
    )


class DatabaseCacheBackend:
    """
    Cache backend that stores entries in a relational database table.

    Mirrors ``database`` cache store: entries live in a
    dedicated table (``cache_key`` / ``cache_value`` / ``expiration``)
    resolved through the ``cache.stores.database`` configuration, and
    atomic locks used by ``Cache::lock()`` are kept in a separate
    ``cache_locks``-like table so the ``database`` driver does not
    require Redis or Memcached to support locking.
    """

    # ruff: noqa: ANN401

    __slots__ = ("_connection", "_lock_table", "_ready", "_ready_lock", "_table")

    def __init__(
        self,
        connection: IConnection,
        table: str,
        lock_table: str | None = None,
    ) -> None:
        """
        Initialize the backend bound to a connection and table names.

        Parameters
        ----------
        connection : IConnection
            Database connection used to store cache entries and locks.
        table : str
            Table name used to store cache entries.
        lock_table : str | None, optional
            Table name used to store atomic locks. Defaults to
            ``'cache_locks'`` when not provided.
        """
        self._connection = connection
        self._table = table
        self._lock_table = lock_table or _DEFAULT_LOCK_TABLE
        self._ready = False
        self._ready_lock = asyncio.Lock()

    # ── Schema bootstrap ─────────────────────────────────────────────────────

    async def _ensureSchema(self) -> None:
        """
        Create the cache and lock tables on first use, if missing.

        Returns
        -------
        None
            This method does not return a value.
        """
        if self._ready:
            return
        async with self._ready_lock:
            if self._ready:
                return
            await self._connection.createTable(_buildEntriesTable(self._table))
            await self._connection.createTable(_buildLocksTable(self._lock_table))
            self._ready = True

    # ── Serialization helpers ────────────────────────────────────────────────

    def __encode(self, value: Any) -> str:
        """
        Serialize *value* to a JSON string suitable for storage.

        Parameters
        ----------
        value : Any
            JSON-serializable value to encode.

        Returns
        -------
        str
            UTF-8 decoded JSON payload.
        """
        return _msgjson.encode(value).decode()

    def __decode(self, raw: str | bytes | None) -> Any:
        """
        Deserialize a stored JSON payload back into a Python object.

        Parameters
        ----------
        raw : str | bytes | None
            Raw payload read from the ``cache_value`` column.

        Returns
        -------
        Any
            Decoded value, or ``None`` when *raw* is missing or invalid.
        """
        if raw is None:
            return None
        data = raw.encode() if isinstance(raw, str) else raw
        try:
            return _msgjson.decode(data)
        except msgspec.DecodeError:
            return None

    # ── Public async API (mirrors FileCacheBackend) ──────────────────────────

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Return the cached value for *key*, or *default* when absent/expired.

        Expired entries are deleted on first read (lazy eviction),
        mirroring ``DatabaseStore::get()``.

        Parameters
        ----------
        key : str
            Cache key.
        default : Any
            Value returned when the key is not found or has expired.

        Returns
        -------
        Any
            Stored value or *default*.
        """
        await self._ensureSchema()
        rows = await self._connection.select(
            f"SELECT cache_value, expiration FROM {self._table} "  # noqa: S608
            "WHERE cache_key = :k",
            {"k": key},
        )
        if not rows:
            return default

        row = rows[0]
        expiration = row.get("expiration")
        if expiration is not None and time.time() >= expiration:
            await self.delete(key)
            return default

        return self.__decode(row.get("cache_value"))

    async def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
        """
        Store *value* under *key* with an optional TTL in seconds.

        Updates the row when it already exists, otherwise inserts a new
        one, providing upsert semantics across every supported dialect
        without relying on driver-specific ``ON CONFLICT`` syntax.

        Parameters
        ----------
        key : str
            Cache key.
        value : Any
            JSON-serializable value to cache.
        ttl : float | None
            Time-to-live in seconds. ``None`` means no expiry.

        Returns
        -------
        bool
            Always True.
        """
        await self._ensureSchema()
        encoded = self.__encode(value)
        expiration = time.time() + ttl if ttl is not None else None

        updated = await self._connection.execute(
            f"UPDATE {self._table} SET cache_value = :v, expiration = :e "  # noqa: S608
            "WHERE cache_key = :k",
            {"v": encoded, "e": expiration, "k": key},
        )
        if not updated:
            await self.__insertOrRetryUpdate(key, encoded, expiration)
        return True

    async def __insertOrRetryUpdate(
        self,
        key: str,
        encoded: str,
        expiration: float | None,
    ) -> None:
        """
        Insert a new cache row, falling back to an update on conflict.

        Parameters
        ----------
        key : str
            Cache key.
        encoded : str
            JSON-encoded value already serialized by :meth:`set`.
        expiration : float | None
            Absolute expiration timestamp, or ``None`` for no expiry.

        Returns
        -------
        None
            This method does not return a value.
        """
        try:
            await self._connection.execute(
                f"INSERT INTO {self._table} "  # noqa: S608
                "(cache_key, cache_value, expiration) VALUES (:k, :v, :e)",
                {"k": key, "v": encoded, "e": expiration},
            )
        except QueryException:
            # Another writer inserted the row first; retry as an update.
            await self._connection.execute(
                f"UPDATE {self._table} SET cache_value = :v, "  # noqa: S608
                "expiration = :e WHERE cache_key = :k",
                {"v": encoded, "e": expiration, "k": key},
            )

    async def exists(self, key: str) -> bool:
        """
        Return True if *key* exists and has not expired.

        Parameters
        ----------
        key : str
            Cache key.

        Returns
        -------
        bool
        """
        return await self.get(key, default=_MISSING) is not _MISSING

    async def delete(self, key: str) -> int:
        """
        Remove *key* from the store.

        Parameters
        ----------
        key : str
            Cache key.

        Returns
        -------
        int
            1 if the key existed, 0 otherwise.
        """
        await self._ensureSchema()
        return await self._connection.execute(
            f"DELETE FROM {self._table} WHERE cache_key = :k",  # noqa: S608
            {"k": key},
        )

    async def clear(self) -> bool:
        """
        Remove all cache entries from the store table.

        Returns
        -------
        bool
            Always True.
        """
        await self._ensureSchema()
        await self._connection.execute(f"DELETE FROM {self._table}")  # noqa: S608
        return True

    async def multiGet(self, keys: list[str], default: Any = None) -> list[Any]:
        """
        Return a list of values for *keys* in the same order.

        Parameters
        ----------
        keys : list[str]
            Cache keys.
        default : Any
            Returned for each missing/expired key.

        Returns
        -------
        list[Any]
        """
        return [await self.get(k, default) for k in keys]

    async def multiSet(
        self,
        pairs: list[tuple[str, Any]],
        ttl: float | None = None,
    ) -> bool:
        """
        Store multiple key/value pairs with an optional shared TTL.

        Parameters
        ----------
        pairs : list[tuple[str, Any]]
            Sequence of (key, value) pairs.
        ttl : float | None
            Shared TTL applied to every pair.

        Returns
        -------
        bool
            Always True.
        """
        for key, value in pairs:
            await self.set(key, value, ttl=ttl)
        return True

    # aiocache-compatible aliases so CacheRepository.getMany/setMany work
    # with this backend without modification.

    async def multi_get(
        self,
        keys: list[str],
        default: Any = None,
    ) -> list[Any]:
        """
        Return a list of values for *keys* (aiocache-compatible alias).

        Parameters
        ----------
        keys : list[str]
            Cache keys.
        default : Any
            Returned for each missing/expired key.

        Returns
        -------
        list[Any]
        """
        return await self.multiGet(keys, default)

    async def multi_set(
        self,
        pairs: list[tuple[str, Any]],
        ttl: float | None = None,
    ) -> bool:
        """
        Store multiple key/value pairs (aiocache-compatible alias).

        Parameters
        ----------
        pairs : list[tuple[str, Any]]
            Sequence of (key, value) pairs.
        ttl : float | None
            Shared TTL applied to every pair.

        Returns
        -------
        bool
            Always True.
        """
        return await self.multiSet(pairs, ttl=ttl)

    async def add(self, key: str, value: Any, ttl: float | None = None) -> bool:
        """
        Store *value* under *key* only if the key does not already exist.

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
            True on success.

        Raises
        ------
        ValueError
            If the key already exists and has not expired.
        """
        if await self.exists(key):
            msg = f"Key {key!r} already exists in the cache."
            raise ValueError(msg)
        return await self.set(key, value, ttl=ttl)

    async def increment(self, key: str, delta: int = 1) -> int:
        """
        Increment the integer stored at *key* by *delta*.

        Creates the key with value *delta* if it does not exist. The
        read/modify/write cycle runs inside a single database
        transaction, mirroring ``DatabaseStore::increment()``.

        Parameters
        ----------
        key : str
            Cache key.
        delta : int
            Amount to add (use negative values to decrement).

        Returns
        -------
        int
            New value after increment.
        """
        await self._ensureSchema()
        await self._connection.begin()
        try:
            new_value = await self.__incrementLocked(key, delta)
        except Exception:
            await self._connection.rollback()
            raise
        else:
            await self._connection.commit()
            return new_value

    async def __incrementLocked(self, key: str, delta: int) -> int:
        """
        Apply the increment while an outer transaction is active.

        Parameters
        ----------
        key : str
            Cache key.
        delta : int
            Amount to add to the current value.

        Returns
        -------
        int
            New value after the increment.
        """
        rows = await self._connection.select(
            f"SELECT cache_value, expiration FROM {self._table} "  # noqa: S608
            "WHERE cache_key = :k",
            {"k": key},
        )
        now = time.time()
        row = rows[0] if rows else None
        expired = row is not None and (
            row.get("expiration") is not None and row["expiration"] <= now
        )

        if row is None or expired:
            new_value = delta
            await self._connection.execute(
                f"DELETE FROM {self._table} WHERE cache_key = :k",  # noqa: S608
                {"k": key},
            )
            await self._connection.execute(
                f"INSERT INTO {self._table} "  # noqa: S608
                "(cache_key, cache_value, expiration) VALUES (:k, :v, NULL)",
                {"k": key, "v": self.__encode(new_value)},
            )
            return new_value

        current = self.__decode(row.get("cache_value")) or 0
        new_value = int(current) + delta
        await self._connection.execute(
            f"UPDATE {self._table} SET cache_value = :v "  # noqa: S608
            "WHERE cache_key = :k",
            {"v": self.__encode(new_value), "k": key},
        )
        return new_value

    # ── Atomic locks (backing orionis.cache.locks.lock.CacheLock) ───────────

    async def acquireLock(self, key: str, owner: str, lease: float) -> bool:
        """
        Attempt to acquire the row-based lock for *key* in a single try.

        Inserts a fresh row for the lock, or steals an expired or
        self-owned row when the insert conflicts, mirroring
        ``DatabaseLock::acquire()``.

        Parameters
        ----------
        key : str
            Resource key to lock.
        owner : str
            Unique token identifying the caller attempting to acquire.
        lease : float
            Number of seconds the lock remains valid once acquired.

        Returns
        -------
        bool
            True when the lock was acquired.
        """
        await self._ensureSchema()
        now = time.time()
        expiration = now + lease
        try:
            await self._connection.execute(
                f"INSERT INTO {self._lock_table} "  # noqa: S608
                "(cache_key, owner, expiration) VALUES (:k, :o, :e)",
                {"k": key, "o": owner, "e": expiration},
            )
        except QueryException:
            updated = await self._connection.execute(
                f"UPDATE {self._lock_table} SET owner = :o, "  # noqa: S608
                "expiration = :e WHERE cache_key = :k "
                "AND (owner = :o OR expiration <= :now)",
                {"k": key, "o": owner, "e": expiration, "now": now},
            )
            return updated > 0
        return True

    async def releaseLock(self, key: str, owner: str) -> None:
        """
        Release the row-based lock for *key* when still owned by *owner*.

        Parameters
        ----------
        key : str
            Resource key to release.
        owner : str
            Token that must match the current row owner.

        Returns
        -------
        None
            This method does not return a value.
        """
        await self._connection.execute(
            f"DELETE FROM {self._lock_table} "  # noqa: S608
            "WHERE cache_key = :k AND owner = :o",
            {"k": key, "o": owner},
        )


def build(
    connection: IConnection,
    table: str,
    lock_table: str | None = None,
) -> DatabaseCacheBackend:
    """
    Build and return a ``DatabaseCacheBackend``.

    Parameters
    ----------
    connection : IConnection
        Database connection used to store cache entries and locks.
    table : str
        Table name used to store cache entries.
    lock_table : str | None
        Table name used to store atomic locks.

    Returns
    -------
    DatabaseCacheBackend
        Configured database-backed cache backend.
    """
    return DatabaseCacheBackend(
        connection=connection,
        table=table,
        lock_table=lock_table,
    )
