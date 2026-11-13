# ruff: noqa: TC003
# Preserve callback annotations on the public entity and generated constructor.
"""Keep deferred failure effects separate from immutable incident metadata."""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from collections.abc import Awaitable, Callable
from types import TracebackType


@dataclass(slots=True, kw_only=True)
class FailureHandling:
    """Own logging and optional presentation for one observed incident.

    The runtime completes logging after the application hook returns. The
    protocol owner may then request presentation with its live request. Keep
    this object local to the operation; immutable receipts contain only status.
    """

    logging: Callable[[], Awaitable[object]] | None = None
    """Deferred asynchronous logging action owned by the coordinator."""
    presentation: Callable[..., Awaitable[object]] | None = None
    """Deferred presentation accepting the owner's flow and live request."""
    reported: bool = False
    """Whether the logging action completed successfully."""
    degraded: bool = False
    """Whether an effect required fallback or failed during handling."""
    _completion_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    """Coordinate consumers of the single logging effect."""
    _presentation_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    """Coordinate consumers of the single presentation effect."""
    _completion_owner: asyncio.Task | None = field(default=None, init=False, repr=False)
    """Task executing logging, cleared when the action finishes or fails."""
    _presentation_owner: asyncio.Task | None = field(
        default=None,
        init=False,
        repr=False,
    )
    """Task executing presentation, cleared when the action finishes or fails."""
    _completed: bool = field(default=False, init=False)
    """Whether logging execution has already been claimed."""
    _presented: bool = field(default=False, init=False)
    """Whether presentation execution has already been claimed."""
    _completion_error: BaseException | None = field(default=None, init=False)
    """Retained logging failure preventing automatic effect retries."""
    _completion_traceback: TracebackType | None = field(
        default=None,
        init=False,
        repr=False,
    )
    """Original logging traceback, without frames added by subsequent callers."""
    _presentation_error: BaseException | None = field(default=None, init=False)
    """Retained presentation failure preventing automatic effect retries."""
    _presentation_traceback: TracebackType | None = field(
        default=None,
        init=False,
        repr=False,
    )
    """Original presentation traceback, restored for repeated failed requests."""
    _presentation_diagnosed: bool = field(default=False, init=False)
    """Whether the coordinator already emitted the presentation diagnostic."""
    _result: object = field(default=None, init=False)
    """Cached presentation outcome shared with concurrent consumers."""

    async def complete(self) -> None:
        """
        Execute the deferred logging action at most once.

        Serialize concurrent calls and preserve failures for later callers.
        Restore the original traceback before re-raising a retained error so
        repeated callers do not accumulate one another's stack frames.
        Set ``reported`` after successful logging; skip logging if no action is
        configured or a previous call completed successfully.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        RuntimeError
            If the logging action recursively waits for its own completion.
        BaseException
            If execution is cancelled, logging fails, or a retained failure is
            re-raised.
        """
        owner = asyncio.current_task()
        if owner is not None and owner is self._completion_owner:
            error_msg = "Recursive completion of the same failure handling plan."
            raise RuntimeError(error_msg)
        async with self._completion_lock:
            if self._completed:
                error = self._completion_error
                if error is not None:
                    BaseException.with_traceback(error, self._completion_traceback)
                    raise error
                return
            self._completed = True
            self._completion_owner = owner
            try:
                if self.logging is not None:
                    await self.logging()
                    self.reported = True
            except BaseException as error:
                self._completion_error = error
                self._completion_traceback = error.__traceback__
                raise
            finally:
                self._completion_owner = None

    async def present(
        self,
        *,
        flow: str,
        request: object | None = None,
    ) -> object:
        """
        Execute deferred presentation at most once and cache its result.

        Serialize concurrent calls and preserve failures for later callers.
        Retained errors keep their identity, cause, and original traceback
        without accumulating the frames of previous consumers.

        Parameters
        ----------
        flow : str
            Execution flow passed to the presentation callback.
        request : object or None, optional
            Live request or execution state passed to the callback, when available.

        Returns
        -------
        object
            Cached presentation result, or ``None`` if no callback is configured.

        Raises
        ------
        RuntimeError
            If presentation recursively waits for its own result.
        BaseException
            If execution is cancelled, presentation fails, or a retained failure
            is re-raised.
        """
        owner = asyncio.current_task()
        if owner is not None and owner is self._presentation_owner:
            error_msg = "Recursive presentation of the same failure handling plan."
            raise RuntimeError(error_msg)
        async with self._presentation_lock:
            if self._presented:
                error = self._presentation_error
                if error is not None:
                    BaseException.with_traceback(error, self._presentation_traceback)
                    raise error
                return self._result
            self._presented = True
            self._presentation_owner = owner
            try:
                self._result = (
                    await self.presentation(flow=flow, request=request)
                    if self.presentation is not None
                    else None
                )
            except BaseException as error:
                self._presentation_error = error
                self._presentation_traceback = error.__traceback__
                raise
            finally:
                self._presentation_owner = None
            return self._result
