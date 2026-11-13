# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from __future__ import annotations
from types import SimpleNamespace
from unittest.mock import Mock, patch
from orionis.storage.drivers import functions as driver_functions
from orionis.foundation.config.filesystems.entitites.gcs import GCS
from orionis.storage.drivers.gcs import GoogleStorageDriver
from orionis.storage.exceptions import (
    MissingStorageDependencyException,
    StoragePathException,
    UnsupportedStorageOperationException,
)
from orionis.test import TestCase


class TestGoogleStorageDriver(TestCase):
    async def testUrlUsesCanonicalGoogleAddress(self) -> None:
        """Compose the canonical storage.googleapis.com URL.

        Validates URL building and quoting without any SDK.

        Returns
        -------
        None
            No return value.
        """
        driver = GoogleStorageDriver(GCS(bucket="media"))
        self.assertEqual(
            await driver.url("img/a b.png"),
            "https://storage.googleapis.com/media/img/a%20b.png",
        )

    async def testUrlPrefersConfiguredBaseUrl(self) -> None:
        """Prefer the configured base URL over the canonical address.

        Validates the url override option of the disk.

        Returns
        -------
        None
            No return value.
        """
        driver = GoogleStorageDriver(
            GCS(bucket="media", url="https://cdn.example.com"),
        )
        self.assertEqual(
            await driver.url("logo.svg"),
            "https://cdn.example.com/logo.svg",
        )

    async def testPathTraversalRejectedBeforeSdkBootstrap(self) -> None:
        """Reject invalid paths before touching the SDK.

        Validates that path safety never depends on the Google SDK.

        Returns
        -------
        None
            No return value.
        """
        driver = GoogleStorageDriver(GCS(bucket="media"))
        with self.assertRaises(StoragePathException):
            await driver.read("..\\escape")

    async def testSetVisibilityValidatesLevelWithoutSdk(self) -> None:
        """Reject unknown visibility levels before touching the SDK.

        Validates the pure level validation of setVisibility().

        Returns
        -------
        None
            No return value.
        """
        driver = GoogleStorageDriver(GCS(bucket="media"))
        with self.assertRaises(UnsupportedStorageOperationException):
            await driver.setVisibility("f.txt", "secret")

    async def testOperationsRequireOptionalDependency(self) -> None:
        """Report controlled SDK absence even when the optional SDK is installed."""
        missing = ModuleNotFoundError("Controlled optional SDK absence.")
        importer = Mock(side_effect=missing)
        driver = GoogleStorageDriver(GCS(bucket="media"))
        with (
            patch.object(
                driver_functions,
                "importlib",
                SimpleNamespace(import_module=importer),
            ),
            self.assertRaises(MissingStorageDependencyException) as caught,
        ):
            await driver.exists("f.txt")
        importer.assert_called_once_with("google.cloud.storage")
        self.assertIs(caught.exception.__cause__, missing)
        self.assertIn("orionis[gcs]", str(caught.exception))
