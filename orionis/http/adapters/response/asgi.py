from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING
from orionis.http.adapters.response.contracts.response import ResponseAdapter
from orionis.http.responses import FileResponse, Response

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Awaitable, Callable
    from pathlib import Path
    from typing import ClassVar
    from orionis.http.adapters.request.contracts.transport import TransportAdapter

class ASGIResponseAdapter(ResponseAdapter):

    RESPONSE_START = "http.response.start"
    RESPONSE_BODY = "http.response.body"

    # Reusable event dict for the terminal empty body message sent at stream end.
    _FINAL_BODY: ClassVar[dict[str, object]] = {
        "type": "http.response.body",
        "body": b"",
        "more_body": False,
    }

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

        # Build the raw headers list; extended in-place for partial content responses.
        headers: list[tuple[bytes, bytes]] = response.getRawHeaders()

        # HEAD requests must receive an empty body.
        if method == "HEAD":
            self.__ensureContentLength(headers, response)
            await send({
                "type": self.RESPONSE_START,
                "status": status,
                "headers": headers,
            })
            await send(self._FINAL_BODY)
            await response.runBackground()
            return

        # Handle FileResponse with optional byte-range support.
        if isinstance(response, FileResponse):
            file_size: int = response.getFileSize()
            range_values: tuple[int, int] | None = self.__parseRange(
                adapter, file_size,
            )

            if range_values:
                start, end = range_values
                # Extend the existing headers list with byte-encoded range fields.
                headers.append((
                    b"content-range",
                    f"bytes {start}-{end - 1}/{file_size}".encode("latin-1"),
                ))
                headers.append((b"accept-ranges", b"bytes"))
                await send({
                    "type": self.RESPONSE_START,
                    "status": 206,
                    "headers": headers,
                })
                async for chunk in self.__fileRangeIterator(
                    response.getPath(), start, end,
                ):
                    await send({
                        "type": self.RESPONSE_BODY,
                        "body": chunk,
                        "more_body": True,
                    })
            else:
                await send({
                    "type": self.RESPONSE_START,
                    "status": status,
                    "headers": headers,
                })
                async for chunk in response.getStream():
                    await send({
                        "type": self.RESPONSE_BODY,
                        "body": chunk,
                        "more_body": True,
                    })

            await send(self._FINAL_BODY)
            await response.runBackground()
            return

        # Stream the response body chunk by chunk when available.
        if response.hasStream():
            await send({
                "type": self.RESPONSE_START,
                "status": status,
                "headers": headers,
            })

            async for chunk in response.getStream():
                await send({
                    "type": self.RESPONSE_BODY,
                    "body": chunk,
                    "more_body": True,
                })

            await send(self._FINAL_BODY)
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

        def _open_and_seek() -> object:
            f = path.open("rb")
            f.seek(start)
            return f

        file = await loop.run_in_executor(None, _open_and_seek)
        try:
            while remaining > 0:
                to_read = min(chunk_size, remaining)
                chunk: bytes = await loop.run_in_executor(
                    None, file.read, to_read,
                )
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
        finally:
            await loop.run_in_executor(None, file.close)

    def __parseRange(
        self,
        adapter: TransportAdapter,
        file_size: int,
    ) -> tuple[int, int] | None:
        """
        Parse the Range header from the incoming request.

        Parameters
        ----------
        adapter : TransportAdapter
            Transport adapter providing request headers.
        file_size : int
            Total size of the file in bytes.

        Returns
        -------
        tuple of int or None
            A (start, end) byte range if the header is valid,
            otherwise None.
        """
        range_header: str | None = adapter.headers().get("range")
        if not range_header:
            return None

        # Only the "bytes" range unit is supported per RFC 7233.
        if not range_header.startswith("bytes="):
            return None

        try:
            # Parse the range start and end from the "bytes=N-M" format.
            start_str, end_str = range_header[6:].split("-", 1)

            start: int = int(start_str) if start_str else 0
            end: int = int(end_str) + 1 if end_str else file_size

            # Clamp range boundaries to valid file bounds.
            start = max(0, start)
            end = min(end, file_size)

            if start >= end:
                return None

            return start, end

        except ValueError:
            # Return None for malformed Range header values.
            return None
