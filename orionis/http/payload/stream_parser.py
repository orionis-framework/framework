from __future__ import annotations
from asyncio import CancelledError, create_task, shield, to_thread
from contextlib import suppress
from typing import TYPE_CHECKING
from orionis.http.payload.contracts.stream_parser import IMultipartStreamParser
from orionis.http.payload.form_data import FormData
from orionis.http.payload.part import MultipartPart

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, AsyncIterator, Callable

# Integer constants for the parser state machine.
_STATE_SEARCH_BOUNDARY: int = 0
_STATE_READ_HEADERS: int = 1
_STATE_READ_BODY: int = 2
_STATE_FINISHED: int = 3
_DELIMITER_INVALID: int = -2

# Byte values for RFC 2046 protocol characters.
_BYTE_DASH: int = ord("-")

async def complete_in_thread[T](function: Callable[..., T], *args: object) -> T:
    """
    Run a blocking function in a worker thread without losing cancellation state.

    Parameters
    ----------
    function : Callable[..., T]
        Function to execute in a worker thread.
    *args : object
        Positional arguments passed to the function.

    Returns
    -------
    T
        The result returned by the function.
    """
    task = create_task(to_thread(function, *args))
    try:
        return await shield(task)
    except CancelledError:
        with suppress(CancelledError):
            await task
        raise


class MultipartStreamParser(IMultipartStreamParser):
    """Parse a multipart byte stream into form fields and uploaded files."""

    __slots__ = (
        "_atStart",
        "_currentPart",
        "_eof",
        "_headerSearch",
        "_paddingEnd",
        "_paddingStart",
        "boundary",
        "buffer",
        "current_part_size",
        "fields_count",
        "files_count",
        "max_fields",
        "max_files",
        "max_header_size",
        "max_part_size",
        "memory_threshold",
        "stream",
    )

    def __init__(  # noqa: PLR0913
        self,
        stream: AsyncIterable[bytes],
        boundary: bytes,
        *,
        max_files: int = 1000,
        max_fields: int = 1000,
        max_part_size: int = 1024 * 1024 * 10,
        memory_threshold: int = 1024 * 1024,
        max_header_size: int = 64 * 1024,
    ) -> None:
        """
        Initialize a new ``MultipartStreamParser`` instance.

        Parameters
        ----------
        stream : AsyncIterable[bytes]
            Async byte stream produced by the transport layer.
        boundary : bytes
            Raw multipart boundary token (without leading ``--``).
        max_files : int, optional
            Maximum number of file parts accepted (default 1 000).
        max_fields : int, optional
            Maximum number of field parts accepted (default 1 000).
        max_part_size : int, optional
            Maximum byte size of a single part (default 10 MiB).
        memory_threshold : int, optional
            Bytes before a file part spills to disk (default 1 MiB).

        max_header_size : int, optional
            Maximum byte size of the MIME headers for each part (default 64 KiB).

        Returns
        -------
        None
        """
        if not boundary:
            error_msg = "Missing multipart boundary"
            raise ValueError(error_msg)
        # Store the async stream for deferred consumption.
        self.stream = stream
        # Build the RFC 2046 delimiter (boundary prefixed with "--").
        self.boundary = b"--" + boundary
        # Allocate the working buffer for incoming byte chunks.
        self.buffer = bytearray()
        # Apply resource-exhaustion limits.
        self.max_files = max_files
        self.max_fields = max_fields
        self.max_header_size = max_header_size
        self.max_part_size = max_part_size
        self.memory_threshold = memory_threshold
        # Initialize runtime counters to zero.
        self.files_count = 0
        self.fields_count = 0
        self.current_part_size = 0
        self._atStart = True
        self._eof = False
        self._headerSearch = 0
        self._paddingStart = -1
        self._paddingEnd = 0
        self._currentPart: MultipartPart | None = None

    def _discardPrefix(self, length: int) -> None:
        """
        Discard consumed bytes and realign the delimiter padding cursor.

        Parameters
        ----------
        length : int
            Number of leading bytes to remove from the buffer.
        """
        if not length:
            return
        del self.buffer[:length]
        if self._paddingStart >= length:
            self._paddingStart -= length
            self._paddingEnd -= length
        else:
            self._paddingStart = -1
            self._paddingEnd = 0

    def _delimiterEnd(self, start: int) -> int:
        """
        Resolve the end of a multipart delimiter line.

        Parameters
        ----------
        start : int
            Offset where the boundary candidate begins.

        Returns
        -------
        int
            End offset for a complete delimiter, ``-1`` for an incomplete one,
            or ``-2`` for an invalid boundary.
        """
        buf = self.buffer
        end = start
        closing = buf.startswith(b"--", end)
        if closing:
            end += 2
        if self._paddingStart == start:
            end = max(end, self._paddingEnd)
        while end < len(buf) and buf[end] in (32, 9):
            end += 1
        self._paddingStart = start
        self._paddingEnd = end
        if end - start > self.max_header_size:
            error_msg = "Multipart boundary line exceeds maximum"
            raise ValueError(error_msg)
        if buf.startswith(b"\r\n", end):
            return end + 2
        if closing and self._eof and end == len(buf):
            return end
        if not self._eof and (
            end == len(buf)
            or (end + 1 == len(buf) and buf[end] in (13, 45))
        ):
            return -1
        return _DELIMITER_INVALID

    def _findBoundary(self, marker: bytes) -> tuple[int, int]:
        """
        Find a complete multipart delimiter or an incomplete suffix.

        Parameters
        ----------
        marker : bytes
            Boundary sequence to search for in the active buffer.

        Returns
        -------
        tuple[int, int]
            Pair containing the delimiter start offset and its end offset.
        """
        buf = self.buffer
        start = 0
        while True:
            index = buf.find(marker, start)
            if index == -1:
                return -1, -1
            end = self._delimiterEnd(index + len(marker))
            if end != _DELIMITER_INVALID:
                return index, end
            start = index + 1

    async def _writePart(self, part: MultipartPart, length: int) -> None:
        """
        Write a buffer prefix into the active part and enforce size limits.

        Parameters
        ----------
        part : MultipartPart
            Current multipart part being populated.
        length : int
            Number of bytes to append from the current buffer.
        """
        size = self.current_part_size + length
        if size > self.max_part_size:
            error_msg = "Part size exceeds maximum"
            raise ValueError(error_msg)
        if length:
            with memoryview(self.buffer)[:length] as chunk:
                if part.is_file and part.data.requiresDiskWrite(length):
                    await complete_in_thread(part.write, chunk)
                else:
                    part.write(chunk)
        self.current_part_size = size

    def _newPart(self, header_end: int) -> MultipartPart:
        """
        Create a multipart part from the parsed MIME headers.

        Parameters
        ----------
        header_end : int
            Offset where the header block ends within the buffer.

        Returns
        -------
        MultipartPart
            Initialized multipart part with its metadata and body buffer.
        """
        headers: dict[str, str] = {}
        for line in self.buffer[:header_end].decode("latin-1").split("\r\n"):
            key, separator, value = line.partition(":")
            if separator:
                headers[key.strip().lower()] = value.strip()
        part = MultipartPart(headers, self.memory_threshold)
        try:
            if part.name is None:
                error_msg = "Part missing name attribute"
                raise ValueError(error_msg)
            if part.is_file:
                if self.files_count >= self.max_files:
                    error_msg = "Too many files"
                    raise ValueError(error_msg)
                self.files_count += 1
            else:
                if self.fields_count >= self.max_fields:
                    error_msg = "Too many fields"
                    raise ValueError(error_msg)
                self.fields_count += 1
        except BaseException:
            if part.is_file:
                part.data.close()
            raise
        self.current_part_size = 0
        return part

    def _searchBoundary(self, body_marker: bytes) -> int:
        """
        Search for the next multipart boundary and decide the parser state.

        Parameters
        ----------
        body_marker : bytes
            Delimiter sequence used to terminate a body segment.

        Returns
        -------
        int
            Next parser state to run.
        """
        buf = self.buffer
        boundary = self.boundary
        marker = boundary if self._atStart else body_marker
        index, delimiter_end = self._findBoundary(marker)
        if self._atStart and index > 0:
            index, delimiter_end = self._findBoundary(body_marker)
            marker = body_marker
        if index == -1:
            tail_size = len(body_marker) + 1
            if len(buf) > tail_size:
                self._discardPrefix(len(buf) - tail_size)
                self._atStart = False
            return _STATE_SEARCH_BOUNDARY
        if delimiter_end == -1:
            if index:
                self._discardPrefix(index)
            self._atStart = marker is boundary
            return _STATE_SEARCH_BOUNDARY
        boundary_end = index + len(marker)
        if buf[boundary_end] == _BYTE_DASH:
            return _STATE_FINISHED
        self._discardPrefix(delimiter_end)
        self._headerSearch = 0
        return _STATE_READ_HEADERS

    def _readHeaders(self) -> MultipartPart | None:
        """
        Read a complete MIME header block for the next multipart part.

        Returns
        -------
        MultipartPart | None
            The initialized part when headers are complete, otherwise ``None``.
        """
        buf = self.buffer
        header_end = buf.find(b"\r\n\r\n", self._headerSearch)
        if header_end == -1:
            if len(buf) > self.max_header_size + 3:
                error_msg = "Multipart headers exceed maximum"
                raise ValueError(error_msg)
            self._headerSearch = max(0, len(buf) - 3)
            return None
        if header_end > self.max_header_size:
            error_msg = "Multipart headers exceed maximum"
            raise ValueError(error_msg)
        part = self._newPart(header_end)
        self._currentPart = part
        self._discardPrefix(header_end + 4)
        return part

    async def _finishPart(self, part: MultipartPart) -> object:
        """
        Finalize a part body or decode transfer-encoded file content.

        Parameters
        ----------
        part : MultipartPart
            Part whose content should be finalized.

        Returns
        -------
        object
            Finalized value for the form field or uploaded file.
        """
        encoding = part.headers.get("content-transfer-encoding", "").strip().lower()
        if (
            part.is_file
            and encoding in ("base64", "quoted-printable")
            and part.data.requiresDiskWrite()
        ):
            return await complete_in_thread(part.finalize)
        return part.finalize()

    async def _receiveChunk(self, stream: AsyncIterator[bytes]) -> bool:
        """
        Read the next chunk from the stream and track end-of-stream.

        Parameters
        ----------
        stream : AsyncIterator[bytes]
            Async byte stream providing incoming chunks.

        Returns
        -------
        bool
            ``True`` when more data is available, otherwise ``False``.
        """
        if self._eof:
            return False
        try:
            chunk = await anext(stream)
        except StopAsyncIteration:
            self._eof = True
        else:
            self.buffer.extend(chunk)
        return True

    async def _consumeBody(
        self,
        current_part: MultipartPart,
        form_items: list[tuple[str, object]],
        body_marker: bytes,
        tail_size: int,
    ) -> tuple[int, MultipartPart | None]:
        """
        Consume a body segment and advance the parser to the next state.

        Parameters
        ----------
        current_part : MultipartPart
            Part being read from the incoming multipart stream.
        form_items : list[tuple[str, object]]
            Accumulated form values collected so far.
        body_marker : bytes
            Boundary marker used to detect the end of a body section.
        tail_size : int
            Minimum trailing bytes required to recognize an incomplete boundary.

        Returns
        -------
        tuple[int, MultipartPart | None]
            Parser state and the current part after processing the segment.
        """
        buf = self.buffer
        index, delimiter_end = self._findBoundary(body_marker)
        if delimiter_end == -1:
            length = index if index != -1 else max(0, len(buf) - tail_size)
            await self._writePart(current_part, length)
            self._discardPrefix(length)
            return _STATE_READ_BODY, current_part

        await self._writePart(current_part, index)
        value = await self._finishPart(current_part)
        form_items.append((current_part.name, value))
        self._currentPart = None
        self._discardPrefix(index + 2)
        self._atStart = True
        return _STATE_SEARCH_BOUNDARY, None

    async def _advanceState(
        self,
        state: int,
        current_part: MultipartPart | None,
        form_items: list[tuple[str, object]],
        body_marker: bytes,
        tail_size: int,
    ) -> tuple[int, MultipartPart | None, bool]:
        """
        Advance the parser according to the current state.

        Parameters
        ----------
        state : int
            Current parser state.
        current_part : MultipartPart | None
            Current part being streamed.
        form_items : list[tuple[str, object]]
            Accumulated form values collected so far.
        body_marker : bytes
            Boundary marker used to detect body terminations.
        tail_size : int
            Minimum trailing bytes required to recognize an incomplete boundary.

        Returns
        -------
        tuple[int, MultipartPart | None, bool]
            Next state, part pointer, and whether the loop should continue.
        """
        if state == _STATE_SEARCH_BOUNDARY:
            next_state = self._searchBoundary(body_marker)
            return next_state, current_part, next_state != _STATE_SEARCH_BOUNDARY

        if state == _STATE_READ_HEADERS:
            part = self._readHeaders()
            if part is None:
                return _STATE_READ_HEADERS, current_part, False
            return _STATE_READ_BODY, part, True

        if current_part is None:
            error_msg = "Missing multipart part"
            raise ValueError(error_msg)
        next_state, next_part = await self._consumeBody(
            current_part,
            form_items,
            body_marker,
            tail_size,
        )
        return next_state, next_part, next_state != _STATE_READ_BODY

    async def _parseParts(self, form_items: list[tuple[str, object]]) -> FormData:
        """
        Parse all parts until the multipart stream ends or fails.

        Parameters
        ----------
        form_items : list[tuple[str, object]]
            Accumulated form values collected so far.

        Returns
        -------
        FormData
            Parsed form data container for all field and file parts.
        """
        state = _STATE_SEARCH_BOUNDARY
        body_marker = b"\r\n" + self.boundary
        tail_size = len(body_marker) + 1
        stream = aiter(self.stream)
        current_part: MultipartPart | None = None

        while await self._receiveChunk(stream):
            while True:
                state, current_part, should_continue = await self._advanceState(
                    state,
                    current_part,
                    form_items,
                    body_marker,
                    tail_size,
                )
                if not should_continue:
                    break
                if state == _STATE_FINISHED:
                    return FormData(form_items)
        error_msg = "Incomplete multipart body"
        raise ValueError(error_msg)

    async def parse(self) -> FormData:
        """
        Parse the multipart stream and return the collected form data.

        Returns
        -------
        FormData
            Container with all parsed field values and uploaded files.
        """
        form_items: list[tuple[str, object]] = []
        try:
            return await self._parseParts(form_items)
        except BaseException:
            current_part = self._currentPart
            if current_part is not None and current_part.is_file:
                current_part.data.close()
            for _, value in form_items:
                if not isinstance(value, str):
                    value.close()
            raise
