# ruff: noqa: PYI021
# Keep public facade methods documented alongside their static signatures.
from orionis.container.facades.facade import Facade
from orionis.queues.contracts.driver import IQueueDriver
from orionis.queues.contracts.failed_repository import IFailedJobRepository
from orionis.queues.contracts.manager import IQueueManager
from orionis.queues.contracts.worker import IWorker
from orionis.queues.job import BaseJob
from orionis.queues.pending import PendingDispatch

class Queue(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type[IQueueManager]:
        """Return the queue manager contract."""

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> IQueueManager:
        """Resolve the queue manager from the container."""

    @classmethod
    async def boot(cls) -> None:
        """Register jobs from the application's configured jobs path."""

    @classmethod
    def dispatch(cls, job: BaseJob) -> PendingDispatch:
        """Create one awaitable dispatch without serializing or persisting data."""

    @classmethod
    async def connection(cls, name: str | None = None) -> IQueueDriver:
        """Resolve one shared lazy driver for the selected named connection."""

    @classmethod
    async def worker(
        cls,
        connection: str | None = None,
        queues: tuple[str, ...] | None = None,
        concurrency: int | None = None,
    ) -> IWorker:
        """Create an independent persistent worker using validated defaults."""

    @classmethod
    async def failed(cls) -> IFailedJobRepository:
        """Resolve durable failed-job storage only when first requested."""

    @classmethod
    async def migrate(cls) -> None:
        """Create the tables used by database-backed queues and failed jobs."""

    @classmethod
    async def retryFailed(cls, failed_id: str) -> str:
        """Requeue preserved job data with attempts reset by a fresh push."""

    @classmethod
    async def close(cls) -> None:
        """Release queue-owned resources without closing shared database services."""
