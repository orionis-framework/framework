from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.foundation.config.realtime.entities.realtime import RealtimeConfig
    from orionis.realtime.clients import HubClients
    from orionis.realtime.contracts.connection import RealtimeConnectionLike
    from orionis.realtime.entities import BroadcastResult
    from orionis.realtime.hub import Hub


class IConnectionManager(ABC):
    """
    Define connection ownership and Hub delivery for registry providers.

    The default implementation owns connections in the current process only.
    A distributed provider can replace this contract and explicitly route remote
    delivery; no cross-worker behavior is implied by the default implementation.
    """

    __slots__ = ()

    @property
    @abstractmethod
    def config(self) -> RealtimeConfig:
        """
        Return immutable application limits used by Hub lifecycles.

        Returns
        -------
        RealtimeConfig
            Application-wide invocation, group and broadcast limits.
        """

    @abstractmethod
    def register(self, connection: RealtimeConnectionLike) -> None:
        """
        Register one provisional connection before its onConnect hook.

        Parameters
        ----------
        connection : RealtimeConnectionLike
            Connection with a unique identifier and owning Hub namespace.

        Returns
        -------
        None
            Store connection ownership before it becomes ready for delivery.

        Raises
        ------
        ValueError
            If the identifier is invalid or already owned by a connection.
        """

    @abstractmethod
    def unregister(self, connection: RealtimeConnectionLike) -> None:
        """
        Remove a connection and every group membership it owns.

        Parameters
        ----------
        connection : RealtimeConnectionLike
            Exact connection instance to release.

        Returns
        -------
        None
            Release ownership idempotently without affecting a reused identifier.
        """

    @abstractmethod
    def get(
        self, connection_id: str, hub: type[Hub] | None = None,
    ) -> RealtimeConnectionLike | None:
        """
        Return a ready connection in the requested Hub namespace.

        Parameters
        ----------
        connection_id : str
            Identifier of the requested connection.
        hub : type[Hub] | None, optional
            Required owning Hub class, or None to omit namespace filtering.

        Returns
        -------
        RealtimeConnectionLike | None
            Ready, nonclosing connection in the requested namespace, or None.
        """

    @abstractmethod
    def snapshot(self) -> tuple[RealtimeConnectionLike, ...]:
        """
        Return all owned connections, including provisional connections.

        Returns
        -------
        tuple[RealtimeConnectionLike, ...]
            Connections owned at the time of the call, regardless of readiness.
        """

    @abstractmethod
    def connectionIds(self, hub: type[Hub]) -> tuple[str, ...]:
        """
        Snapshot ready connection identifiers in one Hub namespace.

        Parameters
        ----------
        hub : type[Hub]
            Owning Hub class restricting the selection.

        Returns
        -------
        tuple[str, ...]
            Identifiers of current ready, nonclosing connections.
        """

    @abstractmethod
    def groupIds(self, hub: type[Hub], group: str) -> tuple[str, ...]:
        """
        Snapshot ready members of a group within one Hub namespace.

        Parameters
        ----------
        hub : type[Hub]
            Owning Hub class restricting the selection.
        group : str
            Nonempty Hub-local group name of at most 256 characters.

        Returns
        -------
        tuple[str, ...]
            Identifiers of ready, nonclosing members of the named group.

        Raises
        ------
        ValueError
            If the group name is invalid.
        """

    @abstractmethod
    def join(self, connection_id: str, group: str) -> None:
        """
        Join an owned connection to a bounded, Hub-local group.

        Parameters
        ----------
        connection_id : str
            Owned connection identifier, including provisional connections.
        group : str
            Nonempty Hub-local group name of at most 256 characters.

        Returns
        -------
        None
            Add membership without consuming another slot for repeated joins.

        Raises
        ------
        ValueError
            If the group name is invalid.
        ConnectionError
            If the connection is absent or closing.
        RuntimeError
            If another membership would exceed the configured group limit.
        """

    @abstractmethod
    def leave(self, connection_id: str, group: str) -> None:
        """
        Remove an owned connection from one group idempotently.

        Parameters
        ----------
        connection_id : str
            Identifier of the connection whose membership should be removed.
        group : str
            Nonempty Hub-local group name of at most 256 characters.

        Returns
        -------
        None
            Remove existing membership and discard empty group entries.

        Raises
        ------
        ValueError
            If the group name is invalid.
        """

    @abstractmethod
    def hub(self, hub: type[Hub]) -> HubClients:
        """
        Return client targets usable by application services.

        Parameters
        ----------
        hub : type[Hub]
            Hub class whose clients should receive events or invocations.

        Returns
        -------
        HubClients
            Hub-local client selectors without a connection-specific caller.

        Raises
        ------
        TypeError
            If the supplied class is not a Hub subclass.
        """

    @abstractmethod
    async def broadcast(
        self, hub: type[Hub], connection_ids: tuple[str, ...], envelope: object,
    ) -> BroadcastResult:
        """
        Deliver one envelope through a bounded set of concurrent workers.

        Parameters
        ----------
        hub : type[Hub]
            Hub namespace restricting every recipient.
        connection_ids : tuple[str, ...]
            Snapshot of recipient identifiers selected by the application.
        envelope : object
            Protocol envelope accepted by the selected Hub codecs.

        Returns
        -------
        BroadcastResult
            Successful and failed delivery counts; cancellation propagates.

        Raises
        ------
        TypeError, ValueError
            If the envelope cannot be encoded before delivery begins.
        """
