# ruff: noqa: ASYNC109, TC001
# Keep the existing boundary behavior and deliberately shaped fixtures.
# Resolve protocol annotations without eagerly accessing a partially defined Hub.
"""Describe the connection surface required by the worker-local registry."""

from __future__ import annotations
from typing import Protocol
import orionis.realtime.hub as hub_module
from orionis.realtime.protocol import HubProtocol


class RealtimeConnectionLike(Protocol):
    """Describe the connection surface required by the worker-local registry."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @property
    def context(self) -> hub_module.HubContext:
        """
        Return the immutable connection identity and handshake context.

        Returns
        -------
        orionis.realtime.HubContext
            Connection identity, public socket and authenticated user.
        """
        ...

    @property
    def hub(self) -> type[hub_module.Hub]:
        """
        Return the Hub namespace owning this connection.

        Returns
        -------
        type[orionis.realtime.Hub]
            Application-owned Hub type associated with the connection.
        """
        ...

    @property
    def protocol(self) -> HubProtocol:
        """
        Return the immutable codec selected for this connection.

        Returns
        -------
        orionis.realtime.HubProtocol
            Route-selected codec for protocol envelopes.
        """
        ...

    @property
    def ready(self) -> bool:
        """
        Report whether acceptance has admitted ordered realtime delivery.

        Returns
        -------
        bool
            Whether the ready message has admitted connection targeting.
        """
        ...

    @property
    def closing(self) -> bool:
        """
        Report whether this connection is being released.

        Returns
        -------
        bool
            Whether connection cleanup has started.
        """
        ...

    async def sendEncoded(self, data: str | bytes) -> None:
        """
        Send an encoded frame while preserving transport backpressure.

        Parameters
        ----------
        data : str | bytes
            Immutable, already encoded protocol envelope.

        Returns
        -------
        None
            Complete the ordered transport write.

        Raises
        ------
        ConnectionError
            If connection cleanup has started.
        """
        ...

    async def invoke(
        self,
        target: str,
        *args: object,
        timeout: float | None = None,  # Client completion deadline.
    ) -> object:
        """
        Invoke one client method and await its correlated completion.

        Parameters
        ----------
        target : str
            Explicit client method name.
        *args : object
            Serializable positional arguments supplied to the client method.
        timeout : float | None, optional
            Total send/result deadline in seconds. None uses the configured
            client-result timeout.

        Returns
        -------
        object
            Client completion result, including None.

        Raises
        ------
        ConnectionError
            If the connection is not ready or disconnects.
        RuntimeError
            If the pending client-result budget is exhausted.
        ValueError
            If the target, argument count or deadline is invalid.
        TimeoutError
            If sending or receiving the completion exceeds the deadline.
        orionis.realtime.errors.ClientInvocationError
            If the client returns a completion error.
        """
        ...
