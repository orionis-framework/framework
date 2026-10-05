import asyncio
import traceback
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, uuid5
from orionis.database.exceptions import QueryException
from orionis.orm.query.expressions import (
    DeletePlan,
    InsertPlan,
    OrderClause,
    SelectPlan,
    WhereClause,
)
from orionis.queues.contracts.failed_repository import IFailedJobRepository
from orionis.queues.entities.failed_job import FailedJob
from orionis.queues.functions import current_time
from orionis.queues.schema import build_failed_jobs_table

if TYPE_CHECKING:
    from orionis.database.contracts.connection import IConnection
    from orionis.queues.entities.reserved_job import ReservedJob

class DatabaseFailedJobRepository(IFailedJobRepository):
    """Retain failed envelopes and diagnostics in framework-owned DB storage."""

    __slots__ = ("_connection", "_definition", "_ready", "_ready_lock")

    def __init__(self, connection: IConnection, table: str = "failed_jobs") -> None:
        """
        Bind failure storage to a framework database connection.

        Parameters
        ----------
        connection : IConnection
            Shared framework connection used for failure persistence.
        table : str, optional
            Logical table name for recorded failures.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self._connection = connection
        self._definition = build_failed_jobs_table(table)
        self._ready = False
        self._ready_lock = asyncio.Lock()

    async def _ensureSchema(self) -> None:
        """
        Create the failure table on first use.

        Returns
        -------
        None
            Ensure the failure storage exists.
        """
        if self._ready:
            return
        async with self._ready_lock:
            if not self._ready:
                try:
                    await self._connection.createTable(self._definition)
                except QueryException:
                    if self._connection.inTransaction():
                        raise
                    # Verify another worker created the complete table concurrently.
                    await self._connection.select(SelectPlan(
                        table=self._definition,
                        columns=self._definition.columnNames(),
                        limit_value=0,
                    ))
                self._ready = not self._connection.inTransaction()

    async def record(
        self, reserved: ReservedJob, connection: str, exception: Exception,
    ) -> FailedJob:
        """
        Record a terminal failure once for this reservation token.

        Parameters
        ----------
        reserved : ReservedJob
            Reservation whose encoded envelope must remain retryable.
        connection : str
            Queue connection on which the job failed.
        exception : Exception
            Original failure including its traceback.

        Returns
        -------
        FailedJob
            Persisted failure or its existing idempotent record.
        """
        await self._ensureSchema()
        failure = FailedJob(
            id=str(uuid5(
                NAMESPACE_URL,
                f"orionis:queue:{connection}:{reserved.id}:{reserved.token}",
            )),
            job_id=reserved.id, connection=connection,
            queue=reserved.queue, payload=reserved.payload,
            attempts=reserved.attempts,
            exception_type=(
                f"{type(exception).__module__}.{type(exception).__qualname__}"
            ),
            exception_message=str(exception),
            traceback="".join(traceback.format_exception(exception)),
            failed_at=current_time(),
        )
        try:
            await self._connection.insert(InsertPlan(
                table=self._definition,
                values=[{
                    field: getattr(failure, field)
                    for field in self._definition.columns
                }],
            ))
        except QueryException:
            existing = await self.find(failure.id)
            if existing is None:
                raise
            return existing
        return failure

    async def all(self) -> tuple[FailedJob, ...]:
        """
        Return recorded failures in chronological order.

        Returns
        -------
        tuple of FailedJob
            Persisted failed jobs ordered by timestamp and identifier.
        """
        await self._ensureSchema()
        rows = await self._connection.select(SelectPlan(
            table=self._definition,
            orders=[OrderClause("failed_at"), OrderClause("id")],
        ))
        return tuple(FailedJob(**row) for row in rows)

    async def find(self, failure_id: str) -> FailedJob | None:
        """
        Find one persisted failure by identifier.

        Parameters
        ----------
        failure_id : str
            Stable failure identifier returned by the repository.

        Returns
        -------
        FailedJob or None
            Recorded failure or no matching record.
        """
        await self._ensureSchema()
        rows = await self._connection.select(SelectPlan(
            table=self._definition,
            wheres=[WhereClause("id", value=failure_id)],
            limit_value=1,
        ))
        return FailedJob(**rows[0]) if rows else None

    async def forget(self, failure_id: str) -> bool:
        """
        Remove one recorded failure.

        Parameters
        ----------
        failure_id : str
            Stable identifier of the failure to remove.

        Returns
        -------
        bool
            Whether a failure was removed.
        """
        await self._ensureSchema()
        return await self._connection.delete(DeletePlan(
            table=self._definition,
            wheres=[WhereClause("id", value=failure_id)],
        )) == 1

    async def close(self) -> None:
        """
        Leave the shared database connection under its manager's ownership.

        Returns
        -------
        None
            Preserve the framework-managed connection lifecycle.
        """
        self._ready = False
