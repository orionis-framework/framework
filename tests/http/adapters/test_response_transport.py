from __future__ import annotations
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, get_ident
from types import SimpleNamespace
from typing import TYPE_CHECKING, TypedDict
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.adapters.request.rsgi import RSGITransportAdapter
from orionis.http.adapters.response.asgi import ASGIResponseAdapter
from orionis.http.adapters.response.ranges import parse_range
from orionis.http.adapters.response.rsgi import RSGIResponseAdapter
from orionis.http.responses import FileResponse, Response, StreamingResponse
from orionis.test import TestCase
from tests.http._support import replace_attribute

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Iterator
    from typing import BinaryIO

class _AsgiEvent(TypedDict, total=False):
    type: str
    status: int
    headers: list[tuple[bytes, bytes]]
    body: bytes
    more_body: bool

class _RsgiHeaders:

    def __init__(self) -> None:
        """
        Expose the header accessor required by the RSGI interface.

        Returns
        -------
        None
            No return value.
        """
        self.get_all = self.getAll

    def __iter__(self) -> Iterator[str]:
        """
        Yield the available header names.

        Returns
        -------
        Iterator[str]
            Iterator over the available header names.
        """
        return iter(("X-Test",))

    def getAll(self, _key: str) -> list[str]:
        """
        Return both values of the repeated request header.

        Parameters
        ----------
        _key : str
            Header name requested through the RSGI interface.

        Returns
        -------
        list[str]
            Values belonging to the requested header.
        """
        return ["one", "two"]

def _request(range_header: str | None = None) -> ASGITransportAdapter:
    """
    Build a GET request with an optional byte range.

    Parameters
    ----------
    range_header : str | None
        Optional Range header sent with the request.

    Returns
    -------
    ASGITransportAdapter
        Transport adapter containing the request headers.
    """
    return ASGITransportAdapter({
        "method": "GET",
        "headers": [] if range_header is None else [
            (b"range", range_header.encode("ascii")),
        ],
    })

class TestResponseTransport(TestCase):

    def testRangesCoverPrefixSuffixAndMalformedInput(self) -> None:
        """Parse one bounded interval and ignore malformed or empty intervals."""
        cases = {
            None: None, "bytes=0-2": (0, 3), "bytes=4-": (4, 10),
            "bytes=-3": (7, 10), "bytes=-20": (0, 10), "bytes=-0": None,
            "bytes=2-99": (2, 10), "bytes=10-": None, "bytes=5-2": None,
            "bytes=-": None, "bytes=1-2,4-5": None, "items=1-2": None,
            "bytes=+1-2": None, "bytes=1-+2": None,
            "bytes=" + "9" * 5000 + "-": None,
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(parse_range(value, 10), expected)
        self.assertIsNone(parse_range("bytes=0-", 0))

    def testTransportHeadersAndIpv6RemainReadable(self) -> None:
        """Expose duplicate headers and parse the final client port separator."""
        asgi = ASGITransportAdapter({
            "headers": [(b"X-Test", b"one"), (b"x-test", b"two")],
            "client": ("::1", 1234),
        })
        scope_headers = _RsgiHeaders()
        rsgi = RSGITransportAdapter(SimpleNamespace(
            headers=scope_headers, client="::1:1234",
        ))
        for adapter in (asgi, rsgi):
            self.assertEqual(adapter.headers().getAll("x-test"), ["one", "two"])
            self.assertEqual(adapter.client(), "::1")
            self.assertEqual(adapter["port"], 1234)

    async def testFileOpenRunsOutsideTheEventLoop(self) -> None:
        """Open disk streams on a worker thread."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "file.txt"
            path.write_bytes(b"abcdef")
            response = FileResponse(path, chunk_size=2)
            open_file = Path.open
            threads = []

            def record_open(file_path: Path, mode: str = "r") -> BinaryIO:
                """
                Record the worker thread before opening the file.

                Parameters
                ----------
                file_path : Path
                    Path of the file to inspect or open.
                mode : str
                    Mode passed to the original file opener.

                Returns
                -------
                BinaryIO
                    Opened binary file handle.
                """
                threads.append(get_ident())
                return open_file(file_path, mode)

            with replace_attribute(Path, "open", record_open):
                chunks = [chunk async for chunk in response.getStream()]
            self.assertEqual(chunks, [b"ab", b"cd", b"ef"])
            self.assertNotEqual(threads, [get_ident()])

    async def testCancellationDuringFileOpenClosesTheHandle(self) -> None:
        """Close a file opened by a worker after its consumer is cancelled."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "file.txt"
            path.write_bytes(b"content")
            response = FileResponse(path)
            original_open = Path.open
            loop = asyncio.get_running_loop()
            opened = asyncio.Event()
            release = Event()
            handles = []

            def delayed_open(file_path: Path, mode: str = "r") -> BinaryIO:
                """
                Open the file and wait for the worker to be released.

                Parameters
                ----------
                file_path : Path
                    Path of the file to inspect or open.
                mode : str
                    Mode passed to the original file opener.

                Returns
                -------
                BinaryIO
                    Opened binary file handle.
                """
                file = original_open(file_path, mode)
                handles.append(file)
                loop.call_soon_threadsafe(opened.set)
                release.wait(timeout=5)
                return file

            async def consume() -> list[bytes]:
                """
                Collect the response body from its asynchronous stream.

                Returns
                -------
                list[bytes]
                    Chunks collected in stream order.
                """
                return [part async for part in response.getStream()]

            with replace_attribute(Path, "open", delayed_open):
                task = asyncio.create_task(consume())
                await opened.wait()
                task.cancel()
                release.set()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            self.assertTrue(handles[0].closed)

    async def testDisconnectClosesAsgiAndRsgiIterators(self) -> None:
        """Finalize asynchronous streams when the protocol rejects a chunk."""
        for protocol_name in ("asgi", "rsgi"):
            closed = []

            async def chunks(
                record: Callable[[bool], None] = closed.append,
            ) -> AsyncIterator[bytes]:
                """
                Yield byte chunks and record when the stream is finalized.

                Parameters
                ----------
                record : Callable[[bool], None]
                    Callback recording the observed lifecycle event.

                Yields
                ------
                bytes
                    Chunks emitted before finalization.
                """
                try:
                    yield b"first"
                    yield b"second"
                finally:
                    record(True)

            async def send(event: _AsgiEvent) -> None:
                """
                Reject body chunks to simulate a disconnected client.

                Parameters
                ----------
                event : _AsgiEvent
                    Outgoing ASGI message received from the adapter.

                Returns
                -------
                None
                    No return value.
                """
                if event["type"] == "http.response.body":
                    error_msg = "disconnected"
                    raise ConnectionError(error_msg)

            async def send_bytes(_chunk: bytes) -> None:
                """
                Reject the chunk to simulate a disconnected client.

                Parameters
                ----------
                _chunk : bytes
                    Byte chunk rejected by the protocol.

                Returns
                -------
                None
                    No return value.
                """
                error_msg = "disconnected"
                raise ConnectionError(error_msg)

            response = StreamingResponse(chunks())
            with (
                self.subTest(protocol=protocol_name),
                self.assertRaises(ConnectionError),
            ):
                if protocol_name == "asgi":
                    await ASGIResponseAdapter().send(_request(), response, None, send)
                else:
                    def response_stream(
                        _status: int, _headers: list[tuple[str, str]],
                    ) -> SimpleNamespace:
                        """
                        Return a transport that rejects streamed chunks.

                        Parameters
                        ----------
                        _status : int
                            HTTP status supplied when opening the response stream.
                        _headers : list[tuple[str, str]]
                            Response headers supplied when opening the stream.

                        Returns
                        -------
                        SimpleNamespace
                            File or protocol object exposing the required operations.
                        """
                        return SimpleNamespace(send_bytes=send_bytes)

                    protocol = SimpleNamespace(response_stream=response_stream)
                    await RSGIResponseAdapter().send(_request(), response, protocol)
            self.assertEqual(closed, [True])

    async def testDisconnectClosesFileAndRangeHandles(self) -> None:
        """Close streamed files immediately after a failed protocol send."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "file.txt"
            path.write_bytes(b"content")
            original_open = Path.open
            for range_header in (None, "bytes=1-3"):
                handles = []

                def record_open(
                    file_path: Path,
                    mode: str = "r",
                    *,
                    record: Callable[[BinaryIO], None] = handles.append,
                ) -> BinaryIO:
                    """
                    Open the file and retain its handle for verification.

                    Parameters
                    ----------
                    file_path : Path
                        Path of the file to inspect or open.
                    mode : str
                        Mode passed to the original file opener.
                    record : Callable[[BinaryIO], None]
                        Callback recording the observed lifecycle event.

                    Returns
                    -------
                    BinaryIO
                        Opened binary file handle.
                    """
                    file = original_open(file_path, mode)
                    record(file)
                    return file

                async def send(event: _AsgiEvent) -> None:
                    """
                    Reject body chunks to simulate a disconnected client.

                    Parameters
                    ----------
                    event : _AsgiEvent
                        Outgoing ASGI message received from the adapter.

                    Returns
                    -------
                    None
                        No return value.
                    """
                    if event["type"] == "http.response.body":
                        error_msg = "disconnected"
                        raise ConnectionError(error_msg)

                response = FileResponse(path)
                with (
                    replace_attribute(Path, "open", record_open),
                    self.assertRaises(ConnectionError),
                ):
                    await ASGIResponseAdapter().send(
                        _request(range_header), response, None, send,
                    )
                self.assertTrue(handles[0].closed)

    async def testCancellationWaitsForFileReadBeforeClosing(self) -> None:
        """Finish a worker read before closing the same file handle."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "file.txt"
            path.write_bytes(b"content")
            response = FileResponse(path)
            original_open = Path.open
            loop = asyncio.get_running_loop()
            started = asyncio.Event()
            release = Event()
            finished = Event()
            close_states = []

            def delayed_open(file_path: Path, mode: str = "r") -> SimpleNamespace:
                """
                Open the file and expose a controlled read boundary.

                Parameters
                ----------
                file_path : Path
                    Path of the file to inspect or open.
                mode : str
                    Mode passed to the original file opener.

                Returns
                -------
                SimpleNamespace
                    File or protocol object exposing the required operations.
                """
                file = original_open(file_path, mode)

                def read(size: int) -> bytes:
                    """
                    Wait for release and read bytes from the actual file.

                    Parameters
                    ----------
                    size : int
                        Maximum number of bytes to read.

                    Returns
                    -------
                    bytes
                        Byte content read from the stream.
                    """
                    loop.call_soon_threadsafe(started.set)
                    release.wait(timeout=5)
                    try:
                        return file.read(size)
                    finally:
                        finished.set()

                def close() -> None:
                    """
                    Record whether reading finished and close the actual file.

                    Returns
                    -------
                    None
                        No return value.
                    """
                    close_states.append(finished.is_set())
                    file.close()

                return SimpleNamespace(read=read, close=close)

            async def consume() -> list[bytes]:
                """
                Collect the response body from its asynchronous stream.

                Returns
                -------
                list[bytes]
                    Chunks collected in stream order.
                """
                return [part async for part in response.getStream()]

            with replace_attribute(Path, "open", delayed_open):
                task = asyncio.create_task(consume())
                await started.wait()
                task.cancel()
                await asyncio.sleep(0)
                self.assertFalse(task.done())
                release.set()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            self.assertEqual(close_states, [True])

    async def testAsgiRangeUsesPartialContentLength(self) -> None:
        """Send only the requested suffix with matching length metadata."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "file.txt"
            path.write_bytes(b"0123456789")
            events = []

            async def send(event: _AsgiEvent) -> None:
                """
                Record the outgoing ASGI event.

                Parameters
                ----------
                event : _AsgiEvent
                    Outgoing ASGI message received from the adapter.

                Returns
                -------
                None
                    No return value.
                """
                events.append(event)

            await ASGIResponseAdapter().send(
                _request("bytes=-3"), FileResponse(path), None, send,
            )
            self.assertEqual(events[0]["status"], 206)
            headers = dict(events[0]["headers"])
            self.assertEqual(headers[b"content-length"], b"3")
            self.assertEqual(headers[b"content-range"], b"bytes 7-9/10")
            self.assertEqual(b"".join(item["body"] for item in events[1:]), b"789")

    async def testRsgiRangeUsesPartialContentLength(self) -> None:
        """Pass the requested interval and length to the RSGI protocol."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "file.txt"
            path.write_bytes(b"0123456789")
            calls = []

            def response_file_range(
                status: int,
                headers: list[tuple[str, str]],
                filename: str,
                start: int,
                end: int,
            ) -> None:
                """
                Record the file interval submitted to the RSGI protocol.

                Parameters
                ----------
                status : int
                    HTTP status supplied for the partial response.
                headers : list[tuple[str, str]]
                    Response headers supplied to the protocol.
                filename : str
                    Path of the file sent by the protocol.
                start : int
                    Inclusive starting byte offset.
                end : int
                    Exclusive ending byte offset.

                Returns
                -------
                None
                    No return value.
                """
                calls.append((status, headers, filename, start, end))

            protocol = SimpleNamespace(response_file_range=response_file_range)
            await RSGIResponseAdapter().send(
                _request("bytes=-3"), FileResponse(path), protocol,
            )
            status, headers, _, start, end = calls[0]
            self.assertEqual((status, start, end), (206, 7, 10))
            self.assertEqual(dict(headers)["content-length"], "3")

    async def testAsgiFinalEventIsOwnedByEachRequest(self) -> None:
        """Keep event mutations local to the protocol callback receiving them."""
        adapter = ASGIResponseAdapter()
        bodies = []

        async def send(event: _AsgiEvent) -> None:
            """
            Record and mutate outgoing body messages.

            Parameters
            ----------
            event : _AsgiEvent
                Outgoing ASGI message received from the adapter.

            Returns
            -------
            None
                No return value.
            """
            if event["type"] == "http.response.body":
                bodies.append(event["body"])
                event["body"] = b"changed"

        for _ in range(2):
            await adapter.send(
                ASGITransportAdapter({"method": "HEAD"}), Response(), None, send,
            )
        self.assertEqual(bodies, [b"", b""])
