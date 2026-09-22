from __future__ import annotations
import asyncio
from threading import Event, get_ident
from typing import TYPE_CHECKING
from orionis.http.payload import part as multipart_part
from orionis.http.payload.stream_parser import MultipartStreamParser
from orionis.http.payload.uploaded_file import UploadedFile
from orionis.test import TestCase
from tests.http._support import replace_attribute

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

_BOUNDARY = b"orionis-boundary"

class _CountingBuffer(bytearray):
    """Count indexed padding-byte reads performed by the delimiter scanner."""

    def __init__(self) -> None:
        """Create an empty byte buffer with a padding-read counter."""
        super().__init__()
        self.paddingReads = 0

    def __getitem__(self, key: int | slice) -> int | bytearray:
        """Return a byte or slice and count reads of padding characters."""
        value = super().__getitem__(key)
        if isinstance(key, int) and value in (32, 9):
            self.paddingReads += 1
        return value

async def stream_chunks(chunks: list[bytes]) -> AsyncIterator[bytes]:
    """
    Yield supplied transport chunks in order.

    Parameters
    ----------
    chunks : list[bytes]
        Consecutive transport chunks to deliver.

    Yields
    ------
    bytes
        The next transport chunk.
    """
    for chunk in chunks:
        yield chunk

def multipart_body(value: bytes, disposition: bytes = b'name="field"') -> bytes:
    """
    Build a complete one-part multipart body.

    Parameters
    ----------
    value : bytes
        Content of the multipart field or upload.
    disposition : bytes, optional
        Encoded Content-Disposition parameters.

    Returns
    -------
    bytes
        A body with one named part and a closing delimiter.
    """
    return (
        b"--" + _BOUNDARY + b"\r\nContent-Disposition: form-data; "
        + disposition + b"\r\n\r\n" + value + b"\r\n--" + _BOUNDARY + b"--\r\n"
    )

def upload_factory(
    upload: UploadedFile,
) -> Callable[[str, str | None, int], UploadedFile]:
    """
    Build a factory that returns the upload whose lifecycle is being verified.

    Parameters
    ----------
    upload : UploadedFile
        The concrete file instance to expose to the multipart parser.

    Returns
    -------
    Callable[[str, str | None, int], UploadedFile]
        A factory with the UploadedFile constructor's positional signature.
    """
    def create_upload(
        _filename: str,
        _content_type: str | None,
        _memory_threshold: int,
    ) -> UploadedFile:
        """Return the concrete upload supplied for lifecycle assertions."""
        return upload

    return create_upload

class TestMultipartStreaming(TestCase):
    """Exercise multipart framing, limits, and resource ownership."""

    async def testAcceptsEveryChunkBoundary(self) -> None:
        """Preserve fields when any delimiter or header is split in two."""
        body = multipart_body(b"value")
        for position in range(len(body) + 1):
            parser = MultipartStreamParser(
                stream_chunks([body[:position], body[position:]]), _BOUNDARY,
            )
            with self.subTest(position=position):
                self.assertEqual((await parser.parse()).get("field"), "value")

    async def testAcceptsSingleByteChunks(self) -> None:
        """Recognize boundaries and headers delivered one byte at a time."""
        body = multipart_body(b"value")
        parser = MultipartStreamParser(
            stream_chunks([body[index:index + 1] for index in range(len(body))]),
            _BOUNDARY,
        )
        self.assertEqual((await parser.parse()).get("field"), "value")

    async def testPreservesBoundaryLikeBodyContent(self) -> None:
        """Require the delimiter line prefix and suffix before ending a part."""
        value = b"start--" + _BOUNDARY + b"\r\n--" + _BOUNDARY + b"X\r\nend"
        parser = MultipartStreamParser(
            stream_chunks([multipart_body(value)]), _BOUNDARY,
        )
        self.assertEqual((await parser.parse()).get("field"), value.decode())

    async def testPreservesClosingBoundaryPrefixesInsideFields(self) -> None:
        """Require a complete closing delimiter line before ending a field."""
        value = b"head\r\n--" + _BOUNDARY + b"--not-a-delimiter\r\ntail"
        body = multipart_body(value)
        for position in range(len(body) + 1):
            parser = MultipartStreamParser(
                stream_chunks([body[:position], body[position:]]), _BOUNDARY,
            )
            with self.subTest(position=position):
                self.assertEqual((await parser.parse()).get("field"), value.decode())

    async def testAcceptsDelimiterTransportPadding(self) -> None:
        """Accept spaces and tabs before a delimiter line terminator."""
        body = multipart_body(b"value").replace(
            b"--" + _BOUNDARY + b"\r\n", b"--" + _BOUNDARY + b" \t\r\n",
        ).replace(b"--\r\n", b"-- \t\r\n")
        parser = MultipartStreamParser(
            stream_chunks([body[index:index + 1] for index in range(len(body))]),
            _BOUNDARY,
        )
        self.assertEqual((await parser.parse()).get("field"), "value")

    async def testAcceptsClosingDelimiterWithoutFinalNewline(self) -> None:
        """Recognize a closing delimiter ending at the end of the stream."""
        parser = MultipartStreamParser(
            stream_chunks([multipart_body(b"value")[:-2]]), _BOUNDARY,
        )
        self.assertEqual((await parser.parse()).get("field"), "value")

    async def testScansFragmentedDelimiterPaddingOnce(self) -> None:
        """Keep padding scans linear across prefix removal and false markers."""
        padding = b" \t" * 256
        value = b"body\r\n--" + _BOUNDARY + b"--" + padding + b"X\r\ntail"
        body = b"preamble\r\n" + multipart_body(value).replace(
            b"--" + _BOUNDARY + b"\r\n", b"--" + _BOUNDARY + padding + b"\r\n",
        ).replace(b"--\r\n", b"--" + padding + b"\r\n")
        parser = MultipartStreamParser(
            stream_chunks([body[index:index + 1] for index in range(len(body))]),
            _BOUNDARY,
        )
        buffer = _CountingBuffer()
        parser.buffer = buffer
        self.assertEqual((await parser.parse()).get("field"), value.decode())
        self.assertLess(buffer.paddingReads, len(padding) * 4)

    async def testBoundsPreambleBuffer(self) -> None:
        """Discard preamble bytes while retaining a possible delimiter prefix."""
        parser = MultipartStreamParser(stream_chunks([]), _BOUNDARY)

        async def preamble_stream() -> AsyncIterator[bytes]:
            """Yield preamble fragments and verify the retained suffix bound."""
            for _ in range(100):
                yield b"x" * 1024
                self.assertLessEqual(len(parser.buffer), len(_BOUNDARY) + 5)
            yield b"\r\n" + multipart_body(b"value")

        parser.stream = preamble_stream()
        self.assertEqual((await parser.parse()).get("field"), "value")

    async def testRejectsOversizedHeaders(self) -> None:
        """Reject an unterminated header block beyond the configured limit."""
        parser = MultipartStreamParser(
            stream_chunks([b"--" + _BOUNDARY + b"\r\n" + b"X" * 40]),
            _BOUNDARY,
            max_header_size=16,
        )
        with self.assertRaisesRegex(ValueError, "headers exceed"):
            await parser.parse()

    async def testRejectsOversizedCompletedHeaders(self) -> None:
        """Apply the header limit when the complete block arrives together."""
        parser = MultipartStreamParser(
            stream_chunks([multipart_body(b"value")]), _BOUNDARY,
            max_header_size=16,
        )
        with self.assertRaisesRegex(ValueError, "headers exceed"):
            await parser.parse()

    async def testRejectsTruncatedBodies(self) -> None:
        """Require a final delimiter before returning parsed form data."""
        body = multipart_body(b"value").split(b"\r\n--")[0]
        parser = MultipartStreamParser(stream_chunks([body]), _BOUNDARY)
        with self.assertRaisesRegex(ValueError, "Incomplete multipart"):
            await parser.parse()

    async def testRejectsOversizedParts(self) -> None:
        """Count all streamed field bytes against the part limit."""
        parser = MultipartStreamParser(
            stream_chunks([multipart_body(b"value")]), _BOUNDARY, max_part_size=4,
        )
        with self.assertRaisesRegex(ValueError, "Part size"):
            await parser.parse()

    async def testAcceptsExactPartLimit(self) -> None:
        """Exclude delimiter CRLF bytes from the part's measured size."""
        body = multipart_body(b"value")
        parser = MultipartStreamParser(
            stream_chunks([body[index:index + 1] for index in range(len(body))]),
            _BOUNDARY, max_part_size=5,
        )
        self.assertEqual((await parser.parse()).get("field"), "value")
        self.assertEqual(parser.current_part_size, 5)

    async def testRejectsFieldsBeforeReadingTheirBodies(self) -> None:
        """Enforce the field count while processing the part headers."""
        parser = MultipartStreamParser(
            stream_chunks([multipart_body(b"value")]), _BOUNDARY, max_fields=0,
        )
        with self.assertRaisesRegex(ValueError, "Too many fields"):
            await parser.parse()

    async def testClosesRejectedUpload(self) -> None:
        """Release a spooled file when its part exceeds the size limit."""
        upload = UploadedFile("file.txt", None, memory_threshold=1)
        parser = MultipartStreamParser(
            stream_chunks([multipart_body(b"value", b'name="f"; filename="f"')]),
            _BOUNDARY, max_part_size=4,
        )
        with (
            replace_attribute(multipart_part, "UploadedFile", upload_factory(upload)),
            self.assertRaisesRegex(ValueError, "Part size"),
        ):
            await parser.parse()
        self.assertTrue(upload._file.closed)

    async def testClosesUploadOnCancellation(self) -> None:
        """Release the active upload when transport consumption is cancelled."""
        upload = UploadedFile("file.txt", None)

        async def cancelled_stream() -> AsyncIterator[bytes]:
            """Deliver upload headers before cancelling transport consumption."""
            yield multipart_body(b"value", b'name="f"; filename="f"')[:-25]
            raise asyncio.CancelledError

        parser = MultipartStreamParser(cancelled_stream(), _BOUNDARY)
        with (
            replace_attribute(multipart_part, "UploadedFile", upload_factory(upload)),
            self.assertRaises(asyncio.CancelledError),
        ):
            await parser.parse()
        self.assertTrue(upload._file.closed)

    async def testRetainsSuccessfulUploadUntilFormCloses(self) -> None:
        """Transfer ownership of successful upload handles to FormData."""
        parser = MultipartStreamParser(
            stream_chunks([multipart_body(b"value", b'name="f"; filename="f"')]),
            _BOUNDARY, memory_threshold=1,
        )
        with await parser.parse() as form:
            upload = form.get("f")
            self.assertEqual(upload.read(), b"value")
            self.assertFalse(upload._file.closed)
        self.assertTrue(upload._file.closed)

    async def testRunsDiskWritesOutsideTheEventLoop(self) -> None:
        """Write a spilling upload on a worker thread while keeping its bytes."""
        upload = UploadedFile("file.txt", None, memory_threshold=1)
        original_write = upload.write
        loop_thread = get_ident()
        writer_threads: list[int] = []

        def write_chunk(
            _file: UploadedFile,
            chunk: bytes | bytearray | memoryview,
        ) -> None:
            """Record the worker identity and append the upload bytes."""
            writer_threads.append(get_ident())
            original_write(chunk)

        parser = MultipartStreamParser(
            stream_chunks([multipart_body(b"value", b'name="f"; filename="f"')]),
            _BOUNDARY,
        )
        with (
            replace_attribute(multipart_part, "UploadedFile", upload_factory(upload)),
            replace_attribute(UploadedFile, "write", write_chunk),
            await parser.parse() as form,
        ):
            self.assertEqual(form.get("f").read(), b"value")
        self.assertTrue(writer_threads)
        self.assertNotIn(loop_thread, writer_threads)

    async def testCancellationWaitsForActiveDiskWrite(self) -> None:
        """Finish a worker write before releasing its buffer and closing its file."""
        upload = UploadedFile("file.txt", None, memory_threshold=1)
        original_write = upload.write
        started = Event()
        release = Event()
        finished = Event()

        def write_chunk(
            _file: UploadedFile,
            chunk: bytes | bytearray | memoryview,
        ) -> None:
            """Wait for cancellation before completing the concrete upload write."""
            started.set()
            release.wait(5)
            original_write(chunk)
            finished.set()

        parser = MultipartStreamParser(
            stream_chunks([multipart_body(b"value", b'name="f"; filename="f"')]),
            _BOUNDARY,
        )
        with (
            replace_attribute(multipart_part, "UploadedFile", upload_factory(upload)),
            replace_attribute(UploadedFile, "write", write_chunk),
        ):
            task = asyncio.create_task(parser.parse())
            try:
                self.assertTrue(await asyncio.to_thread(started.wait, 5))
                task.cancel()
                await asyncio.sleep(0)
                self.assertFalse(upload._file.closed)
            finally:
                release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(finished.is_set())
        self.assertTrue(upload._file.closed)
