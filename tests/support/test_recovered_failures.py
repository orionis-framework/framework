# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify recovered storage, cache, session and mail errors remain observable."""

import asyncio
import os
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from orionis.cache.serializer import Serializer
from orionis.cache.locks.coalescing import RedisResolverLease
from orionis.cache.locks.lock import CacheLock
from orionis.cache.stores.database import DatabaseCacheBackend
from orionis.database.exceptions import QueryException
from orionis.failure.runtime import operation
from orionis.foundation.config.filesystems.entitites.aws import S3
from orionis.mail.composer import MailComposer
from orionis.mail.entities.attachment import Attachment
from orionis.mail.transports.file import FileTransport
from orionis.session.stores.database import DatabaseSessionStore
from orionis.session.stores.file import FileSessionStore
from orionis.storage.drivers.gcs import GoogleStorageDriver
from orionis.storage.drivers.s3 import S3StorageDriver
from orionis.test import TestCase
from tests.support.failure_runtime import activate_runtime


class TestRecoveredServiceFailures(TestCase):
    """Keep existing fallbacks and cancellation while notifying the app hook."""

    async def testS3AclFallbackRetainsMetadata(self) -> None:
        """Observe denied ACL access without losing object metadata."""
        app, runtime, handler = activate_runtime()
        driver = S3StorageDriver(S3(bucket="media", region="us-east-1"))
        error = OSError("acl denied")
        driver._client_error = OSError
        with (
            operation(app),
            patch.object(
                S3StorageDriver,
                "_S3StorageDriver__headSync",
                return_value={"ContentLength": 12},
            ),
            patch.object(
                S3StorageDriver,
                "_S3StorageDriver__visibilitySync",
                side_effect=error,
            ),
        ):
            info = await driver.info("asset.txt")
            await runtime.drain()
        self.assertEqual(info.visibility, "private")
        self.assertEqual(info.size, 12)
        self.assertEqual(handler.reports, [error])

    async def testGoogleAclFallbackReportsOriginalError(self) -> None:
        """Observe failed ACL lookup while retaining private visibility."""
        app, runtime, handler = activate_runtime()
        driver = object.__new__(GoogleStorageDriver)
        driver._cloud_error = OSError
        error = OSError("acl denied")
        acl = MagicMock()
        acl.__iter__.side_effect = error
        with operation(app):
            result = await asyncio.to_thread(
                driver._GoogleStorageDriver__isPublicSync,
                SimpleNamespace(acl=acl),
            )
            await runtime.drain()
        self.assertFalse(result)
        self.assertEqual(handler.reports, [error])

    async def testSerializerReadDistinguishesAbsenceAndAccessError(self) -> None:
        """Preserve cache misses while observing denied file reads."""
        app, runtime, handler = activate_runtime()
        error = PermissionError("denied")
        for failure in (FileNotFoundError(), error):
            with operation(app), patch.object(Path, "read_bytes", side_effect=failure):
                self.assertIsNone(Serializer.loadFromFile(Path("unused")))
                await runtime.drain()
        self.assertEqual(handler.reports, [error])

    async def testCorruptDatabaseCacheAndSessionsRemainMisses(self) -> None:
        """Observe malformed persisted payloads without changing fallback values."""
        app, runtime, handler = activate_runtime()
        cache = object.__new__(DatabaseCacheBackend)
        file_session = object.__new__(FileSessionStore)
        database_session = object.__new__(DatabaseSessionStore)
        with operation(app):
            self.assertIsNone(cache._DatabaseCacheBackend__decode(b"invalid"))
            self.assertIsNone(file_session._deserialize(b"invalid"))
            self.assertIsNone(
                database_session._DatabaseSessionStore__decode(b"invalid"),
            )
            await runtime.drain()
        self.assertEqual(len(handler.failures), 3)
        self.assertEqual(
            [context.flow for _, context in handler.failures],
            ["cache", "session", "session"],
        )

    async def testMailCleanupFailureDoesNotReplaceReadError(self) -> None:
        """Observe suppressed cleanup while propagating the original read failure."""
        app, _, handler = activate_runtime()
        original, cleanup = OSError("read"), OSError("close")
        stream = SimpleNamespace(
            __aenter__=AsyncMock(),
            read=AsyncMock(side_effect=original),
            close=AsyncMock(side_effect=cleanup),
        )
        storage = MagicMock()
        storage.disk.return_value.file.return_value.open.return_value = stream
        composer = MailComposer(MagicMock(), storage)
        with operation(app), self.assertRaises(OSError) as caught:
            await composer._readAttachment(
                Attachment(path="asset.txt", mime_type="text/plain"),
            )
        self.assertIs(caught.exception, original)
        self.assertEqual(handler.reports, [cleanup])

    async def testCancelledMailAttachmentObservesLateReadFailure(self) -> None:
        """Drain owned attachment reads and keep the caller cancellation."""
        app, _, handler = activate_runtime()
        started, release = asyncio.Event(), asyncio.Event()
        error = OSError("late storage failure")

        async def read(*_args: object) -> None:
            """Raise the original read error after explicit release."""
            started.set()
            await release.wait()
            raise error

        composer = MailComposer(MagicMock(), MagicMock())
        with operation(app), patch.object(MailComposer, "_readAttachment", read):
            task = asyncio.create_task(
                composer._resolveAttachment(
                    Attachment(path="asset.txt"),
                ),
            )
            await started.wait()
            task.cancel()
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(handler.reports, [error])

    async def testSessionRetryIsObservableWithoutDefaultReport(self) -> None:
        """Notify expected sharing retries without reporting an operational fault."""
        app, runtime, handler = activate_runtime()
        store = object.__new__(FileSessionStore)
        store._rename_lock = threading.Lock()
        error = PermissionError("sharing violation")
        with (
            operation(app),
            patch.object(Path, "replace", side_effect=[error, None]),
            patch("orionis.session.stores.file.time.sleep"),
        ):
            store._replace(Path("unused.tmp"), Path("unused.json"))
            await runtime.drain()
        self.assertEqual(len(handler.failures), 1)
        self.assertTrue(handler.failures[0][1].expected)
        self.assertEqual(handler.reports, [])

    async def testSessionWriteCleanupPreservesOriginalFailure(self) -> None:
        """Record cleanup errors while keeping the failed publication exception."""
        app, runtime, handler = activate_runtime()
        store = object.__new__(FileSessionStore)
        original, cleanup = OSError("write"), PermissionError("cleanup")
        with (
            operation(app),
            patch.object(Path, "write_bytes", side_effect=original),
            patch.object(Path, "unlink", side_effect=cleanup),
        ):
            with self.assertRaises(OSError) as caught:
                store._writeFile(Path("unused.json"), b"data")
            await runtime.drain()
        self.assertIs(caught.exception, original)
        self.assertEqual(handler.reports, [cleanup])

    async def testFileMailPublicationSurvivesCleanupFailure(self) -> None:
        """Preserve the published message while reporting temporary-file cleanup."""
        app, runtime, handler = activate_runtime()
        error = PermissionError("cleanup")
        with TemporaryDirectory() as directory:
            transport = FileTransport(Path(directory))
            with operation(app), patch.object(Path, "unlink", side_effect=error):
                published = await asyncio.to_thread(transport._store, b"message")
                await runtime.drain()
            self.assertEqual(published.read_bytes(), b"message")
        self.assertEqual(handler.reports, [error])

    async def testSessionSweepContinuesAfterIndependentCleanupFailures(self) -> None:
        """Observe each failed cleanup while continuing the session sweep."""
        app, runtime, handler = activate_runtime()
        temporary_error = PermissionError("temporary cleanup")
        session_error = PermissionError("session cleanup")
        with TemporaryDirectory() as directory:
            root = Path(directory)
            temporary = FileSessionStore._tempPath(root / "session.json")
            temporary.write_bytes(b"partial")
            os.utime(temporary, (0, 0))
            (root / "session.json").write_bytes(b"{}")
            store = FileSessionStore(root)
            with (
                operation(app),
                patch(
                    "orionis.session.stores.file.os.unlink",
                    side_effect=temporary_error,
                ),
                patch.object(
                    FileSessionStore,
                    "_readRecord",
                    side_effect=session_error,
                ),
            ):
                await store.gc()
                await runtime.drain()
        self.assertCountEqual(handler.reports, [temporary_error, session_error])

    async def testCacheLeaseCleanupPreservesAcquisitionFailure(self) -> None:
        """Observe a failed lease cleanup while retaining the acquisition error."""
        app, _, handler = activate_runtime()
        original, cleanup = OSError("acquire"), OSError("release")
        lease = RedisResolverLease(MagicMock(), "key", 10, 1)
        with (
            operation(app),
            patch.object(
                RedisResolverLease,
                "_acquire",
                AsyncMock(side_effect=original),
            ),
            patch.object(
                RedisResolverLease,
                "_release",
                AsyncMock(side_effect=cleanup),
            ),
            self.assertRaises(OSError) as caught,
        ):
            await lease.__aenter__()
        self.assertIs(caught.exception, original)
        self.assertEqual(handler.reports, [cleanup])

    async def testRecoveredDatabaseConflictCallsHookWithoutDefaultReport(self) -> None:
        """Keep a successful update fallback observable as an expected recovery."""
        app, _, handler = activate_runtime()
        error = QueryException("concurrent insert")
        connection = MagicMock()
        connection.insert = AsyncMock(side_effect=error)
        connection.update = AsyncMock(return_value=1)
        backend = DatabaseCacheBackend(connection, "cache", "locks")
        with operation(app):
            await backend._DatabaseCacheBackend__insertOrRetryUpdate("key", "1", None)
        self.assertEqual(len(handler.failures), 1)
        self.assertIs(handler.failures[0][0], error)
        self.assertTrue(handler.failures[0][1].expected)
        self.assertEqual(handler.reports, [])

    async def testCacheLeaseCleanupPreservesBodyFailure(self) -> None:
        """Observe release failure without replacing the protected operation.

        Returns
        -------
        None
            Keep the original error and report its failed cleanup exactly once.
        """
        app, _, handler = activate_runtime()
        original, cleanup = OSError("body"), OSError("release")
        lease = RedisResolverLease(MagicMock(), "key", 10, 1)
        with (
            operation(app),
            patch.object(RedisResolverLease, "_acquire", AsyncMock()),
            patch.object(
                RedisResolverLease,
                "_release",
                AsyncMock(side_effect=cleanup),
            ) as release,
            self.assertRaises(OSError) as caught,
        ):
            async with lease:
                raise original
        self.assertIs(caught.exception, original)
        self.assertEqual(handler.reports, [original, cleanup])
        self.assertIs(cleanup.__context__, original)
        self.assertEqual(handler.failures[1][1].phase, "cleanup")
        self.assertEqual(
            handler.failures[1][1].parent_event_id,
            handler.failures[0][1].event_id,
        )
        release.assert_awaited_once()

    async def testDatabaseCacheLockCleanupPreservesBodyFailure(self) -> None:
        """Retain the resolver failure if its database lease cannot be released.

        Returns
        -------
        None
            Preserve the protected operation and observe its cleanup once.
        """
        app, runtime, handler = activate_runtime()
        original, cleanup = OSError("resolver"), OSError("release")
        backend = DatabaseCacheBackend(MagicMock(), "cache", "locks")
        with (
            operation(app),
            patch.object(
                DatabaseCacheBackend,
                "acquireLock",
                AsyncMock(return_value=True),
            ),
            patch.object(
                DatabaseCacheBackend,
                "releaseLock",
                AsyncMock(side_effect=cleanup),
            ) as release,
            self.assertRaises(OSError) as caught,
        ):
            async with CacheLock(backend, "key"):
                raise original
        await runtime.drain()
        self.assertIs(caught.exception, original)
        self.assertEqual(handler.reports, [original, cleanup])
        self.assertEqual(
            handler.failures[1][1].parent_event_id,
            handler.failures[0][1].event_id,
        )
        release.assert_awaited_once()
