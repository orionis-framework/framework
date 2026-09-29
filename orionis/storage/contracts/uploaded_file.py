from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.storage.contracts.file import IFile

class IUploadedFile(ABC):
    """
    Define the contract for a file received through HTTP.

    An uploaded file adapts an incoming multipart payload so it can be
    persisted onto any configured disk. It is fully decoupled from the
    HTTP request object: it only consumes the buffered payload handle.
    """

    __slots__ = ()

    @abstractmethod
    def originalName(self) -> str:
        """
        Return the sanitized client-supplied file name.

        Returns
        -------
        str
            Original file name as reported by the client.
        """

    @abstractmethod
    def extension(self) -> str:
        """
        Return the lowercase file extension including the dot.

        Returns
        -------
        str
            Extension such as ``'.png'``, or an empty string when the
            original name has none.
        """

    @abstractmethod
    def size(self) -> int:
        """
        Return the size of the uploaded payload in bytes.

        Returns
        -------
        int
            Payload size in bytes.
        """

    @abstractmethod
    def mimeType(self) -> str | None:
        """
        Return the MIME type declared by the client.

        Returns
        -------
        str | None
            Declared MIME type, or ``None`` when absent.
        """

    @abstractmethod
    def hashName(self) -> str:
        """
        Return a random, collision-safe name for the file.

        The name is generated once and cached, so repeated calls on the
        same instance always return the same value.

        Returns
        -------
        str
            Random hexadecimal name with the original extension.
        """

    @abstractmethod
    async def read(self) -> bytes:
        """
        Read the full uploaded payload.

        Returns
        -------
        bytes
            Complete payload contents.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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
