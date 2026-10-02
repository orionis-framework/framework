from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.queues.contracts.driver import IQueueDriver
    from orionis.queues.contracts.failed_repository import IFailedJobRepository
    from orionis.queues.contracts.worker import IWorker
    from orionis.queues.job import BaseJob
    from orionis.queues.pending import PendingDispatch

class IQueueManager(ABC):
    """Declare the canonical dispatch and queue administration API."""

    __slots__ = ()

    @abstractmethod
    def dispatch(self, job: BaseJob) -> PendingDispatch:
        """
        Create an awaitable operation without performing I/O.

        Parameters
        ----------
        job : BaseJob
            Serializable application job.

        Returns
        -------
        PendingDispatch
            Deferred operation with fluent selection and delay.
        """

    @abstractmethod
    async def connection(self, name: str | None = None) -> IQueueDriver:
        """
        Resolve a configured connection lazily.

        Parameters
        ----------
        name : str | None, optional
            Connection name, or the central default.

        Returns
        -------
        IQueueDriver
            Driver shared by logical queues on this connection.
        """

    @abstractmethod
    async def worker(
        self,
        connection: str | None = None,
        queues: tuple[str, ...] | None = None,
        concurrency: int | None = None,
    ) -> IWorker:
        """
        Create a worker using validated central settings.

        Parameters
        ----------
        connection : str | None, optional
            Backend name, or the default.
        queues : tuple[str, ...] | None, optional
            Priority-ordered channels, or the connection default.
        concurrency : int | None, optional
            Maximum simultaneous attempts, or the worker default.

        Returns
        -------
        IWorker
            Independent worker runtime.
        """

    @abstractmethod
    async def failed(self) -> IFailedJobRepository:
        """
        Resolve the durable failure repository lazily.

        Returns
        -------
        IFailedJobRepository
            Central repository shared by connections.
        """

    @abstractmethod
    async def retryFailed(self, failed_id: str) -> str:
        """
        Requeue a failed job with a fresh attempt budget.

        Parameters
        ----------
        failed_id : str
            Failure identifier to retry.

        Returns
        -------
        str
            Identifier returned by persistent dispatch.
        """

    @abstractmethod
    async def close(self) -> None:
        """
        Close queue-owned clients without disposing shared database services.

        Returns
        -------
        None
            Release resources owned by queue drivers.
        """
