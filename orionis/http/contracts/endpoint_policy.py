"""Customize endpoint framing without replacing routing or middleware."""

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
    """Declare that this class introduces no additional instance slots."""
    monitor_disconnects: ClassVar[bool] = False
    """Monitor disconnects flag used by ``IHttpEndpointPolicy``."""

    def isExpectedFailure(self, exception: Exception) -> bool:  # noqa: ARG002
        """
        Classify a protocol rejection before global failure observation.

        Parameters
        ----------
        exception : Exception
            Original exception that the endpoint will translate.

        Returns
        -------
        bool
            False unless the policy recognizes an expected client failure.
        """
        return False

    @abstractmethod
    def before(self, adapter: TransportAdapter) -> Response | None:
        """
        Validate protocol connection metadata before admission and middleware.

        Parameters
        ----------
        adapter : orionis.http.adapters.request.contracts.transport.TransportAdapter
            Value supplied for ``adapter``.

        Returns
        -------
        orionis.http.Response | None
            Result of the operation described above.
        """

    @abstractmethod
    async def response(self, response: Response) -> Response:
        """
        Adapt middleware and handler responses to the endpoint's wire format.

        Parameters
        ----------
        response : orionis.http.Response
            Value supplied for ``response``.

        Returns
        -------
        orionis.http.Response
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
        orionis.http.Response
            Result of the operation described above.
        """
