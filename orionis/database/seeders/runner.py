# ruff: noqa: PLC0415, TC001, TC003
# Preserve runtime injection and load recovery reporting only on failure.
"""Apply new seeders exactly once on the selected database connection."""

import time
from functools import partial
from typing import Any
from pathlib import Path
from orionis.database.contracts.connection import IConnection
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.exceptions import QueryException
from orionis.database.migrations.context import migration_connection_scope
from orionis.database.migrations.discovery import _discover_steps
from orionis.database.migrations.events import _report_failure
from orionis.database.seeders.events import NO_EVENTS, SeederEvents
from orionis.database.seeders.seeder import Seeder
from orionis.foundation.contracts.application import IApplication
from orionis.orm.query.expressions import (
    InsertPlan,
    OrderClause,
    SelectPlan,
    SortDirection,
    UpdatePlan,
    WhereClause,
)
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, Integer, String


class _ClaimFailed(Exception):
    """Signal that inserting a seeder claim failed inside a transaction."""

    __slots__ = ("error",)
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, error: QueryException) -> None:
        """
        Retain the query error that prevented a seeder claim.

        Parameters
        ----------
        error : orionis.database.QueryException
            Query failure that prevented the claim.

        Returns
        -------
        None
            No return value.
        """
        self.error = error
        """Query failure that prevented the claim."""
        super().__init__(str(error))


def _build_seeders_table() -> TableDefinition:
    """
    Build the persistent seeder tracking table definition.

    Returns
    -------
    orionis.orm.schema.TableDefinition
        Table with a unique seeder name, batch and completion timestamp.
    """
    id_column: ColumnDefinition = Integer().primary().autoIncrement()
    id_column.name = "id"

    seeder_column: ColumnDefinition = String(255).unique()
    seeder_column.name = "seeder"

    batch_column: ColumnDefinition = Integer()
    batch_column.name = "batch"

    seeded_at_column: ColumnDefinition = BigInteger()
    seeded_at_column.name = "seeded_at"

    return TableDefinition(
        name="seeders",
        columns={
            "id": id_column,
            "seeder": seeder_column,
            "batch": batch_column,
            "seeded_at": seeded_at_column,
        },
        primary_key="id",
    )


_SEEDERS_TABLE: TableDefinition = _build_seeders_table()
"""Seeders table used by ``runner``."""


class SeederRunner:
    """
    Apply new seeders exactly once on the selected database connection.

    Files under ``database/seeders`` are discovered in lexical filename
    order. The application container builds each seeder so constructors can
    receive dependencies. Each seeder and its tracking row commit in the same
    transaction. The unique tracking key acts as a database-level claim when
    runs overlap.
    """

    # The container resolves constructor dependencies from runtime types.

    __slots__ = ("__app", "__conn_manager", "__discovered_cache")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self,
        app: IApplication,
        conn_manager: IConnectionManager,
    ) -> None:
        """
        Initialize the runner with the application and connection manager.

        Parameters
        ----------
        app : orionis.IApplication
            Application providing the seeder directory.
        conn_manager : orionis.database.contracts.IConnectionManager
            Manager resolving configured database connections.

        Returns
        -------
        None
            No return value.
        """
        self.__app = app
        """Application providing the seeder directory."""
        self.__conn_manager = conn_manager
        """Manager resolving configured database connections."""
        self.__discovered_cache: dict[str, type[Seeder]] | None = None
        """Cached results of filesystem discovery."""

    async def seed(
        self,
        *,
        connection: str | None = None,
        events: SeederEvents | None = None,
    ) -> list[str]:
        """
        Run every discovered seeder that has no committed tracking row.

        Parameters
        ----------
        connection : str or None, optional
            Named database connection, or the configured default.
        events : orionis.database.seeders.events.SeederEvents or None, optional
            Progress callbacks for executed seeders.

        Returns
        -------
        list of str
            Seeder names completed by this call, in execution order.
        """
        target = self.__conn_manager.connection(connection)
        if not target.supportsUniqueConstraints():
            message = (
                "Once-only seeders require enforced unique constraints; "
                "Amazon Redshift cannot guarantee exclusive seeder claims."
            )
            raise QueryException(message)
        await self.__ensureTrackingTable(target)

        ran = await self.__getRan(target)
        ran_names = {row["seeder"] for row in ran}
        pending = [
            (name, cls)
            for name, cls in self.__discover().items()
            if name not in ran_names
        ]
        if not pending:
            return []

        batch = max((int(row["batch"]) for row in ran), default=0) + 1
        reporter = events or NO_EVENTS
        applied: list[str] = []
        for name, seeder_cls in pending:
            if await self.__runStep(target, name, seeder_cls, batch, reporter):
                applied.append(name)
        return applied

    async def __ensureTrackingTable(self, connection: IConnection) -> None:
        """
        Create the tracking table, tolerating a concurrent creator.

        Parameters
        ----------
        connection : orionis.database.contracts.IConnection
            Selected database connection.

        Returns
        -------
        None
            No return value.
        """
        try:
            await connection.createTable(_SEEDERS_TABLE)
        except QueryException as exc:
            # createTable checks for existence before issuing DDL. Another
            # process may create it between those statements on a fresh DB.
            try:
                await self.__getRan(connection)
            except QueryException:
                raise exc from None
            from orionis.failure.runtime import capture

            await capture(
                exc,
                app=self.__app,
                flow="database",
                phase="recovery",
                operation="seeders.schema",
                expected=True,
            )

    def __seedersPath(self) -> Path:
        """
        Return the application's configured seeder directory.

        Returns
        -------
        pathlib.Path
            Absolute path under ``database/seeders``.
        """
        return self.__app.path("database_seeders")

    def __discover(self) -> dict[str, type[Seeder]]:
        """
        Find local Seeder subclasses in deterministic filename order.

        Returns
        -------
        dict of str ``to`` type of orionis.database.seeders.Seeder
            Seeder classes keyed by persisted filename stem.

        Raises
        ------
        ValueError
            If more than one class resolves to the same persisted name.
        """
        if self.__discovered_cache is not None:
            return self.__discovered_cache

        self.__discovered_cache = _discover_steps(
            self.__app.basePath,
            self.__seedersPath(),
            Seeder,
            "seeder",
        )
        return self.__discovered_cache

    async def __getRan(self, connection: IConnection) -> list[dict[str, Any]]:
        """
        Read committed tracking rows in insertion order.

        Parameters
        ----------
        connection : orionis.database.contracts.IConnection
            Connection holding the tracking table.

        Returns
        -------
        list of dict
            Tracking rows ordered by primary key.
        """
        return await connection.select(
            SelectPlan(
                table=_SEEDERS_TABLE,
                columns=("id", "seeder", "batch", "seeded_at"),
                orders=[OrderClause("id", SortDirection.ASC)],
            ),
        )

    async def __isRecorded(self, connection: IConnection, name: str) -> bool:
        """
        Check whether another transaction committed this seeder.

        Observe a failed recovery read without replacing the pending claim error.
        The caller propagates that original error when recovery is unconfirmed.
        Return False after observing a QueryException that prevents the lookup.

        Parameters
        ----------
        connection : orionis.database.contracts.IConnection
            Connection holding the tracking table.
        name : str
            Seeder filename stem.

        Returns
        -------
        bool
            Whether a committed tracking row was confirmed by the recovery read.
        """
        try:
            rows = await connection.select(
                SelectPlan(
                    table=_SEEDERS_TABLE,
                    columns=("id",),
                    wheres=[WhereClause(column="seeder", value=name)],
                    limit_value=1,
                ),
            )
        except QueryException as error:
            from orionis.failure.runtime import capture

            await capture(
                error,
                app=self.__app,
                flow="database",
                phase="recovery",
                operation="seeders.claim",
            )
            return False
        return bool(rows)

    async def __runStep(
        self,
        connection: IConnection,
        name: str,
        seeder_cls: type[Seeder],
        batch: int,
        events: SeederEvents,
    ) -> bool:
        """
        Claim, run and commit one seeder and its tracking row.

        Parameters
        ----------
        connection : orionis.database.contracts.IConnection
            Connection shared by the seeder and tracking transaction.
        name : str
            Persisted seeder filename stem.
        seeder_cls : type of orionis.database.seeders.Seeder
            Class to instantiate and execute.
        batch : int
            Batch assigned to this invocation.
        events : orionis.database.seeders.events.SeederEvents
            Progress callbacks.

        Returns
        -------
        bool
            Whether this call executed the seeder.
        """
        started_at = time.perf_counter()
        started = False
        try:
            async with connection.transaction():
                try:
                    await connection.insert(
                        InsertPlan(
                            table=_SEEDERS_TABLE,
                            values=[
                                {
                                    "seeder": name,
                                    "batch": batch,
                                    "seeded_at": 0,
                                },
                            ],
                        ),
                    )
                except QueryException as exc:
                    raise _ClaimFailed(exc) from exc

                events.started(name)
                started = True
                with migration_connection_scope(connection):
                    seeder = await self.__app.build(seeder_cls)
                    await seeder.run()
                await connection.update(
                    UpdatePlan(
                        table=_SEEDERS_TABLE,
                        values={"seeded_at": int(time.time())},
                        wheres=[WhereClause(column="seeder", value=name)],
                    ),
                )
        except _ClaimFailed as exc:
            if await self.__isRecorded(connection, name):
                from orionis.failure.runtime import capture

                await capture(
                    exc.error,
                    app=self.__app,
                    flow="database",
                    phase="recovery",
                    operation="seeders.claim",
                    expected=True,
                )
                return False
            _report_failure(partial(events.started, name), exc.error)
            _report_failure(
                partial(events.failed, name, time.perf_counter() - started_at),
                exc.error,
            )
            # Preserve the original driver cause instead of the internal wrapper.
            raise exc.error from exc.error.__cause__
        except Exception as error:
            if started:
                _report_failure(
                    partial(events.failed, name, time.perf_counter() - started_at),
                    error,
                )
            raise

        events.succeeded(name, time.perf_counter() - started_at)
        return True
