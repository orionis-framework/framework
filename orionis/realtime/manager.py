import asyncio
from typing import TYPE_CHECKING
from orionis.foundation.config.realtime.entities.realtime import (
    RealtimeConfig,  # noqa: TC001 - Constructor injection.
)
from orionis.realtime.clients import HubClients, validate_group, validate_identifier
from orionis.realtime.contracts.manager import IConnectionManager
from orionis.realtime.entities import BroadcastResult
from orionis.realtime.hub import Hub

if TYPE_CHECKING:
    from orionis.realtime.contracts.connection import RealtimeConnectionLike


class _Broadcast:
    """Share one immutable encoded payload per codec among bounded workers."""

    __slots__ = ("encoded", "failed", "hub", "manager", "recipients", "sent")

    def __init__(
        self,
        manager: IConnectionManager,
        hub: type[Hub],
        recipients: tuple[str, ...],
        encoded: dict[str, str | bytes],
    ) -> None:
        """
        Prepare a shared recipient iterator and delivery counters.

        Parameters
        ----------
        manager : IConnectionManager
            Registry used to recheck availability immediately before sending.
        hub : type[Hub]
            Hub namespace restricting all recipients.
        recipients : tuple[str, ...]
            Snapshot of recipient identifiers; no connections are retained.
        encoded : dict[str, str | bytes]
            Immutable frame payloads, encoded once per selected codec.

        Returns
        -------
        None
            Store delivery inputs and initialize successful and failed counts.
        """
        self.manager = manager
        self.hub = hub
        self.recipients = iter(recipients)
        self.encoded = encoded
        self.sent = 0
        self.failed = 0

    async def run(self) -> None:
        """
        Drain recipients while respecting each connection's backpressure.

        Returns
        -------
        None
            Count failures independently; task cancellation propagates.
        """
        for connection_id in self.recipients:
            connection = self.manager.get(connection_id, self.hub)
            if connection is None:
                self.failed += 1
                continue
            try:
                await connection.sendEncoded(self.encoded[connection.protocol.name])
            except Exception:  # noqa: BLE001 - One failed recipient cannot abort others.
                self.failed += 1
            else:
                self.sent += 1

class ConnectionManager(IConnectionManager):
    """Own worker-local connections and isolate every group by Hub class.

    Registry mutations contain no await points and run on the application's
    event loop. Delivery snapshots identifiers before awaiting network I/O.
    Replacing IConnectionManager is the extension point for distributed delivery;
    the default registry never crosses process or worker boundaries.
    """

    __slots__ = ("_config", "_connections", "_groups", "_hubs", "_memberships")

    def __init__(self, config: RealtimeConfig) -> None:
        """
        Initialize an empty registry with validated structural limits.

        Parameters
        ----------
        config : RealtimeConfig
            Group and broadcast limits shared by this application.

        Returns
        -------
        None
            Store limits and initialize empty connection and membership maps.
        """
        self._config = config
        self._connections: dict[str, RealtimeConnectionLike] = {}
        self._hubs: dict[type[Hub], set[str]] = {}
        self._groups: dict[tuple[type[Hub], str], set[str]] = {}
        self._memberships: dict[str, set[str]] = {}

    @property
    def config(self) -> RealtimeConfig:
        """
        Return the immutable application limits used by Hub lifecycles.

        Returns
        -------
        RealtimeConfig
            Application-wide invocation, group and broadcast limits.
        """
        return self._config

    @property
    def connectionCount(self) -> int:
        """
        Return the number of owned, including provisional, connections.

        Returns
        -------
        int
            Number of registered connections regardless of readiness.
        """
        return len(self._connections)

    @property
    def groupCount(self) -> int:
        """
        Return the number of nonempty Hub-local groups.

        Returns
        -------
        int
            Number of groups with at least one registered member.
        """
        return len(self._groups)

    def register(self, connection: RealtimeConnectionLike) -> None:
        """
        Own one provisional connection before its onConnect hook.

        Parameters
        ----------
        connection : RealtimeConnectionLike
            Connection with a cryptographically generated unique identifier.

        Returns
        -------
        None
            Register the connection, its Hub namespace and empty memberships.

        Raises
        ------
        ValueError
            If its identifier is invalid or already belongs to a connection.
        """
        connection_id = connection.context.connection_id
        validate_identifier(connection_id, "Connection identifier")
        if connection_id in self._connections:
            error_msg = "A connection already owns this identifier"
            raise ValueError(error_msg)
        self._connections[connection_id] = connection
        self._hubs.setdefault(connection.hub, set()).add(connection_id)
        self._memberships[connection_id] = set()

    def unregister(self, connection: RealtimeConnectionLike) -> None:
        """
        Release owned registry entries and every group reference.

        Parameters
        ----------
        connection : RealtimeConnectionLike
            Exact connection instance to release; repeated release is harmless.

        Returns
        -------
        None
            Remove ownership without touching an instance that reused an ID.
        """
        connection_id = connection.context.connection_id
        if self._connections.get(connection_id) is not connection:
            return
        del self._connections[connection_id]
        members = self._hubs[connection.hub]
        members.remove(connection_id)
        if not members:
            del self._hubs[connection.hub]
        for group in self._memberships.pop(connection_id):
            key = (connection.hub, group)
            members = self._groups[key]
            members.discard(connection_id)
            if not members:
                del self._groups[key]

    def get(
        self, connection_id: str, hub: type[Hub] | None = None,
    ) -> RealtimeConnectionLike | None:
        """
        Look up a ready recipient without crossing an optional Hub boundary.

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
        connection = self._connections.get(connection_id)
        if connection is None or not connection.ready or connection.closing:
            return None
        if hub is not None and connection.hub is not hub:
            return None
        return connection

    def snapshot(self) -> tuple[RealtimeConnectionLike, ...]:
        """
        Snapshot all owned connections for bounded lifecycle shutdown.

        Returns
        -------
        tuple[RealtimeConnectionLike, ...]
            Active and provisional connections owned at the time of the call.
        """
        return tuple(self._connections.values())

    def connectionIds(self, hub: type[Hub]) -> tuple[str, ...]:
        """
        Snapshot ready connection identifiers in one Hub namespace.

        Parameters
        ----------
        hub : type[Hub]
            Owning Hub class.

        Returns
        -------
        tuple[str, ...]
            Current ready recipients; no connection objects are retained.
        """
        return tuple(
            identifier for identifier in self._hubs.get(hub, ())
            if self.get(identifier, hub) is not None
        )

    def groupIds(self, hub: type[Hub], group: str) -> tuple[str, ...]:
        """
        Snapshot ready group members without crossing Hub namespaces.

        Parameters
        ----------
        hub : type[Hub]
            Owning Hub class.
        group : str
            Group name within that Hub.

        Returns
        -------
        tuple[str, ...]
            Current ready recipients of the named group.

        Raises
        ------
        ValueError
            If the group name is invalid.
        """
        validate_group(group)
        return tuple(
            identifier for identifier in self._groups.get((hub, group), ())
            if self.get(identifier, hub) is not None
        )

    def join(self, connection_id: str, group: str) -> None:
        """
        Join an active or provisional connection to a bounded group set.

        Parameters
        ----------
        connection_id : str
            Owned connection, including one in its onConnect hook.
        group : str
            Hub-local group name, at most 256 characters.

        Returns
        -------
        None
            Add membership without consuming another slot for repeated joins.

        Raises
        ------
        ValueError
            If the group name is invalid.
        ConnectionError
            If this connection is absent or closing.
        RuntimeError
            If joining another group would exceed its configured limit.
        """
        validate_group(group)
        connection = self._connections.get(connection_id)
        if connection is None or connection.closing:
            error_msg = "Cannot join a group without an active owned connection"
            raise ConnectionError(error_msg)
        groups = self._memberships[connection_id]
        if group in groups:
            return
        if len(groups) >= self._config.max_groups_per_connection:
            error_msg = "The connection has reached its group membership limit"
            raise RuntimeError(error_msg)
        groups.add(group)
        self._groups.setdefault((connection.hub, group), set()).add(connection_id)

    def leave(self, connection_id: str, group: str) -> None:
        """
        Remove membership idempotently and discard empty group entries.

        Parameters
        ----------
        connection_id : str
            Connection whose membership is being released.
        group : str
            Hub-local group name.

        Returns
        -------
        None
            Remove the membership if still owned.

        Raises
        ------
        ValueError
            If the group name is invalid.
        """
        validate_group(group)
        connection = self._connections.get(connection_id)
        if connection is None:
            return
        self._memberships[connection_id].discard(group)
        key = (connection.hub, group)
        members = self._groups.get(key)
        if members is not None:
            members.discard(connection_id)
            if not members:
                del self._groups[key]

    def hub(self, hub: type[Hub]) -> HubClients:
        """
        Return application-service client targets for a Hub namespace.

        Parameters
        ----------
        hub : type[Hub]
            Hub class whose clients should receive events or invocations.

        Returns
        -------
        HubClients
            Client selectors without a connection-specific caller.

        Raises
        ------
        TypeError
            If the supplied class is not a Hub subclass.
        """
        if not isinstance(hub, type) or not issubclass(hub, Hub):
            error_msg = "Realtime targets require a Hub subclass"
            raise TypeError(error_msg)
        return HubClients(self, hub)

    async def broadcast(
        self, hub: type[Hub], connection_ids: tuple[str, ...], envelope: object,
    ) -> BroadcastResult:
        """
        Encode once per codec and deliver through bounded concurrent workers.

        Parameters
        ----------
        hub : type[Hub]
            Hub namespace restricting every recipient.
        connection_ids : tuple[str, ...]
            Recipient identifiers selected by the application.
        envelope : object
            Typed or mapping envelope accepted by the selected Hub codecs.

        Returns
        -------
        BroadcastResult
            Successful and failed recipient counts; cancellation propagates.

        Raises
        ------
        TypeError, ValueError
            If the payload cannot be encoded before delivery begins.
        """
        if not connection_ids:
            return BroadcastResult()
        encoded: dict[str, str | bytes] = {}
        for identifier in connection_ids:
            connection = self.get(identifier, hub)
            if connection is not None and connection.protocol.name not in encoded:
                encoded[connection.protocol.name] = connection.protocol.encode(envelope)
        delivery = _Broadcast(self, hub, connection_ids, encoded)
        workers = min(self._config.broadcast_concurrency, len(connection_ids))
        if workers == 1:
            await delivery.run()
        else:
            async with asyncio.TaskGroup() as tasks:
                for _ in range(workers):
                    tasks.create_task(delivery.run())
        return BroadcastResult(sent=delivery.sent, failed=delivery.failed)
