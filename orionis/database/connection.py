from __future__ import annotations
from asyncio import current_task
from contextvars import ContextVar
from functools import lru_cache
from importlib import import_module
from typing import TYPE_CHECKING, Any
from sqlalchemy import create_engine, text
from sqlalchemy.exc import NoSuchModuleError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from orionis.database.compiler import SQLCompiler
from orionis.database.contracts.connection import IConnection
from orionis.database.dialect import (
    build_engine_url,
    configure_engine,
    engine_options,
    missing_dependency_error,
    resolve_driver,
)
from orionis.database.entities.result import InsertResult
from orionis.database.exceptions import QueryException, TransactionException
from orionis.database.threaded.connection import ThreadedConnection
from orionis.database.threaded.engine import ThreadedEngine
from orionis.database.transaction import Transaction

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from contextlib import AbstractAsyncContextManager
    from sqlalchemy.engine import CursorResult
    from sqlalchemy.ext.asyncio import AsyncConnection, AsyncTransaction
    from sqlalchemy.sql.elements import TextClause
    from orionis.database.contracts.transaction import ITransaction
    from orionis.database.threaded.result import ThreadedResult
    from orionis.database.threaded.transaction import ThreadedTransaction
    from orionis.orm.query.expressions import (
        DeletePlan,
        InsertPlan,
        SelectPlan,
        UpdatePlan,
    )
    from orionis.orm.schema.table import TableDefinition

# Error message used when transaction control has no active transaction.
_NO_ACTIVE_TRANSACTION: str = "No active transaction on this connection."

@lru_cache(maxsize=256)
def _text_statement(sql: str) -> TextClause:
    """
    Parse a SQL string into a reusable parameterized statement.

    Parameters
    ----------
    sql : str
        Value supplied for ``sql``.

    Returns
    -------
    TextClause
        Result of the operation described above.
    """
    return text(sql)

class _TransactionState:
    """Per-task stack of open transactions bound to one raw connection."""

    __slots__ = ("connection", "owner", "transactions")

    def __init__(
        self,
        connection: AsyncConnection | ThreadedConnection,
        transaction: AsyncTransaction | ThreadedTransaction,
    ) -> None:
        """
        Initialize the state with its root transaction.

        Parameters
        ----------
        connection : AsyncConnection | ThreadedConnection
            Raw connection owning the transaction stack.
        transaction : AsyncTransaction | ThreadedTransaction
            Root transaction opened on the connection.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.connection = connection
        self.owner = current_task()
        self.transactions: list[AsyncTransaction | ThreadedTransaction] = [transaction]

    async def __aenter__(self) -> AsyncConnection | ThreadedConnection:
        """
        Expose the wrapped connection without opening a new one.

        Returns
        -------
        AsyncConnection | ThreadedConnection
            The wrapped, already-open connection.
        """
        return self.connection

    async def __aexit__(self, *exc_info: object) -> None:
        """
        Leave the wrapped connection open for the enclosing transaction.

        Parameters
        ----------
        *exc_info : object
            Exception information from the ``with`` block; unused since
            the transaction lifecycle is controlled by its owner.

        Returns
        -------
        None
            This method does not return a value.
        """

class Connection(IConnection):
    """
    Named database connection encapsulating the SQL engine.

    The connection lazily builds its async engine from the Orionis
    configuration, compiles query plans through :class:`SQLCompiler`,
    and exposes only framework-owned types: dictionaries, integers,
    and result entities. Transactions are task-local and support
    nesting through savepoints when supported. Redshift uses the official
    blocking connector through a thread-backed Core engine; it does not
    support savepoints or returning server-generated identity values.
    """

    # ruff: noqa: ANN401

    __slots__ = ("_compiler", "_config", "_engine", "_name", "_tx_state")

    def __init__(
        self,
        name: str,
        config: dict[str, Any],
    ) -> None:
        """
        Initialize the connection with its configuration.

        Parameters
        ----------
        name : str
            Connection name as registered in the manager.
        config : dict
            Driver configuration for the connection.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        UnsupportedDriverException
            If the configured driver has no registered dialect.
        """
        # Validate the driver eagerly so misconfiguration fails fast.
        driver = resolve_driver(config)

        self._name = name
        self._config = dict(config)
        self._engine: AsyncEngine | ThreadedEngine | None = None
        self._compiler = SQLCompiler(
            str(self._config.get("prefix", "") or ""), driver=driver,
        )
        # Task-local transaction state keeps concurrent tasks isolated.
        self._tx_state: ContextVar[_TransactionState | None] = ContextVar(
            f"orionis_db_tx_{name}",
            default=None,
        )

    def getName(self) -> str:
        """
        Return the configured name of this connection.

        Returns
        -------
        str
            Connection name as registered in the manager.
        """
        return self._name

    # ── Query execution ─────────────────────────────────────────────────────

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
        if isinstance(query, str):
            statement: Any = _text_statement(query)
            parameters = bindings
        else:
            statement = self._compiler.compileSelect(query)
            parameters = None

        async with self._acquire() as connection:
            result = await self._run(connection, statement, parameters)
            # Materialize rows before the connection is released.
            return [dict(row) for row in result.mappings()]

    async def insert(
        self,
        plan: InsertPlan,
    ) -> InsertResult:
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
        parameters = (
            plan.values if self._compiler.supportsBatchInsert(plan) else None
        )
        statement = self._compiler.compileInsert(
            plan, parameterized=parameters is not None,
        )

        async with self._acquire() as connection:
            result = await self._run(connection, statement, parameters)
            # The generated key is only reported for single-row inserts.
            last_id: Any = None
            if len(plan.values) == 1:
                generated = result.inserted_primary_key
                if generated is not None and len(generated) > 0:
                    last_id = generated[0]
            return InsertResult(
                last_insert_id=last_id,
                row_count=int(result.rowcount or 0),
            )

    async def update(
        self,
        plan: UpdatePlan,
    ) -> int:
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
        statement = self._compiler.compileUpdate(plan)
        async with self._acquire() as connection:
            result = await self._run(connection, statement)
            return int(result.rowcount or 0)

    async def delete(
        self,
        plan: DeletePlan,
    ) -> int:
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
        statement = self._compiler.compileDelete(plan)
        async with self._acquire() as connection:
            result = await self._run(connection, statement)
            return int(result.rowcount or 0)

    async def scalar(
        self,
        plan: SelectPlan,
    ) -> Any:
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
        statement = self._compiler.compileSelect(plan)
        async with self._acquire() as connection:
            result = await self._run(connection, statement)
            return result.scalar()

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
            If the statement fails to execute. Driver messages and bound
            values are excluded because they may contain credentials.
        """
        async with self._acquire() as connection:
            result = await self._run(connection, _text_statement(sql), bindings)
            return int(result.rowcount or 0)

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
        async with self._acquire() as connection:
            await self._run(connection, _text_statement(sql), bindings)
            return True

    # ── Schema helpers ──────────────────────────────────────────────────────

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
        statement = self._compiler.compileCreateTable(
            table, if_not_exists=if_not_exists,
        )
        async with self._acquire() as connection:
            try:
                run_sync = (
                    connection.runSync
                    if isinstance(connection, ThreadedConnection)
                    else connection.run_sync
                )
                await run_sync(statement.element.create, checkfirst=if_not_exists)
            except SQLAlchemyError as exc:
                raise self._queryException(exc) from None
            return True

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
        statement = self._compiler.compileDropTable(
            name, schema, if_exists=if_exists,
        )
        async with self._acquire() as connection:
            await self._run(connection, statement)
            return True

    # ── Transactions ────────────────────────────────────────────────────────

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
        state = self._transactionState()
        try:
            if state is None:
                # Open a dedicated raw connection with a root transaction.
                raw = await self._getEngine().connect()
                try:
                    transaction = await raw.begin()
                except BaseException:
                    await raw.close()
                    raise
                self._tx_state.set(_TransactionState(raw, transaction))
            else:
                # Nested calls open a savepoint on the same connection.
                if isinstance(state.connection, ThreadedConnection):
                    error_msg = "Amazon Redshift does not support nested transactions."
                    raise TransactionException(error_msg)
                savepoint = await state.connection.begin_nested()
                state.transactions.append(savepoint)
        except SQLAlchemyError as exc:
            error_msg = f"Unable to begin transaction: {exc}"
            raise TransactionException(error_msg) from exc

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
            If no transaction is active or the commit fails.
        """
        state = self._transactionState()
        if state is None or not state.transactions:
            raise TransactionException(_NO_ACTIVE_TRANSACTION)

        transaction = state.transactions.pop()
        try:
            await transaction.commit()
        except SQLAlchemyError as exc:
            error_msg = f"Unable to commit transaction: {exc}"
            raise TransactionException(error_msg) from exc
        finally:
            await self._releaseIfSettled(state)

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
            If no transaction is active or the rollback fails.
        """
        state = self._transactionState()
        if state is None or not state.transactions:
            raise TransactionException(_NO_ACTIVE_TRANSACTION)

        transaction = state.transactions.pop()
        try:
            await transaction.rollback()
        except SQLAlchemyError as exc:
            error_msg = f"Unable to roll back transaction: {exc}"
            raise TransactionException(error_msg) from exc
        finally:
            await self._releaseIfSettled(state)

    def transaction(self) -> ITransaction:
        """
        Return a transaction usable as an async context manager.

        Returns
        -------
        ITransaction
            Context manager committing on success and rolling back on error.
        """
        return Transaction(self)

    def inTransaction(self) -> bool:
        """
        Report whether a transaction is active in the current task.

        Returns
        -------
        bool
            ``True`` when at least one transaction level is open.
        """
        state = self._tx_state.get()
        return (
            state is not None
            and state.owner is current_task()
            and bool(state.transactions)
        )

    # ── Lifecycle ───────────────────────────────────────────────────────────

    async def disconnect(self) -> None:
        """
        Dispose the underlying engine and release its pooled resources.

        Returns
        -------
        None
            This method does not return a value.
        """
        if self._engine is not None:
            engine = self._engine
            self._engine = None
            await engine.dispose()

    # ── Internal plumbing ───────────────────────────────────────────────────

    def _getEngine(self) -> AsyncEngine | ThreadedEngine:
        """
        Build the asynchronous engine or blocking-driver adapter on first use.

        Returns
        -------
        AsyncEngine | ThreadedEngine
            Configured engine for this connection.

        Raises
        ------
        MissingDatabaseDependencyException
            If the driver package or its SQLAlchemy dialect is not installed.
        """
        if self._engine is None:
            url = build_engine_url(self._config)
            options = engine_options(self._config)
            try:
                if resolve_driver(self._config) == "redshift":
                    import_module("sqlalchemy_redshift.dialect")
                engine = (
                    ThreadedEngine(create_engine(url, **options), self._name)
                    if resolve_driver(self._config) == "redshift"
                    else create_async_engine(url, **options)
                )
            except (ImportError, NoSuchModuleError) as exc:
                raise missing_dependency_error(
                    resolve_driver(self._config),
                    exc,
                ) from exc
            configure_engine(engine, self._config)
            self._engine = engine
        return self._engine

    def _transactionState(self) -> _TransactionState | None:
        """
        Resolve the transaction owned by the current asyncio task.

        Returns
        -------
        _TransactionState | None
            Result of the operation described above.
        """
        state = self._tx_state.get()
        if state is None or state.owner is current_task():
            return state
        if state.transactions:
            error_msg = (
                "An active transaction cannot be shared with a child task. "
                "Execute its queries in the task that began the transaction."
            )
            raise TransactionException(error_msg)
        self._tx_state.set(None)
        return None

    def _acquire(
        self,
    ) -> (
        AbstractAsyncContextManager[AsyncConnection | ThreadedConnection]
        | _TransactionState
    ):
        """
        Resolve the connection context to execute statements on.

        Inside a transaction the transactional connection is reused;
        otherwise an ephemeral autocommit connection is opened. The
        context manager is returned directly to the caller.

        Returns
        -------
        AbstractAsyncContextManager
            Context manager yielding the connection to execute on.
        """
        state = self._transactionState()
        if state is not None:
            # Reuse the transactional connection without committing.
            return state

        return self._getEngine().begin()

    async def _run(
        self,
        connection: AsyncConnection | ThreadedConnection,
        statement: Any,
        parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    ) -> CursorResult[Any] | ThreadedResult:
        """
        Execute a statement translating engine errors into Orionis errors.

        Parameters
        ----------
        connection : AsyncConnection | ThreadedConnection
            Raw connection to execute on.
        statement : Any
            Executable statement or textual clause.
        parameters : Mapping, Sequence of Mapping or None, optional
            Bound parameters for a statement or a batch of row mappings.

        Returns
        -------
        CursorResult | ThreadedResult
            Raw execution result, consumed internally by callers.

        Raises
        ------
        QueryException
            If the statement fails to execute.
        """
        try:
            if parameters:
                return await connection.execute(statement, parameters)
            return await connection.execute(statement)
        except SQLAlchemyError as exc:
            raise self._queryException(exc) from None

    def _queryException(self, error: SQLAlchemyError) -> QueryException:
        """
        Create a query exception without exposing SQL or bound values.

        Parameters
        ----------
        error : SQLAlchemyError
            Database error whose type identifies the failure.

        Returns
        -------
        QueryException
            Sanitized exception identifying the connection and error type.
        """
        return QueryException(
            f"Query failed on connection '{self._name}' "
            f"({type(error).__name__}).",
        )

    async def _releaseIfSettled(
        self,
        state: _TransactionState,
    ) -> None:
        """
        Close the raw connection once every transaction level is settled.

        Parameters
        ----------
        state : _TransactionState
            Transaction state to inspect and release.

        Returns
        -------
        None
            This method does not return a value.
        """
        if not state.transactions:
            self._tx_state.set(None)
            await state.connection.close()
