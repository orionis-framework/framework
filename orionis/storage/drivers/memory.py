from __future__ import annotations
import asyncio
import hashlib
import io
import mimetypes
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import quote
from orionis.storage.contracts.driver import IStorageDriver
from orionis.storage.entities.file_info import FileInfo
from orionis.storage.enums.visibility import Visibility
from orionis.storage.exceptions import (
    StorageFileNotFoundException,
    UnsupportedStorageOperationException,
)
from orionis.storage.paths import normalizeFilePath, normalizePath
from orionis.storage.stream import AsyncStream

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, AsyncIterator
    from typing import BinaryIO

# Default chunk size for streaming operations (64 KiB).
_CHUNK_SIZE: int = 64 * 1024

# Binary modes accepted by open().
_ALLOWED_MODES: frozenset[str] = frozenset(
    {"rb", "wb", "ab", "rb+", "wb+", "ab+"},
)

def _now() -> datetime:
    """
    Return the current timezone-aware UTC timestamp.

    Returns
    -------
    datetime
        Current time in UTC.
    """
    return datetime.now(tz=UTC)

@dataclass(slots=True)
class _MemoryEntry:
    """
    Hold the content and metadata of a single in-memory file.

    Attributes
    ----------
    content : bytes
        Raw file contents.
    visibility : str
        Visibility level of the file.
    created_at : datetime
        Timestamp of the first write.
    modified_at : datetime
        Timestamp of the most recent write.
    """

    content: bytes
    visibility: str = Visibility.PRIVATE.value
    created_at: datetime = field(default_factory=_now)
    modified_at: datetime = field(default_factory=_now)

class MemoryStorageDriver(IStorageDriver):
    """
    Storage driver keeping every object in process memory.

    Designed for testing and ephemeral workloads: it implements the
    full driver contract over plain dictionaries, enabling fakes such
    as a future ``Storage.fake()`` without touching the rest of the
    component. Directories exist implicitly through file prefixes and
    explicitly through :meth:`createDirectory`.

    Concurrency
    -----------
    The store is a plain dictionary mutated without locks. Every
    operation completes without awaiting midway, so concurrent tasks
    on a single event loop never observe a partial mutation. No
    guarantee is offered when the same path is mutated from several
    threads at once, which streams opened with :meth:`open` do because
    they flush their buffer on a worker thread.
    """

    __slots__ = ("_base_url", "_directories", "_files")

    def __init__(self, base_url: str | None = None) -> None:
        """
        Initialize an empty in-memory disk.

        Parameters
        ----------
        base_url : str | None
            Base URL used to build public file URLs, or ``None`` when
            the disk does not expose URLs.

        Returns
        -------
        None
        """
        self._files: dict[str, _MemoryEntry] = {}
        self._directories: set[str] = set()
        self._base_url: str | None = base_url.rstrip("/") if base_url else None

    # ── Internal helpers ─────────────────────────────────────────────────────

    def __entryOrFail(self, normalized: str) -> _MemoryEntry:
        """
        Return the entry stored at *normalized* or raise when absent.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.

        Returns
        -------
        _MemoryEntry
            Stored entry for the path.

        Raises
        ------
        StorageFileNotFoundException
            If no file exists at the path.
        """
        entry = self._files.get(normalized)
        if entry is None:
            error_msg = f"File does not exist at path [{normalized}]."
            raise StorageFileNotFoundException(error_msg)
        return entry

    def __storeSync(
        self,
        normalized: str,
        data: bytes,
        visibility: str | None,
    ) -> None:
        """
        Persist *data* under *normalized*, preserving creation time.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.
        data : bytes
            Raw bytes to persist.
        visibility : str | None
            Visibility to apply, or ``None`` to keep the current one.

        Returns
        -------
        None
        """
        existing = self._files.get(normalized)
        if existing is None:
            self._files[normalized] = _MemoryEntry(
                content=data,
                visibility=str(visibility or Visibility.PRIVATE.value),
            )
        else:
            existing.content = data
            existing.modified_at = _now()
            if visibility is not None:
                existing.visibility = str(visibility)

    def __allDirectories(self) -> set[str]:
        """
        Return every explicit and implicit directory path.

        Returns
        -------
        set[str]
            Union of explicitly created directories and the ancestor
            prefixes implied by stored file paths.
        """
        # Start from explicit directories and add their ancestors.
        found: set[str] = set()
        for directory in self._directories:
            found.update(self.__ancestors(directory))
            found.add(directory)

        # Add the ancestor chain implied by every stored file path.
        for key in self._files:
            found.update(self.__ancestors(key))
        return found

    @staticmethod
    def __ancestors(path: str) -> set[str]:
        """
        Return every ancestor prefix of *path*.

        Parameters
        ----------
        path : str
            Canonical root-relative path.

        Returns
        -------
        set[str]
            Ancestor directory prefixes, excluding the path itself.
        """
        ancestors: set[str] = set()
        segments = path.split("/")
        for index in range(1, len(segments)):
            ancestors.add("/".join(segments[:index]))
        return ancestors

    def __listSync(
        self,
        normalized: str,
        *,
        recursive: bool,
        want_dirs: bool,
    ) -> list[str]:
        """
        List entries under *normalized*.

        Parameters
        ----------
        normalized : str
            Canonical root-relative directory path.
        recursive : bool
            When ``True``, traverse the whole subtree.
        want_dirs : bool
            When ``True``, collect directories; otherwise files.

        Returns
        -------
        list[str]
            Sorted root-relative entry paths.
        """
        prefix = f"{normalized}/" if normalized else ""
        candidates = (
            self.__allDirectories() if want_dirs else set(self._files)
        )

        results: list[str] = []
        for candidate in candidates:
            if not candidate.startswith(prefix) or candidate == normalized:
                continue
            remainder = candidate[len(prefix):]
            if recursive or "/" not in remainder:
                results.append(candidate)

        results.sort()
        return results

    def __buildUrl(self, normalized: str) -> str:
        """
        Build the public URL for *normalized*.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.

        Returns
        -------
        str
            URL composed from the configured base URL.
        """
        return f"{self._base_url}/{quote(normalized, safe='/')}"

    def __digest(self, data: bytes, algorithm: str) -> str:
        """
        Compute the hex digest of *data* using *algorithm*.

        Parameters
        ----------
        data : bytes
            Raw bytes to hash.
        algorithm : str
            Any algorithm name accepted by :func:`hashlib.new`.

        Returns
        -------
        str
            Hexadecimal digest of the data.

        Raises
        ------
        UnsupportedStorageOperationException
            If *algorithm* is not available.
        """
        try:
            hasher = hashlib.new(algorithm, usedforsecurity=False)
        except ValueError as exc:
            error_msg = f"Unsupported hash algorithm [{algorithm}]."
            raise UnsupportedStorageOperationException(error_msg) from exc
        hasher.update(data)
        return hasher.hexdigest()

    # ── Read operations ──────────────────────────────────────────────────────

    async def read(self, path: str) -> bytes:
        """
        Read the full contents of the file at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        bytes
            Complete file contents.

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        """
        return self.__entryOrFail(normalizeFilePath(path)).content

    async def readStream(
        self,
        path: str,
        chunk_size: int = _CHUNK_SIZE,
    ) -> AsyncIterator[bytes]:
        """
        Stream the contents of the file at *path* in chunks.

        Parameters
        ----------
        path : str
            Root-relative file path.
        chunk_size : int
            Maximum number of bytes per yielded chunk.

        Yields
        ------
        bytes
            Consecutive chunks of the file contents.

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        """
        content = self.__entryOrFail(normalizeFilePath(path)).content
        for start in range(0, len(content), chunk_size):
            yield content[start:start + chunk_size]

    async def exists(self, path: str) -> bool:
        """
        Check whether a file exists at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        bool
            ``True`` if a file exists at the given path.
        """
        return normalizeFilePath(path) in self._files

    # ── Write operations ─────────────────────────────────────────────────────

    async def write(
        self,
        path: str,
        contents: bytes | str,
        visibility: str | None = None,
    ) -> None:
        """
        Write *contents* to *path*, replacing any existing file.

        Parameters
        ----------
        path : str
            Root-relative file path.
        contents : bytes | str
            Data to persist. Strings are encoded as UTF-8.
        visibility : str | None
            Visibility to apply, or ``None`` to keep the current one.

        Returns
        -------
        None
        """
        data = (
            contents.encode("utf-8")
            if isinstance(contents, str)
            else bytes(contents)
        )
        self.__storeSync(normalizeFilePath(path), data, visibility)

    async def writeStream(
        self,
        path: str,
        stream: AsyncIterable[bytes],
        visibility: str | None = None,
    ) -> None:
        """
        Write the chunks produced by *stream* to *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.
        stream : AsyncIterable[bytes]
            Asynchronous byte-chunk producer.
        visibility : str | None
            Visibility to apply, or ``None`` to keep the current one.

        Returns
        -------
        None
        """
        buffer = bytearray()
        async for chunk in stream:
            buffer.extend(chunk)
        self.__storeSync(normalizeFilePath(path), bytes(buffer), visibility)

    async def delete(self, path: str) -> bool:
        """
        Delete the file at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        bool
            ``True`` if the file existed and was removed.
        """
        return self._files.pop(normalizeFilePath(path), None) is not None

    async def copy(self, source: str, target: str) -> None:
        """
        Copy the file at *source* to *target*.

        Parameters
        ----------
        source : str
            Root-relative path of the existing file.
        target : str
            Root-relative destination path.

        Returns
        -------
        None

        Raises
        ------
        StorageFileNotFoundException
            If the source file does not exist.
        """
        entry = self.__entryOrFail(normalizeFilePath(source))
        self._files[normalizeFilePath(target)] = _MemoryEntry(
            content=entry.content,
            visibility=entry.visibility,
        )

    async def move(self, source: str, target: str) -> None:
        """
        Move the file at *source* to *target*.

        Parameters
        ----------
        source : str
            Root-relative path of the existing file.
        target : str
            Root-relative destination path.

        Returns
        -------
        None

        Raises
        ------
        StorageFileNotFoundException
            If the source file does not exist.
        """
        normalized = normalizeFilePath(source)
        entry = self.__entryOrFail(normalized)
        self._files[normalizeFilePath(target)] = entry
        del self._files[normalized]

    # ── Metadata operations ──────────────────────────────────────────────────

    async def size(self, path: str) -> int:
        """
        Return the size in bytes of the file at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        int
            File size in bytes.

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        """
        return len(self.__entryOrFail(normalizeFilePath(path)).content)

    async def mimeType(self, path: str) -> str | None:
        """
        Guess the MIME type of the file at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        str | None
            MIME type, or ``None`` when it cannot be determined.
        """
        return mimetypes.guess_type(normalizeFilePath(path))[0]

    async def lastModified(self, path: str) -> datetime:
        """
        Return the last-modification timestamp of the file at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        datetime
            Timezone-aware modification timestamp (UTC).

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        """
        return self.__entryOrFail(normalizeFilePath(path)).modified_at

    async def visibility(self, path: str) -> str:
        """
        Return the visibility of the file at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        str
            ``'public'`` or ``'private'``.

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        """
        return self.__entryOrFail(normalizeFilePath(path)).visibility

    async def setVisibility(self, path: str, visibility: str) -> None:
        """
        Change the visibility of the file at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.
        visibility : str
            Target visibility (``'public'`` or ``'private'``).

        Returns
        -------
        None

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        UnsupportedStorageOperationException
            If *visibility* is not a supported level.
        """
        normalized_visibility = str(visibility)
        if normalized_visibility not in (
            Visibility.PUBLIC.value,
            Visibility.PRIVATE.value,
        ):
            error_msg = f"Unsupported visibility level [{visibility}]."
            raise UnsupportedStorageOperationException(error_msg)
        entry = self.__entryOrFail(normalizeFilePath(path))
        entry.visibility = normalized_visibility

    async def hash(self, path: str, algorithm: str = "sha256") -> str:
        """
        Compute the content hash of the file at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.
        algorithm : str
            Any algorithm name accepted by :func:`hashlib.new`.

        Returns
        -------
        str
            Hexadecimal digest of the file contents.

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        UnsupportedStorageOperationException
            If *algorithm* is not available.
        """
        entry = self.__entryOrFail(normalizeFilePath(path))
        return self.__digest(entry.content, algorithm)

    async def info(self, path: str) -> FileInfo:
        """
        Collect a metadata snapshot for the file at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        FileInfo
            Immutable entity with size, MIME type, timestamps, hashes,
            visibility, and URL when available.

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        """
        normalized = normalizeFilePath(path)
        entry = self.__entryOrFail(normalized)
        return FileInfo(
            path=normalized,
            size=len(entry.content),
            lastModified=entry.modified_at,
            visibility=entry.visibility,
            mimeType=mimetypes.guess_type(normalized)[0],
            createdAt=entry.created_at,
            etag=self.__digest(entry.content, "md5"),
            checksum=self.__digest(entry.content, "sha256"),
            url=self.__buildUrl(normalized) if self._base_url else None,
        )

    # ── Directory operations ─────────────────────────────────────────────────

    async def createDirectory(self, path: str) -> None:
        """
        Create the directory at *path*, including missing parents.

        Parameters
        ----------
        path : str
            Root-relative directory path.

        Returns
        -------
        None
        """
        normalized = normalizePath(path)
        if normalized:
            self._directories.add(normalized)

    async def deleteDirectory(self, path: str) -> bool:
        """
        Recursively delete the directory at *path*.

        Parameters
        ----------
        path : str
            Root-relative directory path.

        Returns
        -------
        bool
            ``True`` if the directory existed and was removed.
        """
        normalized = normalizePath(path)
        if not normalized:
            # Deleting the root clears the whole disk.
            existed = bool(self._files or self._directories)
            self._files.clear()
            self._directories.clear()
            return existed

        prefix = f"{normalized}/"
        existed = (
            normalized in self.__allDirectories()
        )

        # Drop every nested file and explicit directory entry.
        self._files = {
            key: entry
            for key, entry in self._files.items()
            if not key.startswith(prefix)
        }
        self._directories = {
            directory
            for directory in self._directories
            if directory != normalized and not directory.startswith(prefix)
        }
        return existed

    async def directoryExists(self, path: str) -> bool:
        """
        Check whether a directory exists at *path*.

        Parameters
        ----------
        path : str
            Root-relative directory path. The empty string denotes
            the disk root.

        Returns
        -------
        bool
            ``True`` if a directory exists at the given path.
        """
        normalized = normalizePath(path)
        if not normalized:
            return True
        return normalized in self.__allDirectories()

    async def files(
        self,
        path: str = "",
        *,
        recursive: bool = False,
    ) -> list[str]:
        """
        List the file paths contained in the directory at *path*.

        Parameters
        ----------
        path : str
            Root-relative directory path. Empty string for the root.
        recursive : bool
            When ``True``, include files from all nested directories.

        Returns
        -------
        list[str]
            Sorted root-relative file paths.
        """
        return self.__listSync(
            normalizePath(path),
            recursive=recursive,
            want_dirs=False,
        )

    async def directories(
        self,
        path: str = "",
        *,
        recursive: bool = False,
    ) -> list[str]:
        """
        List the directory paths contained in the directory at *path*.

        Parameters
        ----------
        path : str
            Root-relative directory path. Empty string for the root.
        recursive : bool
            When ``True``, include all nested directories.

        Returns
        -------
        list[str]
            Sorted root-relative directory paths.
        """
        return self.__listSync(
            normalizePath(path),
            recursive=recursive,
            want_dirs=True,
        )

    # ── URLs and transfers ───────────────────────────────────────────────────

    async def url(self, path: str) -> str:
        """
        Build the public URL for the file at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        str
            Publicly accessible URL for the file.

        Raises
        ------
        UnsupportedStorageOperationException
            If the disk has no base URL configured.
        """
        normalized = normalizeFilePath(path)
        if self._base_url is None:
            error_msg = (
                f"This disk does not expose public URLs for [{normalized}]."
            )
            raise UnsupportedStorageOperationException(error_msg)
        return self.__buildUrl(normalized)

    async def temporaryUrl(self, path: str, expires_in: int) -> str:  # noqa: ARG002
        """
        Build a signed, time-limited URL for the file at *path*.

        The memory driver cannot sign URLs, so this operation always
        fails.

        Parameters
        ----------
        path : str
            Root-relative file path.
        expires_in : int
            Lifetime of the URL in seconds.

        Returns
        -------
        str
            Never returned by this driver.

        Raises
        ------
        UnsupportedStorageOperationException
            Always, since memory disks cannot sign URLs.
        """
        error_msg = (
            f"The memory driver does not support temporary URLs for [{path}]."
        )
        raise UnsupportedStorageOperationException(error_msg)

    async def download(self, path: str, destination: str | Path) -> Path:
        """
        Copy the file at *path* to a location on the local filesystem.

        Parameters
        ----------
        path : str
            Root-relative file path on the disk.
        destination : str | Path
            Local target. When it points to an existing directory the
            file keeps its original name inside that directory.

        Returns
        -------
        Path
            Absolute local path of the downloaded file.

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        """
        normalized = normalizeFilePath(path)
        entry = self.__entryOrFail(normalized)

        def _persist() -> Path:
            # Keep the original name when the destination is a directory.
            target = Path(destination)
            if target.is_dir():
                target = target / PurePosixPath(normalized).name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(entry.content)
            return target.resolve()

        return await asyncio.to_thread(_persist)

    def open(self, path: str, mode: str = "rb") -> AsyncStream:
        """
        Open an asynchronous binary stream for the file at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.
        mode : str
            Binary mode: ``'rb'``, ``'wb'``, ``'ab'``, ``'rb+'``,
            ``'wb+'``, or ``'ab+'``.

        Returns
        -------
        AsyncStream
            Lazily opened stream; use it as an async context manager.

        Raises
        ------
        UnsupportedStorageOperationException
            If *mode* is not a supported binary mode.
        """
        normalized = normalizeFilePath(path)
        if mode not in _ALLOWED_MODES:
            error_msg = f"Unsupported stream mode [{mode}]."
            raise UnsupportedStorageOperationException(error_msg)

        def opener() -> BinaryIO:
            # Read-oriented modes require the file to already exist.
            if mode in ("rb", "rb+"):
                buffer = io.BytesIO(self.__entryOrFail(normalized).content)
            elif mode in ("ab", "ab+"):
                entry = self._files.get(normalized)
                buffer = io.BytesIO(entry.content if entry else b"")
                buffer.seek(0, io.SEEK_END)
            else:
                buffer = io.BytesIO()
            return buffer

        def flush(handle: BinaryIO) -> None:
            # Persist the buffered content back into the store on close.
            handle.seek(0)
            self.__storeSync(normalized, handle.read(), None)

        # Only writable modes need the flush-on-close callback.
        on_close = None if mode == "rb" else flush
        return AsyncStream(opener, on_close)
