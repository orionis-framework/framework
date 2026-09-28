from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
from orionis.database.migrations.context import current_migration_connection
from orionis.orm.exceptions import OrmConfigurationException

if TYPE_CHECKING:
    from orionis.database.contracts.connection import IConnection
    from orionis.database.contracts.connection_manager import IConnectionManager

class ConnectionResolver:
    """
    Static bridge between the ORM and the database connection manager.

    The database service provider installs the manager here during boot;
    models and query builders resolve their connections through this
    class without ever touching the container or the SQL engine.
    """

    _manager: ClassVar[IConnectionManager | None] = None

    @classmethod
    def setManager(cls, manager: IConnectionManager) -> None:
        """
        Install the connection manager used by every model.

        Parameters
        ----------
        manager : IConnectionManager
            Manager resolving named database connections.

        Returns
        -------
        None
            This method does not return a value.
        """
        cls._manager = manager

    @classmethod
    def manager(cls) -> IConnectionManager:
        """
        Return the installed connection manager.

        Returns
        -------
        IConnectionManager
            Manager resolving named database connections.

        Raises
        ------
        OrmConfigurationException
            If no manager has been installed yet.
        """
        if cls._manager is None:
            error_msg = (
                "No connection manager installed. Boot the application or "
                "call ConnectionResolver.setManager() before querying models."
            )
            raise OrmConfigurationException(error_msg)
        return cls._manager

    @classmethod
    def connection(cls, name: str | None = None) -> IConnection:
        """
        Resolve a database connection by name.

        Parameters
        ----------
        name : str or None, optional
            Connection name, or ``None`` for the default connection.

        Returns
        -------
        IConnection
            Resolved connection.

        Raises
        ------
        OrmConfigurationException
            If no manager has been installed yet.
        ConnectionNotFoundException
            If the connection is not declared in the configuration.
        """
        if name is None:
            migration_connection = current_migration_connection()
            if migration_connection is not None:
                return migration_connection
        return cls.manager().connection(name)

    @classmethod
    def clear(cls) -> None:
        """
        Remove the installed manager, mainly for test isolation.

        Returns
        -------
        None
            This method does not return a value.
        """
        cls._manager = None
