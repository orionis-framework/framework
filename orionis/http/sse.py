from __future__ import annotations
import asyncio
from collections.abc import AsyncIterable, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, cast
from orionis.http.adapters.response.streams import await_cleanup

if TYPE_CHECKING:
    from asyncio import Future
    from collections.abc import AsyncIterator, Iterator

def _encode_data(data: str) -> bytes:
    """
    Encode a text payload as one UTF-8 server-sent event.

    Parameters
    ----------
    data : str
        Payload whose CRLF and CR separators are normalized to LF.

    Returns
    -------
    bytes
        Data fields with explicit empty lines and a terminating empty line.
    """
    normalized = data.replace("\r\n", "\n").replace("\r", "\n")
    return ("data: " + normalized.replace("\n", "\ndata: ") + "\n\n").encode(
        "utf-8",
    )

@dataclass(frozen=True, slots=True, kw_only=True)
class ServerSentEvent:
    """
    Represent one immutable UTF-8 server-sent event.

    Parameters
    ----------
    data : str | None, optional
        Text payload; serialize structured values explicitly before passing them.
    event : str | None, optional
        Single-line event name.
    id : str | None, optional
        Single-line cursor without NUL characters.
    retry : int | None, optional
        Non-negative reconnection delay in milliseconds; booleans are rejected.
    comment : str | None, optional
        Comment text, including manual heartbeat messages.
    """

    data: str | None = None
    event: str | None = None
    id: str | None = None
    retry: int | None = None
    comment: str | None = None

    def __post_init__(self) -> None:
        """
        Validate field types and prevent single-line field injection.

        Returns
        -------
        None
            Validate immutable event fields before the event can be used.

        Raises
        ------
        TypeError
            If text fields are not strings or retry is not a non-boolean integer.
        ValueError
            If retry is negative, event/id contain newlines, or id contains NUL.
        """
        for name in ("data", "event", "id", "comment"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                error_msg = f"ServerSentEvent {name} must be a string or None"
                raise TypeError(error_msg)
        for name in ("event", "id"):
            value = getattr(self, name)
            if value is not None and ("\r" in value or "\n" in value):
                error_msg = f"ServerSentEvent {name} must not contain newlines"
                raise ValueError(error_msg)
        if self.id is not None and "\0" in self.id:
            error_msg = "ServerSentEvent id must not contain NUL"
            raise ValueError(error_msg)
        if self.retry is not None:
            self._validateRetry()

    def _validateRetry(self) -> None:
        """
        Require a nonnegative integer for an explicitly supplied retry delay.

        Returns
        -------
        None
            Accept the retry delay without coercing it.

        Raises
        ------
        TypeError
            If the retry delay is not a non-boolean integer.
        ValueError
            If the retry delay is negative.
        """
        retry = self.retry
        if isinstance(retry, bool) or not isinstance(retry, int):
            error_msg = "ServerSentEvent retry must be an integer or None"
            raise TypeError(error_msg)
        if retry < 0:
            error_msg = "ServerSentEvent retry must not be negative"
            raise ValueError(error_msg)

    def encode(self) -> bytes:
        """
        Encode the event as UTF-8 fields followed by one empty line.

        Returns
        -------
        bytes
            SSE frame with CRLF/CR normalized to LF in multiline fields.
        """
        lines: list[str] = []
        if self.comment is not None:
            comment = self.comment.replace("\r\n", "\n").replace("\r", "\n")
            lines.append(": " + comment.replace("\n", "\n: "))
        if self.event is not None:
            lines.append(f"event: {self.event}")
        if self.id is not None:
            lines.append(f"id: {self.id}")
        if self.retry is not None:
            lines.append(f"retry: {self.retry}")
        if self.data is not None:
            data = self.data.replace("\r\n", "\n").replace("\r", "\n")
            lines.append("data: " + data.replace("\n", "\ndata: "))
        return ("\n".join(lines) + "\n\n").encode("utf-8")

class _EventStreamIterator:
    """Encode an owned event source without prefetching or buffering events."""

    __slots__ = ("_asynchronous", "_close_task", "_iterator", "_source")

    def __init__(
        self,
        source: AsyncIterable[ServerSentEvent | str] | Iterable[ServerSentEvent | str],
    ) -> None:
        """
        Retain a source without starting its iterator.

        Parameters
        ----------
        source : AsyncIterable[ServerSentEvent | str] | Iterable[ServerSentEvent | str]
            Event source owned until the response adapter closes this wrapper.

        Returns
        -------
        None
            Retain the source without allocating tasks or calling its iterator.

        Raises
        ------
        TypeError
            If the source does not support synchronous or asynchronous iteration.
        """
        self._asynchronous = isinstance(source, AsyncIterable)
        if not self._asynchronous and not isinstance(source, Iterable):
            error_msg = (
                "EventStreamResponse content must be "
                "AsyncIterable[ServerSentEvent | str] "
                "or Iterable[ServerSentEvent | str]"
            )
            raise TypeError(error_msg)
        self._source: (
            AsyncIterable[ServerSentEvent | str]
            | Iterable[ServerSentEvent | str]
            | None
        ) = source
        self._close_task: Future[None] | None = None
        self._iterator: (
            AsyncIterator[ServerSentEvent | str]
            | Iterator[ServerSentEvent | str]
            | None
        ) = None

    def __aiter__(self) -> Self:
        """
        Return this single-use byte iterator.

        Returns
        -------
        Self
            The wrapper without starting the producer.
        """
        return self

    async def __anext__(self) -> bytes:
        """
        Pull and encode exactly one event when the transport is ready.

        Returns
        -------
        bytes
            One encoded SSE frame.

        Raises
        ------
        StopAsyncIteration
            If the source is exhausted or has been closed.
        TypeError
            If the next item is neither text nor a ServerSentEvent.
        """
        source = self._source
        if source is None:
            raise StopAsyncIteration
        if self._iterator is None:
            self._iterator = (
                aiter(source) if isinstance(source, AsyncIterable) else iter(source)
            )
        if self._asynchronous:
            item = await anext(
                cast("AsyncIterator[ServerSentEvent | str]", self._iterator),
            )
        else:
            try:
                item = next(cast("Iterator[ServerSentEvent | str]", self._iterator))
            except StopIteration:
                raise StopAsyncIteration from None
        if isinstance(item, str):
            return _encode_data(item)
        if not isinstance(item, ServerSentEvent):
            error_msg = "EventStreamResponse items must be ServerSentEvent or str"
            raise TypeError(error_msg)
        return item.encode()

    def _startClose(self) -> Future[None] | None:
        """
        Release source references and schedule its asynchronous finalizer.

        Returns
        -------
        Future[None] | None
            Owned asynchronous cleanup, or None after synchronous/no cleanup.
        """
        source = self._source
        if source is None:
            return None
        iterator = self._iterator
        self._source = None
        self._iterator = None
        target = source if iterator is None else iterator
        close_async = getattr(target, "aclose", None)
        if close_async is None:
            close_sync = getattr(target, "close", None)
            if close_sync is not None:
                close_sync()
            return None
        self._close_task = asyncio.ensure_future(close_async())
        return self._close_task

    async def aclose(self) -> None:
        """
        Close the owned iterator once and release its source references.

        An unstarted response closes its source without invoking ``__aiter__``.
        Synchronous generators use ``close()`` when ``aclose()`` is unavailable.
        Asynchronous cleanup completes before propagating cancellation.

        Returns
        -------
        None
            Producer cleanup completes or its exception propagates.
        """
        pending = self._close_task or self._startClose()
        if pending is None:
            return
        try:
            await await_cleanup(pending)
        finally:
            if pending.done():
                self._close_task = None
