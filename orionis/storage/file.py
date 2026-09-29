from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.storage.contracts.file import IFile
from orionis.storage.exceptions import StoragePathException
from orionis.storage.paths import normalizeFilePath

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, AsyncIterator
    from datetime import datetime
    from pathlib import Path
    from orionis.storage.contracts.driver import IStorageDriver
    from orionis.storage.contracts.stream import IStorageStream
    from orionis.storage.entities.file_info import FileInfo

class File(IFile):
    """
    Represent a single file on a storage disk.

    The object encapsulates its canonical path and the driver of the
    disk it belongs to. It never knows which physical medium backs it:
    every operation is delegated to the driver.
    """

    __slots__ = ("_driver", "_path")

    def __init__(self, driver: IStorageDriver, path: str) -> None:
        """
        Initialize the file with its driver and canonical path.

        Parameters
        ----------
        driver : IStorageDriver
            Driver of the disk that owns the file.
        path : str
            Root-relative file path; normalized on ingestion.

        Returns
        -------
        None

        Raises
        ------
        StoragePathException
            If *path* is invalid or resolves to the disk root.
        """
        self._driver = driver
        self._path = normalizeFilePath(path)

    def path(self) -> str:
        """
        Return the canonical root-relative path of the file.

        Returns
        -------
        str
            Normalized path relative to the disk root.
        """
        return self._path

    # ── Content operations ───────────────────────────────────────────────────

    async def read(self) -> bytes:
        """
        Read the full contents of the file.

        Returns
        -------
        bytes
            Complete file contents.

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        """
        return await self._driver.read(self._path)

    def readStream(self, chunk_size: int = 65536) -> AsyncIterator[bytes]:
        """
        Stream the contents of the file in chunks.

        Parameters
        ----------
        chunk_size : int
            Maximum number of bytes per yielded chunk.

        Returns
        -------
        AsyncIterator[bytes]
            Asynchronous iterator yielding consecutive chunks.

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        """
        return self._driver.readStream(self._path, chunk_size)

    async def write(
        self,
        contents: bytes | str,
        visibility: str | None = None,
    ) -> IFile:
        """
        Write *contents* to the file, replacing existing data.

        Parameters
        ----------
        contents : bytes | str
            Data to persist. Strings are encoded as UTF-8.
        visibility : str | None
            Visibility to apply, or ``None`` for the medium default.

        Returns
        -------
        IFile
            The file itself, enabling fluent chaining.
        """
        await self._driver.write(self._path, contents, visibility)
        return self

    async def writeStream(
        self,
        stream: AsyncIterable[bytes],
        visibility: str | None = None,
    ) -> IFile:
        """
        Write the chunks produced by *stream* to the file.

        Parameters
        ----------
        stream : AsyncIterable[bytes]
            Asynchronous byte-chunk producer.
        visibility : str | None
            Visibility to apply, or ``None`` for the medium default.

        Returns
        -------
        IFile
            The file itself, enabling fluent chaining.
        """
        await self._driver.writeStream(self._path, stream, visibility)
        return self

    def open(self, mode: str = "rb") -> IStorageStream:
        """
        Open an asynchronous binary stream over the file.

        Parameters
        ----------
        mode : str
            Binary mode: ``'rb'``, ``'wb'``, ``'ab'``, ``'rb+'``,
            ``'wb+'``, or ``'ab+'``.

        Returns
        -------
        IStorageStream
            Lazily opened stream; use it as an async context manager.

        Raises
        ------
        UnsupportedStorageOperationException
            If *mode* is not a supported binary mode.
        """
        return self._driver.open(self._path, mode)

    async def delete(self) -> bool:
        """
        Delete the file from its disk.

        Returns
        -------
        bool
            ``True`` if the file existed and was removed.
        """
        return await self._driver.delete(self._path)

    async def exists(self) -> bool:
        """
        Check whether the file exists on its disk.

        Returns
        -------
        bool
            ``True`` if the file exists.
        """
        return await self._driver.exists(self._path)

    # ── Relocation operations ────────────────────────────────────────────────

    async def copyTo(self, target: str) -> IFile:
        """
        Copy the file to *target* on the same disk.

        Parameters
        ----------
        target : str
            Root-relative destination path.

        Returns
        -------
        IFile
            A new file object pointing at the copy.

        Raises
        ------
        StorageFileNotFoundException
            If the source file does not exist.
        """
        destination = File(self._driver, target)
        await self._driver.copy(self._path, destination.path())
        return destination

    async def moveTo(self, target: str) -> IFile:
        """
        Move the file to *target* on the same disk.

        The current object keeps pointing at the old path; use the
        returned object to keep working with the moved file.

        Parameters
        ----------
        target : str
            Root-relative destination path.

        Returns
        -------
        IFile
            A new file object pointing at the moved file.

        Raises
        ------
        StorageFileNotFoundException
            If the source file does not exist.
        """
        destination = File(self._driver, target)
        await self._driver.move(self._path, destination.path())
        return destination

    async def rename(self, name: str) -> IFile:
        """
        Rename the file within its current directory.

        Parameters
        ----------
        name : str
            New file name without any directory separator.

        Returns
        -------
        IFile
            A new file object pointing at the renamed file.

        Raises
        ------
        StoragePathException
            If *name* is empty or contains a directory separator.
        StorageFileNotFoundException
            If the source file does not exist.
        """
        # A rename never relocates the file to another directory.
        if not name or "/" in name or "\\" in name:
            error_msg = f"Invalid file name [{name}] for rename."
            raise StoragePathException(error_msg)

        parent, _, _ = self._path.rpartition("/")
        target = f"{parent}/{name}" if parent else name
        return await self.moveTo(target)

    # ── Metadata operations ──────────────────────────────────────────────────

    async def size(self) -> int:
        """
        Return the size of the file in bytes.

        Returns
        -------
        int
            File size in bytes.

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        """
        return await self._driver.size(self._path)

    async def mimeType(self) -> str | None:
        """
        Guess the MIME type of the file.

        Returns
        -------
        str | None
            MIME type, or ``None`` when it cannot be determined.
        """
        return await self._driver.mimeType(self._path)

    async def lastModified(self) -> datetime:
        """
        Return the last-modification timestamp of the file.

        Returns
        -------
        datetime
            Timezone-aware modification timestamp (UTC).

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        """
        return await self._driver.lastModified(self._path)

    async def url(self) -> str:
        """
        Build the public URL of the file.

        Returns
        -------
        str
            Publicly accessible URL.

        Raises
        ------
        UnsupportedStorageOperationException
            If the disk does not expose public URLs.
        """
        return await self._driver.url(self._path)

    async def temporaryUrl(self, expires_in: int = 3600) -> str:
        """
        Build a signed, time-limited URL for the file.

        Parameters
        ----------
        expires_in : int
            Lifetime of the URL in seconds.

        Returns
        -------
        str
            Temporary URL valid for *expires_in* seconds.

        Raises
        ------
        UnsupportedStorageOperationException
            If the driver does not support temporary URLs.
        """
        return await self._driver.temporaryUrl(self._path, expires_in)

    async def visibility(self) -> str:
        """
        Return the visibility of the file.

        Returns
        -------
        str
            ``'public'`` or ``'private'``.

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        """
        return await self._driver.visibility(self._path)

    async def setVisibility(self, visibility: str) -> IFile:
        """
        Change the visibility of the file.

        Parameters
        ----------
        visibility : str
            Target visibility (``'public'`` or ``'private'``).

        Returns
        -------
        IFile
            The file itself, enabling fluent chaining.

        Raises
        ------
        StorageFileNotFoundException
            If the file does not exist.
        """
        await self._driver.setVisibility(self._path, visibility)
        return self

    async def download(self, destination: str | Path) -> Path:
        """
        Copy the file to a location on the local filesystem.

        Parameters
        ----------
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
        return await self._driver.download(self._path, destination)

    async def hash(self, algorithm: str = "sha256") -> str:
        """
        Compute the content hash of the file.

        Parameters
        ----------
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
        """
        return await self._driver.hash(self._path, algorithm)

    async def info(self) -> FileInfo:
        """
        Collect a metadata snapshot for the file.

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
        return await self._driver.info(self._path)
