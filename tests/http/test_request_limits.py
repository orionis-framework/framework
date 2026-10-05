from __future__ import annotations
import asyncio
from threading import Event
from typing import TYPE_CHECKING
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.enums.interfaces import Interface
from orionis.http.middleware import BaseMiddleware
from orionis.http.payload import part as multipart_part
from orionis.http.payload.uploaded_file import UploadedFile
from orionis.http.request import Request
from orionis.test import TestCase
from tests.http.payload.test_body_limits import _BodyReceive, _RsgiBody
from tests.http.payload.test_stream_parser import (
    _BOUNDARY,
    multipart_body,
    upload_factory,
)
from tests.http.test_kernel import (
    _StubRsgiProtocol,
    _StubRsgiScope,
    boot_kernel,
    dispatch,
    make_asgi_scope,
    receive_empty,
    send_noop,
)
from tests.http.test_support import replace_attribute

if TYPE_CHECKING:
    from orionis.http.middleware import NextCallable
    from orionis.http.responses import Response

class _BodyReader(BaseMiddleware):
    """Consume the body using the kernel-created request and its limits."""

    __slots__ = ()

    async def handle(self, request: Request, call_next: NextCallable) -> Response:
        """Read the body before proceeding to the fixture handler.

        Parameters
        ----------
        request : Request
            Kernel-created request.
        call_next : NextCallable
            Next middleware continuation.

        Returns
        -------
        Response
            Handler response when body limits permit it.
        """
        await request.body()
        return await call_next()

class _FormReader(BaseMiddleware):
    """Retain a parsed upload to inspect its deterministic kernel cleanup."""

    __slots__ = ("upload",)

    def __init__(self) -> None:
        """Initialize an empty upload reference.

        Returns
        -------
        None
            Prepare the request consumption recorder.
        """
        self.upload: UploadedFile | None = None

    async def handle(self, request: Request, call_next: NextCallable) -> Response:
        """Read multipart form content and retain the uploaded file.

        Parameters
        ----------
        request : Request
            Kernel-created request.
        call_next : NextCallable
            Next middleware continuation.

        Returns
        -------
        Response
            Handler response after parsing.
        """
        self.upload = (await request.form()).get("file")
        return await call_next()

class _BlockingAdapter:
    """Block successful response delivery while allowing overload responses."""

    __slots__ = ("release", "started")

    def __init__(self) -> None:
        """Create deterministic synchronization events for admission tests.

        Returns
        -------
        None
            Prepare the transport recorder.
        """
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def send(
        self, _adapter: object, response: Response, *_transport: object,
    ) -> Response:
        """Keep an accepted request active until released or cancelled.

        Parameters
        ----------
        _adapter : object
            Request transport metadata.
        response : Response
            Response produced by the kernel.
        *_transport : object
            ASGI or RSGI transport arguments.

        Returns
        -------
        Response
            The response after transport synchronization completes.
        """
        if response.getStatusCode() != 503:
            self.started.set()
            await self.release.wait()
        return response

class TestKernelBodyLimits(TestCase):
    """Verify limits are effective through complete kernel request lifecycles."""

    async def testRejectsDeclaredOversizeBeforeReadingTheTransport(self) -> None:
        """Return 413 for oversized declarations without allocating request bytes.

        Returns
        -------
        None
            Confirm rejection applies even to a handler that ignores the body.
        """
        kernel, _app, _responses, catch = await boot_kernel(
            body_limits={"max_body_size": 4},
        )
        receive = _BodyReceive([b"hello"])
        response = await kernel.handleASGI(
            make_asgi_scope("/api", headers=[(b"content-length", b"5")]),
            receive,
            send_noop,
        )
        self.assertEqual(response.getStatusCode(), 413)
        self.assertEqual(receive.calls, 0)
        self.assertEqual(catch.handled, [])

    async def testRejectsMalformedAndAmbiguousLengthHeaders(self) -> None:
        """Return 400 for invalid, duplicated or conflicting request framing.

        Returns
        -------
        None
            Ensure malformed framing cannot bypass declared body limits.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        headers_list = (
            [(b"content-length", b"-1")],
            [(b"content-length", b"1x")],
            [(b"content-length", b"1"), (b"content-length", b"1")],
            [(b"content-length", b"1"), (b"transfer-encoding", b"chunked")],
        )
        for headers in headers_list:
            with self.subTest(headers=headers):
                response = await dispatch(kernel, "/api", headers=headers)
                self.assertEqual(response.getStatusCode(), 400)

    async def testRejectsAnUnboundedIntegerDeclarationWithoutParsingIt(self) -> None:
        """Return 413 for a huge decimal header instead of hitting integer limits.

        Returns
        -------
        None
            Exercise length comparison without expensive integer conversion.
        """
        kernel, _app, _responses, catch = await boot_kernel()
        response = await dispatch(
            kernel, "/api", headers=[(b"content-length", b"9" * 5000)],
        )
        self.assertEqual(response.getStatusCode(), 413)
        self.assertEqual(catch.handled, [])

    async def testRejectsActualBytesWithAbsentOrFalseLength(self) -> None:
        """Count streamed bytes independently from untrusted declared length.

        Returns
        -------
        None
            Verify the kernel maps incremental read failures to 413.
        """
        for headers in ([], [(b"content-length", b"1")]):
            kernel, _app, _responses, catch = await boot_kernel(
                body_limits={"max_body_size": 4},
            )
            kernel._KernelHTTP__api_middleware = (_BodyReader(),)
            response = await kernel.handleASGI(
                make_asgi_scope("/api", headers=headers),
                _BodyReceive([b"12", b"345"]),
                send_noop,
            )
            self.assertEqual(response.getStatusCode(), 413)
            self.assertEqual(catch.handled, [])

    async def testRejectsBufferingAboveTheConfiguredLimit(self) -> None:
        """Wire the separate read budget through kernel-created Request objects.

        Returns
        -------
        None
            Verify buffered parsers use configured rather than constructor limits.
        """
        kernel, _app, _responses, _catch = await boot_kernel(
            body_limits={"max_body_size": 100, "max_buffer_size": 4},
        )
        kernel._KernelHTTP__api_middleware = (_BodyReader(),)
        response = await kernel.handleASGI(
            make_asgi_scope("/api"), _BodyReceive([b"12345"]), send_noop,
        )
        self.assertEqual(response.getStatusCode(), 413)

    async def testRejectsActualRsgiBytes(self) -> None:
        """Apply actual body limits and 413 mapping through the RSGI entry point.

        Returns
        -------
        None
            Confirm complete adapter parity without a Content-Length header.
        """
        kernel, _app, _responses, catch = await boot_kernel(
            body_limits={"max_body_size": 4},
        )
        kernel._KernelHTTP__api_middleware = (_BodyReader(),)
        response = await kernel.handleRSGI(
            _StubRsgiScope("/api"), _RsgiBody([b"12", b"345"]),
        )
        self.assertEqual(response.getStatusCode(), 413)
        self.assertEqual(catch.handled, [])

    async def testClosesSuccessfulUploadsAfterResponseDelivery(self) -> None:
        """Release parsed upload handles even if the handler retains references.

        Returns
        -------
        None
            Confirm requests transfer cleanup responsibility to the kernel.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        reader = _FormReader()
        kernel._KernelHTTP__api_middleware = (reader,)
        body = multipart_body(b"content", b'name="file"; filename="data"')
        response = await kernel.handleASGI(
            make_asgi_scope(
                "/api",
                headers=[
                    (b"content-type", b"multipart/form-data; boundary=" + _BOUNDARY),
                ],
            ),
            _BodyReceive([body]),
            send_noop,
        )
        self.assertEqual(response.getStatusCode(), 200)
        self.assertTrue(reader.upload._file.closed)

    async def testClosesUploadsAndReleasesAdmissionOnCancellation(self) -> None:
        """Keep streaming delivery admitted and release resources when cancelled.

        Returns
        -------
        None
            Confirm overload, cleanup and recovery through actual entry points.
        """
        kernel, app, _responses, _catch = await boot_kernel(
            body_limits={"max_concurrent_requests": 1},
        )
        adapter = _BlockingAdapter()
        kernel._KernelHTTP__asgi_adapter = adapter
        reader = _FormReader()
        kernel._KernelHTTP__api_middleware = (reader,)
        body = multipart_body(b"content", b'name="file"; filename="data"')
        task = asyncio.create_task(
            kernel.handleASGI(
                make_asgi_scope(
                    "/api",
                    headers=[
                        (
                            b"content-type",
                            b"multipart/form-data; boundary=" + _BOUNDARY,
                        ),
                    ],
                ),
                _BodyReceive([body]),
                send_noop,
            ),
        )
        await asyncio.wait_for(adapter.started.wait(), timeout=5)
        try:
            self.assertFalse(reader.upload._file.closed)
            response = await kernel.handleRSGI(
                _StubRsgiScope("/api"), _StubRsgiProtocol(),
            )
            self.assertEqual(response.getStatusCode(), 503)
            self.assertEqual(response.getHeader("retry-after"), ["1"])
            self.assertEqual(len(app.scopes), 1)
        finally:
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(reader.upload._file.closed)
        adapter.release.set()
        kernel._KernelHTTP__api_middleware = ()
        response = await kernel.handleASGI(
            make_asgi_scope("/api"), receive_empty, send_noop,
        )
        self.assertEqual(response.getStatusCode(), 200)

    async def testRepeatedCancellationWaitsForUploadBeforeLeavingScope(self) -> None:
        """Drain the upload worker before closing request resources and admission.

        Returns
        -------
        None
            Verify unfinished disk writes stay admitted across cancellations.
        """
        kernel, app, _responses, _catch = await boot_kernel(
            body_limits={"max_concurrent_requests": 1},
        )
        kernel._KernelHTTP__api_middleware = (_FormReader(),)
        upload = UploadedFile("file.txt", None, memory_threshold=1)
        original_write = upload.write
        started = Event()
        release = Event()
        finished = Event()

        def write_chunk(
            _file: UploadedFile, chunk: bytes | bytearray | memoryview,
        ) -> None:
            """Block at the worker barrier before writing the retained buffer.

            Parameters
            ----------
            _file : UploadedFile
                Concrete upload whose write method is being observed.
            chunk : bytes | bytearray | memoryview
                Parser-owned buffer retained until the disk write completes.

            Returns
            -------
            None
                Complete the write before publishing worker completion.
            """
            started.set()
            release.wait(5)
            original_write(chunk)
            finished.set()

        body = multipart_body(b"content", b'name="file"; filename="file.txt"')
        with (
            replace_attribute(multipart_part, "UploadedFile", upload_factory(upload)),
            replace_attribute(UploadedFile, "write", write_chunk),
        ):
            task = asyncio.create_task(
                kernel.handleASGI(
                    make_asgi_scope(
                        "/api",
                        headers=[
                            (
                                b"content-type",
                                b"multipart/form-data; boundary=" + _BOUNDARY,
                            ),
                        ],
                    ),
                    _BodyReceive([body]),
                    send_noop,
                ),
            )
            try:
                self.assertTrue(await asyncio.to_thread(started.wait, 5))
                for _ in range(2):
                    task.cancel()
                    await asyncio.sleep(0)
                self.assertFalse(task.done())
                self.assertFalse(upload._file.closed)
                response = await kernel.handleRSGI(
                    _StubRsgiScope("/api"), _StubRsgiProtocol(),
                )
                self.assertEqual(response.getStatusCode(), 503)
                self.assertEqual(len(app.scopes), 1)
            finally:
                release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(finished.is_set())
        self.assertTrue(upload._file.closed)
        kernel._KernelHTTP__api_middleware = ()
        response = await dispatch(kernel, "/api")
        self.assertEqual(response.getStatusCode(), 200)

    async def testCustomRequestLimitsApplyToLazyStreams(self) -> None:
        """Respect custom limits when creating Request independently of a kernel.

        Returns
        -------
        None
            Confirm manually created lazy requests remain configurable.
        """
        from orionis.foundation.config.http import HTTPBodyLimits
        from orionis.http.payload.body import PayloadTooLargeException

        request = Request(
            Interface.ASGI,
            ASGITransportAdapter(make_asgi_scope("/api")),
            receive_or_protocol=_BodyReceive([b"12345"]),
            body_limits=HTTPBodyLimits(max_body_size=4),
        )
        with self.assertRaises(PayloadTooLargeException):
            await request.body()
