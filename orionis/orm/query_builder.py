from typing import TYPE_CHECKING, Self
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.contracts.transaction import ITransaction
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

    def __init__(
        self,
        db_manager: IConnectionManager,
        connection_name: str | None = None,
    ) -> None:
        """
        Initialize the gateway with the connection manager to delegate to.

        Parameters
        ----------
        db_manager : IConnectionManager
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
        self._connection_name: str | None = connection_name

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
        QueryBuilder
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
        IRawQueryBuilder
            Fluent, model-less query builder over the table.
        """
        builder = RawQueryBuilder()
        target = connection or self._connection_name
        if target is not None:
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
        ConnectionNotFoundException
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
        QueryException
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
        QueryException
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
        QueryException
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
        TransactionException
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
        TransactionException
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
        TransactionException
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
        ITransaction
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
        IConnection
            Connection bound to its configuration.

        Raises
        ------
        ConnectionNotFoundException
            If the connection is not declared in the configuration.
        """
        return self._db_manager.connection(name or self._connection_name)



