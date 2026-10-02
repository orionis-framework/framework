import asyncio
from typing import TYPE_CHECKING
from uuid import uuid4
import msgspec
from orionis.database.exceptions import QueryException
from orionis.orm.query.expressions import (
    AggregateClause,
    AggregateFunction,
    DeletePlan,
    InsertPlan,
    OrderClause,
    SelectPlan,
    UpdatePlan,
    WhereClause,
    WhereType,
)
from orionis.queues.contracts.driver import IQueueDriver
from orionis.queues.entities.reserved_job import ReservedJob
from orionis.queues.exceptions import QueueStorageError
from orionis.queues.functions import current_time, validate_name, validate_seconds
from orionis.queues.schema import build_jobs_table

if TYPE_CHECKING:
    from orionis.database.contracts.connection import IConnection
    from orionis.queues.entities.envelope import JobEnvelope

_ENCODER = msgspec.json.Encoder()
_CLAIM_ROUNDS = 100

def eligible_clauses(queue: str, now: float) -> list[WhereClause]:
    """Build predicates for an available or expired queue row.

    Parameters
    ----------
    queue : str
        Logical queue whose jobs are eligible.
    now : float
        Current epoch timestamp.

    Returns
    -------
    list of WhereClause
        Predicates shared by candidate lookup and atomic claim.
    """
    return [
        WhereClause("queue", value=queue),
        WhereClause("available_at", operator="<=", value=now),
        WhereClause(
            "",
            where_type=WhereType.NESTED,
            value=[
                WhereClause("reserved_until", where_type=WhereType.NULL),
                WhereClause(
                    "reserved_until", operator="<=", value=now, boolean="or",
                ),
            ],
        ),
    ]

class DatabaseQueueDriver(IQueueDriver):
    """Persist queued jobs using atomic conditional updates and expiring leases."""

    __slots__ = ("_connection", "_definition", "_ready", "_ready_lock")

    def __init__(self, connection: IConnection, table: str = "jobs") -> None:
        """
        Bind the queue driver to a framework database connection.

        Parameters
        ----------
        connection : IConnection
            Shared framework connection used for queue persistence.
        table : str, optional
            Logical table name, with the connection prefix applied by DB.
        """
        self._connection = connection
        self._definition = build_jobs_table(table)
        self._ready = False
        self._ready_lock = asyncio.Lock()

    async def _ensureSchema(self) -> None:
        """
        Create the queue table on first use.

        Returns
        -------
        None
            Ensure the queue storage exists.
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

    async def push(self, envelope: JobEnvelope, delay: float = 0) -> str:
        """
        Store an envelope for immediate or delayed consumption.

        Parameters
        ----------
        envelope : JobEnvelope
            Immutable serialized job configuration and state.
        delay : float, optional
            Seconds before the job becomes available.

        Returns
        -------
        str
            Persisted job identifier.
        """
        delay = validate_seconds(delay, "delay")
        await self._ensureSchema()
        now = current_time()
        await self._connection.insert(InsertPlan(
            table=self._definition,
            values=[{
                "id": envelope.id,
                "queue": envelope.queue,
                "payload": _ENCODER.encode(envelope),
                "attempts": 0,
                "available_at": now + delay,
                "reserved_until": None,
                "reservation_token": None,
                "created_at": now,
            }],
        ))
        return envelope.id

    async def reserve(
        self, queues: tuple[str, ...], retry_after: float,
    ) -> ReservedJob | None:
        """
        Claim one eligible job in queue priority order.

        Parameters
        ----------
        queues : tuple of str
            Logical queues ordered from highest to lowest priority.
        retry_after : float
            Lease duration in seconds.

        Returns
        -------
        ReservedJob or None
            Acquired reservation, or no available job.

        Raises
        ------
        QueueStorageError
            If an ambient transaction would prevent committing the claim.
        """
        retry_after = validate_seconds(retry_after, "retry_after", positive=True)
        if self._connection.inTransaction():
            message = (
                "Queue reservations must run outside an active database "
                "transaction so the acquired lease is committed before execution."
            )
            raise QueueStorageError(message)
        await self._ensureSchema()
        for queue in queues:
            validate_name(queue, "queue")
            for _ in range(_CLAIM_ROUNDS):
                now = current_time()
                rows = await self._connection.select(SelectPlan(
                    table=self._definition,
                    wheres=eligible_clauses(queue, now),
                    orders=[
                        OrderClause("available_at"),
                        OrderClause("created_at"),
                        OrderClause("id"),
                    ],
                    limit_value=1,
                ))
                if not rows:
                    break
                row = rows[0]
                attempts = row["attempts"] + 1
                token = uuid4().hex
                now = current_time()
                reserved_until = now + retry_after
                # Acquire only if the observed row remains eligible and unchanged.
                claimed = await self._connection.update(UpdatePlan(
                    table=self._definition,
                    values={
                        "attempts": attempts,
                        "reservation_token": token,
                        "reserved_until": reserved_until,
                    },
                    wheres=[
                        WhereClause("id", value=row["id"]),
                        WhereClause("attempts", value=row["attempts"]),
                        *eligible_clauses(queue, now),
                    ],
                ))
                if claimed == 1:
                    return ReservedJob(
                        id=row["id"], payload=bytes(row["payload"]),
                        queue=queue, attempts=attempts, token=token,
                        reserved_until=reserved_until,
                    )
        return None

    def _ownershipClauses(self, reserved: ReservedJob) -> list[WhereClause]:
        """
        Require a current, unexpired reservation for a transition.

        Parameters
        ----------
        reserved : ReservedJob
            Reservation whose ownership must still hold.

        Returns
        -------
        list of WhereClause
            Predicates fencing reclaimed and expired reservations.
        """
        return [
            WhereClause("id", value=reserved.id),
            WhereClause("reservation_token", value=reserved.token),
            WhereClause("reserved_until", operator=">", value=current_time()),
        ]

    async def release(self, reserved: ReservedJob, delay: float = 0) -> bool:
        """
        Release an owned reservation for another attempt.

        Parameters
        ----------
        reserved : ReservedJob
            Reservation owned by the releasing worker.
        delay : float, optional
            Seconds before the job becomes available again.

        Returns
        -------
        bool
            Whether a current reservation was released.
        """
        delay = validate_seconds(delay, "delay")
        return await self._connection.update(UpdatePlan(
            table=self._definition,
            values={
                "available_at": current_time() + delay,
                "reserved_until": None,
                "reservation_token": None,
            },
            wheres=self._ownershipClauses(reserved),
        )) == 1

    async def delete(self, reserved: ReservedJob) -> bool:
        """
        Acknowledge an owned reservation by removing its row.

        Parameters
        ----------
        reserved : ReservedJob
            Reservation owned by the acknowledging worker.

        Returns
        -------
        bool
            Whether a current reservation was removed.
        """
        return await self._connection.delete(DeletePlan(
            table=self._definition, wheres=self._ownershipClauses(reserved),
        )) == 1

    async def size(self, queue: str) -> int:
        """
        Count ready, delayed, and reserved jobs in one queue.

        Parameters
        ----------
        queue : str
            Logical queue whose jobs are counted.

        Returns
        -------
        int
            Total number of persisted jobs in the queue.
        """
        validate_name(queue, "queue")
        await self._ensureSchema()
        return int(await self._connection.scalar(SelectPlan(
            table=self._definition,
            wheres=[WhereClause("queue", value=queue)],
            aggregate=AggregateClause(AggregateFunction.COUNT),
        )))

    async def clear(self, queue: str) -> int:
        """
        Remove every job in one logical queue.

        Parameters
        ----------
        queue : str
            Logical queue whose jobs are removed.

        Returns
        -------
        int
            Number of removed jobs, including active reservations.
        """
        validate_name(queue, "queue")
        await self._ensureSchema()
        return await self._connection.delete(DeletePlan(
            table=self._definition, wheres=[WhereClause("queue", value=queue)],
        ))

    async def close(self) -> None:
        """
        Leave the shared database connection under its manager's ownership.

        Returns
        -------
        None
            Preserve the framework-managed connection lifecycle.
        """
        self._ready = False
