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
    socket: WebSocket
    user: object | None = None


class Hub:
    """Define an invocation-scoped realtime endpoint with explicit remote methods."""

    __slots__ = ("clients", "context", "groups")

    context: HubContext
    clients: HubClients
    groups: HubGroups

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
