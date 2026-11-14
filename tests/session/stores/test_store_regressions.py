# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Preserve session storage ownership, expiry and failure contracts."""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
import inspect
import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from types import SimpleNamespace
from typing import TYPE_CHECKING, get_type_hints
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from orionis.cache.repository import CacheRepository
from orionis.cache.stores.file import FileCacheBackend
from orionis.database.connection import Connection
from orionis.database.exceptions import QueryException
from orionis.session.contracts.store import ISessionStore
from orionis.session.entities.record import SessionRecord
from orionis.session.stores.cache import CacheSessionStore
from orionis.session.stores.database import DatabaseSessionStore
from orionis.session.stores.file import FileSessionStore
from orionis.session.stores.memory import MemorySessionStore
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable
    from datetime import tzinfo
    from filelock import BaseFileLock


def _hold_worker(
    original: Callable[..., object],
    started: asyncio.Event,
    released: Event,
    finished: Event,
) -> Callable[..., object]:
    """Hold a real worker until its owning test releases it.

    Parameters
    ----------
    original : collections.abc.Callable[..., object]
        Operation performed after the release signal.
    started : asyncio.Event
        Loop-side notice that the worker has started.
    released : threading.Event
        Permission to finish the active operation.
    finished : threading.Event
        Notice that the operation no longer uses its resources.

    Returns
    -------
    collections.abc.Callable[..., object]
        Synchronous worker preserving the original result or failure.
    """
    loop = asyncio.get_running_loop()

    def blocked(*args: object) -> object:
        """Run the operation after receiving the release signal.

        Parameters
        ----------
        *args : object
            Original worker arguments.

        Returns
        -------
        object
            Original worker result.
        """
        loop.call_soon_threadsafe(started.set)
        try:
            if not released.wait(5):
                message = "The test did not release its session worker."
                raise TimeoutError(message)
            return original(*args)
        finally:
            finished.set()

    return blocked


def _record(identifier: str = "owned") -> SessionRecord:
    """Build a live record for an isolated store.

    Parameters
    ----------
    identifier : str
        Identifier belonging to the controlled test store.

    Returns
    -------
    SessionRecord
        Record with a fresh mutable payload and UTC deadline.
    """
    return SessionRecord(
        id=identifier,
        data={"value": 1},
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )


class TestStoreRegressions(TestCase):
    """Exercise real files and SQLite while controlling failure boundaries."""

    def testPublicStoreAnnotationsResolveAtRuntime(self) -> None:
        """Resolve every public store contract and implementation annotation.

        Returns
        -------
        None
            No return value.
        """
        for target in (
            ISessionStore,
            MemorySessionStore,
            CacheSessionStore,
            DatabaseSessionStore,
            FileSessionStore,
        ):
            for name, function in vars(target).items():
                if name.startswith("_") and name != "__init__":
                    continue
                if inspect.isfunction(function):
                    with self.subTest(store=target.__name__, method=name):
                        self.assertIn("return", get_type_hints(function))

    async def testCancelledFileOperationsRetainTheirActiveWorkers(self) -> None:
        """Finish active workers before exposing cancellation to their callers.

        Returns
        -------
        None
            No return value.
        """
        cases = (
            ("read", "_readRecord"),
            ("write", "_writeRecord"),
            ("update", "_updateRecord"),
            ("delete", "_deleteFile"),
            ("gc", "_gcSweep"),
            ("write_error", "_writeRecord"),
        )
        for method, helper in cases:
            with self.subTest(method=method), TemporaryDirectory() as directory:
                store = FileSessionStore(Path(directory))
                record = _record()
                await store.write(record)
                started = asyncio.Event()
                released, finished = Event(), Event()
                error = OSError("The controlled session worker failed.")
                original = (
                    Mock(side_effect=error)
                    if method == "write_error"
                    else getattr(FileSessionStore, helper)
                )
                worker = _hold_worker(original, started, released, finished)
                operation = "write" if method == "write_error" else method
                arguments = (
                    ()
                    if method == "gc"
                    else (record if operation in ("write", "update") else record.id,)
                )
                with (
                    patch.object(FileSessionStore, helper, worker),
                    patch(
                        "orionis.failure.runtime.capture",
                        new_callable=AsyncMock,
                    ) as capture,
                ):
                    pending = asyncio.create_task(getattr(store, operation)(*arguments))
                    try:
                        await asyncio.wait_for(started.wait(), timeout=5)
                        pending.cancel()
                        await asyncio.sleep(0)
                        self.assertFalse(finished.is_set())
                        self.assertFalse(pending.done())
                    finally:
                        released.set()
                        await asyncio.gather(pending, return_exceptions=True)
                        await asyncio.to_thread(finished.wait, 5)
                    self.assertTrue(pending.cancelled())
                    self.assertTrue(finished.is_set())
                    if method == "write_error":
                        capture.assert_awaited_once()
                        self.assertIs(capture.await_args.args[0], error)

    async def testFileGcPreservesNamesOutsideItsStorageFormat(self) -> None:
        """Reclaim only session staging files and valid session filenames.

        Returns
        -------
        None
            No return value.
        """
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            store = FileSessionStore(folder)
            unrelated = (
                folder / "unrelated.tmp",
                folder / "backup.invalid.json",
                folder / "owned.json.not-a-random-token.tmp",
            )
            orphan = folder / "owned.json.0123456789abcdef.tmp"
            for path in (*unrelated, orphan):
                path.write_bytes(b"controlled content")
                os.utime(path, (1, 1))
            await store.gc()
            self.assertFalse(orphan.exists())
            for path in unrelated:
                with self.subTest(name=path.name):
                    self.assertEqual(path.read_bytes(), b"controlled content")

    async def testRelativeFileDirectoryRetainsItsOriginalLocation(self) -> None:
        """Keep storage and lock paths fixed when the working directory changes.

        Returns
        -------
        None
            No return value.
        """
        original_cwd = Path.cwd()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / "first", root / "second"
            first.mkdir()
            second.mkdir()
            try:
                os.chdir(first)
                store = FileSessionStore(Path("sessions"))
                os.chdir(second)
                record = _record()
                await store.write(record)
                self.assertEqual((await store.read(record.id)).data, record.data)
                self.assertTrue((first / "sessions" / (record.id + ".json")).is_file())
                self.assertFalse((second / "sessions").exists())
            finally:
                os.chdir(original_cwd)

    async def testGcWaitsForTheWriterOwningAStaleStagingFile(self) -> None:
        """Retain active staging files even after a forward wall-clock jump.

        Returns
        -------
        None
            No return value.
        """
        loop = asyncio.get_running_loop()
        started, observed = asyncio.Event(), asyncio.Event()
        released, finished = Event(), Event()
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            store = FileSessionStore(folder)
            record = _record()
            held_replace = _hold_worker(
                FileSessionStore._replace,
                started,
                released,
                finished,
            )
            with patch.object(FileSessionStore, "_replace", held_replace):
                writer = asyncio.create_task(store.write(record))
                sweep = None
                try:
                    await asyncio.wait_for(started.wait(), timeout=5)
                    staging = await asyncio.to_thread(
                        # Match the canonical paths passed to unlink by the store.
                        lambda: next(folder.glob("*.tmp")).resolve(),
                    )
                    original_lock = FileSessionStore._lock
                    original_unlink = os.unlink

                    def observed_lock(
                        target_store: FileSessionStore,
                        path: Path,
                    ) -> BaseFileLock:
                        """Notify the loop when cleanup requests the writer's lock.

                        Parameters
                        ----------
                        target_store : FileSessionStore
                            Store performing the garbage collection.
                        path : pathlib.Path
                            Session file protected by the shared lock.

                        Returns
                        -------
                        filelock.BaseFileLock
                            Original lock still owned by the paused writer.
                        """
                        lock = original_lock(target_store, path)
                        loop.call_soon_threadsafe(observed.set)
                        return lock

                    def observed_unlink(path: str | Path) -> None:
                        """Notice an unsafe unlink only after it removed the file.

                        Parameters
                        ----------
                        path : str or pathlib.Path
                            File being removed by garbage collection.

                        Returns
                        -------
                        None
                            No return value.
                        """
                        original_unlink(path)
                        if Path(path) == staging:
                            loop.call_soon_threadsafe(observed.set)

                    shifted_clock = SimpleNamespace(
                        time=lambda: time.time() + 7200,
                        sleep=time.sleep,
                    )
                    with (
                        patch.object(FileSessionStore, "_lock", observed_lock),
                        patch("orionis.session.stores.file.os.unlink", observed_unlink),
                        patch("orionis.session.stores.file.time", shifted_clock),
                    ):
                        sweep = asyncio.create_task(store.gc())
                        try:
                            await asyncio.wait_for(observed.wait(), timeout=5)
                            self.assertTrue(staging.exists())
                            self.assertFalse(finished.is_set())
                        finally:
                            released.set()
                            results = await asyncio.gather(
                                writer,
                                sweep,
                                return_exceptions=True,
                            )
                        self.assertEqual(results, [None, None])
                finally:
                    released.set()
                    pending = (writer,) if sweep is None else (writer, sweep)
                    await asyncio.gather(*pending, return_exceptions=True)
            self.assertEqual((await store.read(record.id)).data, record.data)

    async def testDatabaseReadRejectsCorruptExpirationValues(self) -> None:
        """Treat malformed stored deadlines as misses without escaping errors.

        Returns
        -------
        None
            No return value.
        """
        connection = Connection(
            "session-regressions",
            {"driver": "sqlite", "database": ":memory:"},
        )
        self.addAsyncCleanup(connection.disconnect)
        store = DatabaseSessionStore(connection)
        for expiration in ("invalid", float("inf"), 1e20):
            with self.subTest(expiration=expiration):
                record = _record()
                await store.write(record)
                await connection.execute(
                    "UPDATE sessions SET expires_at = :expiration WHERE id = :id",
                    {"expiration": expiration, "id": record.id},
                )
                self.assertIsNone(await store.read(record.id))

    async def testRecoveryRetainsTheOriginalDatabaseWriteFailure(self) -> None:
        """Observe a failed retry while preserving the original insert error.

        Returns
        -------
        None
            No return value.
        """
        original = QueryException("The controlled session insert failed.")
        cause = OSError("The controlled storage cause.")
        original.__cause__ = cause
        secondary = QueryException("The controlled session retry failed.")

        @asynccontextmanager
        async def transaction() -> AsyncIterator[None]:
            """Yield the controlled transaction boundary.

            Yields
            ------
            None
                Control while the insertion is active.
            """
            yield

        connection = SimpleNamespace(
            supportsUniqueConstraints=lambda: True,
            createTable=AsyncMock(),
            transaction=transaction,
            update=AsyncMock(side_effect=[0, secondary]),
            insert=AsyncMock(side_effect=original),
        )
        store = DatabaseSessionStore(connection)
        with (
            patch("orionis.failure.runtime.capture", new_callable=AsyncMock) as capture,
            self.assertRaises(QueryException) as raised,
        ):
            await store.write(_record())
        self.assertIs(raised.exception, original)
        self.assertIs(raised.exception.__cause__, cause)
        capture.assert_awaited_once()
        self.assertIs(capture.await_args.args[0], secondary)

    async def testCacheUpdatesCannotRenewExpiredFractionalDeadlines(self) -> None:
        """Reject renewal after the record deadline with a real file cache.

        Returns
        -------
        None
            No return value.
        """
        clock = SimpleNamespace(now=datetime(2030, 1, 1, tzinfo=UTC))

        def wall_time() -> float:
            """Return the current controlled timestamp without binding an old date.

            Returns
            -------
            float
                Controlled current epoch seconds.
            """
            return clock.now.timestamp()

        wall_clock = SimpleNamespace(time=wall_time)

        class ClockDateTime(datetime):
            """Preserve datetime parsing while controlling the current instant."""

            __slots__ = ()

            @classmethod
            def now(cls, tz: tzinfo | None = None) -> datetime:
                """Return the controlled instant in the requested timezone.

                Parameters
                ----------
                tz : datetime.tzinfo or None
                    Timezone requested by the store.

                Returns
                -------
                datetime.datetime
                    Controlled current time.
                """
                return cls.fromtimestamp(clock.now.timestamp(), tz=tz)

        with (
            TemporaryDirectory() as directory,
            patch("orionis.cache.stores.file.time", wall_clock),
            patch("orionis.session.stores.cache.datetime", ClockDateTime),
        ):
            repository = CacheRepository(FileCacheBackend(Path(directory)))
            manager = SimpleNamespace(store=MagicMock(return_value=repository))
            store = CacheSessionStore(manager)
            record = SessionRecord(
                id="fractional",
                data={},
                expires_at=clock.now + timedelta(seconds=2.25),
            )
            await store.write(record)
            clock.now += timedelta(seconds=2.5)
            replacement = SessionRecord(
                id=record.id,
                data={"renewed": True},
                expires_at=clock.now + timedelta(hours=1),
            )
            with self.subTest(case="expired fractional deadline"):
                self.assertFalse(await store.update(replacement))

            for operation in ("write", "update"):
                with self.subTest(case="subsecond " + operation):
                    previous = SessionRecord(
                        id=operation,
                        data={"previous": True},
                        expires_at=clock.now + timedelta(hours=1),
                    )
                    await store.write(previous)
                    short = SessionRecord(
                        id=operation,
                        data={},
                        expires_at=clock.now + timedelta(seconds=0.25),
                    )
                    if operation == "write":
                        await store.write(short)
                        self.assertIsNone(await repository.get("session:" + operation))
                    else:
                        self.assertFalse(await store.update(short))
                        self.assertEqual(
                            (await store.read(operation)).data,
                            previous.data,
                        )

            with self.subTest(case="exact integer deadline"):
                exact = SessionRecord(
                    id="exact",
                    data={},
                    expires_at=clock.now + timedelta(seconds=2),
                )
                await store.write(exact)
                clock.now += timedelta(seconds=1.5)
                self.assertIsNotNone(await store.read(exact.id))
                clock.now += timedelta(seconds=0.5)
                self.assertIsNone(await store.read(exact.id))
