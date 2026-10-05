from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from orionis.http.adapters.request.contracts.transport import TransportAdapter
    from orionis.http.request import Request
    from orionis.http.responses import Response

class IHttpEndpointPolicy(ABC):
    """Customize endpoint framing without replacing routing or middleware."""

    __slots__ = ()
    monitor_disconnects: ClassVar[bool] = False

    @abstractmethod
    def before(self, adapter: TransportAdapter) -> Response | None:
        """
        Validate protocol connection metadata before admission and middleware.

        Parameters
        ----------
        adapter : TransportAdapter
            Value supplied for ``adapter``.

        Returns
        -------
        Response | None
            Result of the operation described above.
        """

    @abstractmethod
    async def response(self, response: Response) -> Response:
        """
        Adapt middleware and handler responses to the endpoint's wire format.

        Parameters
        ----------
        response : Response
            Value supplied for ``response``.

        Returns
        -------
        Response
            Result of the operation described above.
        """

    @abstractmethod
    async def exception(
        self, exception: Exception, request: Request | TransportAdapter,
    ) -> Response:
        """
        Report a failure and provide the endpoint's sanitized response.

        Parameters
        ----------
        exception : Exception
            Exception being inspected or reported.
        request : Request | TransportAdapter
            Current request and its trusted execution context.

        Returns
        -------
        Response
            Result of the operation described above.
        """
