from __future__ import annotations
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from orionis.foundation.config.filesystems.entitites.disks import Disks
from orionis.foundation.config.filesystems.entitites.filesystems import (
    Filesystems,
)
from orionis.foundation.config.filesystems.entitites.local import Local
from orionis.storage.contracts.disk import IDisk
from orionis.storage.contracts.manager import IStorageManager
from orionis.storage.contracts.uploaded_file import IUploadedFile
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
from orionis.storage.manager import StorageManager
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import Iterator

# Relative root shipped by the framework, already present in the repo.
_RELATIVE_ROOT: str = "storage/app/private"

class _StubApp:
    """Application double exposing a base path and raw configuration."""

    __slots__ = ("_base_path", "_config")

    def __init__(self, base_path: Path, config: object) -> None:
        self._base_path = base_path
        self._config = config

    @property
    def basePath(self) -> Path:
        """
        Return the application base path.

        Returns
        -------
        Path
            Base path injected at construction time.
        """
        return self._base_path

    def config(self, key: str) -> object:
        """
        Return the configuration stored under *key*.

        Parameters
        ----------
        key : str
            Configuration key requested by the manager.

        Returns
        -------
        object
            Raw dictionary or validated entity for the key.

        Raises
        ------
        KeyError
            If an unexpected configuration key is requested.
        """
        if key != "filesystems":
            raise KeyError(key)
        return self._config

class _FakeUpload:
    """Duck-typed multipart payload produced by the HTTP layer."""

    __slots__ = ("content_type", "extension", "filename", "payload")

    def __init__(self, filename: str, data: bytes) -> None:
        self.filename = filename
        self.content_type = "application/octet-stream"
        self.payload = data
        dot = filename.rfind(".")
        self.extension = filename[dot:].lower() if dot > 0 else ""

    @property
    def size(self) -> int:
        """
        Return the payload size in bytes.

        Returns
        -------
        int
            Byte count of the buffered data.
        """
        return len(self.payload)

    def read(self) -> bytes:
        """
        Return the full buffered payload.

        Returns
        -------
        bytes
            Buffered content.
        """
        return self.payload

    def chunks(self, size: int = 65536) -> Iterator[bytes]:
        """
        Yield the payload in fixed-size chunks.

        Parameters
        ----------
        size : int
            Maximum number of bytes per yielded chunk.

        Yields
        ------
        bytes
            The next chunk of the buffered payload.
        """
        for start in range(0, len(self.payload), size):
            yield self.payload[start:start + size]

    def close(self) -> None:
        """Release the buffered payload (no-op for the double)."""

def build_manager(
    base_path: Path,
    disks: dict[str, dict[str, object]],
    default: str = "local",
) -> StorageManager:
    """
    Build a manager over a stubbed application.

    Parameters
    ----------
    base_path : Path
        Directory acting as the application base path.
    disks : dict[str, dict[str, object]]
        Raw disk declarations merged into the configuration.
    default : str
        Name of the disk configured as default.

    Returns
    -------
    StorageManager
        Manager wired to the supplied configuration.
    """
    config = {"default": default, "disks": disks}
    return StorageManager(_StubApp(base_path, config))  # type: ignore[arg-type]

class TestStorageManagerConfiguration(TestCase):

    def setUp(self) -> None:
        """
        Create an isolated base path before each test.

        Keeps disk roots contained inside a temporary directory.
        """
        self._tmpdir = tempfile.TemporaryDirectory()
        self._base = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        """
        Remove the temporary base path after each test.

        Ensures roots created by the manager are cleaned up.
        """
        self._tmpdir.cleanup()

    def testImplementsTheManagerContract(self) -> None:
        """
        Expose the manager through its published contract.

        Validates the type bound by the service provider.
        """
        manager = build_manager(
            self._base,
            {"local": {"driver": "local", "path": str(self._base / "p")}},
        )
        self.assertIsInstance(manager, IStorageManager)

    def testRawDictionaryConfigurationIsValidated(self) -> None:
        """
        Convert raw configuration dictionaries into the entity.

        Validates the normalization performed at construction time.
        """
        manager = build_manager(
            self._base,
            {"local": {"driver": "local", "path": str(self._base / "p")}},
        )
        self.assertIsInstance(manager._config, Filesystems)
        self.assertEqual(manager._default, "local")

    def testValidatedEntityConfigurationIsUsedAsIs(self) -> None:
        """
        Accept an already validated configuration entity.

        Validates the branch skipping entity construction.
        """
        entity = Filesystems(
            default="public",
            disks=Disks(local=Local(path=str(self._base / "p"))),
        )
        manager = StorageManager(_StubApp(self._base, entity))  # type: ignore[arg-type]
        self.assertIs(manager._config, entity)
        self.assertEqual(manager._default, "public")

class TestStorageManagerDiskResolution(TestCase):

    def setUp(self) -> None:
        """
        Build a manager with two local disks before each test.

        Mirrors the shape of the shipped filesystems configuration.
        """
        self._tmpdir = tempfile.TemporaryDirectory()
        self._base = Path(self._tmpdir.name)
        self._manager = build_manager(
            self._base,
            {
                "local": {
                    "driver": "local",
                    "path": str(self._base / "private"),
                },
                "public": {
                    "driver": "local",
                    "path": str(self._base / "public"),
                    "url": "/static",
                },
            },
        )

    def tearDown(self) -> None:
        """
        Remove the temporary base path after each test.

        Ensures roots created by the manager are cleaned up.
        """
        self._tmpdir.cleanup()

    def testDiskResolvesTheRequestedName(self) -> None:
        """
        Resolve the disk declared under the requested name.

        Validates the primary entry point of the manager.
        """
        disk = self._manager.disk("public")
        self.assertIsInstance(disk, IDisk)
        self.assertEqual(disk.name(), "public")

    def testDiskFallsBackToTheDefaultName(self) -> None:
        """
        Resolve the default disk when no name is supplied.

        Validates the optional argument of disk().
        """
        self.assertEqual(self._manager.disk().name(), "local")

    def testDefaultDelegatesToDisk(self) -> None:
        """
        Resolve the default disk through the dedicated accessor.

        Validates that default() and disk() share one cache.
        """
        self.assertIs(self._manager.default(), self._manager.disk())

    def testDisksAreCachedPerName(self) -> None:
        """
        Reuse the disk instance built on first access.

        Validates the manager-level disk cache.
        """
        self.assertIs(
            self._manager.disk("public"), self._manager.disk("public"),
        )

    def testUnknownDiskRaisesDiskNotFound(self) -> None:
        """
        Reject disk names absent from the configuration.

        Validates the failure contract of disk().
        """
        with self.assertRaises(DiskNotFoundException) as ctx:
            self._manager.disk("dropbox")
        self.assertIn("dropbox", str(ctx.exception))

    def testResolvedDisksAreConcreteDiskObjects(self) -> None:
        """
        Build concrete Disk objects for every configured name.

        Validates the object bound to each configured driver.
        """
        self.assertIsInstance(self._manager.disk("local"), Disk)

    async def testResolvedDisksWriteInsideTheirRoot(self) -> None:
        """
        Anchor every write inside the configured disk root.

        Validates end-to-end persistence through the manager.
        """
        await self._manager.disk("local").put("inner/data.txt", "ok")
        stored = self._base / "private" / "inner" / "data.txt"
        self.assertEqual(stored.read_text(encoding="utf-8"), "ok")

class TestStorageManagerDriverSelection(TestCase):

    def setUp(self) -> None:
        """
        Create an isolated base path before each test.

        Keeps disk roots contained inside a temporary directory.
        """
        self._tmpdir = tempfile.TemporaryDirectory()
        self._base = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        """
        Remove the temporary base path after each test.

        Ensures roots created by the manager are cleaned up.
        """
        self._tmpdir.cleanup()

    def testLocalDriverKeepsAbsoluteRoots(self) -> None:
        """
        Bind local disks declaring an absolute path as is.

        Validates the absolute branch of the local driver builder.
        """
        root = self._base / "private"
        manager = build_manager(
            self._base, {"local": {"driver": "local", "path": str(root)}},
        )
        driver = manager.disk("local")._driver
        self.assertIsInstance(driver, LocalStorageDriver)
        self.assertEqual(driver._root, root.resolve())

    def testLocalDriverAnchorsRelativeRootsToTheBasePath(self) -> None:
        """
        Anchor relative disk roots at the application base path.

        Validates the relative branch of the local driver builder.
        """
        manager = build_manager(
            self._base,
            {"local": {"driver": "local", "path": _RELATIVE_ROOT}},
        )
        driver = manager.disk("local")._driver
        self.assertEqual(driver._root, (self._base / _RELATIVE_ROOT).resolve())

    def testLocalDriverReceivesTheConfiguredUrl(self) -> None:
        """
        Forward the configured base URL to the local driver.

        Validates URL support on public local disks.
        """
        manager = build_manager(
            self._base,
            {
                "public": {
                    "driver": "local",
                    "path": str(self._base / "public"),
                    "url": "/static/",
                },
            },
            default="public",
        )
        self.assertEqual(manager.default()._driver._base_url, "/static")

    def testMemoryDriverIsBuiltFromItsDriverName(self) -> None:
        """
        Bind disks declaring the memory driver to the memory backend.

        Validates the in-process branch of the driver builder.
        """
        manager = build_manager(
            self._base,
            {
                "public": {
                    "driver": "memory",
                    "path": str(self._base / "public"),
                    "url": "/media",
                },
            },
            default="public",
        )
        driver = manager.default()._driver
        self.assertIsInstance(driver, MemoryStorageDriver)
        self.assertEqual(driver._base_url, "/media")

    def testCloudDriversAreBuiltWithoutTheirSdk(self) -> None:
        """
        Bind cloud disks to their official-SDK driver classes.

        Driver construction is lazy, so no cloud SDK is required.
        """
        manager = build_manager(
            self._base,
            {
                "s3": {"driver": "aws", "region": "us-east-1"},
                "azure": {"driver": "azure"},
                "gcs": {"driver": "gcs"},
            },
            default="s3",
        )
        self.assertIsInstance(manager.disk("s3")._driver, S3StorageDriver)
        self.assertIsInstance(
            manager.disk("azure")._driver, AzureStorageDriver,
        )
        self.assertIsInstance(
            manager.disk("gcs")._driver, GoogleStorageDriver,
        )

    def testCloudDriverAliasesAreAccepted(self) -> None:
        """
        Accept the alternative names of the cloud drivers.

        Validates the ``s3`` and ``google`` driver aliases.
        """
        manager = build_manager(
            self._base,
            {
                "s3": {"driver": "s3", "region": "us-east-1"},
                "gcs": {"driver": "google"},
            },
            default="s3",
        )
        self.assertIsInstance(manager.disk("s3")._driver, S3StorageDriver)
        self.assertIsInstance(
            manager.disk("gcs")._driver, GoogleStorageDriver,
        )

    def testUnknownDriverRaisesDriverNotSupported(self) -> None:
        """
        Reject disks referencing a driver without implementation.

        Validates the failure contract of the driver builder.
        """
        manager = build_manager(
            self._base,
            {"s3": {"driver": "dropbox", "region": "us-east-1"}},
            default="s3",
        )
        with self.assertRaises(DriverNotSupportedException) as ctx:
            manager.disk("s3")
        self.assertIn("StorageManager.extend()", str(ctx.exception))

class TestStorageManagerExtension(TestCase):

    def setUp(self) -> None:
        """
        Build a manager with a cloud disk before each test.

        Provides a disk whose builtin driver can be overridden.
        """
        self._tmpdir = tempfile.TemporaryDirectory()
        self._base = Path(self._tmpdir.name)
        self._manager = build_manager(
            self._base,
            {
                "local": {
                    "driver": "local",
                    "path": str(self._base / "private"),
                },
                "s3": {"driver": "aws", "region": "us-east-1"},
            },
        )

    def tearDown(self) -> None:
        """
        Remove the temporary base path after each test.

        Ensures roots created by the manager are cleaned up.
        """
        self._tmpdir.cleanup()

    async def testCustomFactoryTakesPrecedenceOverBuiltins(self) -> None:
        """
        Resolve disks through factories registered at runtime.

        Validates the extend() extension point.
        """
        self._manager.extend("aws", lambda _config: MemoryStorageDriver())
        disk = self._manager.disk("s3")
        self.assertIsInstance(disk._driver, MemoryStorageDriver)
        await disk.put("f.txt", b"x")
        self.assertTrue(await disk.exists("f.txt"))

    def testCustomFactoryReceivesTheDiskConfiguration(self) -> None:
        """
        Hand the disk configuration entity to the factory.

        Validates the argument contract of extend().
        """
        received: list[object] = []

        def factory(config: object) -> MemoryStorageDriver:
            """Build a memory driver recording its configuration."""
            received.append(config)
            return MemoryStorageDriver()

        self._manager.extend("aws", factory)
        self._manager.disk("s3")
        self.assertEqual(getattr(received[0], "region", None), "us-east-1")

    def testExtendInvalidatesPreviouslyCachedDisks(self) -> None:
        """
        Drop cached disks when a new factory is registered.

        Validates that extend() never leaves stale drivers behind.
        """
        first = self._manager.disk("local")
        self._manager.extend("local", lambda _config: MemoryStorageDriver())
        second = self._manager.disk("local")
        self.assertIsNot(first, second)
        self.assertIsInstance(second._driver, MemoryStorageDriver)

class TestStorageManagerUploads(TestCase):

    def setUp(self) -> None:
        """
        Build a manager backed by a temporary local disk.

        Provides a persistence target for uploaded payloads.
        """
        self._tmpdir = tempfile.TemporaryDirectory()
        self._base = Path(self._tmpdir.name)
        self._manager = build_manager(
            self._base,
            {
                "local": {
                    "driver": "local",
                    "path": str(self._base / "private"),
                },
            },
        )

    def tearDown(self) -> None:
        """
        Remove the temporary base path after each test.

        Ensures roots created by the manager are cleaned up.
        """
        self._tmpdir.cleanup()

    def testUploadedWrapsThePayload(self) -> None:
        """
        Wrap an HTTP payload into a storable uploaded file.

        Validates the type returned by uploaded().
        """
        upload = self._manager.uploaded(
            _FakeUpload("photo.png", b"png-bytes"),  # type: ignore[arg-type]
        )
        self.assertIsInstance(upload, IUploadedFile)

    async def testUploadedFilesPersistOnManagedDisks(self) -> None:
        """
        Persist a wrapped payload through the resolved disk.

        Validates the wiring between uploads and the manager.
        """
        upload = self._manager.uploaded(
            _FakeUpload("photo.png", b"png-bytes"),  # type: ignore[arg-type]
        )
        stored = await upload.storeAs("avatars", "user.png", "local")
        self.assertEqual(stored.path(), "avatars/user.png")
        self.assertEqual(await stored.read(), b"png-bytes")
