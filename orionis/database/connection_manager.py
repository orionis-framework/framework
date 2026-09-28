from typing import Any
from orionis.database.connection import Connection
from orionis.database.contracts.connection import IConnection
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.exceptions import ConnectionNotFoundException
from orionis.foundation.contracts.application import IApplication
from orionis.foundation.config.database.entities.database import (
    Database as ConfigDatabase,
)

class ConnectionManager(IConnectionManager):

    # ruff: noqa: TC001

    __slots__ = ("_cached_connections", "_connections", "_default")

    def __init__(
        self,
        app: IApplication,
    ) -> None:
        """
        Initialize the manager from the application configuration.

        Parameters
        ----------
        app : IApplication
            Application container providing the database configuration.

        Returns
        -------
        None
            This method does not return a value.
        """
        raw_config: ConfigDatabase | dict[str, Any] = app.config("database")
        payload: dict[str, Any] = (
            raw_config.toDict()
            if isinstance(raw_config, ConfigDatabase)
            else raw_config
        )
        self._default: str = str(payload["default"]).lower()
        self._connections: dict[str, dict[str, Any]] = dict(
            payload.get("connections") or {},
        )
        self._cached_connections: dict[str, IConnection] = {}

    def connection(
        self,
        name: str | None = None,
    ) -> IConnection:
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
        resolved_name: str = name or self._default
        cached = self._cached_connections.get(resolved_name)
        if cached is not None:
            return cached

        config: dict[str, Any] | None = self._connections.get(resolved_name)
        if config is None:
            raise ConnectionNotFoundException(self.__unknownConnectionMessage(
                resolved_name,
            ))

        instance = Connection(resolved_name, config)
        self._cached_connections[resolved_name] = instance
        return instance

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
        if not isinstance(name, str) or not name.strip():
            error_msg = "Connection name must be a non-empty string."
            raise ValueError(error_msg)
        if not isinstance(config, dict):
            error_msg = "Connection configuration must be a dict."
            raise TypeError(error_msg)

        self._connections[name] = config

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
        return name in self._connections

    def getDefaultName(self) -> str:
        """
        Return the name of the default connection.

        Returns
        -------
        str
            Default connection name as configured.
        """
        return self._default

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
        if name not in self._connections:
            raise ConnectionNotFoundException(self.__unknownConnectionMessage(name))
        self._default = name

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
        if name is not None:
            instance: IConnection | None = self._cached_connections.pop(name, None)
            if instance is not None:
                await instance.disconnect()
            return

        instances: list[IConnection] = list(self._cached_connections.values())
        self._cached_connections.clear()
        for instance in instances:
            await instance.disconnect()

    def configFor(self, name: str | None = None) -> dict[str, Any]:
        """
        Retrieve the configuration for a named connection.

        Parameters
        ----------
        name : str or None, optional
            Connection name to look up, or ``None`` for the default.

        Returns
        -------
        dict[str, Any]
            The configuration dictionary for the requested connection.

        Raises
        ------
        ConnectionNotFoundException
            If the connection is not declared in the configuration.
        """
        resolved_name: str = name or self._default
        config: dict[str, Any] | None = self._connections.get(resolved_name)
        if config is None:
            raise ConnectionNotFoundException(self.__unknownConnectionMessage(
                resolved_name,
            ))
        return config

    def __unknownConnectionMessage(self, name: str) -> str:
        """
        Build the descriptive message for an unresolved connection name.

        Parameters
        ----------
        name : str
            Connection name that failed to resolve.

        Returns
        -------
        str
            Descriptive message listing the declared connection names.
        """
        declared = ", ".join(sorted(self._connections)) or "none"
        return (
            f"Unknown database connection '{name}'. "
            f"Declared connections: {declared}."
        )
