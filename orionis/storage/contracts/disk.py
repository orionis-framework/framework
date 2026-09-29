from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.storage.contracts.directory import IDirectory
    from orionis.storage.contracts.file import IFile

class IDisk(ABC):
    """
    Define the contract for a configured storage disk.

    A disk is the entry point to a storage backend. It builds
    :class:`~orionis.storage.contracts.file.IFile` and
    :class:`~orionis.storage.contracts.directory.IDirectory` objects
    bound to its driver and offers a small set of convenience methods
    that always delegate to those objects.
    """

    __slots__ = ()

    @abstractmethod
    def name(self) -> str:
        """
        Return the configuration name of the disk.

        Returns
        -------
        str
            Disk name as declared in the filesystems configuration.
        """

    @abstractmethod
    def file(self, path: str) -> IFile:
        """
        Build a file object for *path* on this disk.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        IFile
            File object bound to this disk's driver.
        """

    @abstractmethod
    def directory(self, path: str = "") -> IDirectory:
        """
        Build a directory object for *path* on this disk.

        Parameters
        ----------
        path : str
            Root-relative directory path. The empty string denotes
            the disk root.

        Returns
        -------
        IDirectory
            Directory object bound to this disk's driver.
        """

    @abstractmethod
    async def put(
        self,
        path: str,
        contents: bytes | str,
        visibility: str | None = None,
    ) -> IFile:
        """
        Write *contents* to *path* on this disk.

        Parameters
        ----------
        path : str
            Root-relative file path.
        contents : bytes | str
            Data to persist. Strings are encoded as UTF-8.
        visibility : str | None
            Visibility to apply, or ``None`` for the medium default.

        Returns
        -------
        IFile
            File object pointing at the written file.
        """

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """
        Check whether a file exists at *path* on this disk.

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
    async def delete(self, path: str) -> bool:
        """
        Delete the file at *path* from this disk.

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
    async def copy(self, source: str, target: str) -> IFile:
        """
        Copy the file at *source* to *target* on this disk.

        Parameters
        ----------
        source : str
            Root-relative path of the existing file.
        target : str
            Root-relative destination path.

        Returns
        -------
        IFile
            File object pointing at the copy.

        Raises
        ------
        StorageFileNotFoundException
            If the source file does not exist.
        """

    @abstractmethod
    async def move(self, source: str, target: str) -> IFile:
        """
        Move the file at *source* to *target* on this disk.

        Parameters
        ----------
        source : str
            Root-relative path of the existing file.
        target : str
            Root-relative destination path.

        Returns
        -------
        IFile
            File object pointing at the moved file.

        Raises
        ------
        StorageFileNotFoundException
            If the source file does not exist.
        """
