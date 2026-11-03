"""Provide mcp operations through ``AsyncClosable``, ``OwnedStream``."""

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Protocol
from orionis.http.adapters.response.streams import await_cleanup

class AsyncClosable(Protocol):
    """Describe the awaited close operation of an owned asynchronous source."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    async def aclose(self) -> None:
        """
        Release the resources owned by this source.

        Returns
        -------
        None
            The source has completed its close operation.
        """
        ...

class OwnedStream[T](AsyncClosable):
    """Join source cleanup before propagating delivery errors or cancellation."""

    __slots__ = ("_cleanup", "_closed", "_owner", "_source")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self, source: AsyncIterator[T] | Iterator[T],
        owner: OwnedStream[object] | None = None,
    ) -> None:
        """
        Take ownership without advancing or buffering the source.

        Parameters
        ----------
        source : collections.abc.AsyncIterator[``T``] | collections.abc.Iterator[``T``]
            Source whose values or lifecycle are consumed by this operation.
        owner : orionis.mcp.streams.OwnedStream[object] | None
            Value supplied for ``owner``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self._source = source
        """Source whose values or lifecycle are consumed by this operation."""
        self._owner = owner
        """Value supplied for ``owner``."""
        self._closed = False
        """Whether this resource has completed its close lifecycle."""
        self._cleanup: asyncio.Future[None] | None = None
        """Cleanup task shared by callers closing the owned stream."""

    def __aiter__(self) -> AsyncIterator[T]:
        """
        Return this single-consumer iterator.

        Returns
        -------
        collections.abc.AsyncIterator[``T``]
            This single-consumer iterator.
        """
        return self

    async def __anext__(self) -> T:
        """
        Advance one item and close when iteration ends for any reason.

        Returns
        -------
        ``T``
            Result of the operation described above.
        """
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
        """
        Finish cleanup under repeated cancellation and close exactly once.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        if self._cleanup is None:
            self._closed = True
            self._cleanup = asyncio.ensure_future(self._closeOwned())
        await await_cleanup(self._cleanup)

    async def _closeOwned(self) -> None:
        """
        Release a nested owner even when the outer iterator never started.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
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
