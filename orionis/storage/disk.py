"""Represent a configured storage disk."""

from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.storage.contracts.disk import IDisk
from orionis.storage.directory import Directory
from orionis.storage.file import File

if TYPE_CHECKING:
    from orionis.storage.contracts.directory import IDirectory
    from orionis.storage.contracts.driver import IStorageDriver
    from orionis.storage.contracts.file import IFile

class Disk(IDisk):
    """
    Represent a configured storage disk.

    The disk is the high-level entry point to a storage backend. It
    builds :class:`orionis.storage.File` and
    :class:`orionis.storage.Directory` objects bound to its
    driver, and its convenience methods always delegate to those
    objects so no logic is ever duplicated.
    """

    __slots__ = ("_driver", "_name")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, name: str, driver: IStorageDriver) -> None:
        """
        Initialize the disk with its configuration name and driver.

        Parameters
        ----------
        name : str
            Disk name as declared in the filesystems configuration.
        driver : orionis.storage.contracts.IStorageDriver
            Driver instance backing the disk.

        Returns
        -------
        None
            Initialize the disk with its configuration name and driver.
        """
        self._name = name
        """Disk name as declared in the filesystems configuration."""
        self._driver = driver
        """Driver instance backing the disk."""

    def name(self) -> str:
        """
        Return the configuration name of the disk.

        Returns
        -------
        str
            Disk name as declared in the filesystems configuration.
        """
        return self._name

    # ── Object factories ─────────────────────────────────────────────────────

    def file(self, path: str) -> IFile:
        """
        Build a file object for *path* on this disk.

        Parameters
        ----------
        path : str
            Root-relative file path.

        Returns
        -------
        orionis.storage.contracts.IFile
            File object bound to this disk's driver.

        Raises
        ------
        orionis.storage.exceptions.StoragePathException
            If *path* is invalid or resolves to the disk root.
        """
        return File(self._driver, path)

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
        orionis.storage.contracts.IDirectory
            Directory object bound to this disk's driver.

        Raises
        ------
        orionis.storage.exceptions.StoragePathException
            If *path* is invalid or escapes the disk root.
        """
        return Directory(self._driver, path)

    # ── Convenience methods (always delegate to File) ────────────────────────

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
        orionis.storage.contracts.IFile
            File object pointing at the written file.
        """
        return await self.file(path).write(contents, visibility)

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
        return await self.file(path).exists()

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
        return await self.file(path).delete()

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
        orionis.storage.contracts.IFile
            File object pointing at the copy.

        Raises
        ------
        orionis.storage.exceptions.StorageFileNotFoundException
            If the source file does not exist.
        """
        return await self.file(source).copyTo(target)

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
        orionis.storage.contracts.IFile
            File object pointing at the moved file.

        Raises
        ------
        orionis.storage.exceptions.StorageFileNotFoundException
            If the source file does not exist.
        """
        return await self.file(source).moveTo(target)
