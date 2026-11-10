"""Define the contract for catch implementations."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.failure.entities.context import FailureContext, FailureReceipt
    from orionis.http.adapters.request.contracts.transport import TransportAdapter
    from orionis.http.request import Request
    from orionis.http.responses import Response

class ICatch(ABC):
    """Define the contract for catch implementations."""

    #ruff: noqa: PLC0415

    async def capture(
        self,
        exception: BaseException,
        *,
        context: FailureContext,
    ) -> FailureReceipt | None:
        """
        Observe an exception through the active failure runtime.

        Preserve compatibility by delegating to the active runtime without
        requiring a dependency-injection scope.

        Parameters
        ----------
        exception : BaseException
            Original exception instance to observe.
        context : orionis.failure.entities.context.FailureContext
            Immutable execution metadata for the failure.

        Returns
        -------
        orionis.failure.entities.context.FailureReceipt or None
            Delivery status, or ``None`` if no runtime is active or the exception
            represents cancellation or process control.
        """
        from orionis.failure.runtime import get_runtime
        runtime = get_runtime()
        if runtime is None:
            return None
        return await runtime.capture(exception, context=context)

    @abstractmethod
    async def exception(
        self,
        exception: BaseException,
        request: Request | TransportAdapter | None = None,
    ) -> Response | None:
        """
        Handle an exception in the current kernel context.

        Parameters
        ----------
        exception : BaseException
            Original exception instance to handle.
        request : Request or TransportAdapter or None, optional
            HTTP request or transport adapter used for presentation, when available.

        Returns
        -------
        orionis.http.responses.Response or None
            Response produced by presentation, or ``None`` when no response is
            available.

        Raises
        ------
        RuntimeError
            If no application scope or kernel context is active.
        """
