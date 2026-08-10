from typing import TYPE_CHECKING
from orionis.http.adapters.response.contracts.response import ResponseAdapter
from orionis.http.response import FileResponse, Response

if TYPE_CHECKING:
    from granian.rsgi import HTTPProtocol
    from orionis.http.adapters.request.contracts.transport import TransportAdapter

class RSGIResponseAdapter(ResponseAdapter):

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

        # Convert raw bytes headers to (key, value) string tuples.
        headers: list[tuple[str, str]] = self.__convertHeaders(response)

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
            range_values: tuple[int, int] | None = self.__parseRange(
                adapter, file_size,
            )

            if range_values:
                start, end = range_values
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

            async for chunk in response.getStream():
                await transport.send_bytes(chunk)

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

    def __convertHeaders(
        self,
        response: Response,
    ) -> list[tuple[str, str]]:
        """
        Convert raw response headers to a list of string tuples.

        Parameters
        ----------
        response : Response
            Response object containing raw bytes headers.

        Returns
        -------
        list of tuple of str
            Headers represented as (key, value) string pairs.
        """
        # Build string headers directly from the internal dict, bypassing encode/decode.
        return response.getStringHeaders()

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
