# ruff: noqa: PLC0415, PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Keep runtime reflection annotations and intentionally deferred imports.
"""Protect local storage boundaries and resource ownership."""

import asyncio
from io import BytesIO, UnsupportedOperation
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from typing import TYPE_CHECKING
from unittest.mock import patch
from orionis.storage.buffering import iterate_chunks, read_chunks, spool_stream
from orionis.storage.drivers.local import LocalStorageDriver
from orionis.storage.drivers.memory import MemoryStorageDriver
from orionis.storage.exceptions import (
    StoragePathException,
    UnsupportedStorageOperationException,
)
from orionis.storage.stream import AsyncStream
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator


class _FailedClose(BytesIO):
    """Close a real buffer before reporting a controlled cleanup failure."""

    def close(self) -> None:
        """Release the buffer and fail exactly once.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        OSError
            On the first close, after the resource is released.
        """
        if not self.closed:
            super().close()
            message = "buffer close failed"
            raise OSError(message)


class TestStorageResourceRegressions(TestCase):
    """Use disposable disks and bounded events to reproduce storage failures."""

    async def testSpoolRejectsInvalidMemoryBoundsBeforeConsumption(self) -> None:
        """Reject unbounded or invalid spool thresholds before reading input."""
        consumed = []

        async def source() -> AsyncIterator[bytes]:
            """Observe any input consumption attempted before threshold validation."""
            consumed.append(True)
            yield b"payload"

        for size in (0, -1, True, 1.5):
            with self.subTest(size=size):
                buffer = None
                try:
                    with self.assertRaises(ValueError):
                        buffer = await spool_stream(source(), max_size=size)
                finally:
                    if buffer is not None:
                        buffer.close()
        self.assertEqual(consumed, [])

    async def testCleanupErrorsIgnoreAnUnrelatedHandledException(self) -> None:
        """Propagate cleanup failures when the owning operation itself succeeds.

        Returns
        -------
        None
            No return value.
        """
        for kind in ("read", "iterate", "close", "context", "staging"):
            with self.subTest(kind=kind):
                try:
                    message = "unrelated handled error"
                    raise LookupError(message)
                except LookupError:
                    with self.assertRaises(OSError):
                        await self._failCleanup(kind)

    async def _failCleanup(self, kind: str) -> None:
        """Complete a real stream operation whose cleanup deliberately fails.

        Parameters
        ----------
        kind : str
            Resource boundary to exercise.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        OSError
            When the successfully used resource closes.
        """
        if kind == "staging":

            async def source() -> AsyncIterator[bytes]:
                """Yield a complete local upload.

                Yields
                ------
                bytes
                    Fixture content to publish.
                """
                yield b"data"

            with TemporaryDirectory() as directory:
                driver = LocalStorageDriver(Path(directory))
                with patch.object(Path, "unlink", side_effect=OSError("staging close")):
                    await driver.writeStream("data", source())
            return
        handle = _FailedClose(b"data")
        if kind == "read":
            chunks = read_chunks(lambda: handle, 4)
            self.assertEqual([chunk async for chunk in chunks], [b"data"])
        elif kind == "iterate":
            chunks = iterate_chunks(lambda: handle)
            self.assertEqual([chunk async for chunk in chunks], [b"data"])
        else:
            stream = AsyncStream(lambda: handle)
            if kind == "context":
                async with stream:
                    self.assertEqual(await stream.read(), b"data")
            else:
                self.assertEqual(await stream.read(), b"data")
                await stream.close()

    async def testIteratorPreservesEmptyChunksAndCloses(self) -> None:
        """Distinguish an empty yielded chunk from iterator exhaustion."""
        closed = []

        def source() -> Iterator[bytes]:
            """Yield empty chunks around data and expose deterministic closure."""
            try:
                yield from (b"", b"a", b"", b"b", b"")
            finally:
                closed.append(True)

        chunks = [chunk async for chunk in iterate_chunks(source)]
        self.assertEqual(chunks, [b"", b"a", b"", b"b", b""])
        self.assertEqual(closed, [True])

    async def testMemoryMoveToItsOwnNormalizedPathKeepsContent(self) -> None:
        """Retain a file and its timestamps when its normalized destination matches."""
        driver = MemoryStorageDriver()
        await driver.write("data/item", b"value")
        original = await driver.info("data/item")
        await driver.move("data/item", "data/./item")
        self.assertEqual(await driver.read("data/item"), b"value")
        self.assertEqual(await driver.info("data/item"), original)

    async def testMemoryOpenHonorsReadWriteAndAppendModes(self) -> None:
        """Enforce mode capabilities and append after an explicit backward seek."""
        driver = MemoryStorageDriver()
        await driver.write("data", b"original")
        with self.subTest(mode="rb"):
            async with driver.open("data", "rb") as stream:
                with self.assertRaises(UnsupportedOperation):
                    await stream.write(b"replacement")
        with self.subTest(mode="wb"):
            async with driver.open("write-only", "wb") as stream:
                await stream.write(b"data")
                await stream.seek(0)
                with self.assertRaises(UnsupportedOperation):
                    await stream.read()
        with self.subTest(mode="ab+"):
            async with driver.open("data", "ab+") as stream:
                await stream.seek(0)
                await stream.write(b"!")
            self.assertEqual(await driver.read("data"), b"original!")

    async def testMemoryRejectsInvalidChunkSizes(self) -> None:
        """Reject invalid streaming bounds even for an empty in-memory file."""
        driver = MemoryStorageDriver()
        await driver.write("empty", b"")
        for size in (0, -1, True, 1.5):
            with self.subTest(size=size), self.assertRaises(ValueError):
                async for _ in driver.readStream("empty", size):
                    self.fail("An invalid chunk size yielded content.")

    async def testInvalidVisibilityLeavesExistingDataUntouched(self) -> None:
        """Reject invalid visibility before publishing or consuming upload chunks."""
        with TemporaryDirectory() as directory:
            for driver in (MemoryStorageDriver(), LocalStorageDriver(Path(directory))):
                with self.subTest(driver=type(driver).__name__):
                    await driver.write("data", b"original")
                    with self.assertRaises(UnsupportedStorageOperationException):
                        await driver.write("data", b"replacement", "invalid")
                    self.assertEqual(await driver.read("data"), b"original")
                    consumed = []

                    async def chunks(
                        seen: list[bool] = consumed,
                    ) -> AsyncIterator[bytes]:
                        """Record whether validation consumed the input stream.

                        Parameters
                        ----------
                        seen : list[bool]
                            Observations owned by this test scenario.

                        Yields
                        ------
                        bytes
                            Replacement content for the selected backend.
                        """
                        seen.append(True)
                        yield b"replacement"

                    with self.assertRaises(UnsupportedStorageOperationException):
                        await driver.writeStream("data", chunks(), "invalid")
                    self.assertEqual(consumed, [])
                    self.assertEqual(await driver.read("data"), b"original")

    async def testLocalRejectsDirectoryLinksOutsideItsRoot(self) -> None:
        """Reject junction or symlink traversal into a separate owned directory."""
        with TemporaryDirectory() as directory:
            parent = Path(directory)
            root, outside = parent / "root", parent / "outside"
            outside.mkdir()
            (outside / "secret").write_bytes(b"outside")
            driver = LocalStorageDriver(root)
            link = root / "escape"
            if os.name == "nt":
                import _winapi

                _winapi.CreateJunction(str(outside), str(link))
            else:
                link.symlink_to(outside, target_is_directory=True)
            try:
                for operation, arguments in (
                    (driver.read, ("escape/secret",)),
                    (driver.write, ("escape/new", b"must remain absent")),
                    (driver.directoryExists, ("escape",)),
                ):
                    with (
                        self.subTest(operation=operation.__name__),
                        self.assertRaises(StoragePathException),
                    ):
                        await operation(*arguments)
                self.assertFalse((outside / "new").exists())
            finally:
                if os.name == "nt":
                    link.rmdir()
                else:
                    link.unlink()

    async def testCancelledLocalWriteFinishesBeforeReturning(self) -> None:
        """Drain an active file worker before releasing a cancelled write caller."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            driver = LocalStorageDriver(root)
            started = asyncio.Event()
            released, finished = Event(), Event()
            loop = asyncio.get_running_loop()
            original = LocalStorageDriver._LocalStorageDriver__writeSync

            def blocked(
                backend: LocalStorageDriver,
                normalized: str,
                data: bytes,
                visibility: str | None,
            ) -> None:
                """Block the actual file worker until the test permits completion.

                Parameters
                ----------
                backend : LocalStorageDriver
                    Real backend whose worker is intercepted.
                normalized : str
                    Canonical destination passed to the original operation.
                data : bytes
                    Bytes passed unchanged to the real writer.
                visibility : str | None
                    Requested file visibility passed unchanged.
                """
                loop.call_soon_threadsafe(started.set)
                try:
                    if not released.wait(5):
                        message = "The test did not release the file worker."
                        raise TimeoutError(message)
                    original(backend, normalized, data, visibility)
                finally:
                    finished.set()

            with patch.object(
                LocalStorageDriver,
                "_LocalStorageDriver__writeSync",
                blocked,
            ):
                pending = asyncio.create_task(driver.write("data", b"value"))
                try:
                    await asyncio.wait_for(started.wait(), 5)
                    pending.cancel()
                    await asyncio.sleep(0)
                    self.assertFalse(pending.done())
                finally:
                    released.set()
                    await asyncio.gather(pending, return_exceptions=True)
                    self.assertTrue(await asyncio.to_thread(finished.wait, 5))
            self.assertTrue(pending.cancelled())

    async def testFailedStreamPublicationRemovesStagingFile(self) -> None:
        """Preserve the target and remove a staged upload when replacement fails."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            driver = LocalStorageDriver(root)
            await driver.write("data", b"original")
            error = OSError("fixture publication failure")

            async def chunks() -> AsyncIterator[bytes]:
                """Produce replacement data for the failed publication."""
                yield b"replacement"

            with (
                patch.object(Path, "replace", side_effect=error),
                self.assertRaises(OSError) as caught,
            ):
                await driver.writeStream("data", chunks())
            self.assertIs(caught.exception, error)
            self.assertEqual((root / "data").read_bytes(), b"original")
            entries = await asyncio.to_thread(
                lambda: sorted(item.name for item in root.iterdir()),
            )
            self.assertEqual(entries, ["data"])

    async def testMoveDoesNotFallbackOnPermissionFailure(self) -> None:
        """Preserve a denied rename without copying or deleting the source."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            driver = LocalStorageDriver(root)
            await driver.write("source", b"original")
            error = PermissionError("fixture permission denied")
            with (
                patch.object(Path, "replace", side_effect=error),
                self.assertRaises(PermissionError) as caught,
            ):
                await driver.move("source", "destination")
            self.assertIs(caught.exception, error)
            self.assertEqual((root / "source").read_bytes(), b"original")
            self.assertFalse((root / "destination").exists())

    async def testLocalListsOrdinaryTmpFiles(self) -> None:
        """List user files ending in tmp while hiding only internal staging names."""
        with TemporaryDirectory() as directory:
            driver = LocalStorageDriver(Path(directory))
            await driver.write("notes.tmp", b"user data")
            self.assertEqual(await driver.files(), ["notes.tmp"])
            self.assertEqual(await driver.files(recursive=True), ["notes.tmp"])

    async def testDriversRejectVariableLengthDigests(self) -> None:
        """Reject hash algorithms that require an unsupported output-length argument."""
        with TemporaryDirectory() as directory:
            for driver in (MemoryStorageDriver(), LocalStorageDriver(Path(directory))):
                with self.subTest(driver=type(driver).__name__):
                    await driver.write("data", b"value")
                    with self.assertRaises(UnsupportedStorageOperationException):
                        await driver.hash("data", "shake_128")
