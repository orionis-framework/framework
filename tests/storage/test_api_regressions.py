# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect storage references, upload ownership and stream failure identity."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from functools import partial
import inspect
from io import BytesIO
from pathlib import Path
from threading import Barrier, BrokenBarrierError, Event
from types import SimpleNamespace
from typing import TYPE_CHECKING, BinaryIO, get_type_hints

from orionis.failure.runtime import operation
from orionis.http.payload.uploaded_file import UploadedFile as HttpUpload
from orionis.storage.contracts.directory import IDirectory
from orionis.storage.contracts.disk import IDisk
from orionis.storage.contracts.file import IFile
from orionis.storage.contracts.manager import IStorageManager
from orionis.storage.contracts.stream import IStorageStream
from orionis.storage.contracts.uploaded_file import IUploadedFile
from orionis.storage.directory import Directory
from orionis.storage.disk import Disk
from orionis.storage.drivers.memory import MemoryStorageDriver
from orionis.storage.exceptions import StoragePathException
from orionis.storage.file import File
from orionis.storage.manager import StorageManager
from orionis.storage.stream import AsyncStream
from orionis.storage.uploaded_file import UploadedFile
from tests.support.failure_runtime import IsolatedFailureTestCase, activate_runtime

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, Iterator


def _manager() -> StorageManager:
    """Create a real manager with isolated memory-backed configuration.

    Returns
    -------
    StorageManager
        Manager with two independent configured memory disks.
    """
    config = SimpleNamespace(
        default="local",
        disks=SimpleNamespace(
            local=SimpleNamespace(driver="memory"),
            other=SimpleNamespace(driver="memory"),
        ),
    )
    return StorageManager(
        SimpleNamespace(basePath=Path.cwd(), config=lambda _section: config),
    )


class _BlockedUpload(HttpUpload):
    """Pause one real upload operation on its worker thread."""

    def __init__(self, phase: str) -> None:
        """Select the worker operation to hold behind an explicit barrier.

        Parameters
        ----------
        phase : str
            Read, stream or close operation to block.
        """
        super().__init__("payload.txt", "text/plain")
        self.phase = phase
        self.entered = Event()
        self.release = Event()
        self.finished = Event()
        self.write(b"payload")

    def _wait(self) -> None:
        """Hold the worker until its owner explicitly releases the barrier."""
        self.entered.set()
        if not self.release.wait(5):
            message = "The upload worker was not released."
            raise TimeoutError(message)
        self.finished.set()

    def read(self) -> bytes:
        """Read the real payload after the configured barrier is released.

        Returns
        -------
        bytes
            Complete buffered upload contents.
        """
        if self.phase == "read":
            self._wait()
        return super().read()

    def chunks(self, size: int = 65536) -> Iterator[bytes]:
        """Yield real chunks after the configured worker barrier.

        Parameters
        ----------
        size : int
            Maximum number of bytes per chunk.

        Yields
        ------
        bytes
            Buffered upload chunks in order.
        """
        if self.phase == "stream":
            self._wait()
        yield from super().chunks(size)

    def close(self) -> None:
        """Close the real buffer after the configured worker barrier."""
        if self.phase == "close":
            self._wait()
        super().close()


class _TrackedUpload(HttpUpload):
    """Retain a chunk iterator to make explicit closure observable."""

    def __init__(self) -> None:
        """Create buffered content and a retained iterator slot."""
        super().__init__("payload.txt", "text/plain")
        self.iterator = None
        self.iterator_closed = False
        self.write(b"payload")

    def chunks(self, size: int = 65536) -> Iterator[bytes]:
        """Retain an iterator whose finalizer records deterministic closure.

        Parameters
        ----------
        size : int
            Maximum number of bytes per chunk.

        Returns
        -------
        Iterator[bytes]
            Tracked iterator over the real upload buffer.
        """

        def iterate() -> Iterator[bytes]:
            """Yield content and record closure even after partial consumption.

            Yields
            ------
            bytes
                Original buffered upload chunks.
            """
            try:
                yield from super(_TrackedUpload, self).chunks(size)
            finally:
                self.iterator_closed = True

        self.iterator = iterate()
        return self.iterator


class _RejectingDriver(MemoryStorageDriver):
    """Fail after consuming one upload chunk while retaining the producer."""

    def __init__(self, error: Exception) -> None:
        """Retain the exact destination failure used by the fixture.

        Parameters
        ----------
        error : Exception
            Failure raised after the first chunk.
        """
        super().__init__()
        self.error = error
        self.stream = None

    async def writeStream(
        self,
        path: str,
        stream: AsyncIterable[bytes],
        visibility: str | None = None,
    ) -> None:
        """Consume one chunk and fail without taking ownership of the producer.

        Parameters
        ----------
        path : str
            Destination path requested by the caller.
        stream : AsyncIterable[bytes]
            Upload producer retained to prevent garbage-collection cleanup.
        visibility : str | None
            Visibility requested by the caller.
        """
        self.target = (path, visibility)
        self.stream = aiter(stream)
        await anext(self.stream)
        raise self.error


class TestStorageApiRegressions(IsolatedFailureTestCase):
    """Verify storage ownership and public reflection against real components."""

    async def testUploadCancellationDrainsTheActiveWorker(self) -> None:
        """Keep read, iterator advance and close owned until their worker ends."""
        for phase in ("read", "stream", "close"):
            with self.subTest(phase=phase):
                source = _BlockedUpload(phase)
                upload = UploadedFile(source, _manager())
                action = {
                    "read": upload.read,
                    "stream": partial(upload.storeAs, "", "stored.txt"),
                    "close": partial(upload.move, "", "stored.txt"),
                }[phase]
                pending = asyncio.create_task(action())
                try:
                    self.assertTrue(await asyncio.to_thread(source.entered.wait, 2))
                    pending.cancel()
                    done, _ = await asyncio.wait((pending,), timeout=0.02)
                    self.assertFalse(done)
                finally:
                    source.release.set()
                    await asyncio.gather(pending, return_exceptions=True)
                    self.assertTrue(await asyncio.to_thread(source.finished.wait, 2))
                    source.close()
                self.assertTrue(pending.cancelled())

    async def testFailedUploadClosesItsIteratorWithoutClosingItsSource(self) -> None:
        """Release the owned iterator when the destination fails mid-stream."""
        source = _TrackedUpload()
        error = OSError("destination failed")
        driver = _RejectingDriver(error)
        manager = _manager()
        manager.extend("memory", lambda _configuration: driver)
        upload = UploadedFile(source, manager)
        try:
            with self.assertRaises(OSError) as caught:
                await upload.storeAs("", "stored.txt")
            self.assertIs(caught.exception, error)
            self.assertTrue(source.iterator_closed)
            self.assertEqual(await upload.read(), b"payload")
        finally:
            if driver.stream is not None:
                await driver.stream.aclose()
            if source.iterator is not None:
                source.iterator.close()
            source.close()

    async def testStreamPersistenceFailurePreservesTheContextBodyError(self) -> None:
        """Report cleanup separately while propagating the original body failure."""
        app, runtime, handler = activate_runtime()
        self.addAsyncCleanup(runtime.shutdown)
        body_error = RuntimeError("body failed")
        flush_error = ValueError("persistence failed")
        handle = BytesIO(b"payload")

        def flush(_handle: BinaryIO) -> None:
            """Raise the selected persistence failure before handle closure.

            Parameters
            ----------
            _handle : BinaryIO
                Live handle supplied by the stream.
            """
            raise flush_error

        stream = AsyncStream(lambda: handle, flush)
        with operation(app):
            with self.assertRaises(RuntimeError) as caught:
                async with stream:
                    raise body_error
            await runtime.drain()
        self.assertIs(caught.exception, body_error)
        self.assertTrue(handle.closed)
        self.assertEqual(handler.reports, [body_error, flush_error])

    async def testFileNamesCannotResolveToDirectorySegments(self) -> None:
        """Reject dot names before renaming or publishing an uploaded file."""
        for name in (".", ".."):
            with self.subTest(name=name):
                manager = _manager()
                disk = manager.disk()
                original = await disk.put("a/b/original.txt", b"original")
                with self.assertRaises(StoragePathException):
                    await original.rename(name)
                self.assertEqual(await original.read(), b"original")
                source = HttpUpload("payload.txt", "text/plain")
                try:
                    source.write(b"replacement")
                    with self.assertRaises(StoragePathException):
                        await manager.uploaded(source).storeAs("a/b", name)
                finally:
                    source.close()

    async def testConcurrentDiskResolutionSupportsNestedFactories(self) -> None:
        """Publish one disk while allowing a factory to resolve another disk."""
        manager = _manager()
        barrier = Barrier(2)
        dependencies = []

        def factory(configuration: object) -> MemoryStorageDriver:
            """Resolve a dependency and expose concurrent construction.

            Parameters
            ----------
            configuration : object
                Configuration of the disk being constructed.

            Returns
            -------
            MemoryStorageDriver
                New isolated driver for the requested disk.
            """
            if configuration is manager._config.disks.local:
                dependencies.append(manager.disk("other"))
                with suppress(BrokenBarrierError):
                    barrier.wait(timeout=1)
            return MemoryStorageDriver()

        manager.extend("memory", factory)
        with ThreadPoolExecutor(max_workers=2) as executor:
            disks = await asyncio.gather(
                *(asyncio.wrap_future(executor.submit(manager.disk)) for _ in range(2)),
            )
        self.assertIs(disks[0], disks[1])
        self.assertEqual(len(dependencies), 1)
        manager.extend("memory", lambda _configuration: MemoryStorageDriver())
        self.assertIsNot(manager.disk(), disks[0])

    def testPublicApiAnnotationsResolveAtRuntime(self) -> None:
        """Resolve every declared public method across the twelve API classes."""
        for klass in (
            StorageManager,
            Disk,
            File,
            Directory,
            AsyncStream,
            UploadedFile,
            IStorageManager,
            IDisk,
            IFile,
            IDirectory,
            IStorageStream,
            IUploadedFile,
        ):
            for name, method in vars(klass).items():
                if inspect.isfunction(method) and (
                    not name.startswith("_") or name in {"__init__", "__aexit__"}
                ):
                    with self.subTest(klass=klass.__name__, method=name):
                        self.assertIn("return", get_type_hints(method))
