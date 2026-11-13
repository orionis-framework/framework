# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from __future__ import annotations
from types import SimpleNamespace
from unittest.mock import Mock, patch
from orionis.storage.drivers import functions as driver_functions
from orionis.foundation.config.filesystems.entitites.azure import Azure
from orionis.storage.drivers.azure import AzureStorageDriver
from orionis.storage.exceptions import (
    MissingStorageDependencyException,
    UnsupportedStorageOperationException,
)
from orionis.test import TestCase


class TestAzureStorageDriver(TestCase):
    async def testUrlComposedFromAccountAndContainer(self) -> None:
        """Compose the canonical Azure Blob URL for the container.

        Validates URL building and quoting without any SDK.

        Returns
        -------
        None
            No return value.
        """
        driver = AzureStorageDriver(
            Azure(account_name="acct", container="media"),
        )
        self.assertEqual(
            await driver.url("img/a b.png"),
            "https://acct.blob.core.windows.net/media/img/a%20b.png",
        )

    async def testCredentialsParsedFromConnectionString(self) -> None:
        """Derive the account name and key from the connection string.

        Validates the pure parsing performed at construction time.

        Returns
        -------
        None
            No return value.
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
        """Reject per-blob visibility changes.

        Validates the documented Azure limitation.

        Returns
        -------
        None
            No return value.
        """
        driver = AzureStorageDriver(Azure(container="media"))
        with self.assertRaises(UnsupportedStorageOperationException):
            await driver.setVisibility("f.txt", "public")

    async def testTemporaryUrlRequiresAccountKey(self) -> None:
        """Reject SAS generation without an account key.

        Validates the failure contract of temporaryUrl().

        Returns
        -------
        None
            No return value.
        """
        driver = AzureStorageDriver(
            Azure(account_name="acct", container="media"),
        )
        with self.assertRaises(UnsupportedStorageOperationException):
            await driver.temporaryUrl("f.txt", 60)

    async def testOperationsRequireOptionalDependency(self) -> None:
        """Report controlled SDK absence even when the optional SDK is installed."""
        missing = ModuleNotFoundError("Controlled optional SDK absence.")
        importer = Mock(side_effect=missing)
        driver = AzureStorageDriver(Azure(container="media"))
        with (
            patch.object(
                driver_functions,
                "importlib",
                SimpleNamespace(import_module=importer),
            ),
            self.assertRaises(MissingStorageDependencyException) as caught,
        ):
            await driver.exists("f.txt")
        importer.assert_called_once_with("azure.storage.blob")
        self.assertIs(caught.exception.__cause__, missing)
        self.assertIn("orionis[azure]", str(caught.exception))
