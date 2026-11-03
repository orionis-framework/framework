"""Provide realtime operations through ``HubContext``, ``Hub``."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.http.websocket import WebSocket
    from orionis.realtime.clients import HubClients
    from orionis.realtime.groups import HubGroups


@dataclass(frozen=True, slots=True, kw_only=True)
class HubContext:
    """Expose connection identity without providing service location."""

    connection_id: str
    """Identifier of the current realtime connection."""
    socket: WebSocket
    """WebSocket associated with the current realtime invocation."""
    user: object | None = None
    """Authenticated identity associated with the current connection."""


class Hub:
    """Define an invocation-scoped realtime endpoint with explicit remote methods."""

    __slots__ = ("clients", "context", "groups")
    """Declare the instance attribute slots reserved by this class."""

    context: HubContext
    """Runtime context made available to the operation and its callbacks."""
    clients: HubClients
    """Client-target selector available to hub handlers."""
    groups: HubGroups
    """Realtime group membership and targeting interface."""

    async def onConnect(self) -> None:
        """
        Run connection initialization before the ready envelope is sent.

        Returns
        -------
        None
            A subclass may reject or initialize this connection.
        """

    async def onDisconnect(self, code: int, reason: str | None = None) -> None:
        """
        Run after connection-owned calls and registrations are released.

        Parameters
        ----------
        code : int
            Observed close code, or an abnormal closure when unavailable.
        reason : str | None, optional
            Available peer or local close reason.

        Returns
        -------
        None
            A subclass may release application-owned connection resources.
        """
