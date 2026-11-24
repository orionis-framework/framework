# ruff: noqa: N815, PYI021
# Keep public facade methods documented alongside their static signatures.
# Match the mixed-case property names exposed by the connection manager.
from typing import ClassVar
from orionis.container.facades.facade import Facade
from orionis.foundation.config.realtime.entities.realtime import RealtimeConfig
from orionis.realtime.clients import HubClients
from orionis.realtime.contracts.connection import RealtimeConnectionLike
from orionis.realtime.contracts.manager import IConnectionManager
from orionis.realtime.entities import BroadcastResult
from orionis.realtime.hub import Hub

class Realtime(Facade):

    config: ClassVar[RealtimeConfig]
    connectionCount: ClassVar[int]
    groupCount: ClassVar[int]

    @classmethod
    def getFacadeAccessor(cls) -> type[IConnectionManager]:
        """Return the contract registered for this facade in the container."""

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> IConnectionManager:
        """Resolve the connection registry from the container."""

    @classmethod
    def hub(cls, hub: type[Hub]) -> HubClients:
        """Create application-service client selectors for one Hub class."""

    @classmethod
    def register(cls, connection: RealtimeConnectionLike) -> None:
        """Register a connection in its Hub namespace."""

    @classmethod
    def unregister(cls, connection: RealtimeConnectionLike) -> None:
        """Remove a connection and its group memberships."""

    @classmethod
    def get(
        cls,
        connection_id: str,
        hub: type[Hub] | None = None,
    ) -> RealtimeConnectionLike | None:
        """Look up a connection, optionally within one Hub."""

    @classmethod
    def snapshot(cls) -> tuple[RealtimeConnectionLike, ...]:
        """Return the current connections."""

    @classmethod
    def connectionIds(cls, hub: type[Hub]) -> tuple[str, ...]:
        """Return the ready connections for a Hub."""

    @classmethod
    def groupIds(cls, hub: type[Hub], group: str) -> tuple[str, ...]:
        """Return the members of a group within a Hub."""

    @classmethod
    def join(cls, connection_id: str, group: str) -> None:
        """Add a connection to a group in its Hub."""

    @classmethod
    def leave(cls, connection_id: str, group: str) -> None:
        """Remove a connection from a group."""

    @classmethod
    async def broadcast(
        cls,
        hub: type[Hub],
        connection_ids: tuple[str, ...],
        envelope: object,
    ) -> BroadcastResult:
        """Deliver an envelope to the selected connections."""
