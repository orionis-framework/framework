from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping
    from orionis.database.contracts.transaction import ITransaction
    from orionis.database.entities.result import InsertResult
    from orionis.orm.query.expressions import (
        DeletePlan,
        InsertPlan,
        SelectPlan,
        UpdatePlan,
    )
    from orionis.orm.schema.table import TableDefinition

class IConnection(ABC):
    """
    Contract for a single named database connection.

    A connection encapsulates the SQL engine entirely: it accepts Orionis
    query plans or raw SQL strings and always returns plain Python values
    (dictionaries, integers, result entities). Engine objects never leak
    through this interface.
    """

    # ruff: noqa: ANN401

    __slots__ = ()

    @abstractmethod
    def getName(self) -> str:
        """
        Return the configured name of this connection.

        Returns
        -------
        str
            Connection name as registered in the manager.
        """

    def supportsUniqueConstraints(self) -> bool:
        """
        Report whether primary and unique keys reject duplicate values.

        Custom connections retain the relational default. Backends whose keys
        are only informational must override this capability so consumers can
        reject operations that require a database-enforced unique claim.

        Returns
        -------
        bool
            Whether uniqueness is enforced by the database.
        """
        return True

    # ── Query execution ─────────────────────────────────────────────────────

    @abstractmethod
    async def select(
        self,
        query: SelectPlan | str,
        bindings: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Run a SELECT query and return its rows as dictionaries.

        Parameters
        ----------
        query : SelectPlan or str
            Compiled query plan, or a raw SQL string using named
            ``:param`` placeholders.
        bindings : Mapping of str to Any, optional
            Bound parameters for raw SQL strings.

        Returns
        -------
        list of dict
            One dictionary per row keyed by column name.

        Raises
        ------
        QueryException
            If the statement fails to compile or execute.
        """

    @abstractmethod
    async def insert(self, plan: InsertPlan) -> InsertResult:
        """
        Run an INSERT statement described by the given plan.

        Parameters
        ----------
        plan : InsertPlan
            Insert plan with the target table and row values.

        Returns
        -------
        InsertResult
            Result carrying the generated key and affected row count.

        Raises
        ------
        QueryException
            If the statement fails to compile or execute.
        """

    @abstractmethod
    async def update(self, plan: UpdatePlan) -> int:
        """
        Run an UPDATE statement described by the given plan.

        Parameters
        ----------
        plan : UpdatePlan
            Update plan with values and filtering conditions.

        Returns
        -------
        int
            Number of affected rows.

        Raises
        ------
        QueryException
            If the statement fails to compile or execute.
        """

    @abstractmethod
    async def delete(self, plan: DeletePlan) -> int:
        """
        Run a DELETE statement described by the given plan.

        Parameters
        ----------
        plan : DeletePlan
            Delete plan with filtering conditions.

        Returns
        -------
        int
            Number of affected rows.

        Raises
        ------
        QueryException
            If the statement fails to compile or execute.
        """

    @abstractmethod
    async def scalar(self, plan: SelectPlan) -> Any:
        """
        Run a SELECT plan and return the first column of the first row.

        Parameters
        ----------
        plan : SelectPlan
            Query plan, typically carrying an aggregate projection.

        Returns
        -------
        Any
            Scalar value, or ``None`` when the query yields no rows.

        Raises
        ------
        QueryException
            If the statement fails to compile or execute.
        """

    @abstractmethod
    async def execute(
        self,
        sql: str,
        bindings: Mapping[str, Any] | None = None,
    ) -> int:
        """
        Run a raw data-modifying SQL statement.

        Parameters
        ----------
        sql : str
            Raw SQL using named ``:param`` placeholders.
        bindings : Mapping of str to Any, optional
            Bound parameters for the statement.

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
        bindings: Mapping[str, Any] | None = None,
    ) -> bool:
        """
        Run a raw SQL statement without inspecting its result.

        Intended for DDL and maintenance commands.

        Parameters
        ----------
        sql : str
            Raw SQL statement.
        bindings : Mapping of str to Any, optional
            Bound parameters for the statement.

        Returns
        -------
        bool
            ``True`` when the statement executes without errors.

        Raises
        ------
        QueryException
            If the statement fails to execute.
        """

    # ── Schema helpers ──────────────────────────────────────────────────────

    @abstractmethod
    async def createTable(
        self,
        table: TableDefinition,
        *,
        if_not_exists: bool = True,
    ) -> bool:
        """
        Create the physical table described by the given definition.

        Parameters
        ----------
        table : TableDefinition
            Table definition to materialize.
        if_not_exists : bool, optional
            Whether to guard the statement with ``IF NOT EXISTS`` so that
            an already existing table is silently kept.

        Returns
        -------
        bool
            ``True`` when the statement executes without errors.

        Raises
        ------
        QueryException
            If the DDL statement fails to execute.
        """

    @abstractmethod
    async def dropTable(
        self,
        name: str,
        schema: str | None = None,
        *,
        if_exists: bool = True,
    ) -> bool:
        """
        Drop the physical table with the given logical name.

        Parameters
        ----------
        name : str
            Logical table name; the connection prefix is applied.
        schema : str or None, optional
            Database schema owning the table, or ``None`` for the default.
        if_exists : bool, optional
            Whether to guard the statement with ``IF EXISTS`` so that a
            missing table does not raise an error.

        Returns
        -------
        bool
            ``True`` when the statement executes without errors.

        Raises
        ------
        QueryException
            If the DDL statement fails to execute.
        """

    # ── Transactions ────────────────────────────────────────────────────────

    @abstractmethod
    async def begin(self) -> None:
        """
        Begin a transaction, or a savepoint when one is already active.

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
    async def commit(self) -> None:
        """
        Commit the innermost active transaction or savepoint.

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
    async def rollback(self) -> None:
        """
        Roll back the innermost active transaction or savepoint.

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
    def transaction(self) -> ITransaction:
        """
        Return a transaction usable as an async context manager.

        Returns
        -------
        ITransaction
            Context manager committing on success and rolling back on error.
        """

    @abstractmethod
    def inTransaction(self) -> bool:
        """
        Report whether a transaction is active in the current task.

        Returns
        -------
        bool
            ``True`` when at least one transaction level is open.
        """

    # ── Lifecycle ───────────────────────────────────────────────────────────

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Dispose the underlying engine and release its pooled resources.

        Returns
        -------
        None
            This method does not return a value.
        """
