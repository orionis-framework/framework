"""Entry point of the model-less query API, backing the ``DB`` facade."""

from typing import TYPE_CHECKING, Self
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.contracts.transaction import ITransaction
from orionis.database.migrations.context import current_migration_connection
from orionis.orm.contracts.query_builder import IQueryBuilder
from orionis.orm.query.raw_builder import RawQueryBuilder

if TYPE_CHECKING:
    from orionis.database.contracts.connection import IConnection
    from orionis.orm.contracts.raw_builder import IRawQueryBuilder

class QueryBuilder(IQueryBuilder):
    """
    Entry point of the model-less query API, backing the ``DB`` facade.

    Registered as a singleton, so it never keeps per-query state: every
    call returns a brand-new object and the connection scope is carried
    by value. Sharing mutable state here would leak one caller's target
    connection into every other concurrent request.
    """

    # ruff: noqa: TC001

    __slots__ = ("_connection_name", "_db_manager")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self,
        db_manager: IConnectionManager,
        connection_name: str | None = None,
    ) -> None:
        """
        Initialize the gateway with the connection manager to delegate to.

        Parameters
        ----------
        db_manager : orionis.database.contracts.IConnectionManager
            Manager resolving named database connections.
        connection_name : str or None, optional
            Connection every query defaults to, or ``None`` for the
            configured default connection.

        Returns
        -------
        None
            This method does not return a value.
        """
        self._db_manager: IConnectionManager = db_manager
        """Manager resolving named database connections."""
        self._connection_name: str | None = connection_name
        """
        Connection every query defaults to, or ``None`` for the configured default
        connection.
        """

    def connection(
        self,
        name: str | None = None,
    ) -> Self:
        """
        Return a gateway scoped to the connection with the given name.

        A new gateway is returned instead of mutating this one: the
        service is a container singleton, so storing the name on it
        would silently retarget every other caller.

        Parameters
        ----------
        name : str or None, optional
            Connection name as declared in the database configuration,
            or ``None`` for the default connection.

        Returns
        -------
        orionis.orm.query_builder.QueryBuilder
            Gateway bound to the requested connection.
        """
        return type(self)(self._db_manager, name)

    def table(
        self,
        name: str,
        *,
        alias: str | None = None,
        connection: str | None = None,
    ) -> IRawQueryBuilder:
        """
        Build a fluent, model-less query over a plain table name.

        A brand-new builder is created on every call so that concurrent
        callers sharing this gateway never mutate each other's query
        state.

        Parameters
        ----------
        name : str
            Logical table name, without the connection prefix.
        alias : str or None, optional
            Alias the table is referred to by inside the query.
        connection : str or None, optional
            Named connection to run the query against; defaults to the
            connection this gateway is scoped to.

        Returns
        -------
        orionis.orm.contracts.raw_builder.IRawQueryBuilder
            Fluent, model-less query builder over the table.
        """
        builder = RawQueryBuilder()
        target = connection or self._connection_name
        if target is None:
            migration = current_migration_connection()
            target = (
                migration.getName() if migration is not None
                else self._db_manager.getDefaultName()
            )
        builder.connection(target)
        return builder.table(name, alias=alias)

    def getDefaultName(self) -> str:
        """
        Return the name of the default connection.

        Returns
        -------
        str
            Name of the connection used when none is specified.
        """
        return self._db_manager.getDefaultName()

    def setDefaultName(self, name: str) -> None:
        """
        Change the connection used when none is specified.

        Parameters
        ----------
        name : str
            Connection name as declared in the database configuration.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        orionis.database.ConnectionNotFoundException
            If the connection is not declared in the configuration.
        """
        self._db_manager.setDefaultName(name)

    async def select(
        self,
        sql: str,
        bindings: dict[str, object] | None = None,
        name: str | None = None,
    ) -> list[dict[str, object]]:
        """
        Run a raw SELECT statement and return its rows.

        Parameters
        ----------
        sql : str
            Raw SQL using named ``:param`` placeholders.
        bindings : dict or None, optional
            Values bound to the placeholders of the statement.
        name : str or None, optional
            Named connection to run the statement on; defaults to the
            connection this gateway is scoped to.

        Returns
        -------
        list of dict
            One dictionary per row keyed by column name.

        Raises
        ------
        orionis.database.QueryException
            If the statement fails to execute.
        """
        return await self._resolve(name).select(sql, bindings)

    async def execute(
        self,
        sql: str,
        bindings: dict[str, object] | None = None,
        name: str | None = None,
    ) -> int:
        """
        Run a raw data-modifying statement and return the affected rows.

        Parameters
        ----------
        sql : str
            Raw SQL using named ``:param`` placeholders.
        bindings : dict or None, optional
            Values bound to the placeholders of the statement.
        name : str or None, optional
            Named connection to run the statement on; defaults to the
            connection this gateway is scoped to.

        Returns
        -------
        int
            Number of affected rows.

        Raises
        ------
        orionis.database.QueryException
            If the statement fails to execute.
        """
        return await self._resolve(name).execute(sql, bindings)

    async def statement(
        self,
        sql: str,
        bindings: dict[str, object] | None = None,
        name: str | None = None,
    ) -> bool:
        """
        Run a raw statement without inspecting its result.

        Parameters
        ----------
        sql : str
            Raw SQL statement, typically DDL or a maintenance command.
        bindings : dict or None, optional
            Values bound to the placeholders of the statement.
        name : str or None, optional
            Named connection to run the statement on; defaults to the
            connection this gateway is scoped to.

        Returns
        -------
        bool
            ``True`` when the statement executes without errors.

        Raises
        ------
        orionis.database.QueryException
            If the statement fails to execute.
        """
        return await self._resolve(name).statement(sql, bindings)

    async def beginTransaction(
        self,
        name: str | None = None,
    ) -> None:
        """
        Begin a transaction, or a savepoint when one is already active.

        Parameters
        ----------
        name : str or None, optional
            Named connection to start the transaction on, or ``None``
            for the default connection.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        orionis.database.TransactionException
            If the transaction cannot be started.
        """
        await self._resolve(name).begin()

    async def commit(
        self,
        name: str | None = None,
    ) -> None:
        """
        Commit the innermost active transaction or savepoint.

        Parameters
        ----------
        name : str or None, optional
            Named connection to commit, or ``None`` for the default
            connection.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        orionis.database.TransactionException
            If no transaction is active.
        """
        await self._resolve(name).commit()

    async def rollback(
        self,
        name: str | None = None,
    ) -> None:
        """
        Roll back the innermost active transaction or savepoint.

        Parameters
        ----------
        name : str or None, optional
            Named connection to roll back, or ``None`` for the default
            connection.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        orionis.database.TransactionException
            If no transaction is active.
        """
        await self._resolve(name).rollback()

    def transaction(
        self,
        name: str | None = None,
    ) -> ITransaction:
        """
        Return a transaction usable as an async context manager.

        Parameters
        ----------
        name : str or None, optional
            Named connection the transaction runs against, or ``None``
            for the default connection.

        Returns
        -------
        orionis.database.contracts.ITransaction
            Context manager committing on success and rolling back on
            error.
        """
        return self._resolve(name).transaction()

    def _resolve(self, name: str | None) -> IConnection:
        """
        Resolve the connection a call targets.

        Parameters
        ----------
        name : str or None
            Explicit connection name, or ``None`` to fall back to the
            connection this gateway is scoped to.

        Returns
        -------
        orionis.database.contracts.IConnection
            Connection bound to its configuration.

        Raises
        ------
        orionis.database.ConnectionNotFoundException
            If the connection is not declared in the configuration.
        """
        target = name or self._connection_name
        if target is None:
            scoped = current_migration_connection()
            if scoped is not None:
                return scoped
        return self._db_manager.connection(target)



