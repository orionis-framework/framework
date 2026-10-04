"""Optional response and early-validation rules for static protocol endpoints."""

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
        """Validate protocol connection metadata before admission and middleware."""

    @abstractmethod
    async def response(self, response: Response) -> Response:
        """Adapt middleware and handler responses to the endpoint's wire format."""

    @abstractmethod
    async def exception(
        self, exception: Exception, request: Request | TransportAdapter,
    ) -> Response:
        """Report a failure and provide the endpoint's sanitized response."""
