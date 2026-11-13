# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from __future__ import annotations
import dataclasses
from types import SimpleNamespace
from unittest.mock import Mock, patch
from orionis.storage.drivers import functions as driver_functions
from orionis.foundation.config.filesystems.entitites.aws import S3
from orionis.storage.drivers.s3 import S3StorageDriver
from orionis.storage.exceptions import (
    MissingStorageDependencyException,
    StoragePathException,
    UnsupportedStorageOperationException,
)
from orionis.test import TestCase

# Options the driver actually reads from the disk configuration.
_CONSUMED_OPTIONS: frozenset[str] = frozenset(
    {
        "driver",
        "key",
        "secret",
        "region",
        "bucket",
        "url",
        "endpoint",
        "use_path_style_endpoint",
    },
)


class TestS3StorageDriver(TestCase):
    def testEntityDeclaresOnlyConsumedOptions(self) -> None:
        """Declare exactly the options the S3 driver consumes.

        Validates that the configuration entity never grows fields
        that no driver ever reads.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(
            {field.name for field in dataclasses.fields(S3)},
            set(_CONSUMED_OPTIONS),
        )

    async def testUrlUsesVirtualHostAddress(self) -> None:
        """Compose the canonical virtual-host URL for the bucket.

        Validates URL building and quoting without any SDK.

        Returns
        -------
        None
            No return value.
        """
        driver = S3StorageDriver(S3(bucket="media", region="us-east-1"))
        self.assertEqual(
            await driver.url("img/a b.png"),
            "https://media.s3.us-east-1.amazonaws.com/img/a%20b.png",
        )

    async def testUrlPrefersConfiguredBaseUrl(self) -> None:
        """Prefer the configured base URL over computed addresses.

        Validates the url override option of the disk.

        Returns
        -------
        None
            No return value.
        """
        driver = S3StorageDriver(
            S3(bucket="media", url="https://cdn.example.com/"),
        )
        self.assertEqual(
            await driver.url("logo.svg"),
            "https://cdn.example.com/logo.svg",
        )

    async def testUrlUsesCustomEndpointWhenConfigured(self) -> None:
        """Compose path-style URLs against custom endpoints.

        Validates URL building for S3-compatible services.

        Returns
        -------
        None
            No return value.
        """
        driver = S3StorageDriver(
            S3(bucket="media", endpoint="http://localhost:9000"),
        )
        self.assertEqual(
            await driver.url("f.bin"),
            "http://localhost:9000/media/f.bin",
        )

    async def testPathTraversalRejectedBeforeSdkBootstrap(self) -> None:
        """Reject invalid paths before touching the SDK.

        Validates that path safety never depends on boto3.

        Returns
        -------
        None
            No return value.
        """
        driver = S3StorageDriver(S3(bucket="media"))
        with self.assertRaises(StoragePathException):
            await driver.read("../escape")

    def testOpenRejectsTextModesWithoutSdk(self) -> None:
        """Reject text stream modes before touching the SDK.

        Validates the shared mode whitelist in the S3 driver.

        Returns
        -------
        None
            No return value.
        """
        driver = S3StorageDriver(S3(bucket="media"))
        with self.assertRaises(UnsupportedStorageOperationException):
            driver.open("f.txt", "w")

    async def testOperationsRequireOptionalDependency(self) -> None:
        """Report controlled SDK absence even when the optional SDK is installed."""
        missing = ModuleNotFoundError("Controlled optional SDK absence.")
        importer = Mock(side_effect=missing)
        driver = S3StorageDriver(S3(bucket="media"))
        with (
            patch.object(
                driver_functions,
                "importlib",
                SimpleNamespace(import_module=importer),
            ),
            self.assertRaises(MissingStorageDependencyException) as caught,
        ):
            await driver.exists("f.txt")
        importer.assert_called_once_with("boto3")
        self.assertIs(caught.exception.__cause__, missing)
        self.assertIn("orionis[s3]", str(caught.exception))
