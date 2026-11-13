# ruff: noqa: PT009, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Observe Azure policy fallbacks using in-memory SDK collaborators."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from orionis.failure.runtime import operation
from orionis.foundation.config.filesystems.entitites.azure import Azure
from orionis.storage.drivers.azure import AzureStorageDriver
from orionis.test import TestCase
from tests.support.failure_runtime import activate_runtime


class TestAzureFailureObservation(TestCase):
    """Retain private visibility while notifying original service errors."""

    async def testVisibilityFallbackReportsOriginalPolicyError(self) -> None:
        """Verify visibility fallback reports original policy error."""
        app, runtime, handler = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)
        error = OSError("policy service")
        driver = AzureStorageDriver(Azure(account_name="test", container="media"))
        driver._http_error = OSError
        container = SimpleNamespace(
            get_container_access_policy=MagicMock(side_effect=error),
        )
        with (
            operation(app),
            patch.object(AzureStorageDriver, "_AzureStorageDriver__propsSync"),
            patch.object(
                AzureStorageDriver,
                "_AzureStorageDriver__containerClient",
                return_value=container,
            ),
        ):
            result = await driver.visibility("asset.txt")
            await runtime.drain()
        self.assertEqual(result, "private")
        self.assertEqual(handler.reports, [error])

    async def testInfoFallbackReportsWithoutLosingMetadata(self) -> None:
        """Verify info fallback reports without losing metadata."""
        app, runtime, handler = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)
        error = OSError("policy service")
        driver = AzureStorageDriver(Azure(account_name="test", container="media"))
        driver._http_error = OSError
        props = SimpleNamespace(
            content_settings=SimpleNamespace(
                content_md5=None,
                content_type="text/plain",
            ),
            size=12,
            last_modified=datetime(2024, 1, 1, tzinfo=UTC),
            creation_time=None,
            etag="etag",
        )
        container = SimpleNamespace(
            get_container_access_policy=MagicMock(side_effect=error),
        )
        with (
            operation(app),
            patch.object(
                AzureStorageDriver,
                "_AzureStorageDriver__propsSync",
                return_value=props,
            ),
            patch.object(
                AzureStorageDriver,
                "_AzureStorageDriver__containerClient",
                return_value=container,
            ),
        ):
            result = await driver.info("asset.txt")
            await runtime.drain()
        self.assertEqual(result.visibility, "private")
        self.assertEqual(result.size, 12)
        self.assertEqual(handler.reports, [error])
