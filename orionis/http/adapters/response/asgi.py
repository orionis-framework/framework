from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING
from orionis.http.adapters.response.contracts.response import ResponseAdapter
from orionis.http.adapters.response.files import complete_file_read, open_file
from orionis.http.adapters.response.ranges import parse_range
from orionis.http.responses import FileResponse, Response

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Awaitable, Callable
    from pathlib import Path
    from orionis.http.adapters.request.contracts.transport import TransportAdapter

class ASGIResponseAdapter(ResponseAdapter):

    RESPONSE_START = "http.response.start"
    RESPONSE_BODY = "http.response.body"

    __slots__ = ()

    async def send(
        self,
        adapter: TransportAdapter,
        response: Response,
        _receive: Callable[..., Awaitable[dict]],
        send: Callable[..., Awaitable[None]],
    ) -> None:
        """
        Send the HTTP response using the ASGI protocol.

        Parameters
        ----------
        adapter : TransportAdapter
            Transport adapter containing request information.
        response : Response
            Response object to be sent back to the client.
        _receive : Callable[..., Awaitable[dict]]
            Awaitable callable to receive ASGI messages (reserved for
            future use, e.g. request body reading by handlers).
        send : Callable[..., Awaitable[None]]
            Awaitable callable to send ASGI messages.

        Returns
        -------
        None
            Sends the response via ASGI protocol and returns nothing.
        """
        # Identify the server software via the Server header.
        response.setHeader("server", "Orionis ASGI")

        # Extract the HTTP status code and request method.
        status: int = response.getStatusCode()
        method: str = adapter.method()

        # Encode the response headers for ASGI messages.
        headers: list[tuple[bytes, bytes]] = response.getRawHeaders()

        # HEAD requests must receive an empty body.
        if method == "HEAD":
            self.__ensureContentLength(headers, response)
            await send({
                "type": self.RESPONSE_START,
                "status": status,
                "headers": headers,
            })
            await send({
                "type": self.RESPONSE_BODY,
                "body": b"",
                "more_body": False,
            })
            await response.runBackground()
            return

        # Select the requested file interval or the response stream.
        stream = response.getStream()
        if isinstance(response, FileResponse):
            file_size = response.getFileSize()
            range_values = parse_range(adapter.headers().get("range"), file_size)
            if range_values is not None:
                start, end = range_values
                headers = [
                    pair for pair in headers
                    if pair[0] not in {
                        b"content-length", b"content-range", b"accept-ranges",
                    }
                ]
                headers.extend((
                    (b"content-length", str(end - start).encode("ascii")),
                    (
                        b"content-range",
                        f"bytes {start}-{end - 1}/{file_size}".encode("ascii"),
                    ),
                    (b"accept-ranges", b"bytes"),
                ))
                status = 206
                stream = self.__fileRangeIterator(response.getPath(), start, end)

        # Send the selected stream one chunk at a time.
        if stream is not None:
            await send({
                "type": self.RESPONSE_START,
                "status": status,
                "headers": headers,
            })
            iterator = aiter(stream)
            try:
                async for chunk in iterator:
                    await send({
                        "type": self.RESPONSE_BODY,
                        "body": chunk,
                        "more_body": True,
                    })
            finally:
                close = getattr(iterator, "aclose", None)
                if close is not None:
                    await close()
            await send({
                "type": self.RESPONSE_BODY,
                "body": b"",
                "more_body": False,
            })
            await response.runBackground()
            return

        # Fall back to a regular buffered body response.
        body: bytes = response.getBody() or b""

        await send({"type": self.RESPONSE_START, "status": status, "headers": headers})
        await send({"type": self.RESPONSE_BODY, "body": body, "more_body": False})
        await response.runBackground()

    def __ensureContentLength(
        self,
        headers: list[tuple[bytes, bytes]],
        response: Response,
    ) -> None:
        """
        Add content-length to headers if absent, reflecting the body size.

        Parameters
        ----------
        headers : list of tuple of bytes
            Mutable headers list to append content-length into.
        response : Response
            Response object used to compute the expected body size.

        Returns
        -------
        None
            Headers list is mutated in place; no value is returned.
        """
        # Check whether a content-length header is already present.
        if response.hasHeader("content-length"):
            return
        if isinstance(response, FileResponse):
            headers.append((b"content-length", str(response.getFileSize()).encode()))
        elif not response.hasStream():
            body_len = len(response.getBody() or b"")
            headers.append((b"content-length", str(body_len).encode()))

    async def __fileRangeIterator(
        self,
        path: Path,
        start: int,
        end: int,
        chunk_size: int = 64 * 1024,
    ) -> AsyncGenerator[bytes]:
        """
        Yield file bytes within [start, end) range asynchronously.

        Parameters
        ----------
        path : Path
            Path to the file to read.
        start : int
            Byte offset to start reading from.
        end : int
            Exclusive byte offset to stop reading at.
        chunk_size : int, default=65536
            Number of bytes to read per chunk.

        Returns
        -------
        AsyncGenerator[bytes]
            Asynchronous generator yielding file chunks.
        """
        loop = asyncio.get_running_loop()
        remaining = end - start

        executor = loop.run_in_executor
        file = await open_file(path, start)
        try:
            read = file.read
            while remaining > 0:
                to_read = min(chunk_size, remaining)
                chunk = await complete_file_read(executor(None, read, to_read))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
        finally:
            await executor(None, file.close)
