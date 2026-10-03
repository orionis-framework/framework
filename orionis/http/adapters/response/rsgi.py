from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.http.adapters.response.contracts.response import ResponseAdapter
from orionis.http.adapters.response.ranges import parse_range
from orionis.http.adapters.response.streams import close_stream, send_until_disconnect
from orionis.http.responses import EventStreamResponse, FileResponse, Response

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from granian.rsgi import HTTPProtocol
    from orionis.http.adapters.request.contracts.transport import TransportAdapter

class RSGIResponseAdapter(ResponseAdapter):

    __slots__ = ()

    async def send(
        self,
        adapter: TransportAdapter,
        response: Response,
        protocol: HTTPProtocol,
    ) -> None:
        """
        Send the HTTP response using the appropriate protocol adapter.

        Parameters
        ----------
        adapter : TransportAdapter
            Transport adapter containing request information.
        response : Response
            Response object to be sent back to the client.
        protocol : HTTPProtocol
            Protocol instance used to send the response.

        Returns
        -------
        None
            Sends the response via protocol and returns nothing.

        Raises
        ------
        BaseException
            Propagate metadata or delivery failures after closing an owned SSE source.
        """
        # Identify the server software via the Server header.
        response.setHeader("server", "Orionis RSGI")

        # Extract the HTTP status code.
        status = response.getStatusCode()

        # Read response headers as name/value string tuples.
        try:
            headers: list[tuple[str, str]] = response.getStringHeaders()
        except BaseException as failure:
            await close_stream(response.getStream(), failure)
            raise

        # Send the selected response representation.
        if adapter.method() == "HEAD":
            await self.__sendHead(response, protocol, status, headers)
        elif isinstance(response, FileResponse):
            self.__sendFile(adapter, response, protocol, status, headers)
        elif response.hasStream():
            if not await self.__sendResponseStream(response, protocol, status, headers):
                return
        else:
            body = response.getBody() or b""
            if body:
                protocol.response_bytes(status, headers, body)
            else:
                protocol.response_empty(status, headers)

        if (
            response.background is not None
            or type(response).runBackground is not Response.runBackground
        ):
            await response.runBackground()

    async def __sendResponseStream(
        self,
        response: Response,
        protocol: HTTPProtocol,
        status: int,
        headers: list[tuple[str, str]],
    ) -> bool:
        """
        Deliver an ordinary stream or observe disconnects for an event stream.

        Parameters
        ----------
        response : Response
            Response owning the selected stream.
        protocol : HTTPProtocol
            RSGI response writer and disconnect notifier.
        status : int
            Response status code.
        headers : list[tuple[str, str]]
            Serialized response headers.

        Returns
        -------
        bool
            Whether delivery and cleanup completed before a client disconnect.
        """
        if not isinstance(response, EventStreamResponse):
            iterator = aiter(response.getStream())
            await self.__sendStream(iterator, protocol, status, headers)
            return True
        event_stream = response.getStream()
        try:
            return await send_until_disconnect(
                self.__sendStream(event_stream, protocol, status, headers),
                self.__waitDisconnect(protocol),
            )
        finally:
            await event_stream.aclose()

    async def __sendHead(
        self,
        response: Response,
        protocol: HTTPProtocol,
        status: int,
        headers: list[tuple[str, str]],
    ) -> None:
        """
        Send HEAD metadata without starting an event producer.

        Parameters
        ----------
        response : Response
            Response whose metadata is sent.
        protocol : HTTPProtocol
            RSGI response writer.
        status : int
            Response status code.
        headers : list[tuple[str, str]]
            Response headers.

        Returns
        -------
        None
            Close an unstarted event stream after sending the empty response.
        """
        self.__ensureContentLength(headers, response)
        try:
            protocol.response_empty(status, headers)
        finally:
            if isinstance(response, EventStreamResponse):
                await response.getStream().aclose()

    async def __waitDisconnect(self, protocol: HTTPProtocol) -> None:
        """
        Await Granian's supported HTTP client disconnect notification.

        Parameters
        ----------
        protocol : HTTPProtocol
            RSGI protocol exposing ``client_disconnect()``.

        Returns
        -------
        None
            Return when the client connection closes.
        """
        await protocol.client_disconnect()

    async def __sendStream(
        self,
        iterator: AsyncIterator[bytes],
        protocol: HTTPProtocol,
        status: int,
        headers: list[tuple[str, str]],
    ) -> None:
        """
        Send and close a stream through the existing RSGI transport.

        Parameters
        ----------
        iterator : AsyncIterator[bytes]
            Owned iterator, closed even when stream creation fails.
        protocol : HTTPProtocol
            RSGI response protocol.
        status : int
            Response status code.
        headers : list[tuple[str, str]]
            Response headers.

        Returns
        -------
        None
            Return after all bytes have been sent and cleanup succeeds.
        """
        failure = None
        try:
            transport = protocol.response_stream(status, headers)
            async for chunk in iterator:
                await transport.send_bytes(chunk)
        except BaseException as exc:
            failure = exc
            raise
        finally:
            await close_stream(iterator, failure)

    def __sendFile(
        self,
        adapter: TransportAdapter,
        response: FileResponse,
        protocol: HTTPProtocol,
        status: int,
        headers: list[tuple[str, str]],
    ) -> None:
        """
        Send a file or the byte interval selected by the request.

        Parameters
        ----------
        adapter : TransportAdapter
            Request headers used to select the file range.
        response : FileResponse
            File metadata and source path.
        protocol : HTTPProtocol
            RSGI response writer.
        status : int
            HTTP status for a complete file.
        headers : list[tuple[str, str]]
            Response headers for this request.

        Returns
        -------
        None
            The file response is handed to the protocol.
        """
        path = str(response.getPath())
        file_size = response.getFileSize()
        interval = parse_range(adapter.headers().get("range"), file_size)
        if interval is None:
            protocol.response_file(status, headers, path)
            return
        start, end = interval
        headers = [
            pair for pair in headers
            if pair[0] not in {"content-length", "content-range", "accept-ranges"}
        ]
        headers.extend((
            ("content-length", str(end - start)),
            ("content-range", f"bytes {start}-{end - 1}/{file_size}"),
            ("accept-ranges", "bytes"),
        ))
        protocol.response_file_range(206, headers, path, start, end)

    def __ensureContentLength(
        self,
        headers: list[tuple[str, str]],
        response: Response,
    ) -> None:
        """
        Add content-length to headers if absent, reflecting the body size.

        Parameters
        ----------
        headers : list of tuple of str
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
            headers.append(("content-length", str(response.getFileSize())))
        elif not response.hasStream():
            headers.append(("content-length", str(len(response.getBody() or b""))))
