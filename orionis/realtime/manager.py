"""Own worker-local connections and isolate every group by Hub class."""

import asyncio
from typing import TYPE_CHECKING
from orionis.failure.runtime import capture, capture_result
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
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self,
        manager: IConnectionManager,
        hub: type[Hub],
        recipients: tuple[str, ...],
        encoded: dict[str, str | bytes],
    ) -> None:
        """
        Share recipient iteration, encoded frames, and counters across workers.

        Parameters
        ----------
        manager : orionis.realtime.contracts.manager.IConnectionManager
            Registry used to recheck recipient availability before each send.
        hub : type[orionis.realtime.Hub]
            Hub namespace that every recipient must belong to.
        recipients : tuple[str, ``...``]
            Recipient identifier snapshot shared by all delivery workers.
        encoded : dict[str, str | bytes]
            Frame values shared across workers, encoded once per selected codec.

        Returns
        -------
        None
            Retain delivery inputs and initialize shared sent/failed counters.
        """
        self.manager = manager
        """Registry used to recheck availability immediately before sending."""
        self.hub = hub
        """Hub namespace restricting all recipients."""
        self.recipients = iter(recipients)
        """Snapshot of recipient identifiers; no connections are retained."""
        self.encoded = encoded
        """Immutable frame payloads, encoded once per selected codec."""
        self.sent = 0
        """Sent value used by ``_Broadcast``."""
        self.failed = 0
        """Failed value used by ``_Broadcast``."""

    async def run(self) -> None:
        """
        Drain the shared recipient iterator and count per-connection outcomes.

        Returns
        -------
        None
            Count completed sends and failed or unavailable recipients, continuing
            after ordinary delivery exceptions.

        Raises
        ------
        asyncio.CancelledError
            If the worker is cancelled; retain counts for completed recipients.
        """
        for connection_id in self.recipients:
            connection = self.manager.get(connection_id, self.hub)
            if connection is None:
                self.failed += 1
                await capture_result(
                    "recipient_unavailable", flow="realtime", phase="broadcast",
                    operation=self.hub.__name__, correlation_id=connection_id,
                    expected=True,
                )
                continue
            try:
                await connection.sendEncoded(self.encoded[connection.protocol.name])
            except Exception as exc:  # noqa: BLE001 - Preserve partial delivery.
                await capture(
                    exc, flow="realtime", phase="broadcast",
                    operation=self.hub.__name__, correlation_id=connection_id,
                    runtime=getattr(connection, "_failure_runtime", None),
                )
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
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, config: RealtimeConfig) -> None:
        """
        Initialize connection and Hub-local group registries with validated limits.

        Parameters
        ----------
        config : orionis.foundation.config.realtime.entities.realtime.RealtimeConfig
            Realtime limits shared by connections and broadcast workers.

        Returns
        -------
        None
            Retain configuration and create empty connection and membership indexes.
        """
        self._config = config
        """Group and broadcast limits shared by this application."""
        self._connections: dict[str, RealtimeConnectionLike] = {}
        """Active realtime connections indexed by identifier."""
        self._hubs: dict[type[Hub], set[str]] = {}
        """Hub registrations associated with active connections."""
        self._groups: dict[tuple[type[Hub], str], set[str]] = {}
        """Realtime group membership and targeting interface."""
        self._memberships: dict[str, set[str]] = {}
        """Group memberships indexed by connection identifier."""

    @property
    def config(self) -> RealtimeConfig:
        """
        Return the application-wide realtime configuration.

        Returns
        -------
        orionis.foundation.config.realtime.entities.realtime.RealtimeConfig
            Invocation, client-result, group, and broadcast limits used by the manager.
        """
        return self._config

    @property
    def connectionCount(self) -> int:
        """
        Count registered connections regardless of readiness or closing state.

        Returns
        -------
        int
            Number of owned entries, including provisional and closing connections.
        """
        return len(self._connections)

    @property
    def groupCount(self) -> int:
        """
        Count nonempty groups across all Hub namespaces.

        Returns
        -------
        int
            Number of Hub/group entries with at least one registered member.
        """
        return len(self._groups)

    def register(self, connection: RealtimeConnectionLike) -> None:
        """
        Register a connection and its initial Hub-local membership state.

        Parameters
        ----------
        connection : orionis.realtime.contracts.connection.RealtimeConnectionLike
            Connection with a valid identifier not already owned by this worker.

        Returns
        -------
        None
            Retain the connection and initialize its Hub and membership indexes.

        Raises
        ------
        ValueError
            If the identifier is invalid or already belongs to a registered connection.
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
        Remove one owned connection and all of its group memberships.

        Parameters
        ----------
        connection : orionis.realtime.contracts.connection.RealtimeConnectionLike
            Exact registered instance; ignore absent or replaced instances.

        Returns
        -------
        None
            Remove its registry and Hub entries and discard empty groups without
            affecting another instance that reused the identifier.
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
        Return a ready, nonclosing connection within an optional Hub namespace.

        Parameters
        ----------
        connection_id : str
            Registered connection identifier to resolve.
        hub : type[orionis.realtime.Hub] or None, optional
            Exact owning Hub class, or ``None`` to disable namespace filtering.

        Returns
        -------
        orionis.realtime.contracts.connection.RealtimeConnectionLike or None
            Ready, nonclosing connection, or ``None`` for absent, unready, closing,
            or differently namespaced entries.
        """
        connection = self._connections.get(connection_id)
        if connection is None or not connection.ready or connection.closing:
            return None
        if hub is not None and connection.hub is not hub:
            return None
        return connection

    def snapshot(self) -> tuple[RealtimeConnectionLike, ...]:
        """
        Return all currently owned connections for lifecycle coordination.

        Returns
        -------
        tuple[orionis.realtime.contracts.connection.RealtimeConnectionLike, ``...``]
            Registered connection references, including provisional and closing ones,
            at the time of the call.
        """
        return tuple(self._connections.values())

    def connectionIds(self, hub: type[Hub]) -> tuple[str, ...]:
        """
        Snapshot ready, nonclosing connection identifiers in one Hub namespace.

        Parameters
        ----------
        hub : type[orionis.realtime.Hub]
            Exact owning Hub class whose recipients should be selected.

        Returns
        -------
        tuple[str, ``...``]
            Ready recipient IDs at the time of the call; an unknown Hub produces
            an empty tuple.
        """
        return tuple(
            identifier for identifier in self._hubs.get(hub, ())
            if self.get(identifier, hub) is not None
        )

    def groupIds(self, hub: type[Hub], group: str) -> tuple[str, ...]:
        """
        Snapshot ready, nonclosing group members within one Hub namespace.

        Parameters
        ----------
        hub : type[orionis.realtime.Hub]
            Exact Hub class owning the requested group.
        group : str
            Group name within the selected Hub namespace.

        Returns
        -------
        tuple[str, ``...``]
            Ready member IDs at the time of the call, or an empty tuple for an
            unknown Hub or group.

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
        Join a nonclosing owned connection to a Hub-local group.

        Parameters
        ----------
        connection_id : str
            Registered connection identifier, including provisional connections.
        group : str
            Group name within the connection's owning Hub namespace.

        Returns
        -------
        None
            Add membership, leaving repeated joins unchanged without using capacity.

        Raises
        ------
        ValueError
            If the group name is invalid.
        ConnectionError
            If the connection is absent or closing.
        RuntimeError
            If adding a membership would exceed the connection's configured limit.
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
        Remove an owned membership and discard empty Hub-local groups.

        Parameters
        ----------
        connection_id : str
            Connection whose membership should be removed, if still registered.
        group : str
            Valid group name in the connection's Hub namespace.

        Returns
        -------
        None
            Discard owned membership; ignore absent IDs and repeated leaves.

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
        Create application-service client selectors for one Hub class.

        Parameters
        ----------
        hub : type[orionis.realtime.Hub]
            Hub class defining the recipient namespace.

        Returns
        -------
        orionis.realtime.HubClients
            Selectors without a connection-specific caller, suitable for services.

        Raises
        ------
        TypeError
            If the supplied value is not a Hub class.
        """
        if not isinstance(hub, type) or not issubclass(hub, Hub):
            error_msg = "Realtime targets require a Hub subclass"
            raise TypeError(error_msg)
        return HubClients(self, hub)

    async def broadcast(
        self, hub: type[Hub], connection_ids: tuple[str, ...], envelope: object,
    ) -> BroadcastResult:
        """
        Broadcast an envelope with per-codec encoding and bounded concurrency.

        Parameters
        ----------
        hub : type[orionis.realtime.Hub]
            Exact Hub namespace restricting every recipient.
        connection_ids : tuple[str, ``...``]
            Recipient identifier occurrences to attempt, without deduplication.
        envelope : object
            Protocol envelope accepted by the selected connection codecs.

        Returns
        -------
        orionis.realtime.BroadcastResult
            Aggregate ``sent`` and ``failed`` counts, including unavailable recipients
            as failures. Empty input returns zero counts.

        Raises
        ------
        TypeError, ValueError
            If encoding fails before recipient delivery starts.
        asyncio.CancelledError
            If delivery is cancelled; admitted connection-owned writes may finish
            independently.
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
