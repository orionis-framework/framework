from typing import TYPE_CHECKING
from uuid import uuid4
from orionis.queues.contracts.driver import IQueueDriver
from orionis.queues.entities.reserved_job import ReservedJob
from orionis.queues.exceptions import QueueDispatchError
from orionis.queues.worker import Worker, WorkerOptions
from orionis.support.facades.datetime import DateTime

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication
    from orionis.queues.contracts.serializer import IJobSerializer
    from orionis.queues.entities.envelope import JobEnvelope
    from orionis.queues.worker import FailedResolver

class SyncQueueDriver(IQueueDriver):
    """Execute one immediate attempt through the shared worker pipeline."""

    __slots__ = ("_retry_after", "_serializer", "_worker")

    def __init__(
        self,
        app: IApplication,
        serializer: IJobSerializer,
        connection: str,
        failed_resolver: FailedResolver,
        retry_after: float = 90.0,
    ) -> None:
        """
        Prepare immediate execution without a durable backend.

        Parameters
        ----------
        app : IApplication
            Existing application container.
        serializer : IJobSerializer
            Registered job serializer.
        connection : str
            Logical connection name.
        failed_resolver : FailedResolver
            Resolver called only on terminal failure.
        retry_after : float, optional
            Execution lease used by the shared pipeline.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self._serializer = serializer
        self._retry_after = retry_after
        self._worker = Worker(
            app,
            self,
            serializer,
            WorkerOptions(
                connection,
                retry_after=retry_after,
            ),
            failed_resolver,
        )

    async def push(self, envelope: JobEnvelope, delay: float = 0.0) -> str:
        """
        Execute the job immediately and propagate its original exception.

        Parameters
        ----------
        envelope : JobEnvelope
            Immutable job payload and execution settings.
        delay : float, optional
            Delay, which must be zero for immediate execution.

        Returns
        -------
        str
            Completed dispatch identifier.

        Raises
        ------
        QueueDispatchError
            If delayed execution is requested.
        """
        if delay != 0:
            message = "The sync connection does not support delayed jobs."
            raise QueueDispatchError(message)
        reserved = ReservedJob(
            id=envelope.id, payload=self._serializer.encodeEnvelope(envelope),
            queue=envelope.queue, attempts=1, token=uuid4().hex,
            reserved_until=DateTime.now().timestamp() + self._retry_after,
        )
        await self._worker.execute(reserved, raise_errors=True)
        return envelope.id

    async def reserve(
        self,
        queues: tuple[str, ...],
        retry_after: float,
    ) -> ReservedJob | None:
        """
        Return no durable work for an immediate connection.

        Parameters
        ----------
        queues : tuple[str, ...]
            Unused channel selection.
        retry_after : float
            Unused lease lifetime.

        Returns
        -------
        None
            Immediate jobs are executed during push.
        """
        del queues, retry_after
        return None

    async def release(self, reserved: ReservedJob, delay: float = 0.0) -> bool:
        """
        Reject persistent retry on an immediate connection.

        Parameters
        ----------
        reserved : ReservedJob
            Unused immediate reservation.
        delay : float, optional
            Requested retry delay.

        Returns
        -------
        bool
            Result of the operation described above.

        Raises
        ------
        QueueDispatchError
            Always, because immediate jobs have no durable storage.
        """
        del reserved, delay
        message = "The sync connection cannot release a job for persistent retry."
        raise QueueDispatchError(message)

    async def delete(self, reserved: ReservedJob) -> bool:
        """
        Acknowledge completion of an immediate execution.

        Parameters
        ----------
        reserved : ReservedJob
            Unused immediate reservation.

        Returns
        -------
        bool
            Always true for the in-process execution.
        """
        del reserved
        return True

    async def size(self, queue: str) -> int:
        """
        Return the empty durable size of an immediate channel.

        Parameters
        ----------
        queue : str
            Unused channel name.

        Returns
        -------
        int
            Zero, because no jobs are persisted.
        """
        del queue
        return 0

    async def clear(self, queue: str) -> int:
        """
        Return zero removed jobs for an immediate channel.

        Parameters
        ----------
        queue : str
            Unused channel name.

        Returns
        -------
        int
            Zero, because no jobs are persisted.
        """
        del queue
        return 0

    async def close(self) -> None:
        """
        Signal the worker to stop without closing application services.

        Returns
        -------
        None
            Set the stop signal without waiting for running jobs.
        """
        self._worker.stop()
