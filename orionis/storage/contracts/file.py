# ruff: noqa: TC001, TC003
# Keep public protocol and native annotations available for runtime reflection.
"""Define the contract for a single file on a storage disk."""

from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import AsyncIterable, AsyncIterator
from datetime import datetime
from pathlib import Path
from orionis.storage.contracts.stream import IStorageStream
from orionis.storage.entities.file_info import FileInfo


class IFile(ABC):
    """
    Define the contract for a single file on a storage disk.

    A file object encapsulates its canonical path and delegates every
    operation to the driver of the disk it belongs to. It never knows
    which physical medium (local, memory, S3...) backs it.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    def path(self) -> str:
        """
        Return the canonical root-relative path of the file.

        Returns
        -------
        str
            Normalized path relative to the disk root.
        """

    @abstractmethod
    def absolutePath(self) -> str:
        """
        Return the absolute filesystem path of the file.

        The file does not need to exist.

        Returns
        -------
        str
            Absolute path using the operating system's separators.

        Raises
        ------
        orionis.storage.exceptions.UnsupportedStorageOperationException
            If the driver does not expose local filesystem paths.
        orionis.storage.exceptions.StoragePathException
            If the file path escapes the disk root.
        """

    @abstractmethod
    def relativePath(self) -> str:
        """
        Return the filesystem path relative to the application base path.

        The file does not need to exist.

        Returns
        -------
        str
            Path from ``app.basePath`` using ``/`` as separator. Roots outside
            the project may require leading ``..`` segments.

        Raises
        ------
        orionis.storage.exceptions.UnsupportedStorageOperationException
            If local filesystem paths or the application base are unavailable.
        orionis.storage.exceptions.StoragePathException
            If the file path escapes the disk root or cannot be expressed
            relative to the application base path.
        """

    @abstractmethod
    async def read(self) -> bytes:
        """
        Read the full contents of the file.

        Returns
        -------
        bytes
            Complete file contents.

        Raises
        ------
        orionis.storage.exceptions.StorageFileNotFoundException
            If the file does not exist.
        """

    @abstractmethod
    def readStream(self, chunk_size: int = 65536) -> AsyncIterator[bytes]:
        """
        Stream the contents of the file in chunks.

        Parameters
        ----------
        chunk_size : int
            Maximum number of bytes per yielded chunk.

        Returns
        -------
        collections.abc.AsyncIterator[bytes]
            Asynchronous iterator yielding consecutive chunks.

        Raises
        ------
        orionis.storage.exceptions.StorageFileNotFoundException
            If the file does not exist.
        """

    @abstractmethod
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
        orionis.storage.contracts.IFile
            The file itself, enabling fluent chaining.
        """

    @abstractmethod
    async def writeStream(
        self,
        stream: AsyncIterable[bytes],
        visibility: str | None = None,
    ) -> IFile:
        """
        Write the chunks produced by *stream* to the file.

        Parameters
        ----------
        stream : collections.abc.AsyncIterable[bytes]
            Asynchronous byte-chunk producer.
        visibility : str | None
            Visibility to apply, or ``None`` for the medium default.

        Returns
        -------
        orionis.storage.contracts.IFile
            The file itself, enabling fluent chaining.
        """

    @abstractmethod
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
        orionis.storage.contracts.IStorageStream
            Lazily opened stream; use it as an async context manager.
        """

    @abstractmethod
    async def delete(self) -> bool:
        """
        Delete the file from its disk.

        Returns
        -------
        bool
            ``True`` if the file existed and was removed.
        """

    @abstractmethod
    async def exists(self) -> bool:
        """
        Check whether the file exists on its disk.

        Returns
        -------
        bool
            ``True`` if the file exists.
        """

    @abstractmethod
    async def copyTo(self, target: str) -> IFile:
        """
        Copy the file to *target* on the same disk.

        Parameters
        ----------
        target : str
            Root-relative destination path.

        Returns
        -------
        orionis.storage.contracts.IFile
            A new file object pointing at the copy.

        Raises
        ------
        orionis.storage.exceptions.StorageFileNotFoundException
            If the source file does not exist.
        """

    @abstractmethod
    async def moveTo(self, target: str) -> IFile:
        """
        Move the file to *target* on the same disk.

        Parameters
        ----------
        target : str
            Root-relative destination path.

        Returns
        -------
        orionis.storage.contracts.IFile
            A new file object pointing at the moved file.

        Raises
        ------
        orionis.storage.exceptions.StorageFileNotFoundException
            If the source file does not exist.
        """

    @abstractmethod
    async def rename(self, name: str) -> IFile:
        """
        Rename the file within its current directory.

        Parameters
        ----------
        name : str
            New file name without any directory separator.

        Returns
        -------
        orionis.storage.contracts.IFile
            A new file object pointing at the renamed file.

        Raises
        ------
        orionis.storage.exceptions.StoragePathException
            If *name* is empty, a dot segment, or contains a directory separator.
        orionis.storage.exceptions.StorageFileNotFoundException
            If the source file does not exist.
        """

    @abstractmethod
    async def size(self) -> int:
        """
        Return the size of the file in bytes.

        Returns
        -------
        int
            File size in bytes.

        Raises
        ------
        orionis.storage.exceptions.StorageFileNotFoundException
            If the file does not exist.
        """

    @abstractmethod
    async def mimeType(self) -> str | None:
        """
        Guess the MIME type of the file.

        Returns
        -------
        str | None
            MIME type, or ``None`` when it cannot be determined.
        """

    @abstractmethod
    async def lastModified(self) -> datetime:
        """
        Return the last-modification timestamp of the file.

        Returns
        -------
        datetime.datetime
            Timezone-aware modification timestamp (UTC).

        Raises
        ------
        orionis.storage.exceptions.StorageFileNotFoundException
            If the file does not exist.
        """

    @abstractmethod
    async def url(self) -> str:
        """
        Build the public URL of the file.

        Returns
        -------
        str
            Publicly accessible URL.

        Raises
        ------
        orionis.storage.exceptions.UnsupportedStorageOperationException
            If the disk does not expose public URLs.
        """

    @abstractmethod
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
        orionis.storage.exceptions.UnsupportedStorageOperationException
            If the driver does not support temporary URLs.
        """

    @abstractmethod
    async def visibility(self) -> str:
        """
        Return the visibility of the file.

        Returns
        -------
        str
            ``'public'`` or ``'private'``.

        Raises
        ------
        orionis.storage.exceptions.StorageFileNotFoundException
            If the file does not exist.
        """

    @abstractmethod
    async def setVisibility(self, visibility: str) -> IFile:
        """
        Change the visibility of the file.

        Parameters
        ----------
        visibility : str
            Target visibility (``'public'`` or ``'private'``).

        Returns
        -------
        orionis.storage.contracts.IFile
            The file itself, enabling fluent chaining.

        Raises
        ------
        orionis.storage.exceptions.StorageFileNotFoundException
            If the file does not exist.
        """

    @abstractmethod
    async def download(self, destination: str | Path) -> Path:
        """
        Copy the file to a location on the local filesystem.

        Parameters
        ----------
        destination : str | pathlib.Path
            Local target. When it points to an existing directory the
            file keeps its original name inside that directory.

        Returns
        -------
        pathlib.Path
            Absolute local path of the downloaded file.

        Raises
        ------
        orionis.storage.exceptions.StorageFileNotFoundException
            If the file does not exist.
        """

    @abstractmethod
    async def hash(self, algorithm: str = "sha256") -> str:
        """
        Compute the content hash of the file.

        Parameters
        ----------
        algorithm : str
            Any algorithm name accepted by ``hashlib.new``.

        Returns
        -------
        str
            Hexadecimal digest of the file contents.

        Raises
        ------
        orionis.storage.exceptions.StorageFileNotFoundException
            If the file does not exist.
        """

    @abstractmethod
    async def info(self) -> FileInfo:
        """
        Collect a metadata snapshot for the file.

        Returns
        -------
        orionis.storage.entities.FileInfo
            Immutable entity with size, MIME type, timestamps, hashes,
            visibility, and URL when available.

        Raises
        ------
        orionis.storage.exceptions.StorageFileNotFoundException
            If the file does not exist.
        """
