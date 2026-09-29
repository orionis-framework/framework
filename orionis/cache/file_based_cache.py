from __future__ import annotations
import hashlib
from pathlib import Path
import struct
import time
from orionis.cache.serializer import Serializer

class FileBasedCache:

    __slots__ = (
        "__file",
        "__file_resolved",
        "__hashInterval",
        "__lasthashcheck",
        "__monitored_dirs",
        "__monitored_files",
        "__path",
        "__sourceshashcache",
    )

    CACHE_VERSION = 1

    def __init__(
        self,
        path: Path,
        filename: str,
        monitored_dirs: list[Path] | None = None,
        monitored_files: list[Path] | None = None,
    ) -> None:
        """
        Initialize the FileBasedCache instance.

        Parameters
        ----------
        path : Path
            Directory path where the cache file will be stored.
        filename : str
            Name of the cache file.
        monitored_dirs : list[Path] or None, optional
            List of directories to monitor for changes.
        monitored_files : list[Path] or None, optional
            List of files to monitor for changes.

        Returns
        -------
        None
            This method does not return a value.
        """
        if not isinstance(path, Path):
            error_msg = "path must be Path"
            raise TypeError(error_msg)

        self.__path = path
        self.__file = path / filename
        # Resolved once at init time — avoids repeated syscalls in the hot path
        self.__file_resolved = self.__file.resolve()

        # Directories and files to monitor for cache invalidation
        self.__monitored_dirs = monitored_dirs or []
        self.__monitored_files = monitored_files or []

        # Ensure the cache directory exists
        self.__path.mkdir(parents=True, exist_ok=True)

        # Internal cache for source hash and timing
        self.__sourceshashcache: str | None = None
        self.__lasthashcheck: float = 0.0
        self.__hashInterval: float = 0.5

    def get(self) -> dict | None:
        """
        Retrieve cached data if valid.

        Returns
        -------
        dict or None
            The cached data if valid, otherwise None.
        """
        # EAFP: loadFromFile handles the missing-file case with a single syscall
        payload = Serializer.loadFromFile(self.__file)
        if not payload:
            return None

        # Extract metadata and validate
        meta = payload.get("__meta__")
        if not meta:
            return None

        # Check cache version
        if meta.get("version") != self.CACHE_VERSION:
            return None

        # Check if sources hash matches
        if meta.get("sourcesHash") != self.__computeSourcesHash():
            return None

        return payload.get("__data__")

    def save(self, data: dict) -> tuple[int, str]:
        """
        Save the provided data to the cache file if it has changed.

        Parameters
        ----------
        data : dict
            The data to be cached.

        Returns
        -------
        tuple[int, str]
            A tuple containing the cache version and the sources hash.
        """
        # Validate that the input data is a dictionary
        if not isinstance(data, dict):
            error_msg = "data must be dict"
            raise TypeError(error_msg)

        # Compute the hash of monitored sources for cache validation
        sourceshash = self.__computeSourcesHash()

        # Load existing cache and skip write if nothing has changed.
        # loadFromFile uses EAFP internally — no redundant exists() check needed.
        existing = Serializer.loadFromFile(self.__file)
        if existing:
            existingmeta = existing.get("__meta__", {})
            # Short-circuit: version or hash mismatch skips the data comparison
            if (
                existingmeta.get("version") == self.CACHE_VERSION
                and existingmeta.get("sourcesHash") == sourceshash
                and existing.get("__data__") == data
            ):
                return self.CACHE_VERSION, sourceshash

        newpayload = {
            "__meta__": {
                "version": self.CACHE_VERSION,
                "generatedAt": int(time.time()),
                "sourcesHash": sourceshash,
            },
            "__data__": data,
        }

        Serializer.dumpToFile(newpayload, self.__file)
        return self.CACHE_VERSION, sourceshash

    def clear(self) -> bool:
        """
        Remove the cache file if it exists.

        Returns
        -------
        bool
            True if the cache file was removed, False if it did not exist.
        """
        try:
            self.__file.unlink()
            return True
        except FileNotFoundError:
            return False

    def __collectFromDirs(
        self,
        cache_file: Path,
        seen: set[str],
        result: list[tuple[str, Path]],
    ) -> None:
        """
        Collect deduplicated Python files from monitored directories.

        Parameters
        ----------
        cache_file : Path
            Resolved cache file path to exclude from collection.
        seen : set[str]
            Set of already collected POSIX paths used for deduplication.
        result : list[tuple[str, Path]]
            Output list updated in place with ``(posix_path, resolved_path)`` tuples.

        Returns
        -------
        None
            This method updates ``result`` in place.
        """
        for directory in self.__monitored_dirs:
            if directory.is_dir():
                for file in directory.rglob("*.py"):
                    resolved = file.resolve()
                    if resolved == cache_file:
                        continue
                    posix = resolved.as_posix()
                    if posix not in seen:
                        seen.add(posix)
                        result.append((posix, resolved))

    def __collectFromFiles(
        self,
        cache_file: Path,
        seen: set[str],
        result: list[tuple[str, Path]],
    ) -> None:
        """
        Add deduplicated monitored files to the result list.

        Parameters
        ----------
        cache_file : Path
            Resolved cache file path to exclude from collection.
        seen : set[str]
            Set of already collected POSIX paths used for deduplication.
        result : list[tuple[str, Path]]
            Output list updated in place with ``(posix_path, resolved_path)`` tuples.

        Returns
        -------
        None
            This method updates ``result`` in place.
        """
        for file in self.__monitored_files:
            if file.exists():
                resolved = file.resolve()
                if resolved == cache_file:
                    continue
                posix = resolved.as_posix()
                if posix not in seen:
                    seen.add(posix)
                    result.append((posix, resolved))

    def __collectFiles(self) -> list[tuple[str, Path]]:
        """
        Collect monitored files for hashing and deduplicate them.

        Gather Python files from monitored directories and explicit monitored
        files, excluding the cache file itself.

        Returns
        -------
        list[tuple[str, Path]]
            Sorted ``(posix_path, resolved_path)`` pairs for unique monitored
            files.

        """
        cache_file = self.__file_resolved
        seen: set[str] = set()
        result: list[tuple[str, Path]] = []
        self.__collectFromDirs(cache_file, seen, result)
        self.__collectFromFiles(cache_file, seen, result)
        result.sort()
        return result

    def __computeSourcesHash(self) -> str:  # NOSONAR
        """
        Compute and return a hash representing the state of monitored sources.

        This method generates a SHA-1 hash based on the modification time and size
        of all monitored files and Python files in monitored directories, excluding
        the cache file itself. The hash is cached for a short interval to avoid
        redundant computation.

        Returns
        -------
        str
            The computed SHA-1 hash as a hexadecimal string.
        """
        # monotonic clock: faster than time.time(), no NTP/DST adjustments
        now = time.monotonic()

        # Use cached hash if within the allowed interval
        if self.__sourceshashcache and now - self.__lasthashcheck < self.__hashInterval:
            return self.__sourceshashcache

        hasher = hashlib.sha1(usedforsecurity=False)

        # Update hash: path bytes + fixed-width binary (mtime_ns, size)
        # struct.pack avoids the temporary str + encode() per file
        for posix, resolved_path in self.__collectFiles():
            stat = resolved_path.stat()
            hasher.update(posix.encode())
            hasher.update(struct.pack(">QQ", stat.st_mtime_ns, stat.st_size))

        self.__sourceshashcache = hasher.hexdigest()
        self.__lasthashcheck = now

        return self.__sourceshashcache
