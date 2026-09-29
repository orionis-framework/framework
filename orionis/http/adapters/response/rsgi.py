from typing import TYPE_CHECKING
from orionis.http.adapters.response.contracts.response import ResponseAdapter
from orionis.http.adapters.response.ranges import parse_range
from orionis.http.responses import FileResponse, Response

if TYPE_CHECKING:
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
        """
        # Identify the server software via the Server header.
        response.setHeader("server", "Orionis RSGI")

        # Extract the HTTP status code.
        status = response.getStatusCode()

        # Read response headers as name/value string tuples.
        headers: list[tuple[str, str]] = response.getStringHeaders()

        # Send the selected response representation.
        if adapter.method() == "HEAD":
            self.__ensureContentLength(headers, response)
            protocol.response_empty(status, headers)
        elif isinstance(response, FileResponse):
            self.__sendFile(adapter, response, protocol, status, headers)
        elif response.hasStream():
            transport = protocol.response_stream(status, headers)
            iterator = aiter(response.getStream())
            try:
                async for chunk in iterator:
                    await transport.send_bytes(chunk)
            finally:
                close = getattr(iterator, "aclose", None)
                if close is not None:
                    await close()
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

    def __sendFile(
        self,
        adapter: TransportAdapter,
        response: FileResponse,
        protocol: HTTPProtocol,
        status: int,
        headers: list[tuple[str, str]],
    ) -> None:
        """Send a file or the byte interval selected by the request.

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
