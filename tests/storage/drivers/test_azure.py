from __future__ import annotations
import importlib.util
from orionis.foundation.config.filesystems.entitites.azure import Azure
from orionis.storage.drivers.azure import AzureStorageDriver
from orionis.storage.exceptions import (
    MissingStorageDependencyException,
    UnsupportedStorageOperationException,
)
from orionis.test import TestCase

class TestAzureStorageDriver(TestCase):

    async def testUrlComposedFromAccountAndContainer(self) -> None:
        """
        Compose the canonical Azure Blob URL for the container.

        Validates URL building and quoting without any SDK.
        """
        driver = AzureStorageDriver(
            Azure(account_name="acct", container="media"),
        )
        self.assertEqual(
            await driver.url("img/a b.png"),
            "https://acct.blob.core.windows.net/media/img/a%20b.png",
        )

    async def testCredentialsParsedFromConnectionString(self) -> None:
        """
        Derive the account name and key from the connection string.

        Validates the pure parsing performed at construction time.
        """
        connection = (
            "DefaultEndpointsProtocol=https;AccountName=demo;"
            "AccountKey=c2VjcmV0;EndpointSuffix=core.windows.net"
        )
        driver = AzureStorageDriver(
            Azure(connection_string=connection, container="media"),
        )
        self.assertEqual(
            await driver.url("f.txt"),
            "https://demo.blob.core.windows.net/media/f.txt",
        )

    async def testSetVisibilityIsUnsupported(self) -> None:
        """
        Reject per-blob visibility changes.

        Validates the documented Azure limitation.
        """
        driver = AzureStorageDriver(Azure(container="media"))
        with self.assertRaises(UnsupportedStorageOperationException):
            await driver.setVisibility("f.txt", "public")

    async def testTemporaryUrlRequiresAccountKey(self) -> None:
        """
        Reject SAS generation without an account key.

        Validates the failure contract of temporaryUrl().
        """
        driver = AzureStorageDriver(
            Azure(account_name="acct", container="media"),
        )
        with self.assertRaises(UnsupportedStorageOperationException):
            await driver.temporaryUrl("f.txt", 60)

    async def testOperationsRequireOptionalDependency(self) -> None:
        """
        Surface the missing Azure SDK with install instructions.

        Only asserted when azure-storage-blob is absent from the
        environment, so the test remains valid anywhere.
        """
        if importlib.util.find_spec("azure") is not None:
            return
        driver = AzureStorageDriver(Azure(container="media"))
        with self.assertRaises(MissingStorageDependencyException):
            await driver.exists("f.txt")
