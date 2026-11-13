# ruff: noqa: PLC0415, TC001, TC003
# Keep extension annotations available while optional driver imports remain lazy.
"""Coordinate disk resolution for the storage component."""

from collections.abc import Callable
from pathlib import Path
from threading import RLock
from orionis.foundation.config.filesystems.entitites.filesystems import Filesystems
from orionis.foundation.contracts.application import IApplication
from orionis.storage.contracts.manager import IStorageManager
from orionis.storage.disk import Disk
from orionis.storage.exceptions import (
    DiskNotFoundException,
    DriverNotSupportedException,
)
from orionis.storage.uploaded_file import UploadedFile
from orionis.http.payload.contracts.uploaded_file import (
    IUploadedFile as IHttpUploadedFile,
)
from orionis.storage.contracts.disk import IDisk
from orionis.storage.contracts.driver import IStorageDriver
from orionis.storage.contracts.uploaded_file import IUploadedFile


class StorageManager(IStorageManager):
    """
    Coordinate disk resolution for the storage component.

    The manager reads the ``filesystems`` configuration, builds
    :class:`orionis.storage.Disk` objects bound to their drivers,
    and caches them per name. It knows nothing about files or
    directories: that behavior lives in the domain objects returned by
    each disk.
    """

    __slots__ = (
        "_app",
        "_base_path",
        "_config",
        "_custom",
        "_default",
        "_disks",
        "_lock",
    )
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, app: IApplication) -> None:
        """
        Initialize the manager and resolve the active configuration.

        Parameters
        ----------
        app : orionis.IApplication
            Application container used to read the configuration and
            the base path.

        Returns
        -------
        None
            No return value.
        """
        self._app = app
        """Application container used to read the configuration and the base path."""
        self._base_path: Path = app.basePath
        """Base path obtained from ``app.basePath``."""

        # Normalize the raw configuration into the validated entity.
        config_data = app.config("filesystems")
        self._config: Filesystems = (
            Filesystems(**config_data) if isinstance(config_data, dict) else config_data
        )
        """Validated configuration used to construct and operate the service."""

        self._default: str = str(self._config.default)
        """Value used when the client omits this argument."""
        self._disks: dict[str, IDisk] = {}
        """Storage disks cached after their first resolution."""
        self._custom: dict[str, Callable[[object], IStorageDriver]] = {}
        """Custom implementations registered by the application."""
        self._lock = RLock()
        """Serialize disk publication while allowing nested synchronous factories."""

    # ── Disk resolution ──────────────────────────────────────────────────────

    def disk(self, name: str | None = None) -> IDisk:
        """
        Resolve the disk registered under *name*.

        Build and publish a single disk on first access, including concurrent
        calls. A synchronous custom factory may resolve another configured disk.
        Subsequent calls reuse the published instance without taking the lock.

        Parameters
        ----------
        name : str | None
            Disk name as declared in the filesystems configuration,
            or ``None`` for the default disk.

        Returns
        -------
        orionis.storage.contracts.IDisk
            Disk bound to its configured driver.

        Raises
        ------
        orionis.storage.exceptions.DiskNotFoundException
            If the disk is not declared in the configuration.
        orionis.storage.exceptions.DriverNotSupportedException
            If the disk references a driver with no implementation.
        """
        resolved = name or self._default
        cached = self._disks.get(resolved)
        if cached is not None:
            return cached

        with self._lock:
            cached = self._disks.get(resolved)
            if cached is None:
                cached = Disk(name=resolved, driver=self.__buildDriver(resolved))
                self._disks[resolved] = cached
        return cached

    def default(self) -> IDisk:
        """
        Resolve the default disk from the configuration.

        Returns
        -------
        orionis.storage.contracts.IDisk
            The disk configured as default.

        Raises
        ------
        orionis.storage.exceptions.DiskNotFoundException
            If the default disk is not declared in the configuration.
        """
        return self.disk()

    # ── Extensibility ────────────────────────────────────────────────────────

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
        factory : typing.Callable[[object], contracts.IStorageDriver]
            Callable building the driver from a disk configuration.

        Returns
        -------
        None
            No return value.
        """
        with self._lock:
            self._custom[driver] = factory
            # Invalidate cached disks so they rebuild with the new factory.
            self._disks.clear()

    def uploaded(self, source: IHttpUploadedFile) -> IUploadedFile:
        """
        Wrap an HTTP multipart payload as a storable uploaded file.

        Parameters
        ----------
        source : orionis.http.payload.contracts.uploaded_file.IUploadedFile
            Buffered multipart payload produced by the HTTP layer.

        Returns
        -------
        orionis.storage.contracts.IUploadedFile
            Uploaded file bound to this manager for disk resolution.
        """
        return UploadedFile(source=source, manager=self)

    # ── Driver construction ──────────────────────────────────────────────────

    def __diskConfig(self, name: str) -> object:
        """
        Return the configuration entity for the disk named *name*.

        Parameters
        ----------
        name : str
            Disk name as declared in the filesystems configuration.

        Returns
        -------
        object
            Disk configuration entity.

        Raises
        ------
        orionis.storage.exceptions.DiskNotFoundException
            If the disk is not declared in the configuration.
        """
        config = getattr(self._config.disks, name, None)
        if config is None:
            error_msg = (
                f"Disk [{name}] is not defined in the filesystems configuration."
            )
            raise DiskNotFoundException(error_msg)
        return config

    def __buildDriver(self, name: str) -> IStorageDriver:
        """
        Instantiate the driver for the disk named *name*.

        Parameters
        ----------
        name : str
            Disk name as declared in the filesystems configuration.

        Returns
        -------
        orionis.storage.contracts.IStorageDriver
            Configured driver instance.

        Raises
        ------
        orionis.storage.exceptions.DiskNotFoundException
            If the disk is not declared in the configuration.
        orionis.storage.exceptions.DriverNotSupportedException
            If the disk references a driver with no implementation.
        """
        config = self.__diskConfig(name)
        driver_name = str(getattr(config, "driver", "") or "")

        # Custom factories registered via extend() take precedence.
        factory = self._custom.get(driver_name)
        if factory is not None:
            return factory(config)

        if driver_name == "local":
            return self.__buildLocalDriver(config)

        if driver_name == "memory":
            from orionis.storage.drivers.memory import MemoryStorageDriver

            return MemoryStorageDriver(
                base_url=getattr(config, "url", None),
            )

        # Cloud drivers rely on optional official SDKs imported lazily;
        # a missing package surfaces on first operation with install
        # instructions (see each driver's docstring).
        if driver_name in ("aws", "s3"):
            from orionis.storage.drivers.s3 import S3StorageDriver

            return S3StorageDriver(config)

        if driver_name == "azure":
            from orionis.storage.drivers.azure import AzureStorageDriver

            return AzureStorageDriver(config)

        if driver_name in ("gcs", "google"):
            from orionis.storage.drivers.gcs import GoogleStorageDriver

            return GoogleStorageDriver(config)

        error_msg = (
            f"Driver [{driver_name}] for disk [{name}] has no registered "
            "implementation. Register one with StorageManager.extend()."
        )
        raise DriverNotSupportedException(error_msg)

    def __buildLocalDriver(self, config: object) -> IStorageDriver:
        """
        Build a local driver from a disk configuration entity.

        Parameters
        ----------
        config : object
            Disk configuration entity exposing ``path`` and,
            optionally, ``url``.

        Returns
        -------
        orionis.storage.contracts.IStorageDriver
            Local driver rooted inside the application base path.
        """
        # Relative roots are anchored to the application base path.
        root = Path(str(getattr(config, "path", "storage/app")))
        if not root.is_absolute():
            root = self._base_path / root

        from orionis.storage.drivers.local import LocalStorageDriver

        return LocalStorageDriver(
            root=root,
            base_url=getattr(config, "url", None),
        )
