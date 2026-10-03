from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.realtime.decorators import validate_remote_name

if TYPE_CHECKING:
    from collections.abc import Iterable
    from orionis.realtime.contracts.manager import IConnectionManager
    from orionis.realtime.entities import BroadcastResult
    from orionis.realtime.hub import Hub

_MAX_IDENTIFIER = 128
_MAX_GROUP = 256
_MAX_ARGUMENTS = 64


def validate_identifier(value: str, label: str = "Identifier") -> None:
    """
    Validate a bounded, nonempty connection or public method identifier.

    Parameters
    ----------
    value : str
        Identifier supplied by application code.
    label : str, optional
        Description included in a validation error.

    Returns
    -------
    None
        Accept the identifier without modifying it.

    Raises
    ------
    ValueError
        If the identifier is missing, non-string or longer than 128 characters.
    """
    if not isinstance(value, str) or not value.strip() or len(value) > _MAX_IDENTIFIER:
        error_msg = (
            f"{label} must be a nonempty string of at most {_MAX_IDENTIFIER} chars"
        )
        raise ValueError(error_msg)


def validate_group(group: str) -> None:
    """
    Validate a bounded, nonempty group name.

    Parameters
    ----------
    group : str
        Hub-local group name supplied by application code.

    Returns
    -------
    None
        Accept the group name without modifying it.

    Raises
    ------
    ValueError
        If the name is missing, non-string or longer than 256 characters.
    """
    if not isinstance(group, str) or not group.strip() or len(group) > _MAX_GROUP:
        error_msg = f"Group must be a nonempty string of at most {_MAX_GROUP} chars"
        raise ValueError(error_msg)


def _validate_call(target: str, args: tuple[object, ...]) -> None:
    """
    Validate a public client target and its argument count.

    Parameters
    ----------
    target : str
        Remote client method or event name.
    args : tuple[object, ...]
        Positional values to serialize.

    Returns
    -------
    None
        Accept the public target and up to 64 positional arguments.

    Raises
    ------
    ValueError
        If a target is private, qualified, oversized or has too many arguments.
    """
    validate_remote_name(target)
    if len(args) > _MAX_ARGUMENTS:
        error_msg = "Client target must accept at most 64 arguments"
        raise ValueError(error_msg)


class ClientTarget:
    """Send to a Hub-local selection or invoke one explicitly selected client."""

    __slots__ = ("_excluded", "_group", "_hub", "_ids", "_manager", "_single")

    def __init__(
        self,
        manager: IConnectionManager,
        hub: type[Hub],
        *,
        connection_ids: tuple[str, ...] | str | None = None,
        group: str | None = None,
        excluded: str | None = None,
    ) -> None:
        """
        Store a connection selection without retaining connection objects.

        Parameters
        ----------
        manager : IConnectionManager
            Registry owning local connections.
        hub : type[Hub]
            Namespace limiting every selected recipient.
        connection_ids : tuple[str, ...] | str | None, optional
            A single recipient, multiple recipients, or None for all/group members.
        group : str | None, optional
            Hub-local group to select when no identifiers are supplied.
        excluded : str | None, optional
            Connection to omit from an all-connections or group selection.

        Returns
        -------
        None
            Store the selection without validating or resolving recipients.
        """
        self._manager = manager
        self._hub = hub
        self._single = isinstance(connection_ids, str)
        self._ids: tuple[str, ...] | None = (
            (connection_ids,) if isinstance(connection_ids, str) else connection_ids
        )
        self._group = group
        self._excluded = excluded

    def _recipients(self) -> tuple[str, ...]:
        """
        Snapshot the identifiers selected for Hub-local delivery.

        Returns
        -------
        tuple[str, ...]
            Explicit identifiers unchanged, or current ready all/group members
            with the excluded connection omitted.

        Raises
        ------
        ValueError
            If a selected group name is invalid.
        """
        if self._ids is not None:
            return self._ids
        selected = (
            self._manager.groupIds(self._hub, self._group)
            if self._group is not None else self._manager.connectionIds(self._hub)
        )
        if self._excluded is not None:
            return tuple(value for value in selected if value != self._excluded)
        return selected

    async def send(self, target: str, *args: object) -> BroadcastResult:
        """
        Deliver a client event and report per-recipient delivery outcomes.

        Parameters
        ----------
        target : str
            Public client event or method name.
        *args : object
            Up to 64 positional values encoded into the event envelope.

        Returns
        -------
        BroadcastResult
            Counts of successful and failed deliveries; no offline persistence.

        Raises
        ------
        ValueError
            If the target, argument count, selected group name or event envelope
            is invalid.
        TypeError
            If the event envelope contains values unsupported by the codec.
        """
        _validate_call(target, args)
        return await self._manager.broadcast(
            self._hub,
            self._recipients(),
            {"type": "send", "target": target, "args": list(args)},
        )

    async def invoke(
        self, target: str, *args: object,
        timeout: float | None = None,  # noqa: ASYNC109 # NOSONAR
    ) -> object:
        """
        Invoke one selected client and await its correlated completion.

        Parameters
        ----------
        target : str
            Public client method name.
        *args : object
            Up to 64 positional values supplied to the client method.
        timeout : float | None, optional
            Total send/result deadline in seconds, or None to use the
            connection's configured client-result timeout.

        Returns
        -------
        object
            Result supplied by the selected client, including None.

        Raises
        ------
        RuntimeError
            If the selection is not a single-client target or the pending
            client-result budget is exhausted.
        ConnectionError
            If the client is unavailable in this Hub namespace or disconnects.
        ValueError
            If the target, argument count or deadline is invalid.
        TimeoutError
            If sending or receiving the completion exceeds the deadline.
        ClientInvocationError
            If the client returns a completion error.
        """
        _validate_call(target, args)
        if not self._single or self._ids is None:
            error_msg = "Client results require .client(connection_id) or .caller"
            raise RuntimeError(error_msg)
        connection = self._manager.get(self._ids[0], self._hub)
        if connection is None:
            error_msg = "The selected client is disconnected or unavailable"
            raise ConnectionError(error_msg)
        return await connection.invoke(target, *args, timeout=timeout)


class HubClients:
    """Select ready clients within one Hub in the current worker."""

    __slots__ = ("_caller_id", "_hub", "_manager")

    def __init__(
        self,
        manager: IConnectionManager,
        hub: type[Hub],
        caller_id: str | None = None,
    ) -> None:
        """
        Bind Hub-local client selection to an optional caller.

        Parameters
        ----------
        manager : IConnectionManager
            Registry owning the connections.
        hub : type[Hub]
            Hub namespace selecting eligible clients.
        caller_id : str | None, optional
            Current connection identifier; absent for application services.

        Returns
        -------
        None
            Store the registry, Hub namespace and optional caller identifier.
        """
        self._manager = manager
        self._hub = hub
        self._caller_id = caller_id

    @property
    def all(self) -> ClientTarget:
        """
        Return a target for every ready connection to this Hub.

        Returns
        -------
        ClientTarget
            Target resolving ready Hub connections at delivery time.
        """
        return ClientTarget(self._manager, self._hub)

    @property
    def caller(self) -> ClientTarget:
        """
        Return a target for the calling connection.

        Returns
        -------
        ClientTarget
            Single-client target supporting event delivery and invocation.

        Raises
        ------
        RuntimeError
            If this proxy was created outside a Hub connection.
        ValueError
            If the caller identifier is invalid.
        """
        return self.client(self._caller())

    @property
    def others(self) -> ClientTarget:
        """
        Return a target excluding the calling connection.

        Returns
        -------
        ClientTarget
            Target resolving other ready Hub connections at delivery time.

        Raises
        ------
        RuntimeError
            If this proxy was created outside a Hub connection.
        """
        return ClientTarget(self._manager, self._hub, excluded=self._caller())

    def _caller(self) -> str:
        """
        Require a connection-specific caller identifier.

        Returns
        -------
        str
            Calling connection's identifier.

        Raises
        ------
        RuntimeError
            If this proxy was created outside a Hub connection.
        """
        if self._caller_id is None:
            error_msg = "Caller targets are available only within a Hub connection"
            raise RuntimeError(error_msg)
        return self._caller_id

    def client(self, connection_id: str) -> ClientTarget:
        """
        Select one connection for event delivery or bidirectional invocation.

        Parameters
        ----------
        connection_id : str
            Identifier belonging to a connection in this Hub.

        Returns
        -------
        ClientTarget
            Single recipient target; unavailable recipients fail on delivery.

        Raises
        ------
        ValueError
            If the identifier is empty, non-string or longer than 128 characters.
        """
        validate_identifier(connection_id, "Connection identifier")
        return ClientTarget(
            self._manager, self._hub, connection_ids=connection_id,
        )

    def clients(self, connection_ids: Iterable[str]) -> ClientTarget:
        """
        Select explicit recipients, preserving order and removing duplicates.

        Parameters
        ----------
        connection_ids : Iterable[str]
            Connection identifiers belonging to this Hub.

        Returns
        -------
        ClientTarget
            Multi-recipient target supporting event delivery.

        Raises
        ------
        TypeError
            If the input is a string, bytes or a noniterable value.
        ValueError
            If any identifier is invalid.
        """
        if isinstance(connection_ids, (str, bytes)):
            error_msg = "Multiple clients require an iterable of identifiers"
            raise TypeError(error_msg)
        unique: dict[str, None] = {}
        for identifier in connection_ids:
            validate_identifier(identifier, "Connection identifier")
            unique[identifier] = None
        return ClientTarget(self._manager, self._hub, connection_ids=tuple(unique))

    def group(self, name: str) -> ClientTarget:
        """
        Select a named group within this Hub namespace.

        Parameters
        ----------
        name : str
            Nonempty group name, at most 256 characters.

        Returns
        -------
        ClientTarget
            Target resolving current group membership at delivery time.

        Raises
        ------
        ValueError
            If the name is empty, non-string or longer than 256 characters.
        """
        validate_group(name)
        return ClientTarget(self._manager, self._hub, group=name)
