from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.storage.contracts.file import IFile

class IDirectory(ABC):
    """
    Define the contract for a directory on a storage disk.

    A directory object encapsulates its canonical path and delegates
    every operation to the driver of the disk it belongs to. Listing
    methods always return domain objects — never plain strings.
    """

    __slots__ = ()

    @abstractmethod
    def path(self) -> str:
        """
        Return the canonical root-relative path of the directory.

        Returns
        -------
        str
            Normalized path relative to the disk root. The empty
            string denotes the disk root itself.
        """

    @abstractmethod
    async def create(self) -> IDirectory:
        """
        Create the directory, including any missing parents.

        Returns
        -------
        IDirectory
            The directory itself, enabling fluent chaining.
        """

    @abstractmethod
    async def delete(self) -> bool:
        """
        Recursively delete the directory and its contents.

        Returns
        -------
        bool
            ``True`` if the directory existed and was removed.
        """

    @abstractmethod
    async def exists(self) -> bool:
        """
        Check whether the directory exists on its disk.

        Returns
        -------
        bool
            ``True`` if the directory exists.
        """

    @abstractmethod
    async def files(self) -> list[IFile]:
        """
        List the files directly contained in the directory.

        Returns
        -------
        list[IFile]
            File objects for every direct child file, sorted by path.
        """

    @abstractmethod
    async def allFiles(self) -> list[IFile]:
        """
        List every file contained in the directory tree.

        Returns
        -------
        list[IFile]
            File objects for all nested files, sorted by path.
        """

    @abstractmethod
    async def directories(self) -> list[IDirectory]:
        """
        List the directories directly contained in the directory.

        Returns
        -------
        list[IDirectory]
            Directory objects for every direct child directory,
            sorted by path.
        """

    @abstractmethod
    async def allDirectories(self) -> list[IDirectory]:
        """
        List every directory contained in the directory tree.

        Returns
        -------
        list[IDirectory]
            Directory objects for all nested directories, sorted by
            path.
        """
