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

        # HEAD requests must receive an empty body.
        if adapter.method() == "HEAD":
            self.__ensureContentLength(headers, response)
            protocol.response_empty(status, headers)
            await response.runBackground()
            return

        # Handle FileResponse with optional byte-range support.
        if isinstance(response, FileResponse):
            file_path: str = str(response.getPath())
            file_size: int = response.getFileSize()
            range_values: tuple[int, int] | None = parse_range(
                adapter.headers().get("range"), file_size,
            )

            if range_values is not None:
                start, end = range_values
                headers = [
                    pair for pair in headers
                    if pair[0] not in {
                        "content-length", "content-range", "accept-ranges",
                    }
                ]
                headers.append(("content-length", str(end - start)))
                headers.append(
                    ("content-range", f"bytes {start}-{end-1}/{file_size}"),
                )
                headers.append(("accept-ranges", "bytes"))
                protocol.response_file_range(
                    206,
                    headers,
                    file_path,
                    start,
                    end,
                )
            else:
                protocol.response_file(status, headers, file_path)

            await response.runBackground()
            return

        # Stream the response body chunk by chunk when available.
        if response.hasStream():
            transport = protocol.response_stream(status, headers)

            iterator = aiter(response.getStream())
            try:
                async for chunk in iterator:
                    await transport.send_bytes(chunk)
            finally:
                close = getattr(iterator, "aclose", None)
                if close is not None:
                    await close()

            await response.runBackground()
            return

        # Fall back to a regular buffered body response.
        body: bytes = response.getBody() or b""

        if not body:
            protocol.response_empty(status, headers)
            await response.runBackground()
            return

        # The body is already encoded; hand the bytes straight to the protocol.
        protocol.response_bytes(status, headers, body)

        await response.runBackground()

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
