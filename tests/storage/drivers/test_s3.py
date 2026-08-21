from __future__ import annotations
import dataclasses
import importlib.util
from orionis.foundation.config.filesystems.entitites.aws import S3
from orionis.storage.drivers.s3 import S3StorageDriver
from orionis.storage.exceptions import (
    MissingStorageDependencyException,
    StoragePathException,
    UnsupportedStorageOperationException,
)
from orionis.test import TestCase

# Options the driver actually reads from the disk configuration.
_CONSUMED_OPTIONS: frozenset[str] = frozenset({
    "driver",
    "key",
    "secret",
    "region",
    "bucket",
    "url",
    "endpoint",
    "use_path_style_endpoint",
})

class TestS3StorageDriver(TestCase):

    def testEntityDeclaresOnlyConsumedOptions(self) -> None:
        """
        Declare exactly the options the S3 driver consumes.

        Validates that the configuration entity never grows fields
        that no driver ever reads.
        """
        self.assertEqual(
            {field.name for field in dataclasses.fields(S3)},
            set(_CONSUMED_OPTIONS),
        )

    async def testUrlUsesVirtualHostAddress(self) -> None:
        """
        Compose the canonical virtual-host URL for the bucket.

        Validates URL building and quoting without any SDK.
        """
        driver = S3StorageDriver(S3(bucket="media", region="us-east-1"))
        self.assertEqual(
            await driver.url("img/a b.png"),
            "https://media.s3.us-east-1.amazonaws.com/img/a%20b.png",
        )

    async def testUrlPrefersConfiguredBaseUrl(self) -> None:
        """
        Prefer the configured base URL over computed addresses.

        Validates the url override option of the disk.
        """
        driver = S3StorageDriver(
            S3(bucket="media", url="https://cdn.example.com/"),
        )
        self.assertEqual(
            await driver.url("logo.svg"),
            "https://cdn.example.com/logo.svg",
        )

    async def testUrlUsesCustomEndpointWhenConfigured(self) -> None:
        """
        Compose path-style URLs against custom endpoints.

        Validates URL building for S3-compatible services.
        """
        driver = S3StorageDriver(
            S3(bucket="media", endpoint="http://localhost:9000"),
        )
        self.assertEqual(
            await driver.url("f.bin"),
            "http://localhost:9000/media/f.bin",
        )

    async def testPathTraversalRejectedBeforeSdkBootstrap(self) -> None:
        """
        Reject invalid paths before touching the SDK.

        Validates that path safety never depends on boto3.
        """
        driver = S3StorageDriver(S3(bucket="media"))
        with self.assertRaises(StoragePathException):
            await driver.read("../escape")

    def testOpenRejectsTextModesWithoutSdk(self) -> None:
        """
        Reject text stream modes before touching the SDK.

        Validates the shared mode whitelist in the S3 driver.
        """
        driver = S3StorageDriver(S3(bucket="media"))
        with self.assertRaises(UnsupportedStorageOperationException):
            driver.open("f.txt", "w")

    async def testOperationsRequireOptionalDependency(self) -> None:
        """
        Surface the missing boto3 package with install instructions.

        Only asserted when boto3 is absent from the environment, so
        the test remains valid on machines that have it installed.
        """
        if importlib.util.find_spec("boto3") is not None:
            return
        driver = S3StorageDriver(S3(bucket="media"))
        with self.assertRaises(MissingStorageDependencyException):
            await driver.exists("f.txt")
