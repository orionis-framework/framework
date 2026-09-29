from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, AsyncIterator
    from datetime import datetime
    from pathlib import Path
    from orionis.storage.contracts.stream import IStorageStream
    from orionis.storage.entities.file_info import FileInfo

class IStorageDriver(ABC):
    """
    Define the low-level contract every storage backend must implement.

    A driver translates canonical root-relative paths into operations
    against a physical medium (local disk, memory, S3, Azure, GCS...).
    Drivers contain **no business logic**; higher-level behavior lives
    in :class:`~orionis.storage.file.File`,
    :class:`~orionis.storage.directory.Directory`, and
    :class:`~orionis.storage.disk.Disk`. User code never interacts with
    a driver directly.
    """

    __slots__ = ()

    @abstractmethod
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

    @abstractmethod
    def readStream(
        self,
        path: str,
        chunk_size: int = 65536,
    ) -> AsyncIterator[bytes]:
        """
        Stream the contents of the file at *path* in chunks.

        Parameters
        ----------
        path : str
            Root-relative file path.
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

    @abstractmethod
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
            Visibility to apply (``'public'`` or ``'private'``), or
            ``None`` to keep the medium default.

        Returns
        -------
        None
        """

    @abstractmethod
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
            Visibility to apply, or ``None`` for the medium default.

        Returns
        -------
        None
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    async def directoryExists(self, path: str) -> bool:
        """
        Check whether a directory exists at *path*.

        Parameters
        ----------
        path : str
            Root-relative directory path. The empty string denotes the
            disk root.

        Returns
        -------
        bool
            ``True`` if a directory exists at the given path.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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
            If the disk does not expose public URLs.
        """

    @abstractmethod
    async def temporaryUrl(self, path: str, expires_in: int) -> str:
        """
        Build a signed, time-limited URL for the file at *path*.

        Parameters
        ----------
        path : str
            Root-relative file path.
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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
        """

    @abstractmethod
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

    @abstractmethod
    def open(self, path: str, mode: str = "rb") -> IStorageStream:
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
        IStorageStream
            Lazily opened stream; use it as an async context manager.

        Raises
        ------
        UnsupportedStorageOperationException
            If *mode* is not a supported binary mode.
        """
