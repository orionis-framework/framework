# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify physical file paths against the configured application base path."""

from __future__ import annotations
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from orionis.foundation.config.filesystems.entitites.aws import S3
from orionis.foundation.config.filesystems.entitites.azure import Azure
from orionis.foundation.config.filesystems.entitites.gcs import GCS
from orionis.storage.drivers import functions as driver_functions
from orionis.storage.drivers.azure import AzureStorageDriver
from orionis.storage.drivers.gcs import GoogleStorageDriver
from orionis.storage.drivers.local import LocalStorageDriver
from orionis.storage.drivers.memory import MemoryStorageDriver
from orionis.storage.drivers.s3 import S3StorageDriver
from orionis.storage.exceptions import (
    StoragePathException,
    UnsupportedStorageOperationException,
)
from orionis.storage.file import File
from orionis.storage.manager import StorageManager
from orionis.test import TestCase


class TestFileFilesystemPaths(TestCase):
    """Exercise synchronous paths through real local disks and file references."""

    def setUp(self) -> None:
        """Create an application root independent of the working directory.

        Returns
        -------
        None
            No return value.
        """
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self._base = Path(temporary.name).resolve()
        self._root = self._base / "storage"

    def testPathsDescribeMissingFilesWithoutCreatingThem(self) -> None:
        """Resolve normalized references without writing files or directories.

        Returns
        -------
        None
            No return value.
        """
        driver = LocalStorageDriver(self._root, base_path=self._base)
        file = File(driver, "\\logs//old/../app.log")

        self.assertEqual(file.path(), "logs/app.log")
        self.assertEqual(file.absolutePath(), str(self._root / "logs/app.log"))
        self.assertEqual(file.relativePath(), "storage/logs/app.log")
        self.assertFalse((self._root / "logs").exists())
        self.assertEqual(file.path(), "logs/app.log")

    def testManagerUsesApplicationBaseForRelativeAndAbsoluteRoots(self) -> None:
        """Anchor both disk configurations to the application's supplied base.

        Returns
        -------
        None
            No return value.
        """
        self.assertNotEqual(self._base, Path.cwd().resolve())
        for root in ("storage", str(self._root)):
            with self.subTest(root=root):
                config = {
                    "default": "local",
                    "disks": {"local": {"driver": "local", "path": root}},
                }
                manager = StorageManager(
                    SimpleNamespace(
                        basePath=self._base,
                        config=lambda _section, value=config: value,
                    ),
                )
                file = manager.disk("local").file("logs/app.log")

                self.assertEqual(file.path(), "logs/app.log")
                self.assertEqual(
                    file.absolutePath(),
                    str(self._root / "logs/app.log"),
                )
                self.assertEqual(file.relativePath(), "storage/logs/app.log")

    def testApplicationBaseIsNormalizedBeforeComputingRelativePaths(self) -> None:
        """Collapse redundant application path segments before comparison.

        Returns
        -------
        None
            No return value.
        """
        driver = LocalStorageDriver(
            self._root,
            base_path=self._base / "config" / "..",
        )
        file = File(driver, "logs/app.log")

        self.assertEqual(file.relativePath(), "storage/logs/app.log")

    def testStandaloneLocalDriverRequiresAnExplicitApplicationBase(self) -> None:
        """Allow native paths without inventing a project root from the process.

        Returns
        -------
        None
            No return value.
        """
        file = File(LocalStorageDriver(self._root), "logs/app.log")

        self.assertEqual(file.absolutePath(), str(self._root / "logs/app.log"))
        with self.assertRaises(UnsupportedStorageOperationException):
            file.relativePath()

    def testRootOutsideTheApplicationUsesParentSegments(self) -> None:
        """Represent a configured external local disk relative to the project.

        Returns
        -------
        None
            No return value.
        """
        project = self._base / "project"
        project.mkdir()
        config = {
            "default": "local",
            "disks": {"local": {"driver": "local", "path": str(self._root)}},
        }
        manager = StorageManager(
            SimpleNamespace(basePath=project, config=lambda _section: config),
        )
        file = manager.disk().file("logs/app.log")

        self.assertEqual(file.absolutePath(), str(self._root / "logs/app.log"))
        self.assertEqual(file.relativePath(), "../storage/logs/app.log")

    async def testRelocatedAndListedFilesRetainApplicationPaths(self) -> None:
        """Keep physical path resolution on every derived file reference.

        Returns
        -------
        None
            No return value.
        """
        config = {
            "default": "local",
            "disks": {"local": {"driver": "local", "path": "storage"}},
        }
        manager = StorageManager(
            SimpleNamespace(basePath=self._base, config=lambda _section: config),
        )
        disk = manager.disk()
        original = await disk.put("logs/app.log", b"entry")
        copied = await original.copyTo("logs/copy.log")
        moved = await copied.moveTo("logs/moved.log")
        renamed = await moved.rename("renamed.log")
        references = [
            (original, "logs/app.log"),
            (copied, "logs/copy.log"),
            (moved, "logs/moved.log"),
            (renamed, "logs/renamed.log"),
        ]
        directory = (await disk.directory().directories())[0]
        listed = await directory.files()
        recursive = await disk.directory().allFiles()
        self.assertEqual(
            [file.path() for file in listed],
            ["logs/app.log", "logs/renamed.log"],
        )
        self.assertEqual(
            [file.path() for file in recursive],
            ["logs/app.log", "logs/renamed.log"],
        )
        references.extend((file, file.path()) for file in [*listed, *recursive])

        for file, path in references:
            with self.subTest(path=path):
                self.assertEqual(file.path(), path)
                self.assertEqual(file.absolutePath(), str(self._root / path))
                self.assertEqual(file.relativePath(), f"storage/{path}")

    def testLocalDriverPathMethodsApplyStoragePathValidation(self) -> None:
        """Protect direct driver calls from traversal and empty file targets.

        Returns
        -------
        None
            No return value.
        """
        driver = LocalStorageDriver(self._root, base_path=self._base)
        for method in (driver.absolutePath, driver.relativePath):
            for path in ("../escape.log", "", "logs/app.log:stream"):
                with (
                    self.subTest(method=method.__name__, path=path),
                    self.assertRaises(StoragePathException),
                ):
                    method(path)

    def testPathsRejectSymbolicLinksEscapingTheDiskRoot(self) -> None:
        """Apply the existing local boundary guard to both path accessors.

        Returns
        -------
        None
            No return value.
        """
        driver = LocalStorageDriver(self._root, base_path=self._base)
        outside = self._base / "outside"
        outside.mkdir()
        try:
            (self._root / "linked").symlink_to(outside, target_is_directory=True)
        except OSError, NotImplementedError:
            self.skipTest("Creating symbolic links is unavailable on this system.")

        file = File(driver, "linked/app.log")
        for method in (file.absolutePath, file.relativePath):
            with (
                self.subTest(method=method.__name__),
                self.assertRaises(StoragePathException),
            ):
                method()

    def testRelativePathsRejectDifferentWindowsDrives(self) -> None:
        """Report paths without a shared drive through the storage exception.

        Returns
        -------
        None
            No return value.
        """
        if os.name != "nt":
            self.skipTest("Drive-relative paths are specific to Windows.")
        other_drive = "Y:" if self._root.drive.upper() == "Z:" else "Z:"
        driver = LocalStorageDriver(
            self._root,
            base_path=Path(f"{other_drive}/orionis"),
        )
        file = File(driver, "logs/app.log")

        self.assertEqual(file.absolutePath(), str(self._root / "logs/app.log"))
        with self.assertRaises(StoragePathException):
            file.relativePath()


class TestNonLocalFilePaths(TestCase):
    """Reject operating-system paths for storage without a local filesystem."""

    def testMemoryAndCloudPathsAreUnsupportedWithoutLoadingAnSdk(self) -> None:
        """Keep unsupported path access independent of optional SDK imports.

        Returns
        -------
        None
            No return value.
        """
        importer = Mock(side_effect=AssertionError("An SDK must not be imported."))
        with patch.object(
            driver_functions,
            "importlib",
            SimpleNamespace(import_module=importer),
        ):
            drivers = (
                MemoryStorageDriver(),
                S3StorageDriver(S3(bucket="media")),
                AzureStorageDriver(Azure(container="media")),
                GoogleStorageDriver(GCS(bucket="media")),
            )
            for driver in drivers:
                file = File(driver, "logs/app.log")
                self.assertEqual(file.path(), "logs/app.log")
                for method in (file.absolutePath, file.relativePath):
                    with (
                        self.subTest(
                            driver=type(driver).__name__,
                            method=method.__name__,
                        ),
                        self.assertRaises(UnsupportedStorageOperationException),
                    ):
                        method()
        importer.assert_not_called()
