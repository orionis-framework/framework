"""Observe recovered file-cache failures without changing cache results."""

import asyncio
from pathlib import Path
from unittest.mock import patch
from orionis.cache.stores.file import FileCacheBackend
from orionis.failure.runtime import operation
from orionis.test import TestCase
from tests.support.failure_runtime import activate_runtime


class TestCacheFailureObservation(TestCase):
    """Distinguish expected cache absence from operational read failure."""

    async def testPermissionFailureIsObservedFromWorkerThread(self) -> None:
        """Verify permission failure is observed from worker thread."""
        app, runtime, handler = activate_runtime()
        error = PermissionError("denied")
        with operation(app), patch.object(Path, "read_bytes", side_effect=error):
            result = await asyncio.to_thread(
                FileCacheBackend._FileCacheBackend__readEntryUnlocked,
                Path("unused-cache-probe"),
            )
            await runtime.drain()
        self.assertIsNone(result)
        self.assertEqual(handler.reports, [error])
        self.assertEqual(handler.failures[0][1].flow, "cache")

    async def testMissingEntryRemainsAnExpectedCacheMiss(self) -> None:
        """Verify missing entry remains an expected cache miss."""
        app, runtime, handler = activate_runtime()
        with (
            operation(app),
            patch.object(Path, "read_bytes", side_effect=FileNotFoundError),
        ):
            result = await asyncio.to_thread(
                FileCacheBackend._FileCacheBackend__readEntryUnlocked,
                Path("unused-cache-probe"),
            )
            await runtime.drain()
        self.assertIsNone(result)
        self.assertEqual(handler.failures, [])

    async def testCorruptEntryIsObservedAndStillReturnsCacheMiss(self) -> None:
        """Verify corrupt entry is observed and still returns cache miss."""
        app, runtime, handler = activate_runtime()
        with (
            operation(app),
            patch.object(Path, "read_bytes", return_value=b"invalid json"),
        ):
            result = await asyncio.to_thread(
                FileCacheBackend._FileCacheBackend__readEntryUnlocked,
                Path("unused-cache-probe"),
            )
            await runtime.drain()
        self.assertIsNone(result)
        self.assertEqual(len(handler.failures), 1)
