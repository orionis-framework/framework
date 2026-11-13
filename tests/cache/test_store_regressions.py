# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect cache publication, expiration and borrowed worker resources."""

import asyncio
from contextlib import contextmanager
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from types import SimpleNamespace
from typing import TYPE_CHECKING, get_type_hints
from unittest.mock import patch

from orionis.cache.stores.database import DatabaseCacheBackend, build
from orionis.cache.stores.file import FileCacheBackend
from orionis.cache.stores.memory import build as build_memory
from orionis.database.connection import Connection
from orionis.database.exceptions import QueryException
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


class TestStoreRegressions(TestCase):
    """Exercise real cache stores with temporary files and isolated SQLite."""

    def testStoreAnnotationsResolveAtRuntime(self) -> None:
        """Resolve public storage constructors and properties without local hints."""
        for function in (
            FileCacheBackend.__init__,
            FileCacheBackend.lockNamespace.fget,
            DatabaseCacheBackend.__init__,
            build,
        ):
            with self.subTest(function=function.__qualname__):
                self.assertIn("return", get_type_hints(function))

    async def testRejectedFileAddLeavesTheKeyAvailable(self) -> None:
        """Keep serialization and write failures from publishing partial entries."""
        with TemporaryDirectory() as directory:
            backend = FileCacheBackend(Path(directory))
            with self.assertRaises(TypeError):
                await backend.add("value", object())
            entries = await asyncio.to_thread(
                lambda: list(Path(directory).glob("*.json")),
            )
            self.assertEqual(entries, [])
            self.assertTrue(await backend.add("value", "valid"))
            self.assertEqual(await backend.get("value"), "valid")

        original_open = Path.open
        error = OSError("fixture write failure")

        @contextmanager
        def failed_open(path: Path, mode: str) -> Iterator[object]:
            """Raise the original I/O failure after writing one real byte."""
            with original_open(path, mode) as stream:

                def write(data: bytes) -> int:
                    """Write a partial payload before reporting the fixture error."""
                    stream.write(data[:1])
                    raise error

                yield SimpleNamespace(write=write)

        with TemporaryDirectory() as directory:
            backend = FileCacheBackend(Path(directory))
            with (
                patch.object(Path, "open", failed_open),
                self.assertRaises(OSError) as caught,
            ):
                await backend.add("value", "interrupted")
            self.assertIs(caught.exception, error)
            entries = await asyncio.to_thread(
                lambda: list(Path(directory).glob("*.json")),
            )
            self.assertEqual(entries, [])
            self.assertTrue(await backend.add("value", "valid"))
            self.assertEqual(await backend.get("value"), "valid")

    async def testFileExpirationSurvivesAMonotonicClockReset(self) -> None:
        """Expire persistent entries by wall time after a simulated system restart."""
        clock = SimpleNamespace(wall=1_000_000.0, monotonic=100_000.0)
        module_clock = SimpleNamespace(
            time=lambda: clock.wall,
            monotonic=lambda: clock.monotonic,
        )
        with (
            TemporaryDirectory() as directory,
            patch("orionis.cache.stores.file.time", module_clock),
        ):
            backend = FileCacheBackend(Path(directory))
            await backend.set("expiring", "old", ttl=60)
            await backend.set("permanent", "kept")
            clock.wall += 61
            clock.monotonic = 0.0
            reopened = FileCacheBackend(Path(directory))
            self.assertEqual(await reopened.get("expiring", "missing"), "missing")
            self.assertEqual(await reopened.get("permanent"), "kept")

    async def testMalformedFileMetadataBehavesAsACacheMiss(self) -> None:
        """Reject invalid stored envelopes without losing explicit null values."""
        with TemporaryDirectory() as directory:
            backend = FileCacheBackend(Path(directory))
            await backend.set("value", "initial")
            entry_path = await asyncio.to_thread(
                lambda: next(Path(directory).glob("*.json")),
            )
            for envelope in (
                {"v": 1, "e": "bad"},
                {"v": 1, "e": []},
                {"v": 1, "e": {}},
                {"e": None},
                [],
            ):
                with self.subTest(envelope=envelope):
                    await asyncio.to_thread(
                        entry_path.write_bytes,
                        json.dumps(envelope).encode(),
                    )
                    self.assertEqual(await backend.get("value", "missing"), "missing")
                    self.assertFalse(await backend.exists("value"))
            await backend.set("value", None)
            self.assertIsNone(await backend.get("value", "missing"))
            self.assertTrue(await backend.exists("value"))

    async def testMemoryClearCancelsObsoleteExpirationCallbacks(self) -> None:
        """Retire old TTL callbacks before a cleared key can be reused."""
        backend = build_memory()
        await backend.set("value", "old", ttl=60)
        timer = backend._handlers[backend.build_key("value")]
        try:
            await backend.clear()
            await backend.set("value", "replacement")
            self.assertTrue(timer.cancelled())
            self.assertEqual(await backend.get("value"), "replacement")
        finally:
            timer.cancel()
            await backend.clear()
            await backend.close()

    async def testCancelledFileOperationsWaitForTheirWorkers(self) -> None:
        """Finish each active file operation before returning cancellation."""
        cases = (
            ("get", "__readSync", ("value",)),
            ("set", "__writeSync", ("value", 2)),
            ("replace", "__replaceIfPresent", ("value", 2)),
            ("add", "__createSync", ("new", 2)),
            ("increment", "__incrementSync", ("value",)),
            ("delete", "__unlinkSync", ("value",)),
            ("clear", "__unlinkSync", ()),
        )
        loop = asyncio.get_running_loop()
        for method, helper, arguments in cases:
            with self.subTest(method=method), TemporaryDirectory() as directory:
                backend = FileCacheBackend(Path(directory))
                await backend.set("value", 1)
                started = asyncio.Event()
                released = Event()
                finished = Event()
                helper_name = "_FileCacheBackend" + helper
                original = getattr(FileCacheBackend, helper_name)

                def blocked(
                    *args: object,
                    _started: asyncio.Event = started,
                    _released: Event = released,
                    _finished: Event = finished,
                    _original: Callable[..., object] = original,
                    **kwargs: object,
                ) -> object:
                    """Run the real operation after the test releases its worker."""
                    loop.call_soon_threadsafe(_started.set)
                    try:
                        if not _released.wait(5):
                            message = "The test did not release its cache worker."
                            raise TimeoutError(message)
                        return _original(*args, **kwargs)
                    finally:
                        _finished.set()

                with patch.object(FileCacheBackend, helper_name, blocked):
                    pending = asyncio.create_task(getattr(backend, method)(*arguments))
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
                    self.assertTrue(finished.is_set())
                    self.assertTrue(pending.cancelled())

    async def testExpiredDatabaseReadPreservesConcurrentRenewal(self) -> None:
        """Delete an expired row only while the stored entry remains expired."""
        connection = Connection(
            "sqlite",
            {"driver": "sqlite", "database": ":memory:", "prefix": ""},
        )
        backend = DatabaseCacheBackend(connection, "entries", "locks")
        selected = asyncio.Event()
        resume = asyncio.Event()
        original = Connection.select

        async def paused(*args: object, **kwargs: object) -> object:
            """Pause after materializing the first real SQLite read."""
            rows = await original(*args, **kwargs)
            if not selected.is_set():
                selected.set()
                await resume.wait()
            return rows

        try:
            await backend.set("value", "expired", ttl=-1)
            with patch.object(Connection, "select", paused):
                pending = asyncio.create_task(backend.get("value", "missing"))
                try:
                    await asyncio.wait_for(selected.wait(), timeout=5)
                    await backend.set("value", "renewed", ttl=60)
                finally:
                    resume.set()
                    result = await pending
            self.assertEqual(result, "missing")
            self.assertEqual(await backend.get("value"), "renewed")
        finally:
            await connection.disconnect()

    async def testDatabaseInsertFailuresAreNotReportedAsSuccess(self) -> None:
        """Propagate real insert failures when no conflicting row exists."""
        connection = Connection(
            "sqlite",
            {"driver": "sqlite", "database": ":memory:", "prefix": ""},
        )
        backend = DatabaseCacheBackend(connection, "entries", "locks")
        try:
            await backend.migrate()
            for table in ("entries", "locks"):
                await connection.statement(
                    f"CREATE TRIGGER reject_{table} BEFORE INSERT ON {table} "
                    "BEGIN SELECT RAISE(ABORT, 'fixture insert rejected'); END",
                )
            for operation, arguments in (
                (backend.set, ("value", 1)),
                (backend.acquireLock, ("value", "owner", 60)),
            ):
                with (
                    self.subTest(operation=operation.__name__),
                    self.assertRaises(QueryException),
                ):
                    await operation(*arguments)
        finally:
            await connection.disconnect()
