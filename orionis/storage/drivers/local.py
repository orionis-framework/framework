from __future__ import annotations
import asyncio
import hashlib
import mimetypes
import secrets
import shutil
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
    from collections.abc import AsyncIterable, AsyncIterator, Iterator
    from typing import BinaryIO

# Default chunk size for streaming operations (64 KiB).
_CHUNK_SIZE: int = 64 * 1024

# POSIX permission bits applied per visibility level.
_FILE_MODES: dict[str, int] = {
    Visibility.PUBLIC.value: 0o644,
    Visibility.PRIVATE.value: 0o600,
}
_DIR_MODES: dict[str, int] = {
    Visibility.PUBLIC.value: 0o755,
    Visibility.PRIVATE.value: 0o700,
}

# Binary modes accepted by open().
_ALLOWED_MODES: frozenset[str] = frozenset(
    {"rb", "wb", "ab", "rb+", "wb+", "ab+"},
)

class LocalStorageDriver(IStorageDriver):
    """
    Storage driver backed by the local filesystem.

    Every path is resolved inside the configured *root* directory and
    all blocking I/O runs on worker threads via
    :func:`asyncio.to_thread`, keeping the event loop responsive.
    Visibility is mapped onto POSIX permission bits (``0o644``/``0o600``
    for files), which degrades gracefully on platforms without a full
    POSIX mode implementation.
    """

    __slots__ = ("_base_url", "_root")

    def __init__(self, root: Path, base_url: str | None = None) -> None:
        """
        Initialize the driver rooted at *root*.

        Parameters
        ----------
        root : Path
            Directory acting as the disk root. It is created when
            missing.
        base_url : str | None
            Base URL used to build public file URLs, or ``None`` when
            the disk does not expose URLs.

        Returns
        -------
        None
        """
        self._root: Path = root.resolve()
        self._base_url: str | None = base_url.rstrip("/") if base_url else None

        # Guarantee the disk root exists before any operation runs.
        self._root.mkdir(parents=True, exist_ok=True)

    # ── Internal helpers (synchronous, executed on worker threads) ──────────

    def __absolute(self, normalized: str) -> Path:
        """
        Return the absolute path for an already normalized path.

        Parameters
        ----------
        normalized : str
            Canonical root-relative path.

        Returns
        -------
        Path
            Absolute path inside the disk root.
        """
        # Normalized paths cannot escape the root, so a plain join is safe.
        return self._root / normalized if normalized else self._root

    def __relative(self, absolute: Path) -> str:
        """
        Return the canonical relative path for *absolute*.

        Parameters
        ----------
        absolute : Path
            Absolute path inside the disk root.

        Returns
        -------
        str
            Root-relative path using ``/`` as separator.
        """
        return absolute.relative_to(self._root).as_posix()

    def __fileMode(self, visibility: str) -> int:
        """
        Return the POSIX file mode for *visibility*.

        Parameters
        ----------
        visibility : str
            Visibility level (``'public'`` or ``'private'``).

        Returns
        -------
        int
            Permission bits to apply to the file.

        Raises
        ------
        UnsupportedStorageOperationException
            If *visibility* is not a supported level.
        """
        mode = _FILE_MODES.get(str(visibility))
        if mode is None:
            error_msg = f"Unsupported visibility level [{visibility}]."
            raise UnsupportedStorageOperationException(error_msg)
        return mode

    def __statOrFail(self, normalized: str) -> tuple[Path, object]:
        """
        Stat the file at *normalized* or raise when it is absent.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.

        Returns
        -------
        tuple[Path, object]
            The absolute path and its ``os.stat_result``.

        Raises
        ------
        StorageFileNotFoundException
            If the path does not reference an existing file.
        """
        absolute = self.__absolute(normalized)
        try:
            stats = absolute.stat()
        except OSError as exc:
            error_msg = f"File does not exist at path [{normalized}]."
            raise StorageFileNotFoundException(error_msg) from exc
        if not absolute.is_file():
            error_msg = f"Path [{normalized}] does not reference a file."
            raise StorageFileNotFoundException(error_msg)
        return absolute, stats

    def __readSync(self, normalized: str) -> bytes:
        """
        Read the file at *normalized* synchronously.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.

        Returns
        -------
        bytes
            Complete file contents.

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        """
        absolute = self.__absolute(normalized)
        try:
            return absolute.read_bytes()
        except (FileNotFoundError, IsADirectoryError, PermissionError) as exc:
            error_msg = f"File does not exist at path [{normalized}]."
            raise StorageFileNotFoundException(error_msg) from exc

    def __openRead(self, normalized: str, mode: str) -> BinaryIO:
        """
        Open the file at *normalized* synchronously.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.
        mode : str
            Binary mode to open the file with.

        Returns
        -------
        BinaryIO
            Open binary handle.

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        """
        absolute = self.__absolute(normalized)

        # Write modes must be able to create missing parent directories.
        if "w" in mode or "a" in mode:
            absolute.parent.mkdir(parents=True, exist_ok=True)
        try:
            return absolute.open(mode)
        except (FileNotFoundError, IsADirectoryError, PermissionError) as exc:
            error_msg = f"File does not exist at path [{normalized}]."
            raise StorageFileNotFoundException(error_msg) from exc

    def __openTemp(self, tmp: Path) -> BinaryIO:
        """
        Open a temporary sibling file for writing synchronously.

        Parameters
        ----------
        tmp : Path
            Absolute path of the temporary file.

        Returns
        -------
        BinaryIO
            Open binary handle in write mode.
        """
        tmp.parent.mkdir(parents=True, exist_ok=True)
        return tmp.open("wb")

    @staticmethod
    def __tempPath(absolute: Path) -> Path:
        """
        Build a unique staging path for an atomic write.

        Parameters
        ----------
        absolute : Path
            Final absolute destination path.

        Returns
        -------
        Path
            Sibling path carrying a random infix, so concurrent
            writers never share a staging file, and still ending in
            ``.tmp`` so listings keep filtering it out.
        """
        return absolute.with_name(f"{absolute.name}.{secrets.token_hex(8)}.tmp")

    def __writeSync(
        self,
        normalized: str,
        data: bytes,
        visibility: str | None,
    ) -> None:
        """
        Atomically write *data* to *normalized* synchronously.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.
        data : bytes
            Raw bytes to persist.
        visibility : str | None
            Visibility to apply, or ``None`` to keep the OS default.

        Returns
        -------
        None
        """
        absolute = self.__absolute(normalized)
        absolute.parent.mkdir(parents=True, exist_ok=True)

        # Write to a sibling temp file then rename for atomic replacement.
        tmp = self.__tempPath(absolute)
        try:
            tmp.write_bytes(data)
            tmp.replace(absolute)
        except OSError:
            tmp.unlink(missing_ok=True)
            raise

        if visibility is not None:
            absolute.chmod(self.__fileMode(visibility))

    def __commitStream(
        self,
        tmp: Path,
        absolute: Path,
        visibility: str | None,
    ) -> None:
        """
        Promote a finished temp file to its final destination.

        Parameters
        ----------
        tmp : Path
            Fully written temporary file.
        absolute : Path
            Final absolute destination path.
        visibility : str | None
            Visibility to apply, or ``None`` to keep the OS default.

        Returns
        -------
        None
        """
        tmp.replace(absolute)
        if visibility is not None:
            absolute.chmod(self.__fileMode(visibility))

    def __copySync(self, source: str, target: str) -> None:
        """
        Copy *source* to *target* synchronously.

        Parameters
        ----------
        source : str
            Canonical root-relative source path.
        target : str
            Canonical root-relative destination path.

        Returns
        -------
        None

        Raises
        ------
        StorageFileNotFoundException
            If the source file does not exist.
        """
        origin, _ = self.__statOrFail(source)
        destination = self.__absolute(target)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, destination)

    def __moveSync(self, source: str, target: str) -> None:
        """
        Move *source* to *target* synchronously.

        Parameters
        ----------
        source : str
            Canonical root-relative source path.
        target : str
            Canonical root-relative destination path.

        Returns
        -------
        None

        Raises
        ------
        StorageFileNotFoundException
            If the source file does not exist.
        """
        origin, _ = self.__statOrFail(source)
        destination = self.__absolute(target)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            origin.replace(destination)
        except OSError:
            # Fall back for cross-device moves where rename cannot work.
            shutil.move(origin, destination)

    @staticmethod
    def __walkEntries(base: Path, *, want_dirs: bool) -> Iterator[Path]:
        """
        Yield every nested entry of the requested kind under *base*.

        Parameters
        ----------
        base : Path
            Absolute directory used as the traversal root.
        want_dirs : bool
            When ``True``, yield directories; otherwise files.

        Yields
        ------
        Path
            Absolute path of each matching entry.
        """
        # Path.walk() traverses the tree without loading it in memory.
        for parent, dirnames, filenames in base.walk():
            for name in dirnames if want_dirs else filenames:
                yield parent / name

    @staticmethod
    def __iterEntries(base: Path, *, want_dirs: bool) -> Iterator[Path]:
        """
        Yield the direct children of the requested kind under *base*.

        Parameters
        ----------
        base : Path
            Absolute directory to inspect.
        want_dirs : bool
            When ``True``, yield directories; otherwise files.

        Yields
        ------
        Path
            Absolute path of each matching entry.
        """
        for entry in base.iterdir():
            if entry.is_dir() is want_dirs:
                yield entry

    def __listSync(
        self,
        normalized: str,
        *,
        recursive: bool,
        want_dirs: bool,
    ) -> list[str]:
        """
        List entries under *normalized* synchronously.

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
        base = self.__absolute(normalized)
        if not base.is_dir():
            return []

        # Select the traversal strategy and drop in-flight temp files
        # left behind by atomic writers.
        walker = self.__walkEntries if recursive else self.__iterEntries
        results = [
            self.__relative(entry)
            for entry in walker(base, want_dirs=want_dirs)
            if want_dirs or not entry.name.endswith(".tmp")
        ]
        results.sort()
        return results

    def __hashSync(self, normalized: str, algorithm: str) -> str:
        """
        Compute the content hash of *normalized* synchronously.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.
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
        absolute, _ = self.__statOrFail(normalized)
        try:
            hasher = hashlib.new(algorithm, usedforsecurity=False)
        except ValueError as exc:
            error_msg = f"Unsupported hash algorithm [{algorithm}]."
            raise UnsupportedStorageOperationException(error_msg) from exc

        # Hash in fixed-size chunks to bound peak memory usage.
        with absolute.open("rb") as handle:
            while chunk := handle.read(_CHUNK_SIZE):
                hasher.update(chunk)
        return hasher.hexdigest()

    def __visibilityFromMode(self, mode: int) -> str:
        """
        Derive the visibility level from POSIX permission bits.

        Parameters
        ----------
        mode : int
            Raw ``st_mode`` value of the file.

        Returns
        -------
        str
            ``'public'`` when group or others can read the file,
            otherwise ``'private'``.
        """
        return (
            Visibility.PUBLIC.value
            if mode & 0o044
            else Visibility.PRIVATE.value
        )

    def __infoSync(self, normalized: str) -> FileInfo:
        """
        Build a metadata snapshot for *normalized* synchronously.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.

        Returns
        -------
        FileInfo
            Immutable metadata snapshot of the file.

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        """
        absolute, stats = self.__statOrFail(normalized)

        # Compute both digests in a single read pass over the file.
        etag = hashlib.new("md5", usedforsecurity=False)
        checksum = hashlib.new("sha256", usedforsecurity=False)
        with absolute.open("rb") as handle:
            while chunk := handle.read(_CHUNK_SIZE):
                etag.update(chunk)
                checksum.update(chunk)

        # Prefer the true birth time where the platform provides it.
        created_raw = getattr(stats, "st_birthtime", None)
        created_at = (
            datetime.fromtimestamp(created_raw, tz=UTC)
            if created_raw is not None
            else None
        )

        return FileInfo(
            path=normalized,
            size=stats.st_size,
            lastModified=datetime.fromtimestamp(stats.st_mtime, tz=UTC),
            visibility=self.__visibilityFromMode(stats.st_mode),
            mimeType=mimetypes.guess_type(normalized)[0],
            createdAt=created_at,
            etag=etag.hexdigest(),
            checksum=checksum.hexdigest(),
            url=self.__buildUrl(normalized) if self._base_url else None,
        )

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

    def __downloadSync(self, normalized: str, destination: str | Path) -> Path:
        """
        Copy *normalized* to a local destination synchronously.

        Parameters
        ----------
        normalized : str
            Canonical root-relative file path.
        destination : str | Path
            Local target file or existing directory.

        Returns
        -------
        Path
            Absolute local path of the downloaded file.

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        """
        source, _ = self.__statOrFail(normalized)
        target = Path(destination)

        # Keep the original name when the destination is a directory.
        if target.is_dir():
            target = target / PurePosixPath(normalized).name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return target.resolve()

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
        normalized = normalizeFilePath(path)
        return await asyncio.to_thread(self.__readSync, normalized)

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
        normalized = normalizeFilePath(path)
        handle = await asyncio.to_thread(self.__openRead, normalized, "rb")
        try:
            while True:
                chunk = await asyncio.to_thread(handle.read, chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            await asyncio.to_thread(handle.close)

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
        absolute = self.__absolute(normalizeFilePath(path))
        return await asyncio.to_thread(absolute.is_file)

    # ── Write operations ─────────────────────────────────────────────────────

    async def write(
        self,
        path: str,
        contents: bytes | str,
        visibility: str | None = None,
    ) -> None:
        """
        Write *contents* to *path*, replacing any existing file.

        The write is atomic: data lands in a sibling temporary file
        that is renamed over the destination once complete.

        Parameters
        ----------
        path : str
            Root-relative file path.
        contents : bytes | str
            Data to persist. Strings are encoded as UTF-8.
        visibility : str | None
            Visibility to apply, or ``None`` to keep the OS default.

        Returns
        -------
        None
        """
        normalized = normalizeFilePath(path)
        data = (
            contents.encode("utf-8")
            if isinstance(contents, str)
            else bytes(contents)
        )
        await asyncio.to_thread(self.__writeSync, normalized, data, visibility)

    async def writeStream(
        self,
        path: str,
        stream: AsyncIterable[bytes],
        visibility: str | None = None,
    ) -> None:
        """
        Write the chunks produced by *stream* to *path*.

        Chunks are appended to a temporary file that atomically
        replaces the destination once the stream is exhausted, so a
        failed transfer never leaves a partial file behind.

        Parameters
        ----------
        path : str
            Root-relative file path.
        stream : AsyncIterable[bytes]
            Asynchronous byte-chunk producer.
        visibility : str | None
            Visibility to apply, or ``None`` to keep the OS default.

        Returns
        -------
        None
        """
        normalized = normalizeFilePath(path)
        absolute = self.__absolute(normalized)
        tmp = self.__tempPath(absolute)
        handle = await asyncio.to_thread(self.__openTemp, tmp)

        # Track completion so failures can discard the partial temp file.
        completed = False
        try:
            async for chunk in stream:
                await asyncio.to_thread(handle.write, chunk)
            completed = True
        finally:
            await asyncio.to_thread(handle.close)
            if not completed:
                await asyncio.to_thread(tmp.unlink, missing_ok=True)

        await asyncio.to_thread(self.__commitStream, tmp, absolute, visibility)

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
        absolute = self.__absolute(normalizeFilePath(path))
        try:
            await asyncio.to_thread(absolute.unlink)
        except FileNotFoundError:
            return False
        return True

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
        await asyncio.to_thread(
            self.__copySync,
            normalizeFilePath(source),
            normalizeFilePath(target),
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
        await asyncio.to_thread(
            self.__moveSync,
            normalizeFilePath(source),
            normalizeFilePath(target),
        )

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
        _, stats = await asyncio.to_thread(
            self.__statOrFail,
            normalizeFilePath(path),
        )
        return stats.st_size

    async def mimeType(self, path: str) -> str | None:
        """
        Guess the MIME type of the file at *path*.

        The guess is derived from the file extension and requires no
        disk access.

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
        _, stats = await asyncio.to_thread(
            self.__statOrFail,
            normalizeFilePath(path),
        )
        return datetime.fromtimestamp(stats.st_mtime, tz=UTC)

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
        _, stats = await asyncio.to_thread(
            self.__statOrFail,
            normalizeFilePath(path),
        )
        return self.__visibilityFromMode(stats.st_mode)

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
        mode = self.__fileMode(visibility)
        absolute, _ = await asyncio.to_thread(
            self.__statOrFail,
            normalizeFilePath(path),
        )
        await asyncio.to_thread(absolute.chmod, mode)

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
        return await asyncio.to_thread(
            self.__hashSync,
            normalizeFilePath(path),
            algorithm,
        )

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
        return await asyncio.to_thread(
            self.__infoSync,
            normalizeFilePath(path),
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
        absolute = self.__absolute(normalizePath(path))
        await asyncio.to_thread(absolute.mkdir, parents=True, exist_ok=True)

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
        absolute = self.__absolute(normalizePath(path))
        if not await asyncio.to_thread(absolute.is_dir):
            return False
        await asyncio.to_thread(shutil.rmtree, absolute)
        return True

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
        absolute = self.__absolute(normalizePath(path))
        return await asyncio.to_thread(absolute.is_dir)

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
        return await asyncio.to_thread(
            lambda: self.__listSync(
                normalizePath(path),
                recursive=recursive,
                want_dirs=False,
            ),
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
        return await asyncio.to_thread(
            lambda: self.__listSync(
                normalizePath(path),
                recursive=recursive,
                want_dirs=True,
            ),
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

        The local driver cannot sign URLs, so this operation always
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
            Always, since local disks cannot sign URLs.
        """
        error_msg = (
            f"The local driver does not support temporary URLs for [{path}]."
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
        return await asyncio.to_thread(
            self.__downloadSync,
            normalizeFilePath(path),
            destination,
        )

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

        # The opener runs on a worker thread once the stream is first used.
        return AsyncStream(lambda: self.__openRead(normalized, mode))
