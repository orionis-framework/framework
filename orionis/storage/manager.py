from pathlib import Path
from typing import TYPE_CHECKING
from orionis.foundation.config.filesystems.entitites.filesystems import Filesystems
from orionis.foundation.contracts.application import IApplication
from orionis.storage.contracts.manager import IStorageManager
from orionis.storage.disk import Disk
from orionis.storage.drivers.azure import AzureStorageDriver
from orionis.storage.drivers.gcs import GoogleStorageDriver
from orionis.storage.drivers.local import LocalStorageDriver
from orionis.storage.drivers.memory import MemoryStorageDriver
from orionis.storage.drivers.s3 import S3StorageDriver
from orionis.storage.exceptions import (
    DiskNotFoundException,
    DriverNotSupportedException,
)
from orionis.storage.uploaded_file import UploadedFile

if TYPE_CHECKING:
    from collections.abc import Callable
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
    :class:`~orionis.storage.disk.Disk` objects bound to their drivers,
    and caches them per name. It knows nothing about files or
    directories: that behavior lives in the domain objects returned by
    each disk.
    """

    # ruff: noqa: TC001

    __slots__ = ("_app", "_base_path", "_config", "_custom", "_default", "_disks")

    def __init__(self, app: IApplication) -> None:
        """
        Initialize the manager and resolve the active configuration.

        Parameters
        ----------
        app : IApplication
            Application container used to read the configuration and
            the base path.

        Returns
        -------
        None
        """
        self._app = app
        self._base_path: Path = app.basePath

        # Normalize the raw configuration into the validated entity.
        config_data = app.config("filesystems")
        self._config: Filesystems = (
            Filesystems(**config_data)
            if isinstance(config_data, dict)
            else config_data
        )

        self._default: str = str(self._config.default)
        self._disks: dict[str, IDisk] = {}
        self._custom: dict[str, Callable[[object], IStorageDriver]] = {}

    # ── Disk resolution ──────────────────────────────────────────────────────

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
        resolved = name or self._default
        cached = self._disks.get(resolved)
        if cached is not None:
            return cached

        built = Disk(name=resolved, driver=self.__buildDriver(resolved))
        self._disks[resolved] = built
        return built

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
        factory : Callable[[object], IStorageDriver]
            Callable building the driver from a disk configuration.

        Returns
        -------
        None
        """
        self._custom[driver] = factory

        # Invalidate cached disks so they rebuild with the new factory.
        self._disks.clear()

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
        DiskNotFoundException
            If the disk is not declared in the configuration.
        """
        config = getattr(self._config.disks, name, None)
        if config is None:
            error_msg = (
                f"Disk [{name}] is not defined in the filesystems "
                "configuration."
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
        IStorageDriver
            Configured driver instance.

        Raises
        ------
        DiskNotFoundException
            If the disk is not declared in the configuration.
        DriverNotSupportedException
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
            return MemoryStorageDriver(
                base_url=getattr(config, "url", None),
            )

        # Cloud drivers rely on optional official SDKs imported lazily;
        # a missing package surfaces on first operation with install
        # instructions (see each driver's docstring).
        if driver_name in ("aws", "s3"):
            return S3StorageDriver(config)

        if driver_name == "azure":
            return AzureStorageDriver(config)

        if driver_name in ("gcs", "google"):
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
        IStorageDriver
            Local driver rooted inside the application base path.
        """
        # Relative roots are anchored to the application base path.
        root = Path(str(getattr(config, "path", "storage/app")))
        if not root.is_absolute():
            root = self._base_path / root

        return LocalStorageDriver(
            root=root,
            base_url=getattr(config, "url", None),
        )
