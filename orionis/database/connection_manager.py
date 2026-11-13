# ruff: noqa: BLE001, PLC0415, TC001
# Keep runtime contracts and observe secondary lifecycle failures centrally.
"""Resolve named database connections and manage their lifecycle."""

from typing import Any
from asyncio import CancelledError
from threading import RLock
from orionis.database.contracts.connection import IConnection
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.exceptions import ConnectionNotFoundException
from orionis.foundation.contracts.application import IApplication
from orionis.foundation.config.database.entities.database import (
    Database as ConfigDatabase,
)


class ConnectionManager(IConnectionManager):
    """Resolve named database connections and manage their lifecycle."""

    __slots__ = ("_cached_connections", "_connections", "_default", "_lock")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self,
        app: IApplication,
    ) -> None:
        """
        Initialize the manager from the application configuration.

        Parameters
        ----------
        app : orionis.IApplication
            Application container providing the database configuration.

        Returns
        -------
        None
            No return value.
        """
        raw_config: ConfigDatabase | dict[str, Any] = app.config("database")
        payload: dict[str, Any] = (
            raw_config.toDict()
            if isinstance(raw_config, ConfigDatabase)
            else raw_config
        )
        self._connections: dict[str, dict[str, Any]] = dict(
            payload.get("connections") or {},
        )
        """Database configurations indexed by their case-sensitive registered name."""
        configured_default = str(payload["default"])
        self._default: str = (
            configured_default
            if configured_default in self._connections
            else configured_default.lower()
        )
        """Exact registered default name, with the legacy lowercase fallback."""
        self._cached_connections: dict[str, IConnection] = {}
        """Cached connections value, computed on first access."""
        self._lock = RLock()
        """Serialize publication and registry mutation without holding async cleanup."""

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
        orionis.database.contracts.IConnection
            Connection bound to its configuration.

        Raises
        ------
        orionis.database.ConnectionNotFoundException
            If the connection is not declared in the configuration.
        """
        resolved_name: str = name or self._default
        cached = self._cached_connections.get(resolved_name)
        if cached is not None:
            return cached

        with self._lock:
            cached = self._cached_connections.get(resolved_name)
            if cached is None:
                config = self._connections.get(resolved_name)
                if config is None:
                    raise ConnectionNotFoundException(
                        self.__unknownConnectionMessage(resolved_name),
                    )
                from orionis.database.connection import Connection

                cached = Connection(resolved_name, config)
                self._cached_connections[resolved_name] = cached
        return cached

    def addConnection(self, name: str, config: dict[str, Any]) -> None:
        """
        Register or replace a named connection configuration at runtime.

        A live connection built from a previous configuration keeps
        serving until :meth:`orionis.database.ConnectionManager.disconnect` is called
        for that name.

        Parameters
        ----------
        name : str
            Connection name to register.
        config : dict
            Driver configuration for the connection.

        Returns
        -------
        None
            No return value.

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

        with self._lock:
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
            No return value.

        Raises
        ------
        orionis.database.ConnectionNotFoundException
            If the connection is not declared in the configuration.
        """
        with self._lock:
            if name not in self._connections:
                raise ConnectionNotFoundException(self.__unknownConnectionMessage(name))
            self._default = name

    async def disconnect(self, name: str | None = None) -> None:
        """
        Dispose one or all cached connections.

        Attempt every cached connection even if an earlier disconnect fails.
        Propagate cancellation in preference to ordinary errors; otherwise
        preserve the first failure and report additional errors centrally.

        Parameters
        ----------
        name : str or None, optional
            Connection to dispose, or ``None`` to dispose every cached
            connection.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        Exception
            The first ordinary failure after all selected connections settle.
        asyncio.CancelledError
            If cancellation interrupts a disconnect, after remaining attempts.
        """
        if name is not None:
            with self._lock:
                instance = self._cached_connections.pop(name, None)
            if instance is not None:
                await instance.disconnect()
            return

        with self._lock:
            instances = list(self._cached_connections.values())
            self._cached_connections.clear()
        errors: list[BaseException] = []
        for instance in instances:
            try:
                await instance.disconnect()
            except (Exception, CancelledError) as error:
                errors.append(error)
        if errors:
            from orionis.failure.runtime import capture

            primary = next(
                (error for error in errors if isinstance(error, CancelledError)),
                errors[0],
            )
            for error in errors:
                if error is not primary:
                    await capture(error, flow="database", phase="disconnect")
            raise primary

    def configFor(self, name: str | None = None) -> dict[str, Any]:
        """
        Retrieve the configuration for a named connection.

        Parameters
        ----------
        name : str or None, optional
            Connection name to look up, or ``None`` for the default.

        Returns
        -------
        dict[str, typing.Any]
            The configuration dictionary for the requested connection.

        Raises
        ------
        orionis.database.ConnectionNotFoundException
            If the connection is not declared in the configuration.
        """
        resolved_name: str = name or self._default
        config: dict[str, Any] | None = self._connections.get(resolved_name)
        if config is None:
            raise ConnectionNotFoundException(
                self.__unknownConnectionMessage(
                    resolved_name,
                ),
            )
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
            f"Unknown database connection '{name}'. Declared connections: {declared}."
        )
