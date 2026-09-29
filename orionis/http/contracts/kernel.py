from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from granian.rsgi import HTTPProtocol, Scope

class IKernelHTTP(ABC):

    __slots__ = ()

    @abstractmethod
    async def boot(self) -> None:
        """
        Boot the HTTP kernel by initializing core components.

        Resolve routes, initialize middleware stack, configure response
        adapters, and set up request printer for each protocol.

        Returns
        -------
        None
        """

    @abstractmethod
    async def handleRSGI(
        self,
        scope: Scope,
        protocol: HTTPProtocol,
    ) -> object | None:
        """
        Handle an incoming RSGI HTTP request end-to-end.

        Open a per-request scope, run global middleware, resolve the
        route, build the request object, invoke the handler, and send
        the response.

        Parameters
        ----------
        scope : Scope
            Granian RSGI scope object with connection metadata.
        protocol : HTTPProtocol
            RSGI HTTP protocol object used to send the response.

        Returns
        -------
        object | None
            The result of sending the RSGI response, or None on error.
        """

    @abstractmethod
    async def handleASGI(
        self,
        scope: dict,
        receive: object,
        send: object,
    ) -> None:
        """
        Handle an incoming ASGI HTTP request end-to-end.

        Open a per-request scope, run global middleware, resolve the
        route, build the request object, invoke the handler, and send
        the response.

        Parameters
        ----------
        scope : dict
            ASGI connection scope dict with request metadata.
        receive : object
            ASGI receive callable for reading request body and events.
        send : object
            ASGI send callable for sending response messages.

        Returns
        -------
        None
        """
