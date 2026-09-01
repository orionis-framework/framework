from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.http.adapters.request.contracts.transport import TransportAdapter
    from orionis.http.responses import Response

class ResponseAdapter(ABC):
    """
    Write abstraction for sending an HTTP response over a protocol transport.

    Decouples response-sending logic from the underlying server protocol,
    allowing the framework to operate against a single unified interface
    regardless of whether the server speaks ASGI or RSGI.
    """

    __slots__ = ()

    @abstractmethod
    async def send(
        self,
        adapter: TransportAdapter,
        response: Response,
        *args: object,
        **kwargs: object,
    ) -> None:
        """
        Send the HTTP response using the underlying protocol transport.

        Parameters
        ----------
        adapter : TransportAdapter
            Transport adapter containing request information used to inspect
            the HTTP method and headers.
        response : Response
            Response object to be serialised and sent back to the client.
        *args : object
            Protocol-specific positional arguments (e.g. ASGI ``send``
            callable or RSGI ``HTTPProtocol`` instance).
        **kwargs : object
            Protocol-specific keyword arguments reserved for future use.

        Returns
        -------
        None
            Sends the response via the protocol transport and returns nothing.
        """
