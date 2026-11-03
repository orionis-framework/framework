"""Named database connection encapsulating the SQL engine."""

from __future__ import annotations
from asyncio import CancelledError, create_task, current_task, ensure_future
from contextlib import asynccontextmanager
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
from orionis.database.threaded.worker import _wait_for_completion
from orionis.database.transaction import Transaction

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Mapping, Sequence
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
"""Error message used when transaction control has no active transaction."""

@lru_cache(maxsize=256)
def _text_statement(sql: str) -> TextClause:
    """
    Parse and cache a SQL string as a reusable textual statement.

    Parameters
    ----------
    sql : str
        SQL text with optional named ``:param`` placeholders.

    Returns
    -------
    ``sqlalchemy.sql.elements.TextClause``
        SQLAlchemy textual statement with parsed bind parameters.
    """
    return text(sql)

class _TransactionState:
    """Per-task stack of open transactions bound to one raw connection."""

    __slots__ = ("connection", "owner", "transactions")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self,
        connection: AsyncConnection | ThreadedConnection,
        transaction: AsyncTransaction | ThreadedTransaction,
    ) -> None:
        """
        Bind a raw connection and root transaction to the current task.

        Parameters
        ----------
        connection : ``AsyncConnection`` | ThreadedConnection
            Open connection shared by all transaction levels.
        transaction : ``AsyncTransaction`` | ThreadedTransaction
            Root transaction used to initialize the stack.

        Returns
        -------
        None
            Store the connection, owning task, and transaction stack.
        """
        self.connection = connection
        """Open connection shared by all transaction levels."""
        self.owner = current_task()
        """Owner produced by ``current_task``."""
        self.transactions: list[AsyncTransaction | ThreadedTransaction] = [transaction]
        """Transaction scopes currently associated with the connection context."""

    async def __aenter__(self) -> AsyncConnection | ThreadedConnection:
        """
        Return the existing raw connection without acquiring another one.

        Returns
        -------
        ``AsyncConnection`` | ThreadedConnection
            Open connection retained by the transaction owner.
        """
        return self.connection

    async def __aexit__(self, *exc_info: object) -> None:
        """
        Leave transaction control and cleanup to the owning task.

        Parameters
        ----------
        *exc_info : object
            Exception details supplied by the context manager; unused.

        Returns
        -------
        None
            Leave the connection and transaction stack unchanged.
        """

class Connection(IConnection):
    """
    Named database connection encapsulating the SQL engine.

    The connection lazily builds its async engine from the Orionis
    configuration, compiles query plans through :class:`orionis.database.SQLCompiler`,
    and exposes only framework-owned types: dictionaries, integers,
    and result entities. Transactions are task-local and support
    nesting through savepoints when supported. Redshift uses the official
    blocking connector through a thread-backed Core engine; it does not
    support savepoints or returning server-generated identity values.
    """

    # ruff: noqa: ANN401

    __slots__ = ("_compiler", "_config", "_engine", "_name", "_tx_state")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self,
        name: str,
        config: dict[str, Any],
    ) -> None:
        """
        Validate the driver and initialize a lazy named connection.

        No engine or database connection is created until first use.

        Parameters
        ----------
        name : str
            Name identifying this connection in the manager.
        config : dict of str ``to`` typing.Any
            Driver, connection settings, and optional table prefix.

        Returns
        -------
        None
            Copy the settings and initialize the compiler and task-local state.

        Raises
        ------
        orionis.database.UnsupportedDriverException
            If the driver is missing or unsupported.
        """
        # Validate the driver eagerly so misconfiguration fails fast.
        driver = resolve_driver(config)

        self._name = name
        """Name identifying this connection in the manager."""
        self._config = dict(config)
        """Driver, connection settings, and optional table prefix."""
        self._engine: AsyncEngine | ThreadedEngine | None = None
        """Database engine, created lazily when the connection is first used."""
        self._compiler = SQLCompiler(
            str(self._config.get("prefix", "") or ""), driver=driver,
        )
        """Compiler produced by ``SQLCompiler``."""
        # Task-local transaction state keeps concurrent tasks isolated.
        self._tx_state: ContextVar[_TransactionState | None] = ContextVar(
            f"orionis_db_tx_{name}",
            default=None,
        )
        """Task-local transaction state keeps concurrent tasks isolated."""

    def getName(self) -> str:
        """
        Return this connection's registered name.

        Returns
        -------
        str
            Name assigned at construction.
        """
        return self._name

    def supportsUniqueConstraints(self) -> bool:
        """
        Report whether the configured backend enforces key uniqueness.

        Returns
        -------
        bool
            ``False`` for Redshift; ``True`` for all other registered drivers.
        """
        return resolve_driver(self._config) != "redshift"

    def toSql(self, plan: SelectPlan, *, literal_binds: bool = False) -> str:
        """
        Render a SELECT plan without creating an engine or executing SQL.

        Parameters
        ----------
        plan : orionis.orm.query.SelectPlan
            Query plan to render with the configured connection dialect.
        literal_binds : bool, optional
            Include bound values for debugging instead of placeholders. Values
            may contain sensitive data; some types cannot be rendered literally.

        Returns
        -------
        str
            SQL text with expanded parameters and the configured table prefix.

        Raises
        ------
        orionis.database.QueryException
            If the plan or a literal value cannot be compiled.
        orionis.database.MissingDatabaseDependencyException
            If the configured SQL dialect is unavailable.
        """
        try:
            statement = self._compiler.compileSelect(plan)
            if self._engine is None:
                if resolve_driver(self._config) == "redshift":
                    import_module("sqlalchemy_redshift.dialect")
                dialect = build_engine_url(self._config).get_dialect(_is_async=True)()
            elif isinstance(self._engine, ThreadedEngine):
                dialect = self._engine.sync_engine.dialect
            else:
                dialect = self._engine.dialect
            return str(statement.compile(
                dialect=dialect,
                compile_kwargs={
                    "literal_binds": literal_binds,
                    "render_postcompile": True,
                },
            ))
        except (ImportError, NoSuchModuleError) as exc:
            raise missing_dependency_error(
                resolve_driver(self._config), exc,
            ) from exc
        except SQLAlchemyError as exc:
            raise self._queryException(exc) from None

    # ── Query execution ─────────────────────────────────────────────────────

    async def select(
        self,
        query: SelectPlan | str,
        bindings: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a SELECT plan or raw SQL and materialize its rows.

        Parameters
        ----------
        query : orionis.orm.query.SelectPlan or str
            Query plan to compile, or SQL using named ``:param`` placeholders.
        bindings : collections.abc.Mapping of str ``to`` typing.Any, optional
            Parameters for raw SQL only; ignored when ``query`` is a plan.

        Returns
        -------
        list of dict
            Rows keyed by column name, materialized before connection release.
            Return an empty list when no rows match.

        Raises
        ------
        orionis.database.QueryException
            If compilation, execution, or connection cleanup fails.
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
        Execute an INSERT plan and report its key and row count.

        Parameters
        ----------
        plan : orionis.orm.query.InsertPlan
            Target table and one or more rows to insert.

        Returns
        -------
        orionis.database.entities.InsertResult
            Affected row count and optional first primary-key value. Keys are
            reported only for single-row inserts when the driver provides one.

        Raises
        ------
        orionis.database.QueryException
            If compilation, execution, or connection cleanup fails.
        """
        parameters = (
            plan.values if self._compiler.supportsBatchInsert(plan) else None
        )
        statement = self._compiler.compileInsert(
            plan, parameterized=parameters is not None,
        )
        if resolve_driver(self._config) in {"oracle", "sqlserver", "redshift"}:
            # Oracle closes executemany cursors before lazy rowcount access;
            # Paged insertmanyvalues needs aggregated actual row counts.
            statement = statement.execution_options(preserve_rowcount=True)

        async with self._acquire() as connection:
            result = await self._run(connection, statement, parameters)
            # The generated key is only reported for single-row inserts.
            last_id: Any = None
            if len(plan.values) == 1:
                generated = result.inserted_primary_key
                if generated is not None and len(generated) > 0:
                    last_id = generated[0]
            row_count = (
                sum(1 for _row in result.mappings())
                if parameters is not None and resolve_driver(self._config) == "pgsql"
                else int(result.rowcount or 0)
            )
            if (
                resolve_driver(self._config) == "sqlserver"
                and row_count < 0
                and result.returned_defaults_rows is not None
            ):
                # pyodbc reports -1 for INSERT ... OUTPUT. Core has already
                # buffered those actual server rows to extract generated keys.
                row_count = len(result.returned_defaults_rows)
            return InsertResult(
                last_insert_id=last_id,
                row_count=row_count,
            )

    async def update(
        self,
        plan: UpdatePlan,
    ) -> int:
        """
        Execute an UPDATE plan and return the driver's affected row count.

        Parameters
        ----------
        plan : orionis.orm.query.UpdatePlan
            Target table, replacement values, and filtering conditions.

        Returns
        -------
        int
            Backend row count, which may count matched rather than changed rows.

        Raises
        ------
        orionis.database.QueryException
            If compilation, execution, or connection cleanup fails.
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
        Execute a DELETE plan and return the driver's affected row count.

        Parameters
        ----------
        plan : orionis.orm.query.DeletePlan
            Target table and conditions selecting the rows to delete.

        Returns
        -------
        int
            Driver-reported number of deleted rows.

        Raises
        ------
        orionis.database.QueryException
            If compilation, execution, or connection cleanup fails.
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
        Execute a SELECT plan and return its first scalar value.

        Parameters
        ----------
        plan : orionis.orm.query.SelectPlan
            Query plan whose first row and column provide the result.

        Returns
        -------
        typing.Any
            First column of the first row, or ``None`` when no rows are returned.

        Raises
        ------
        orionis.database.QueryException
            If compilation, execution, or connection cleanup fails.
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
        Execute raw SQL and return the driver's affected row count.

        Parameters
        ----------
        sql : str
            Data-modifying SQL with optional named ``:param`` placeholders.
        bindings : collections.abc.Mapping of str ``to`` typing.Any, optional
            Values bound to the statement's named parameters.

        Returns
        -------
        int
            Row count supplied by the driver, or ``0`` when it supplies none.

        Raises
        ------
        orionis.database.QueryException
            If execution or cleanup fails; SQL and bound values are omitted.
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
        Execute raw SQL and discard its result.

        Use this for DDL or maintenance commands with no result to consume.

        Parameters
        ----------
        sql : str
            SQL statement with optional named ``:param`` placeholders.
        bindings : collections.abc.Mapping of str ``to`` typing.Any, optional
            Values bound to the statement's named parameters.

        Returns
        -------
        bool
            ``True`` after the statement and connection cleanup succeed.

        Raises
        ------
        orionis.database.QueryException
            If execution or connection cleanup fails.
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
        Create a table from its schema definition.

        Parameters
        ----------
        table : orionis.orm.schema.TableDefinition
            Logical table definition; the connection prefix is applied.
        if_not_exists : bool, optional
            Skip creation when the table already exists. Defaults to ``True``.

        Returns
        -------
        bool
            ``True`` after creating the table or keeping an existing one.

        Raises
        ------
        orionis.database.QueryException
            If schema compilation, creation, or connection cleanup fails.
        """
        statement = self._compiler.compileCreateTable(
            table, if_not_exists=if_not_exists,
        )
        async with self._acquire(sqlite_immediate=True) as connection:
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
        Drop a table using its logical name and optional schema.

        Parameters
        ----------
        name : str
            Logical name to drop after applying the connection prefix.
        schema : str or None, optional
            Schema owning the table, or ``None`` for the default schema.
        if_exists : bool, optional
            Request ``IF EXISTS`` protection for a missing table. Defaults to
            ``True``.

        Returns
        -------
        bool
            ``True`` when the DROP statement completes without errors.

        Raises
        ------
        orionis.database.QueryException
            If schema compilation, execution, or connection cleanup fails.
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
        Begin a task-local transaction or create a nested savepoint.

        Returns
        -------
        None
            Push the new transaction level onto the current task's stack.

        Raises
        ------
        orionis.database.TransactionException
            If acquisition or transaction control fails, nesting is unsupported,
            or an active transaction belongs to another task.
        """
        state = self._transactionState()
        try:
            if state is None:
                # Open a dedicated raw connection with a root transaction.
                raw = await self._getEngine().connect()
                try:
                    transaction = (
                        await raw.begin() if isinstance(raw, ThreadedConnection)
                        else await _wait_for_completion(ensure_future(raw.begin()))
                    )
                except BaseException as exc:
                    try:
                        if isinstance(exc, CancelledError):
                            await _wait_for_completion(create_task(raw.invalidate()))
                    finally:
                        await _wait_for_completion(create_task(raw.close()))
                    raise
                self._tx_state.set(_TransactionState(raw, transaction))
            else:
                # Nested calls open a savepoint on the same connection.
                if isinstance(state.connection, ThreadedConnection):
                    error_msg = "Amazon Redshift does not support nested transactions."
                    raise TransactionException(error_msg)
                savepoint = await _wait_for_completion(
                    ensure_future(state.connection.begin_nested()),
                    on_cancel=lambda late: _wait_for_completion(
                        create_task(late.rollback()),
                    ),
                )
                state.transactions.append(savepoint)
        except SQLAlchemyError as exc:
            error_msg = (
                f"Unable to begin transaction on connection '{self._name}' "
                f"({type(exc).__name__})."
            )
            raise TransactionException(error_msg) from None

    async def commit(self) -> None:
        """
        Commit the current task's innermost transaction or savepoint.

        Returns
        -------
        None
            Close the connection when no transaction levels remain.

        Raises
        ------
        orionis.database.TransactionException
            If no level is active, it belongs to another task, or commit fails.
        orionis.database.QueryException
            If releasing the settled connection fails.
        """
        state = self._transactionState()
        if state is None or not state.transactions:
            raise TransactionException(_NO_ACTIVE_TRANSACTION)

        transaction = state.transactions.pop()
        try:
            if isinstance(state.connection, ThreadedConnection):
                await transaction.commit()
            else:
                await _wait_for_completion(create_task(transaction.commit()))
        except CancelledError:
            await _wait_for_completion(create_task(state.connection.invalidate()))
            raise
        except SQLAlchemyError as exc:
            if isinstance(state.connection, ThreadedConnection):
                await state.connection.invalidate()
            error_msg = (
                f"Unable to commit transaction on connection '{self._name}' "
                f"({type(exc).__name__})."
            )
            raise TransactionException(error_msg) from None
        finally:
            await self._releaseIfSettled(state)

    async def rollback(self) -> None:
        """
        Roll back the current task's innermost transaction or savepoint.

        Returns
        -------
        None
            Close the connection when no transaction levels remain.

        Raises
        ------
        orionis.database.TransactionException
            If no level is active, it belongs to another task, or rollback fails.
        orionis.database.QueryException
            If releasing the settled connection fails.
        """
        state = self._transactionState()
        if state is None or not state.transactions:
            raise TransactionException(_NO_ACTIVE_TRANSACTION)

        transaction = state.transactions.pop()
        try:
            if isinstance(state.connection, ThreadedConnection):
                await transaction.rollback()
            else:
                await _wait_for_completion(create_task(transaction.rollback()))
        except CancelledError:
            await _wait_for_completion(create_task(state.connection.invalidate()))
            raise
        except SQLAlchemyError as exc:
            if isinstance(state.connection, ThreadedConnection):
                await state.connection.invalidate()
            error_msg = (
                f"Unable to roll back transaction on connection '{self._name}' "
                f"({type(exc).__name__})."
            )
            raise TransactionException(error_msg) from None
        finally:
            await self._releaseIfSettled(state)

    def transaction(self) -> ITransaction:
        """
        Return a context manager for a task-local transaction.

        Returns
        -------
        orionis.database.contracts.ITransaction
            Unentered context manager that commits on success or rolls back
            when its block raises an exception.
        """
        return Transaction(self)

    def inTransaction(self) -> bool:
        """
        Report whether the current task owns an active transaction.

        Returns
        -------
        bool
            ``True`` when this task owns a nonempty transaction stack.
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
        Dispose the cached engine and release its idle pooled connections.

        Returns
        -------
        None
            Clear the cached engine reference; skip disposal if no engine exists.

        Raises
        ------
        orionis.database.QueryException
            If engine disposal fails.
        """
        if self._engine is not None:
            engine = self._engine
            self._engine = None
            try:
                await _wait_for_completion(create_task(engine.dispose()))
            except SQLAlchemyError as exc:
                raise self._queryException(exc) from None

    # ── Internal plumbing ───────────────────────────────────────────────────

    def _getEngine(self) -> AsyncEngine | ThreadedEngine:
        """
        Return the cached engine, creating and configuring it on first use.

        Returns
        -------
        ``sqlalchemy.ext.asyncio.AsyncEngine`` | threaded.engine.ThreadedEngine
            Native async engine or Redshift's thread-backed engine adapter.

        Raises
        ------
        orionis.database.MissingDatabaseDependencyException
            If a required DBAPI package or registered dialect is unavailable.
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
        Return transaction state owned by the current task.

        Returns
        -------
        orionis.database.connection._TransactionState | None
            State for this task, or ``None`` if no usable state exists.

        Raises
        ------
        orionis.database.TransactionException
            If another task owns an inherited state with active transaction levels.
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
        *,
        sqlite_immediate: bool = False,
    ) -> (
        AbstractAsyncContextManager[AsyncConnection | ThreadedConnection]
        | _TransactionState
    ):
        """
        Return a context manager for reusing or acquiring a connection.

        Reuse an owned transaction without committing it; otherwise open a
        temporary transaction and close its connection on exit.

        Parameters
        ----------
        sqlite_immediate : bool, optional
            Reserve SQLite writes before starting a temporary transaction.
            Leave existing transactions and other database drivers unchanged.

        Returns
        -------
        contextlib.AbstractAsyncContextManager or connection._TransactionState
            Context yielding the raw connection used for statement execution.

        Raises
        ------
        orionis.database.TransactionException
            If an active transaction is inherited from another task.
        orionis.database.MissingDatabaseDependencyException
            If engine creation requires an unavailable driver or dialect.
        """
        state = self._transactionState()
        if state is not None:
            # Reuse the transactional connection without committing.
            return state

        engine = self._getEngine()
        driver = resolve_driver(self._config)
        if driver == "redshift":
            return engine.begin()
        if sqlite_immediate and driver == "sqlite" and isinstance(engine, AsyncEngine):
            engine = engine.execution_options(sqlite_begin_immediate=True)

        @asynccontextmanager
        async def protected() -> AsyncGenerator[AsyncConnection | ThreadedConnection]:
            """
            Yield a temporary connection and drain transaction control on exit.

            Keep pool acquisition cancellable; finish transaction control and
            connection cleanup before propagating cancellation.

            Yields
            ------
            ``sqlalchemy.ext.asyncio.AsyncConnection`` | connection.ThreadedConnection
                Raw connection with an active temporary transaction.

            Raises
            ------
            orionis.database.QueryException
                If a SQLAlchemy error occurs during connection use or cleanup.
            asyncio.CancelledError
                If cancelled while acquiring or using the temporary connection.
            """
            try:
                raw = await engine.connect()
                try:
                    transaction = raw.begin()
                    await _wait_for_completion(create_task(transaction.__aenter__()))
                    try:
                        yield raw
                    except BaseException as exc:
                        await _wait_for_completion(create_task(
                            transaction.__aexit__(type(exc), exc, exc.__traceback__),
                        ))
                        raise
                    else:
                        await _wait_for_completion(create_task(
                            transaction.__aexit__(None, None, None),
                        ))
                except CancelledError:
                    await _wait_for_completion(create_task(raw.invalidate()))
                    raise
                finally:
                    await _wait_for_completion(create_task(raw.close()))
            except SQLAlchemyError as exc:
                raise self._queryException(exc) from None

        return protected()

    async def _run(
        self,
        connection: AsyncConnection | ThreadedConnection,
        statement: Any,
        parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    ) -> CursorResult[Any] | ThreadedResult:
        """
        Execute a SQLAlchemy statement and sanitize database errors.

        Parameters
        ----------
        connection
            Open raw connection used for execution.
        statement : typing.Any
            SQLAlchemy executable, including textual statements.
        parameters
            Named bind parameters or per-row parameter mappings for a batch.

        Returns
        -------
        ``sqlalchemy.engine.CursorResult`` | threaded.result.ThreadedResult
            Raw driver result to be consumed by the calling connection method.

        Raises
        ------
        orionis.database.QueryException
            If execution raises a SQLAlchemy error; driver details are omitted.
        """
        try:
            if resolve_driver(self._config) == "oracle":
                # Drain the native thin-driver operation before rollback or pool
                # release. Cancelling its protocol await can leave a late DML
                # response racing with the next transaction-control message.
                operation = create_task(
                    connection.execute(statement, parameters)
                    if parameters else connection.execute(statement),
                )
                return await _wait_for_completion(operation)
            if parameters:
                return await connection.execute(statement, parameters)
            return await connection.execute(statement)
        except SQLAlchemyError as exc:
            raise self._queryException(exc) from None

    def _queryException(self, error: SQLAlchemyError) -> QueryException:
        """
        Build a query error containing only the connection name and error type.

        Parameters
        ----------
        error : ``sqlalchemy.exc.SQLAlchemyError``
            Original SQLAlchemy error; only its class name is retained.

        Returns
        -------
        orionis.database.QueryException
            Framework exception without SQL, parameters, or the driver message.
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
        Release the raw connection when its transaction stack becomes empty.

        Parameters
        ----------
        state : orionis.database.connection._TransactionState
            State whose remaining transaction levels determine whether to close.

        Returns
        -------
        None
            Clear task-local state and close only a fully settled connection.

        Raises
        ------
        orionis.database.QueryException
            If closing the settled connection fails.
        """
        if not state.transactions:
            self._tx_state.set(None)
            try:
                await _wait_for_completion(create_task(state.connection.close()))
            except SQLAlchemyError as exc:
                raise self._queryException(exc) from None
