from __future__ import annotations
import asyncio
import secrets
from typing import TYPE_CHECKING
from orionis.storage.contracts.uploaded_file import IUploadedFile
from orionis.storage.exceptions import StoragePathException

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from orionis.http.payload.contracts.uploaded_file import (
        IUploadedFile as IHttpUploadedFile,
    )
    from orionis.storage.contracts.file import IFile
    from orionis.storage.contracts.manager import IStorageManager

class UploadedFile(IUploadedFile):
    """
    Represent a file received through HTTP, ready to be stored.

    The object adapts the buffered multipart payload produced by the
    HTTP layer so it can be persisted onto any configured disk. It is
    fully decoupled from the request object and internally always
    delegates persistence to :class:`~orionis.storage.file.File`
    through the disk resolved by the manager.
    """

    __slots__ = ("_hash_name", "_manager", "_source")

    def __init__(
        self,
        source: IHttpUploadedFile,
        manager: IStorageManager,
    ) -> None:
        """
        Initialize the uploaded file with its payload and manager.

        Parameters
        ----------
        source : IHttpUploadedFile
            Buffered multipart payload produced by the HTTP layer.
        manager : IStorageManager
            Manager used to resolve target disks.

        Returns
        -------
        None
        """
        self._source = source
        self._manager = manager
        self._hash_name: str | None = None

    # ── Payload metadata ─────────────────────────────────────────────────────

    def originalName(self) -> str:
        """
        Return the sanitized client-supplied file name.

        Returns
        -------
        str
            Original file name as reported by the client.
        """
        return self._source.filename

    def extension(self) -> str:
        """
        Return the lowercase file extension including the dot.

        Returns
        -------
        str
            Extension such as ``'.png'``, or an empty string when the
            original name has none.
        """
        return self._source.extension

    def size(self) -> int:
        """
        Return the size of the uploaded payload in bytes.

        Returns
        -------
        int
            Payload size in bytes.
        """
        return self._source.size

    def mimeType(self) -> str | None:
        """
        Return the MIME type declared by the client.

        Returns
        -------
        str | None
            Declared MIME type, or ``None`` when absent.
        """
        return self._source.content_type

    def hashName(self) -> str:
        """
        Return a random, collision-safe name for the file.

        The name is generated once and cached, so repeated calls on
        the same instance always return the same value.

        Returns
        -------
        str
            Random hexadecimal name with the original extension.
        """
        if self._hash_name is None:
            self._hash_name = secrets.token_hex(20) + self.extension()
        return self._hash_name

    # ── Content access ───────────────────────────────────────────────────────

    async def read(self) -> bytes:
        """
        Read the full uploaded payload.

        Returns
        -------
        bytes
            Complete payload contents.
        """
        # The payload may be spooled to disk, so read on a worker thread.
        return await asyncio.to_thread(self._source.read)

    async def __stream(self) -> AsyncIterator[bytes]:
        """
        Stream the payload in chunks without loading it in memory.

        Yields
        ------
        bytes
            Consecutive chunks of the buffered payload.
        """
        iterator = self._source.chunks()

        # Advance the blocking iterator on a worker thread per chunk.
        while True:
            chunk = await asyncio.to_thread(next, iterator, b"")
            if not chunk:
                break
            yield chunk

    # ── Persistence operations ───────────────────────────────────────────────

    async def store(
        self,
        directory: str = "",
        disk: str | None = None,
        visibility: str | None = None,
    ) -> IFile:
        """
        Persist the payload under a generated hash name.

        Parameters
        ----------
        directory : str
            Root-relative target directory on the disk.
        disk : str | None
            Disk name, or ``None`` for the default disk.
        visibility : str | None
            Visibility to apply, or ``None`` for the medium default.

        Returns
        -------
        IFile
            File object pointing at the stored file.
        """
        return await self.storeAs(directory, self.hashName(), disk, visibility)

    async def storeAs(
        self,
        directory: str,
        name: str,
        disk: str | None = None,
        visibility: str | None = None,
    ) -> IFile:
        """
        Persist the payload under an explicit file name.

        Parameters
        ----------
        directory : str
            Root-relative target directory on the disk.
        name : str
            Target file name without directory separators.
        disk : str | None
            Disk name, or ``None`` for the default disk.
        visibility : str | None
            Visibility to apply, or ``None`` for the medium default.

        Returns
        -------
        IFile
            File object pointing at the stored file.

        Raises
        ------
        StoragePathException
            If *name* is empty or contains a directory separator.
        """
        # The name must be a single path segment; directories go apart.
        if not name or "/" in name or "\\" in name:
            error_msg = f"Invalid upload file name [{name}]."
            raise StoragePathException(error_msg)

        target = f"{directory}/{name}" if directory else name
        file = self._manager.disk(disk).file(target)
        return await file.writeStream(self.__stream(), visibility)

    async def move(
        self,
        directory: str,
        name: str | None = None,
        disk: str | None = None,
    ) -> IFile:
        """
        Persist the payload and release the upload buffer.

        Parameters
        ----------
        directory : str
            Root-relative target directory on the disk.
        name : str | None
            Target file name, or ``None`` to use a generated hash
            name.
        disk : str | None
            Disk name, or ``None`` for the default disk.

        Returns
        -------
        IFile
            File object pointing at the stored file.
        """
        stored = await self.storeAs(directory, name or self.hashName(), disk)

        # Release the temporary upload buffer once persisted.
        await asyncio.to_thread(self._source.close)
        return stored

    async def copy(
        self,
        directory: str,
        name: str | None = None,
        disk: str | None = None,
    ) -> IFile:
        """
        Persist the payload while keeping the upload buffer usable.

        Parameters
        ----------
        directory : str
            Root-relative target directory on the disk.
        name : str | None
            Target file name, or ``None`` to use a generated hash
            name.
        disk : str | None
            Disk name, or ``None`` for the default disk.

        Returns
        -------
        IFile
            File object pointing at the stored file.
        """
        return await self.storeAs(directory, name or self.hashName(), disk)
