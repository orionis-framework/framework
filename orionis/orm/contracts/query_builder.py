from __future__ import annotations
from abc import abstractmethod, ABC
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from orionis.database.contracts.transaction import ITransaction
    from orionis.orm.contracts.raw_builder import IRawQueryBuilder

class IQueryBuilder(ABC):
    """
    Contract of the entry point backing the ``DB`` facade.

    Implementations resolve named connections, start model-less queries,
    and drive transactions. They are registered as singletons, so every
    method must be free of per-query state: the connection scope travels
    with the returned object rather than being stored on the service.
    """

    __slots__ = ()

    @abstractmethod
    def connection(
        self,
        name: str | None = None,
    ) -> Self:
        """
        Return a gateway scoped to the connection with the given name.

        Parameters
        ----------
        name : str or None, optional
            Connection name as declared in the database configuration,
            or ``None`` for the default connection.

        Returns
        -------
        Self
            Gateway bound to the requested connection.

        Raises
        ------
        ConnectionNotFoundException
            If the connection is not declared in the configuration.
        """

    @abstractmethod
    def table(
        self,
        name: str,
        *,
        alias: str | None = None,
        connection: str | None = None,
    ) -> IRawQueryBuilder:
        """
        Build a fluent, model-less query over a plain table name.

        Parameters
        ----------
        name : str
            Logical table name, without the connection prefix.
        alias : str or None, optional
            Alias the table is referred to by inside the query.
        connection : str or None, optional
            Named connection to run the query against, or ``None`` for
            the default connection.

        Returns
        -------
        IRawQueryBuilder
            Fluent, model-less query builder over the table.
        """

    @abstractmethod
    async def beginTransaction(self, name: str | None = None) -> None:
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

    @abstractmethod
    async def commit(self, name: str | None = None) -> None:
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

    @abstractmethod
    async def rollback(self, name: str | None = None) -> None:
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

    @abstractmethod
    def transaction(self, name: str | None = None) -> ITransaction:
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

    @abstractmethod
    def getDefaultName(self) -> str:
        """
        Return the name of the default connection.

        Returns
        -------
        str
            Name of the connection used when none is specified.
        """

    @abstractmethod
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

    @abstractmethod
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
            Named connection to run the statement on, or ``None`` for
            the connection this gateway is scoped to.

        Returns
        -------
        list of dict
            One dictionary per row keyed by column name.

        Raises
        ------
        QueryException
            If the statement fails to execute.
        """

    @abstractmethod
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
            Named connection to run the statement on, or ``None`` for
            the connection this gateway is scoped to.

        Returns
        -------
        int
            Number of affected rows.

        Raises
        ------
        QueryException
            If the statement fails to execute.
        """

    @abstractmethod
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
            Named connection to run the statement on, or ``None`` for
            the connection this gateway is scoped to.

        Returns
        -------
        bool
            ``True`` when the statement executes without errors.

        Raises
        ------
        QueryException
            If the statement fails to execute.
        """
