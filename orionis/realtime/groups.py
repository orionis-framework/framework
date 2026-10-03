from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.realtime.contracts.manager import IConnectionManager


class HubGroups:
    """Manage group membership owned by the current Hub connection."""

    __slots__ = ("_connection_id", "_manager")

    def __init__(self, manager: IConnectionManager, connection_id: str) -> None:
        """
        Bind membership operations to one owned connection.

        Parameters
        ----------
        manager : IConnectionManager
            Registry owning this connection and its Hub namespace.
        connection_id : str
            Current connection identifier.

        Returns
        -------
        None
            Store the registry and connection identifier for membership changes.
        """
        self._manager = manager
        self._connection_id = connection_id

    async def join(self, group: str) -> None: # NOSONAR
        """
        Join a group without consuming another slot for existing membership.

        Parameters
        ----------
        group : str
            Hub-local group name, at most 256 characters.

        Returns
        -------
        None
            Add the current connection, subject to its configured group limit.

        Raises
        ------
        ValueError
            If the group name is invalid.
        ConnectionError
            If the connection is absent or closing.
        RuntimeError
            If another membership would exceed the configured group limit.
        """
        self._manager.join(self._connection_id, group)

    async def leave(self, group: str) -> None: # NOSONAR
        """
        Remove the current connection from one group idempotently.

        Parameters
        ----------
        group : str
            Hub-local group name.

        Returns
        -------
        None
            Remove membership and discard groups with no remaining members.

        Raises
        ------
        ValueError
            If the group name is invalid.
        """
        self._manager.leave(self._connection_id, group)
