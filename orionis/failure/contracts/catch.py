"""Define the contract for catch implementations."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.http.adapters.request.contracts.transport import TransportAdapter
    from orionis.http.request import Request
    from orionis.http.responses import Response

class ICatch(ABC):
    """Define the contract for catch implementations."""

    @abstractmethod
    async def exception(
        self,
        exception: BaseException,
        request: Request | TransportAdapter | None = None,
    ) -> Response | None:
        """
        Handle an exception based on the current kernel context.

        Parameters
        ----------
        exception : BaseException
            The exception instance to handle.
        request
            The HTTP request or transport adapter associated with the exception.

        Returns
        -------
        None | orionis.http.Response
            This method performs side effects and may return a Response.

        Notes
        -----
        Determines the context and delegates exception handling accordingly.
        """
