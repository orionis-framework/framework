from __future__ import annotations
import importlib.util
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
        """
        Compose the canonical storage.googleapis.com URL.

        Validates URL building and quoting without any SDK.
        """
        driver = GoogleStorageDriver(GCS(bucket="media"))
        self.assertEqual(
            await driver.url("img/a b.png"),
            "https://storage.googleapis.com/media/img/a%20b.png",
        )

    async def testUrlPrefersConfiguredBaseUrl(self) -> None:
        """
        Prefer the configured base URL over the canonical address.

        Validates the url override option of the disk.
        """
        driver = GoogleStorageDriver(
            GCS(bucket="media", url="https://cdn.example.com"),
        )
        self.assertEqual(
            await driver.url("logo.svg"),
            "https://cdn.example.com/logo.svg",
        )

    async def testPathTraversalRejectedBeforeSdkBootstrap(self) -> None:
        """
        Reject invalid paths before touching the SDK.

        Validates that path safety never depends on the Google SDK.
        """
        driver = GoogleStorageDriver(GCS(bucket="media"))
        with self.assertRaises(StoragePathException):
            await driver.read("..\\escape")

    async def testSetVisibilityValidatesLevelWithoutSdk(self) -> None:
        """
        Reject unknown visibility levels before touching the SDK.

        Validates the pure level validation of setVisibility().
        """
        driver = GoogleStorageDriver(GCS(bucket="media"))
        with self.assertRaises(UnsupportedStorageOperationException):
            await driver.setVisibility("f.txt", "secret")

    async def testOperationsRequireOptionalDependency(self) -> None:
        """
        Surface the missing Google SDK with install instructions.

        Only asserted when google-cloud-storage is absent from the
        environment, so the test remains valid anywhere.
        """
        if importlib.util.find_spec("google") is not None:
            return
        driver = GoogleStorageDriver(GCS(bucket="media"))
        with self.assertRaises(MissingStorageDependencyException):
            await driver.exists("f.txt")
