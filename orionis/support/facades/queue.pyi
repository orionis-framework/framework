from orionis.container.contracts.facade import IFacade
from orionis.queues.contracts.driver import IQueueDriver
from orionis.queues.contracts.failed_repository import IFailedJobRepository
from orionis.queues.contracts.worker import IWorker
from orionis.queues.job import BaseJob
from orionis.queues.pending import PendingDispatch

class Queue(IFacade):

    @staticmethod
    def dispatch(job: BaseJob) -> PendingDispatch:
        ...

    @staticmethod
    async def connection(name: str | None = None) -> IQueueDriver:
        ...

    @staticmethod
    async def worker(
        connection: str | None = None,
        queues: tuple[str, ...] | None = None,
        concurrency: int | None = None,
    ) -> IWorker:
        ...

    @staticmethod
    async def failed() -> IFailedJobRepository:
        ...

    @staticmethod
    async def retryFailed(failed_id: str) -> str:
        ...

    @staticmethod
    async def close() -> None:
        ...
