from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from orionis.database.contracts.connection import IConnection

class IConnectionManager(ABC):

    __slots__ = ()

    @abstractmethod
    def connection(self, name: str | None = None) -> IConnection:
        """
        Resolve the connection registered under the given name.

        The connection is built on first access and cached for reuse.

        Parameters
        ----------
        name : str or None, optional
            Connection name as declared in the database configuration,
            or ``None`` for the default connection.

        Returns
        -------
        IConnection
            Connection bound to its configuration.

        Raises
        ------
        ConnectionNotFoundException
            If the connection is not declared in the configuration.
        """

    @abstractmethod
    def addConnection(self, name: str, config: dict[str, Any]) -> None:
        """
        Register or replace a named connection configuration at runtime.

        A live connection built from a previous configuration keeps
        serving until :meth:`disconnect` is called for that name.

        Parameters
        ----------
        name : str
            Connection name to register.
        config : dict
            Driver configuration for the connection.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If the name is empty.
        TypeError
            If the configuration is not a mapping.
        """

    @abstractmethod
    def hasConnection(self, name: str) -> bool:
        """
        Report whether a connection configuration exists.

        Parameters
        ----------
        name : str
            Connection name to look up.

        Returns
        -------
        bool
            ``True`` when the configuration is registered.
        """

    @abstractmethod
    def getDefaultName(self) -> str:
        """
        Return the name of the default connection.

        Returns
        -------
        str
            Default connection name as configured.
        """

    @abstractmethod
    def setDefaultName(self, name: str) -> None:
        """
        Change the default connection name.

        Parameters
        ----------
        name : str
            Connection name to use as the default; must already be
            declared in the configuration.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ConnectionNotFoundException
            If the connection is not declared in the configuration.
        """

    @abstractmethod
    async def disconnect(self, name: str | None = None) -> None:
        """
        Dispose one or all cached connections.

        Parameters
        ----------
        name : str or None, optional
            Connection to dispose, or ``None`` to dispose every cached
            connection.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    def configFor(self, name: str | None = None) -> dict[str, Any]:
        """
        Retrieve the configuration for a named connection.

        Parameters
        ----------
        name : str or None, optional
            Connection name as declared in the database configuration,
            or ``None`` for the default connection.

        Returns
        -------
        dict
            The driver configuration for the connection.

        Raises
        ------
        ConnectionNotFoundException
            If the connection is not declared in the configuration.
        """
