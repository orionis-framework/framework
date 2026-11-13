# ruff: noqa: PYI021
# Keep public facade methods documented alongside their static signatures.
from orionis.container.contracts.facade import IFacade
from orionis.queues.contracts.driver import IQueueDriver
from orionis.queues.contracts.failed_repository import IFailedJobRepository
from orionis.queues.contracts.worker import IWorker
from orionis.queues.job import BaseJob
from orionis.queues.pending import PendingDispatch

class Queue(IFacade):
    @staticmethod
    def dispatch(job: BaseJob) -> PendingDispatch:
        """Create one awaitable dispatch without serializing or persisting data."""

    @staticmethod
    async def connection(name: str | None = None) -> IQueueDriver:
        """Resolve one shared lazy driver for the selected named connection."""

    @staticmethod
    async def worker(
        connection: str | None = None,
        queues: tuple[str, ...] | None = None,
        concurrency: int | None = None,
    ) -> IWorker:
        """Create an independent persistent worker using validated defaults."""

    @staticmethod
    async def failed() -> IFailedJobRepository:
        """Resolve durable failed-job storage only when first requested."""

    @staticmethod
    async def retryFailed(failed_id: str) -> str:
        """Requeue preserved job data with attempts reset by a fresh push."""

    @staticmethod
    async def close() -> None:
        """Release queue-owned resources without closing shared database services."""
