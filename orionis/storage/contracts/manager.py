from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from orionis.http.payload.contracts.uploaded_file import (
        IUploadedFile as IHttpUploadedFile,
    )
    from orionis.storage.contracts.disk import IDisk
    from orionis.storage.contracts.driver import IStorageDriver
    from orionis.storage.contracts.uploaded_file import IUploadedFile

class IStorageManager(ABC):
    """
    Define the contract for the storage manager.

    The manager resolves the filesystems configuration, builds
    :class:`~orionis.storage.contracts.disk.IDisk` objects on demand,
    caches them, and exposes extension points for custom drivers. It
    never performs file operations itself.
    """

    __slots__ = ()

    @abstractmethod
    def disk(self, name: str | None = None) -> IDisk:
        """
        Resolve the disk registered under *name*.

        The disk is built on first access and cached for reuse.

        Parameters
        ----------
        name : str | None
            Disk name as declared in the filesystems configuration,
            or ``None`` for the default disk.

        Returns
        -------
        IDisk
            Disk bound to its configured driver.

        Raises
        ------
        DiskNotFoundException
            If the disk is not declared in the configuration.
        DriverNotSupportedException
            If the disk references a driver with no implementation.
        """

    @abstractmethod
    def default(self) -> IDisk:
        """
        Resolve the default disk from the configuration.

        Returns
        -------
        IDisk
            The disk configured as default.

        Raises
        ------
        DiskNotFoundException
            If the default disk is not declared in the configuration.
        """

    @abstractmethod
    def extend(
        self,
        driver: str,
        factory: Callable[[object], IStorageDriver],
    ) -> None:
        """
        Register a custom driver factory under *driver*.

        The factory receives the disk configuration entity and must
        return a ready-to-use driver instance. Registering a factory
        clears the disk cache so new resolutions pick it up.

        Parameters
        ----------
        driver : str
            Driver name as referenced by disk configurations.
        factory : Callable[[object], IStorageDriver]
            Callable building the driver from a disk configuration.

        Returns
        -------
        None
        """

    @abstractmethod
    def uploaded(self, source: IHttpUploadedFile) -> IUploadedFile:
        """
        Wrap an HTTP multipart payload as a storable uploaded file.

        Parameters
        ----------
        source : IHttpUploadedFile
            Buffered multipart payload produced by the HTTP layer.

        Returns
        -------
        IUploadedFile
            Uploaded file bound to this manager for disk resolution.
        """
