from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING
from orionis.http.adapters.response.contracts.response import ResponseAdapter
from orionis.http.adapters.response.files import complete_file_read, open_file
from orionis.http.adapters.response.ranges import parse_range
from orionis.http.adapters.response.streams import close_stream, send_until_disconnect
from orionis.http.responses import EventStreamResponse, FileResponse, Response

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
    from pathlib import Path
    from orionis.http.adapters.request.contracts.transport import TransportAdapter

class ASGIResponseAdapter(ResponseAdapter):

    RESPONSE_START = "http.response.start"
    RESPONSE_BODY = "http.response.body"

    __slots__ = ()

    async def send( # NOSONAR
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
            Receive callable observed for disconnects during event streams.
            Handlers must consume required request body data before returning
            an event stream, which owns receive during response delivery.
        send : Callable[..., Awaitable[None]]
            Awaitable callable to send ASGI messages.

        Returns
        -------
        None
            Sends the response via ASGI protocol and returns nothing.

        Raises
        ------
        BaseException
            Propagate metadata or delivery failures after closing an owned SSE source.
        """
        # Identify the server software via the Server header.
        response.setHeader("server", "Orionis ASGI")

        # Extract the HTTP status code and request method.
        status: int = response.getStatusCode()
        method: str = adapter.method()

        # Encode the response headers for ASGI messages.
        try:
            headers: list[tuple[bytes, bytes]] = response.getRawHeaders()
        except BaseException as failure:
            await close_stream(response.getStream(), failure)
            raise

        # HEAD requests must receive an empty body.
        if method == "HEAD":
            await self.__sendHead(response, status, headers, send)
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
            if isinstance(response, EventStreamResponse):
                event_stream = response.getStream()
                try:
                    completed = await send_until_disconnect(
                        self.__sendStream(event_stream, status, headers, send),
                        self.__waitDisconnect(_receive),
                    )
                finally:
                    # Also cover cancellation before the sender task starts.
                    # The event stream wrapper makes repeated close a no-op.
                    await event_stream.aclose()
                if not completed:
                    return
            else:
                await self.__sendStream(aiter(stream), status, headers, send)
            if (
                response.background is not None
                or type(response).runBackground is not Response.runBackground
            ):
                await response.runBackground()
            return

        # Fall back to a regular buffered body response.
        body: bytes = response.getBody() or b""

        await send({"type": self.RESPONSE_START, "status": status, "headers": headers})
        await send({"type": self.RESPONSE_BODY, "body": body, "more_body": False})
        if (
            response.background is not None
            or type(response).runBackground is not Response.runBackground
        ):
            await response.runBackground()

    async def __sendHead(
        self,
        response: Response,
        status: int,
        headers: list[tuple[bytes, bytes]],
        send: Callable[..., Awaitable[None]],
    ) -> None:
        """
        Send HEAD framing without starting an event producer.

        Parameters
        ----------
        response : Response
            Response whose metadata is sent.
        status : int
            Response status code.
        headers : list[tuple[bytes, bytes]]
            Encoded response headers.
        send : Callable[..., Awaitable[None]]
            ASGI response writer.

        Returns
        -------
        None
            Close an unstarted event stream, then run successful background work.
        """
        self.__ensureContentLength(headers, response)
        try:
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
        finally:
            if isinstance(response, EventStreamResponse):
                await response.getStream().aclose()
        if (
            response.background is not None
            or type(response).runBackground is not Response.runBackground
        ):
            await response.runBackground()

    async def __waitDisconnect(
        self, receive: Callable[..., Awaitable[dict]],
    ) -> None:
        """
        Wait for disconnect, draining unconsumed request messages.

        Parameters
        ----------
        receive : Callable[..., Awaitable[dict]]
            ASGI receive channel, owned by the response after handler return.

        Returns
        -------
        None
            Return only when the client disconnects.

        Raises
        ------
        RuntimeError
            If the HTTP channel produces an unexpected message type.
        """
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                error_msg = "Unexpected ASGI message during event stream"
                raise RuntimeError(error_msg)

    async def __sendStream(
        self,
        iterator: AsyncIterator[bytes],
        status: int,
        headers: list[tuple[bytes, bytes]],
        send: Callable[..., Awaitable[None]],
    ) -> None:
        """
        Send and close a stream with transport backpressure.

        Parameters
        ----------
        iterator : AsyncIterator[bytes]
            Owned iterator to close even if sending headers fails.
        status : int
            Response status code.
        headers : list[tuple[bytes, bytes]]
            Encoded response headers.
        send : Callable[..., Awaitable[None]]
            ASGI response writer.

        Returns
        -------
        None
            Finish the body only after iteration and cleanup succeed.
        """
        failure = None
        try:
            await send({
                "type": self.RESPONSE_START, "status": status, "headers": headers,
            })
            async for chunk in iterator:
                await send({
                    "type": self.RESPONSE_BODY, "body": chunk, "more_body": True,
                })
        except BaseException as exc:
            failure = exc
            raise
        finally:
            await close_stream(iterator, failure)
        await send({
            "type": self.RESPONSE_BODY, "body": b"", "more_body": False,
        })

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
