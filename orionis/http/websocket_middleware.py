"""Define a connection middleware resolved inside each WebSocket scope."""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.http.websocket import WebSocket

type WebSocketNext = Callable[[], Awaitable[None]]
"""Type alias for ``Callable[[], Awaitable[None]]``."""


class WebSocketMiddleware(ABC):
    """Define a connection middleware resolved inside each WebSocket scope."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    async def handle(
        self,
        socket: WebSocket,
        call_next: WebSocketNext,
    ) -> None:
        """
        Inspect the handshake or wrap the connection handler.

        Parameters
        ----------
        socket : orionis.http.WebSocket
            Connection metadata and messaging API.
        call_next : orionis.http.WebSocketNext
            Single-use continuation for the next connection layer.

        Returns
        -------
        None
            Advance the pipeline or reject the pending connection.
        """
