"""Keep deferred failure effects separate from immutable incident metadata."""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

@dataclass(slots=True, kw_only=True)
class FailureHandling:
    """Own logging and optional presentation for one observed incident.

    The runtime completes logging after the application hook returns. The
    protocol owner may then request presentation with its live request. Keep
    this object local to the operation; immutable receipts contain only status.
    """

    logging: Callable[[], Awaitable[object]] | None = None
    presentation: Callable[..., Awaitable[object]] | None = None
    reported: bool = False
    degraded: bool = False
    _completion_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _presentation_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _completed: bool = field(default=False, init=False)
    _presented: bool = field(default=False, init=False)
    _completion_error: BaseException | None = field(default=None, init=False)
    _presentation_error: BaseException | None = field(default=None, init=False)
    _result: object = field(default=None, init=False)

    async def complete(self) -> None:
        """
        Execute the deferred logging action at most once.

        Serialize concurrent calls and preserve failures for later callers.

        Returns
        -------
        None
            Set ``reported`` after successful logging; skip logging if no action
            is configured or a previous call completed successfully.

        Raises
        ------
        BaseException
            If execution is cancelled, logging fails, or a retained failure is
            re-raised.
        """
        async with self._completion_lock:
            if self._completed:
                if self._completion_error is not None:
                    raise self._completion_error
                return
            self._completed = True
            try:
                if self.logging is not None:
                    await self.logging()
                    self.reported = True
            except BaseException as error:
                self._completion_error = error
                raise

    async def present(
        self, *, flow: str, request: object | None = None,
    ) -> object:
        """
        Execute deferred presentation at most once and cache its result.

        Serialize concurrent calls and preserve failures for later callers.

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
        BaseException
            If execution is cancelled, presentation fails, or a retained failure
            is re-raised.
        """
        async with self._presentation_lock:
            if self._presented:
                if self._presentation_error is not None:
                    raise self._presentation_error
                return self._result
            self._presented = True
            try:
                self._result = (
                    await self.presentation(flow=flow, request=request)
                    if self.presentation is not None else None
                )
            except BaseException as error:
                self._presentation_error = error
                raise
            return self._result
