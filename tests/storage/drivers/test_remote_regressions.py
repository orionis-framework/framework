# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Check remote-driver ownership with controlled transports and real buffers."""

import asyncio
from contextlib import aclosing, suppress
import hashlib
import importlib
import inspect
from io import BytesIO, UnsupportedOperation
import tempfile
from threading import Barrier, BrokenBarrierError, Event
from types import SimpleNamespace
from typing import TYPE_CHECKING, get_type_hints
from unittest.mock import patch

from orionis.storage.drivers import functions
from orionis.storage.drivers.azure import AzureStorageDriver
from orionis.storage.drivers.gcs import GoogleStorageDriver
from orionis.storage.drivers.s3 import S3StorageDriver
from orionis.storage.exceptions import (
    StorageFileNotFoundException,
    UnsupportedStorageOperationException,
)
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable
    from typing import BinaryIO


_DRIVERS = (S3StorageDriver, AzureStorageDriver, GoogleStorageDriver)


async def _payload() -> AsyncIterator[bytes]:
    """Yield a fixed upload without accessing any external source."""
    yield b"payload"


def _upload_driver(kind: type, upload: Callable[..., None]) -> object:
    """Attach a controlled transport using each driver's actual upload contract."""
    driver = kind(SimpleNamespace(bucket="fixture", container="fixture"))
    if kind is S3StorageDriver:
        driver._client = SimpleNamespace(upload_fileobj=upload)
    elif kind is AzureStorageDriver:
        driver._container = SimpleNamespace(upload_blob=upload)
    else:
        driver._bucket = SimpleNamespace(
            blob=lambda _name: SimpleNamespace(upload_from_file=upload),
        )
    return driver


class _ClientError(Exception):
    """Retain the error response passed through the S3 exception protocol."""

    def __init__(self, response: dict, operation: str) -> None:
        """Store the same response and operation supplied to an SDK error."""
        self.response = response
        super().__init__(operation)


def _object_driver(kind: type, objects: dict[str, bytes]) -> object:
    """Provide the SDK object protocol over a controlled byte mapping."""
    driver = kind(SimpleNamespace(bucket="fixture", container="fixture"))

    def contents(key: str) -> bytes:
        """Return an existing object or the transport's missing-object error."""
        if key not in objects:
            raise _ClientError({"Error": {"Code": "NoSuchKey"}}, "fixture")
        return objects[key]

    def upload(name: str, data: object, **_kwargs: object) -> None:
        """Store the bytes consumed by the real driver's upload call."""
        objects[name] = data if isinstance(data, bytes) else data.read()

    def blob(key: str) -> object:
        """Expose the blob operations used by Azure and GCS streams."""
        return SimpleNamespace(
            name=key,
            exists=lambda: key in objects,
            download_blob=lambda: SimpleNamespace(
                readinto=lambda buffer: buffer.write(contents(key)),
            ),
            download_to_file=lambda buffer: buffer.write(contents(key)),
            upload_from_file=lambda buffer, **kwargs: upload(key, buffer, **kwargs),
            delete=lambda: objects.pop(key, None),
            delete_blob=lambda: objects.pop(key, None),
        )

    if kind is S3StorageDriver:
        driver._client_error = _ClientError
        driver._client = SimpleNamespace(
            download_fileobj=lambda _bucket, key, buffer: buffer.write(contents(key)),
            upload_fileobj=lambda buffer, _bucket, key, **kwargs: upload(
                key,
                buffer,
                **kwargs,
            ),
            head_object=lambda **kwargs: {
                "ContentLength": len(contents(kwargs["Key"])),
            },
            copy_object=lambda **kwargs: upload(
                kwargs["Key"],
                contents(kwargs["CopySource"]["Key"]),
            ),
            delete_object=lambda **kwargs: objects.pop(kwargs["Key"], None),
        )
    elif kind is AzureStorageDriver:
        driver._not_found = _ClientError
        driver._container = SimpleNamespace(get_blob_client=blob, upload_blob=upload)
    else:
        driver._not_found = _ClientError
        driver._bucket = SimpleNamespace(
            blob=blob,
            get_blob=lambda key: blob(key) if key in objects else None,
            copy_blob=lambda origin, _bucket, target: upload(
                target,
                contents(origin.name),
            ),
        )
    return driver


class TestRemoteRegressions(TestCase):
    """Exercise transport contracts without authenticating to remote services."""

    def testRemoteAnnotationsResolveAtRuntime(self) -> None:
        """Resolve every public driver method and shared helper annotation."""
        targets = [
            function
            for driver in _DRIVERS
            for name, function in driver.__dict__.items()
            if inspect.isfunction(function)
            and (not name.startswith("_") or name == "__init__")
        ]
        targets.extend(
            function
            for name, function in functions.__dict__.items()
            if not name.startswith("_") and inspect.isfunction(function)
        )
        for function in targets:
            with self.subTest(function=function.__qualname__):
                self.assertIn("return", get_type_hints(function))

    async def testCancelledUploadsKeepTheirBuffersUntilWorkersFinish(self) -> None:
        """Drain each blocked upload before closing its owned spool."""
        loop = asyncio.get_running_loop()
        for kind in _DRIVERS:
            with self.subTest(driver=kind.__name__):
                started = asyncio.Event()
                release = Event()
                finished = Event()
                buffers = []
                observed = []

                def upload(
                    *args: object,
                    _started: asyncio.Event = started,
                    _release: Event = release,
                    _finished: Event = finished,
                    _buffers: list = buffers,
                    _observed: list = observed,
                    **kwargs: object,
                ) -> None:
                    """Hold the real spool until the test releases this transfer."""
                    buffer = kwargs.get("data") if "data" in kwargs else args[0]
                    _buffers.append(buffer)
                    loop.call_soon_threadsafe(_started.set)
                    try:
                        if not _release.wait(5):
                            message = "The test did not release its upload."
                            raise TimeoutError(message)
                        _observed.append(buffer.closed)
                    finally:
                        _finished.set()

                driver = _upload_driver(kind, upload)
                pending = asyncio.create_task(driver.writeStream("object", _payload()))
                try:
                    await asyncio.wait_for(started.wait(), timeout=5)
                    pending.cancel()
                    completed, _ = await asyncio.wait({pending}, timeout=0.05)
                    self.assertFalse(completed)
                    self.assertFalse(buffers[0].closed)
                finally:
                    release.set()
                    await asyncio.gather(pending, return_exceptions=True)
                    await asyncio.to_thread(finished.wait, 5)
                self.assertEqual(observed, [False])
                self.assertTrue(buffers[0].closed)
                self.assertTrue(pending.cancelled())

    async def testFailedStreamOpenClosesItsAllocatedSpool(self) -> None:
        """Release an allocated spool when SDK bootstrap or download fails."""
        original = tempfile.SpooledTemporaryFile
        for kind, helper in (
            (S3StorageDriver, "_S3StorageDriver__client"),
            (AzureStorageDriver, "_AzureStorageDriver__blob"),
            (GoogleStorageDriver, "_GoogleStorageDriver__blob"),
        ):
            with self.subTest(driver=kind.__name__):
                buffers = []

                def allocate(
                    *args: object,
                    _buffers: list = buffers,
                    **kwargs: object,
                ) -> BinaryIO:
                    """Track the actual spooled file allocated by the opener."""
                    buffer = original(*args, **kwargs)
                    _buffers.append(buffer)
                    return buffer

                driver = kind(SimpleNamespace(bucket="fixture", container="fixture"))
                error = RuntimeError("fixture SDK failure")
                try:
                    with (
                        patch.object(tempfile, "SpooledTemporaryFile", allocate),
                        patch.object(kind, helper, side_effect=error),
                        self.assertRaises(RuntimeError) as caught,
                    ):
                        async with driver.open("object"):
                            self.fail("Opening must propagate the SDK failure.")
                    self.assertIs(caught.exception, error)
                    self.assertEqual(len(buffers), 1)
                    self.assertTrue(buffers[0].closed)
                finally:
                    for buffer in buffers:
                        buffer.close()

    async def testS3PartialDeleteFailureDoesNotReportSuccess(self) -> None:
        """Raise the SDK error contract when a batch reports failed objects."""
        response = {
            "Deleted": [{"Key": "directory/good"}],
            "Errors": [
                {"Key": "directory/bad", "Code": "AccessDenied", "Message": "fixture"},
            ],
        }
        driver = S3StorageDriver(SimpleNamespace(bucket="fixture"))
        driver._client_error = _ClientError
        driver._client = SimpleNamespace(
            get_paginator=lambda _name: SimpleNamespace(
                paginate=lambda **_kwargs: [
                    {"Contents": [{"Key": "directory/good"}, {"Key": "directory/bad"}]},
                ],
            ),
            delete_objects=lambda **_kwargs: response,
        )
        with self.assertRaises(_ClientError) as caught:
            await driver.deleteDirectory("directory")
        self.assertEqual(caught.exception.response["Errors"], response["Errors"])

    async def testRemoteHashesRejectVariableLengthAlgorithms(self) -> None:
        """Reject XOF algorithms while retaining fixed-length streamed hashes."""
        for kind in _DRIVERS:
            with self.subTest(driver=kind.__name__):
                driver = kind(SimpleNamespace(bucket="fixture", container="fixture"))
                if kind is S3StorageDriver:
                    driver._client = SimpleNamespace(
                        get_object=lambda **_kwargs: {"Body": BytesIO(b"payload")},
                    )
                elif kind is AzureStorageDriver:
                    driver._container = SimpleNamespace(
                        get_blob_client=lambda _name: SimpleNamespace(
                            download_blob=lambda: SimpleNamespace(
                                chunks=lambda: [b"payload"],
                            ),
                        ),
                    )
                else:
                    driver._bucket = SimpleNamespace(
                        get_blob=lambda _name: SimpleNamespace(
                            open=lambda _mode: BytesIO(b"payload"),
                        ),
                    )
                with self.assertRaises(UnsupportedStorageOperationException):
                    await driver.hash("object", "shake_128")
                self.assertEqual(
                    await driver.hash("object"),
                    hashlib.sha256(b"payload").hexdigest(),
                )

    async def testS3RejectsVisibilityBeforeSdkOrStreamConsumption(self) -> None:
        """Validate visibility before bootstrapping a client or consuming a source."""
        driver = S3StorageDriver(SimpleNamespace(bucket="fixture"))
        consumed = []

        async def payload() -> AsyncIterator[bytes]:
            """Record whether validation consumed the upload producer."""
            consumed.append(True)
            yield b"payload"

        for operation, arguments in (
            (driver.write, ("object", b"payload", "invalid")),
            (driver.writeStream, ("object", payload(), "invalid")),
        ):
            with (
                self.subTest(operation=operation.__name__),
                patch.object(
                    S3StorageDriver,
                    "_S3StorageDriver__client",
                    side_effect=AssertionError("SDK must not run"),
                ),
                self.assertRaises(UnsupportedStorageOperationException),
            ):
                await operation(*arguments)
        self.assertEqual(consumed, [])

    async def testAzureRejectsInvalidChunkSizesBeforeSdk(self) -> None:
        """Validate advisory chunk sizes before creating a remote downloader."""
        driver = AzureStorageDriver(SimpleNamespace(container="fixture"))
        for size in (0, -1, True, 1.5):
            with (
                self.subTest(size=size),
                patch.object(
                    AzureStorageDriver,
                    "_AzureStorageDriver__blob",
                    side_effect=AssertionError("SDK must not run"),
                ),
                self.assertRaises(ValueError),
            ):
                async with aclosing(driver.readStream("object", size)) as chunks:
                    await anext(chunks)

    async def testConcurrentBootstrapPublishesOneClient(self) -> None:
        """Build one SDK client when two worker operations start concurrently."""
        for kind in _DRIVERS:
            with self.subTest(driver=kind.__name__):
                rendezvous = Barrier(2)
                calls = []
                blob = SimpleNamespace(exists=lambda: True)
                container = SimpleNamespace(
                    get_blob_client=lambda _name, _blob=blob: _blob,
                )
                bucket = SimpleNamespace(blob=lambda _name, _blob=blob: _blob)
                client = SimpleNamespace(
                    head_object=lambda **_kwargs: {},
                    get_container_client=lambda _name, _container=container: _container,
                    bucket=lambda _name, _bucket=bucket: _bucket,
                )

                def create(
                    *args: object,
                    _rendezvous: Barrier = rendezvous,
                    _calls: list = calls,
                    _client: object = client,
                    **kwargs: object,
                ) -> object:
                    """Allow overlapping factories to rendezvous before returning."""
                    del args, kwargs
                    _calls.append(True)
                    with suppress(BrokenBarrierError):
                        _rendezvous.wait(timeout=0.1)
                    return _client

                dependencies = {
                    "boto3": SimpleNamespace(client=create),
                    "botocore.config": SimpleNamespace(),
                    "botocore.exceptions": SimpleNamespace(ClientError=_ClientError),
                    "azure.storage.blob": SimpleNamespace(BlobServiceClient=create),
                    "azure.core.exceptions": SimpleNamespace(
                        ResourceNotFoundError=LookupError,
                        HttpResponseError=OSError,
                    ),
                    "google.cloud.storage": SimpleNamespace(Client=create),
                    "google.cloud.exceptions": SimpleNamespace(
                        NotFound=LookupError,
                        GoogleCloudError=OSError,
                    ),
                }

                def dependency(
                    name: str,
                    *_args: str,
                    _dependencies: dict = dependencies,
                ) -> object:
                    """Return the controlled SDK protocol requested by the driver."""
                    return _dependencies[name]

                driver = kind(SimpleNamespace(bucket="fixture", container="fixture"))
                module = importlib.import_module(kind.__module__)
                with patch.object(module, "importDriverDependency", dependency):
                    results = await asyncio.gather(
                        driver.exists("first"),
                        driver.exists("second"),
                    )
                self.assertEqual(results, [True, True])
                self.assertEqual(len(calls), 1)

    async def testRemoteStreamsEnforceReadWriteAndAppendModes(self) -> None:
        """Keep binary permissions and append positioning consistent across drivers."""
        for kind in _DRIVERS:
            with self.subTest(driver=kind.__name__):
                objects = {"object": b"initial"}
                driver = _object_driver(kind, objects)
                async with driver.open("object", "rb") as stream:
                    with self.assertRaises(UnsupportedOperation):
                        await stream.write(b"forbidden")
                    self.assertEqual(await stream.read(), b"initial")
                async with driver.open("object", "wb") as stream:
                    with self.assertRaises(UnsupportedOperation):
                        await stream.read()
                    await stream.write(b"new")
                self.assertEqual(objects["object"], b"new")
                async with driver.open("object", "ab") as stream:
                    await stream.seek(0)
                    await stream.write(b"+")
                self.assertEqual(objects["object"], b"new+")
                with self.assertRaises(StorageFileNotFoundException):
                    async with driver.open("absent", "rb+"):
                        self.fail("An existing object is required.")

    async def testRemoteMoveToTheSamePathPreservesTheObject(self) -> None:
        """Keep existing content when source and destination identify one object."""
        for kind in _DRIVERS:
            with self.subTest(driver=kind.__name__):
                objects = {"object": b"initial"}
                driver = _object_driver(kind, objects)
                await driver.move("object", "object")
                self.assertEqual(objects, {"object": b"initial"})
                with self.assertRaises(StorageFileNotFoundException):
                    await driver.move("absent", "absent")

    def testBufferCapabilitiesCannotBypassBinaryModes(self) -> None:
        """Enforce permissions through inherited buffered I/O entry points."""
        raw = BytesIO(b"first\nsecond\n")
        with functions._ModeBuffer(raw, "rb") as reader:
            self.assertTrue(reader.readable())
            self.assertFalse(reader.writable())
            self.assertTrue(reader.seekable())
            self.assertEqual(reader.readlines(), [b"first\n", b"second\n"])
            for operation, arguments in (
                (reader.writelines, ([b"forbidden"],)),
                (reader.truncate, (0,)),
                (reader.detach, ()),
            ):
                with (
                    self.subTest(operation=operation.__name__),
                    self.assertRaises(UnsupportedOperation),
                ):
                    operation(*arguments)
        self.assertTrue(raw.closed)
        reader.close()
        with self.assertRaises(ValueError):
            reader.readable()
        with functions._ModeBuffer(BytesIO(), "wb") as writer:
            for operation, arguments in (
                (writer.read1, (1,)),
                (writer.readinto, (bytearray(1),)),
                (writer.readinto1, (bytearray(1),)),
                (writer.readline, ()),
                (writer.readlines, ()),
            ):
                with (
                    self.subTest(operation=operation.__name__),
                    self.assertRaises(UnsupportedOperation),
                ):
                    operation(*arguments)
        with functions._ModeBuffer(BytesIO(b"initial"), "ab+") as appender:
            appender.seek(0)
            appender.writelines([b"1", b"2"])
            appender.seek(0)
            self.assertEqual(appender.read(), b"initial12")

    async def testSuccessfulUploadDoesNotInheritAnUnrelatedException(self) -> None:
        """Propagate buffer close failures when only the caller handled an error."""
        for kind in _DRIVERS:
            with self.subTest(driver=kind.__name__):
                buffer = BytesIO()
                self.addCleanup(buffer.close)
                close_error = OSError("The controlled buffer close failed.")
                uploads = []

                def upload(
                    *args: object,
                    _uploads: list = uploads,
                    **kwargs: object,
                ) -> None:
                    """Consume the successful upload through the driver's protocol."""
                    handle = kwargs["data"] if "data" in kwargs else args[0]
                    _uploads.append(handle.read())

                driver = _upload_driver(kind, upload)
                with (
                    patch(
                        "orionis.storage.buffering.tempfile.SpooledTemporaryFile",
                        return_value=buffer,
                    ),
                    patch.object(buffer, "close", side_effect=close_error),
                    patch("orionis.failure.runtime.capture_nowait") as capture,
                ):
                    try:
                        message = "An unrelated caller operation failed."
                        raise ValueError(message)
                    except ValueError:
                        with self.assertRaises(OSError) as raised:
                            await driver.writeStream("object", _payload())
                    self.assertIs(raised.exception, close_error)
                    self.assertEqual(uploads, [b"payload"])
                    capture.assert_not_called()
