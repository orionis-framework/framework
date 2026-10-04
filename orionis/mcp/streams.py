"""Lazy owned iterators which release sources even before the first read."""

import asyncio
from collections.abc import AsyncIterator, Iterator

from orionis.http.adapters.response.streams import await_cleanup


class OwnedStream[T]:
    """Join source cleanup before propagating delivery errors or cancellation."""

    __slots__ = ("_cleanup", "_closed", "_owner", "_source")

    def __init__(
        self, source: AsyncIterator[T] | Iterator[T],
        owner: OwnedStream[object] | None = None,
    ) -> None:
        """Take ownership without advancing or buffering the source."""
        self._source = source
        self._owner = owner
        self._closed = False
        self._cleanup: asyncio.Future[None] | None = None

    def __aiter__(self) -> AsyncIterator[T]:
        """Return this single-consumer iterator."""
        return self

    async def __anext__(self) -> T:
        """Advance one item and close when iteration ends for any reason."""
        if self._closed:
            await self.aclose()
            raise StopAsyncIteration
        try:
            if isinstance(self._source, AsyncIterator):
                return await anext(self._source)
            try:
                return next(self._source)
            except StopIteration:
                raise StopAsyncIteration from None
        except BaseException:
            await self.aclose()
            raise

    async def aclose(self) -> None:
        """Finish cleanup under repeated cancellation and close exactly once."""
        if self._cleanup is None:
            self._closed = True
            self._cleanup = asyncio.ensure_future(self._close_owned())
        await await_cleanup(self._cleanup)

    async def _close_owned(self) -> None:
        """Release a nested owner even when the outer iterator never started."""
        try:
            close = getattr(self._source, "aclose", None)
            if close is not None:
                await close()
            else:
                close = getattr(self._source, "close", None)
                if close is not None:
                    close()
        finally:
            if self._owner is not None:
                await self._owner.aclose()
