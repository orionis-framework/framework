from dataclasses import fields
from inspect import signature
from typing import TYPE_CHECKING
from orionis.foundation.config.http import HTTP, HTTPBodyLimits
from orionis.http.enums.interfaces import Interface
from orionis.http.payload.body import BodyStream, PayloadTooLargeException
from orionis.http.payload.stream_parser import MultipartStreamParser
from orionis.test import TestCase
from tests.http.payload.test_stream_parser import (
    _BOUNDARY,
    multipart_body,
    stream_chunks,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class _BodyReceive:
    """Provide ASGI chunks while counting reads from the transport."""

    __slots__ = ("calls", "chunks")

    def __init__(self, chunks: list[bytes]) -> None:
        """Store chunks for deferred delivery.

        Parameters
        ----------
        chunks : list[bytes]
            Body chunks to deliver in order.

        Returns
        -------
        None
            Initialize the transport read counter.
        """
        self.chunks = iter(chunks)
        self.calls = 0

    async def __call__(self) -> dict[str, object]:
        """Deliver one chunk without buffering any additional bytes.

        Returns
        -------
        dict[str, object]
            The next ASGI request message.
        """
        self.calls += 1
        chunk = next(self.chunks, None)
        return {
            "type": "http.request",
            "body": chunk or b"",
            "more_body": chunk is not None,
        }


class _RsgiBody:
    """Expose the same chunks through RSGI asynchronous iteration."""

    __slots__ = ("chunks",)

    def __init__(self, chunks: list[bytes]) -> None:
        """Store chunks without materializing the combined request.

        Parameters
        ----------
        chunks : list[bytes]
            Transport body chunks.

        Returns
        -------
        None
            Initialize the RSGI body source.
        """
        self.chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """Yield chunks exactly once per transport iteration.

        Yields
        ------
        bytes
            The next body chunk.
        """
        for chunk in self.chunks:
            yield chunk


class TestBodyLimits(TestCase):
    """Exercise actual byte limits independently from declared Content-Length."""

    def testPayloadConstructorDefaultsMatchStaticConfiguration(self) -> None:
        """Keep public parser defaults aligned with finite configuration metadata.

        Returns
        -------
        None
            Default signatures remain stable without constructing configuration.
        """
        defaults = {
            item.name: item.metadata["default"] for item in fields(HTTPBodyLimits)
        }
        for parser in (BodyStream, MultipartStreamParser):
            for name, parameter in signature(parser).parameters.items():
                if name in defaults:
                    with self.subTest(parser=parser.__name__, field=name):
                        self.assertEqual(parameter.default, defaults[name])

    def testRejectsUnsafeConfiguration(self) -> None:
        """Reject booleans, None, strings, negative values and zero budgets.

        Returns
        -------
        None
            Confirm limits fail at configuration time.
        """
        for name in HTTPBodyLimits.__dataclass_fields__:
            for value in (True, None, "1024", -1):
                with (
                    self.subTest(name=name, value=value),
                    self.assertRaises((TypeError, ValueError)),
                ):
                    HTTPBodyLimits(**{name: value})
            if name not in ("max_files", "max_fields"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    HTTPBodyLimits(**{name: 0})
        self.assertEqual(HTTP(body_limits={"max_files": 0}).body_limits.max_files, 0)

    async def testRejectsActualStreamBytesOnBothTransports(self) -> None:
        """Reject the chunk crossing the total limit before yielding it.

        Returns
        -------
        None
            Verify ASGI and RSGI use identical byte accounting.
        """
        for interface, transport in (
            (Interface.ASGI, _BodyReceive([b"12", b"345"])),
            (Interface.RSGI, _RsgiBody([b"12", b"345"])),
        ):
            stream = BodyStream(interface, transport, max_body_size=4)
            received = []
            with (
                self.subTest(interface=interface),
                self.assertRaises(PayloadTooLargeException),
            ):
                async for chunk in stream.stream():
                    received.append(chunk)  # noqa: PERF401 - Preserve yielded prefix.
            self.assertEqual(received, [b"12"])
            self.assertTrue(stream.isConsumed)
            self.assertFalse(stream.isBuffered)

    async def testKeepsStreamingAvailableAboveBufferLimit(self) -> None:
        """Permit streaming below the total limit while forbidding oversized read.

        Returns
        -------
        None
            Separate request size from contiguous buffering size.
        """
        stream = BodyStream(
            Interface.ASGI, _BodyReceive([b"123", b"45"]), 8, max_buffer_size=4,
        )
        with self.assertRaises(PayloadTooLargeException):
            await stream.read()
        self.assertFalse(stream.isBuffered)
        streamed = BodyStream(
            Interface.ASGI, _BodyReceive([b"123", b"45"]), 8, max_buffer_size=4,
        )
        self.assertEqual([chunk async for chunk in streamed.stream()], [b"123", b"45"])

    async def testBuffersExactlyAtLimitAndReplaysWithoutTransportReads(self) -> None:
        """Cache an exact-limit body and preserve replay semantics.

        Returns
        -------
        None
            Verify repeated reads use the same bytes object.
        """
        receive = _BodyReceive([b"12", b"34"])
        stream = BodyStream(Interface.ASGI, receive, 4, max_buffer_size=4)
        body = await stream.read()
        calls = receive.calls
        self.assertIs(await stream.read(), body)
        self.assertEqual([chunk async for chunk in stream.stream()], [b"1234"])
        self.assertEqual(receive.calls, calls)

    async def testDefaultStreamAndBufferLimitsAreFinite(self) -> None:
        """Reject oversize bodies even when callers omit explicit limits.

        Returns
        -------
        None
            Confirm the default public constructor is hardened.
        """
        defaults = {
            item.name: item.metadata["default"] for item in fields(HTTPBodyLimits)
        }
        stream = BodyStream(
            Interface.ASGI, _BodyReceive([b"x" * (defaults["max_body_size"] + 1)]),
        )
        with self.assertRaises(PayloadTooLargeException):
            await anext(stream.stream())
        stream = BodyStream(
            Interface.ASGI, _BodyReceive([b"x" * (defaults["max_buffer_size"] + 1)]),
        )
        with self.assertRaises(PayloadTooLargeException):
            await stream.read()

    def testManualUnlimitedStreamRequiresExplicitOptOut(self) -> None:
        """Retain explicit None opt-outs and reject invalid direct limits.

        Returns
        -------
        None
            Preserve deliberate custom-stream compatibility.
        """
        BodyStream(Interface.ASGI, None, None, max_buffer_size=None)
        for value in (True, "1024", -1):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                BodyStream(Interface.ASGI, None, value)


class TestMultipartBudgets(TestCase):
    """Check total framing and aggregate memory beyond individual part limits."""

    async def testRejectsTotalBodyIncludingPreambleAndEpilogue(self) -> None:
        """Count discarded framing and trailing bytes in the total body limit.

        Returns
        -------
        None
            Close the epilogue early-return bypass.
        """
        body = multipart_body(b"ok")
        for chunks in ([b"prefix\r\n", body], [body, b"trailing epilogue"]):
            parser = MultipartStreamParser(
                stream_chunks(chunks), _BOUNDARY, max_body_size=len(body),
            )
            with (
                self.subTest(chunks=chunks),
                self.assertRaises(PayloadTooLargeException),
            ):
                await parser.parse()

    async def testRejectsAggregateFieldsBelowIndividualLimit(self) -> None:
        """Enforce retained field memory even when each field individually fits.

        Returns
        -------
        None
            Reject accumulated decoded field strings.
        """
        one = multipart_body(b"x" * 80)
        body = one[: -(len(_BOUNDARY) + 8)] + b"\r\n" + one
        parser = MultipartStreamParser(
            stream_chunks([body]), _BOUNDARY, max_memory_size=240,
        )
        with self.assertRaises(PayloadTooLargeException):
            await parser.parse()

    async def testRejectsLargeFieldWithoutRejectingSpilledFile(self) -> None:
        """Apply the field cap separately while spooling accepted file content.

        Returns
        -------
        None
            Confirm file payloads do not consume the retained memory budget.
        """
        parser = MultipartStreamParser(
            stream_chunks([multipart_body(b"x" * 100)]), _BOUNDARY, max_field_size=50,
        )
        with self.assertRaises(PayloadTooLargeException):
            await parser.parse()
        body = multipart_body(b"x" * 100, b'name="file"; filename="data"')
        parser = MultipartStreamParser(
            stream_chunks([body]),
            _BOUNDARY,
            max_field_size=50,
            memory_threshold=16,
            max_memory_size=32,
        )
        with await parser.parse() as form:
            upload = form.get("file")
            self.assertTrue(upload.requiresDiskWrite())
            self.assertEqual(upload.size, 100)

    async def testRejectsOversizedBoundaryBeforeConsumingTransport(self) -> None:
        """Restrict boundary length before allocating parser lookbehind buffers.

        Returns
        -------
        None
            Verify arbitrary header input cannot select an enormous tail buffer.
        """
        with self.assertRaises(ValueError):
            MultipartStreamParser(stream_chunks([]), b"x" * 71)
        parser = MultipartStreamParser(
            stream_chunks([multipart_body(b"ok")]), _BOUNDARY,
        )
        self.assertEqual((await parser.parse()).get("field"), "ok")
