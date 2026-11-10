"""Provide mcp operations through ``AsyncClosable``, ``OwnedStream``."""

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Protocol
from orionis.failure.runtime import capture
from orionis.http.adapters.response.streams import await_cleanup

def _caller_cancelled(error: BaseException, cancellations: int) -> bool:
    """
    Identify new caller cancellation while an owned cleanup was awaited.

    Parameters
    ----------
    error : BaseException
        Outcome of joining cleanup, which may itself have been cancelled.
    cancellations : int
        Caller cancellation count recorded before the owned operation.

    Returns
    -------
    bool
        Whether the outcome carries a new cancellation request for this caller.
    """
    task = asyncio.current_task()
    if not isinstance(error, asyncio.CancelledError) or task is None:
        return False
    return task.cancelling() > cancellations

class AsyncClosable(Protocol):
    """Describe the awaited close operation of an owned asynchronous source."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    async def aclose(self) -> None:
        """
        Release the resources owned by an asynchronous source.

        Returns
        -------
        None
            Complete the source's asynchronous cleanup contract.
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
        Take lazy ownership of a synchronous or asynchronous iterator.

        Parameters
        ----------
        source : AsyncIterator[``T``] or Iterator[``T``]
            Iterator whose values and cleanup lifecycle this stream owns.
        owner : orionis.mcp.streams.OwnedStream[object] or None, optional
            Nested owner to close after this source, even if iteration never begins.

        Returns
        -------
        None
            Store source and owner without advancing either iterator.
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
        Return this stream as its single-consumer asynchronous iterator.

        Returns
        -------
        collections.abc.AsyncIterator[``T``]
            This stream, without creating or advancing another iterator.
        """
        return self

    async def __anext__(self) -> T:
        """
        Return the next source item and close on exhaustion or failure.

        Returns
        -------
        ``T``
            Next value from the owned synchronous or asynchronous iterator.

        Raises
        ------
        StopAsyncIteration
            If the stream is closed or exhausted and cleanup succeeds.
        BaseException
            If iteration or cleanup fails. Preserve an iteration failure when
            cleanup also fails; surface cleanup errors after normal exhaustion.
            Genuine caller cancellation propagates after cleanup is drained.
        """
        if self._closed:
            await self.aclose()
            raise StopAsyncIteration
        task = asyncio.current_task()
        cancellations = task.cancelling() if task is not None else 0
        try:
            if cancellations:
                await asyncio.sleep(0)
            if isinstance(self._source, AsyncIterator):
                return await anext(self._source)
            try:
                return next(self._source)
            except StopIteration:
                raise StopAsyncIteration from None
        except BaseException as original:
            if isinstance(original, StopAsyncIteration):
                await self.aclose()
                raise
            receipt = None
            try:
                receipt = await capture(original, flow="mcp", phase="stream")
            finally:
                parent = receipt.event_id if receipt is not None else None
                try:
                    await self._close(parent_event_id=parent)
                except (Exception, asyncio.CancelledError) as cleanup:
                    await capture(
                        cleanup, flow="mcp", phase="cleanup", parent_event_id=parent,
                    )
                    if _caller_cancelled(cleanup, cancellations):
                        raise
            raise

    async def aclose(self) -> None:
        """
        Await one shared cleanup task across repeated close calls.

        Returns
        -------
        None
            Finish source and nested-owner cleanup without starting another task.

        Raises
        ------
        BaseException
            If cleanup fails, or if caller cancellation must propagate after
            cleanup has finished.
        """
        await self._close()

    async def _close(self, *, parent_event_id: str | None = None) -> None:
        """
        Share cleanup while transferring its primary incident to the owned task.

        Parameters
        ----------
        parent_event_id : str or None, optional
            Producer incident associated with failures during resource closure.

        Returns
        -------
        None
            Join the existing cleanup or start it once with causal metadata.
        """
        if self._cleanup is None:
            self._closed = True
            self._cleanup = asyncio.ensure_future(self._closeOwned(parent_event_id))
        await await_cleanup(self._cleanup)

    async def _closeOwned(self, parent_event_id: str | None = None) -> None:
        """
        Close the source before releasing its nested owner.

        Prefer ``aclose`` over ``close`` and release the owner even when source
        cleanup fails or iteration never started.

        Parameters
        ----------
        parent_event_id : str or None, optional
            Producer incident transferred without changing exception chains.

        Returns
        -------
        None
            Complete available source hooks and nested-owner cleanup.

        Raises
        ------
        BaseException
            If either cleanup fails; retain the source failure as primary when
            both source and owner cleanup fail.
        """
        original = None
        task = asyncio.current_task()
        cancellations = task.cancelling() if task is not None else 0
        try:
            close = getattr(self._source, "aclose", None)
            if close is not None:
                await close()
            else:
                close = getattr(self._source, "close", None)
                if close is not None:
                    close()
        except BaseException as exc:
            original = exc
            receipt = await capture(
                exc, flow="mcp", phase="cleanup", parent_event_id=parent_event_id,
            )
            if receipt is not None:
                parent_event_id = receipt.event_id
            raise
        finally:
            if self._owner is not None:
                try:
                    await OwnedStream._close(
                        self._owner, parent_event_id=parent_event_id,
                    )
                except (Exception, asyncio.CancelledError) as cleanup:
                    await capture(
                        cleanup, flow="mcp", phase="cleanup",
                        parent_event_id=parent_event_id,
                    )
                    if original is None or _caller_cancelled(cleanup, cancellations):
                        raise
