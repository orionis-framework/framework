from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from orionis.http.websocket_message import WebSocketMessage

class IWebSocketTransport(ABC):
    """Normalize server operations without owning application lifecycle state."""

    __slots__ = ()

    @property
    def supportsCloseDetails(self) -> bool:
        """
        Declare whether custom close details can reach the wire.

        Returns
        -------
        bool
            True when the server supports close codes and reasons.
        """
        return True

    @abstractmethod
    async def accept(
        self, *, subprotocol: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """
        Complete the pending handshake.

        Parameters
        ----------
        subprotocol : str | None, optional
            Negotiated client-offered subprotocol.
        headers : Mapping[str, str] | None, optional
            Additional handshake response headers when supported.

        Returns
        -------
        None
            Await server acceptance.
        """

    @abstractmethod
    async def receive(self) -> WebSocketMessage:
        """
        Receive one normalized server event.

        Returns
        -------
        WebSocketMessage
            Text, binary or disconnect event.
        """

    @abstractmethod
    async def sendText(self, data: str) -> None:
        """
        Await text delivery and server backpressure.

        Parameters
        ----------
        data : str
            Text payload.

        Returns
        -------
        None
            Complete the server write.
        """

    @abstractmethod
    async def sendBytes(self, data: bytes) -> None:
        """
        Await binary delivery and server backpressure.

        Parameters
        ----------
        data : bytes
            Binary payload.

        Returns
        -------
        None
            Complete the server write.
        """

    @abstractmethod
    async def close(self, code: int = 1000, reason: str = "") -> None:
        """
        Close the underlying connection.

        Parameters
        ----------
        code : int, optional
            Valid WebSocket close code.
        reason : str, optional
            UTF-8 close reason.

        Returns
        -------
        None
            Complete the close operation.
        """

    @abstractmethod
    async def reject(self, status_code: int = 403) -> None:
        """
        Reject an unaccepted handshake.

        Parameters
        ----------
        status_code : int, optional
            HTTP rejection status when supported.

        Returns
        -------
        None
            Complete handshake denial.
        """
