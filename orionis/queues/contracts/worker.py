from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.queues.entities.reserved_job import ReservedJob

class IWorker(ABC):
    """Declare asynchronous consumption and graceful stopping."""

    __slots__ = ()

    @abstractmethod
    async def run(
        self,
        *,
        stop_when_empty: bool = False,
        max_jobs: int | None = None,
    ) -> int:
        """
        Consume jobs until stopped or the requested limit is reached.

        Parameters
        ----------
        stop_when_empty : bool, optional
            Exit after all consumers find no immediately eligible job.
        max_jobs : int | None, optional
            Maximum number of attempts started during this run.

        Returns
        -------
        int
            Number of processed reservations.
        """

    @abstractmethod
    def stop(self) -> None:
        """
        Stop reserving jobs and drain in-flight executions.

        Returns
        -------
        None
            Request graceful shutdown.
        """

    @abstractmethod
    async def execute(
        self,
        reserved: ReservedJob,
        *,
        raise_errors: bool = False,
    ) -> None:
        """
        Execute one claim through scoped DI and fenced transitions.

        Parameters
        ----------
        reserved : ReservedJob
            Claim to execute.
        raise_errors : bool, optional
            Propagate the original error for synchronous dispatch.

        Returns
        -------
        None
            Complete acknowledgement, release, or failure handling.
        """
