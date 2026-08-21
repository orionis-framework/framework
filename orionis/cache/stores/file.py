from __future__ import annotations
import asyncio
import hashlib
import secrets
import threading
import time
from typing import TYPE_CHECKING, Any
import msgspec
import msgspec.json as _msgjson

if TYPE_CHECKING:
    from pathlib import Path

# Sentinel object to distinguish "key not found" from a stored None value.
_MISSING = object()

# Retry budget for a rename refused because another process holds the target.
_REPLACE_ATTEMPTS: int = 3
_REPLACE_BACKOFF_SECONDS: float = 0.005

class FileCacheBackend:

    # ruff: noqa: ANN401

    __slots__ = ("_counter_lock", "_path", "_rename_lock")

    def __init__(self, path: Path) -> None:
        """
        Initialize the backend and create the cache directory if needed.

        Parameters
        ----------
        path : Path
            Directory where cache files will be stored.
        """
        self._path: Path = path
        # Serializes the read-modify-write cycle of increment() in this loop.
        self._counter_lock = asyncio.Lock()
        # Writes run in worker threads, so the rename needs a thread lock.
        self._rename_lock = threading.Lock()
        path.mkdir(parents=True, exist_ok=True)

    # ── Internal helpers ────────────────────────────────────────────────────

    def __file(self, key: str) -> Path:
        """
        Return the filesystem path for *key*.

        Parameters
        ----------
        key : str
            Cache key.

        Returns
        -------
        Path
            Path to the corresponding ``.json`` file.
        """
        digest = hashlib.sha256(key.encode()).hexdigest()
        return self._path / f"{digest}.json"

    @staticmethod
    def __tempPath(file: Path) -> Path:
        """
        Return a unique staging path for *file*.

        Parameters
        ----------
        file : Path
            Target cache file.

        Returns
        -------
        Path
            Sibling path ending in ``.tmp`` that no concurrent writer of
            the same key can collide with.
        """
        return file.with_name(f"{file.name}.{secrets.token_hex(8)}.tmp")

    def __readSync(self, file: Path) -> dict | None:
        """
        Read and decode a cache file synchronously.

        Parameters
        ----------
        file : Path
            Path to the cache file.

        Returns
        -------
        dict | None
            Decoded entry, or ``None`` on any error.
        """
        try:
            return _msgjson.decode(file.read_bytes())
        except (OSError, msgspec.DecodeError):
            return None

    def __writeSync(self, file: Path, entry: dict) -> None:
        """
        Atomically write *entry* to *file* via tmp-then-rename.

        Parameters
        ----------
        file : Path
            Target cache file.
        entry : dict
            Serializable cache entry.

        Raises
        ------
        OSError
            If the entry cannot be staged or renamed into place.
        """
        data = _msgjson.encode(entry)
        tmp = self.__tempPath(file)
        try:
            tmp.write_bytes(data)
            self.__replaceSync(tmp, file)
        except OSError:
            tmp.unlink(missing_ok=True)
            raise

    def __replaceSync(self, tmp: Path, file: Path) -> None:
        """
        Publish *tmp* as *file*, retrying a transient sharing violation.

        Parameters
        ----------
        tmp : Path
            Staging file holding the encoded entry.
        file : Path
            Destination cache file.

        Raises
        ------
        OSError
            If the rename keeps failing after the last attempt.
        """
        last = _REPLACE_ATTEMPTS - 1
        for attempt in range(_REPLACE_ATTEMPTS):
            try:
                with self._rename_lock:
                    tmp.replace(file)
            except PermissionError:
                # Windows refuses the rename while another process swaps it.
                if attempt == last:
                    raise
                time.sleep(_REPLACE_BACKOFF_SECONDS)
            else:
                return

    def __createSync(self, file: Path, entry: dict) -> bool:
        """
        Write *entry* to *file* only when the file does not exist yet.

        Parameters
        ----------
        file : Path
            Target cache file.
        entry : dict
            Serializable cache entry.

        Returns
        -------
        bool
            ``True`` when the file was created by this call, ``False``
            when another writer got there first.
        """
        try:
            with file.open("xb") as handle:
                handle.write(_msgjson.encode(entry))
        except FileExistsError:
            return False
        return True

    def __unlinkSync(self, file: Path) -> None:
        """
        Remove *file*, ignoring missing-file errors.

        Parameters
        ----------
        file : Path
            File to remove.
        """
        file.unlink(missing_ok=True)

    # ── Public async API (mirrors aiocache BaseCache interface) ─────────────

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Return the cached value for *key*, or *default* when absent/expired.

        Expired entries are deleted on first read (lazy eviction).

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
        file = self.__file(key)
        entry = await asyncio.to_thread(self.__readSync, file)
        if entry is None:
            return default

        exp: float | None = entry.get("e")
        if exp is not None and time.monotonic() > exp:
            await asyncio.to_thread(self.__unlinkSync, file)
            return default

        return entry.get("v")

    async def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
        """
        Store *value* under *key* with an optional TTL in seconds.

        Parameters
        ----------
        key : str
            Cache key.
        value : Any
            JSON-serializable value to cache.
        ttl : float | None
            Time-to-live in seconds. None means no expiry.

        Returns
        -------
        bool
            Always True.
        """
        entry: dict[str, Any] = {
            "v": value,
            "e": time.monotonic() + ttl if ttl is not None else None,
        }
        file = self.__file(key)
        await asyncio.to_thread(self.__writeSync, file, entry)
        return True

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
        file = self.__file(key)
        try:
            await asyncio.to_thread(file.unlink)
            return 1
        except FileNotFoundError:
            return 0

    async def clear(self) -> bool:
        """
        Remove all cache entries from the store directory.

        Returns
        -------
        bool
            Always True.
        """
        def _clear_all() -> None:
            for f in self._path.glob("*.json"):
                f.unlink(missing_ok=True)
            for f in self._path.glob("*.tmp"):
                f.unlink(missing_ok=True)

        await asyncio.to_thread(_clear_all)
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
        Store multiple key/value pairs with an optional TTL.

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

        The entry is created with an exclusive open, so concurrent callers
        never both succeed and the operation is safe as a mutual-exclusion
        primitive.

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
        entry: dict[str, Any] = {
            "v": value,
            "e": time.monotonic() + ttl if ttl is not None else None,
        }
        file = self.__file(key)
        created = await asyncio.to_thread(self.__createSync, file, entry)

        # exists() evicts an expired entry, releasing the slot for a retry.
        if not created and not await self.exists(key):
            created = await asyncio.to_thread(self.__createSync, file, entry)

        if not created:
            msg = f"Key {key!r} already exists in the cache."
            raise ValueError(msg)

        return created

    async def increment(self, key: str, delta: int = 1) -> int:
        """
        Increment the integer stored at *key* by *delta*.

        Creates the key with value *delta* if it does not exist, and keeps
        the expiry of an existing entry untouched.

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
        file = self.__file(key)
        async with self._counter_lock:
            entry = await asyncio.to_thread(self.__readSync, file)
            current: Any = 0
            expiration: float | None = None

            if entry is not None:
                stored_expiry: float | None = entry.get("e")
                if stored_expiry is None or time.monotonic() <= stored_expiry:
                    current = entry.get("v") or 0
                    expiration = stored_expiry

            new_value = int(current) + delta
            await asyncio.to_thread(
                self.__writeSync,
                file,
                {"v": new_value, "e": expiration},
            )
        return new_value
