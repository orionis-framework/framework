from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.storage.contracts.directory import IDirectory
from orionis.storage.file import File
from orionis.storage.paths import normalizePath

if TYPE_CHECKING:
    from orionis.storage.contracts.driver import IStorageDriver
    from orionis.storage.contracts.file import IFile

class Directory(IDirectory):
    """
    Represent a directory on a storage disk.

    The object encapsulates its canonical path and the driver of the
    disk it belongs to. Listing methods always return
    :class:`~orionis.storage.file.File` and :class:`Directory`
    objects — never plain strings.
    """

    __slots__ = ("_driver", "_path")

    def __init__(self, driver: IStorageDriver, path: str = "") -> None:
        """
        Initialize the directory with its driver and canonical path.

        Parameters
        ----------
        driver : IStorageDriver
            Driver of the disk that owns the directory.
        path : str
            Root-relative directory path; normalized on ingestion.
            The empty string denotes the disk root.

        Returns
        -------
        None

        Raises
        ------
        StoragePathException
            If *path* is invalid or escapes the disk root.
        """
        self._driver = driver
        self._path = normalizePath(path)

    def path(self) -> str:
        """
        Return the canonical root-relative path of the directory.

        Returns
        -------
        str
            Normalized path relative to the disk root. The empty
            string denotes the disk root itself.
        """
        return self._path

    async def create(self) -> IDirectory:
        """
        Create the directory, including any missing parents.

        Returns
        -------
        IDirectory
            The directory itself, enabling fluent chaining.
        """
        await self._driver.createDirectory(self._path)
        return self

    async def delete(self) -> bool:
        """
        Recursively delete the directory and its contents.

        Returns
        -------
        bool
            ``True`` if the directory existed and was removed.
        """
        return await self._driver.deleteDirectory(self._path)

    async def exists(self) -> bool:
        """
        Check whether the directory exists on its disk.

        Returns
        -------
        bool
            ``True`` if the directory exists.
        """
        return await self._driver.directoryExists(self._path)

    async def files(self) -> list[IFile]:
        """
        List the files directly contained in the directory.

        Returns
        -------
        list[IFile]
            File objects for every direct child file, sorted by path.
        """
        paths = await self._driver.files(self._path, recursive=False)
        return [File(self._driver, path) for path in paths]

    async def allFiles(self) -> list[IFile]:
        """
        List every file contained in the directory tree.

        Returns
        -------
        list[IFile]
            File objects for all nested files, sorted by path.
        """
        paths = await self._driver.files(self._path, recursive=True)
        return [File(self._driver, path) for path in paths]

    async def directories(self) -> list[IDirectory]:
        """
        List the directories directly contained in the directory.

        Returns
        -------
        list[IDirectory]
            Directory objects for every direct child directory,
            sorted by path.
        """
        paths = await self._driver.directories(self._path, recursive=False)
        return [Directory(self._driver, path) for path in paths]

    async def allDirectories(self) -> list[IDirectory]:
        """
        List every directory contained in the directory tree.

        Returns
        -------
        list[IDirectory]
            Directory objects for all nested directories, sorted by
            path.
        """
        paths = await self._driver.directories(self._path, recursive=True)
        return [Directory(self._driver, path) for path in paths]
