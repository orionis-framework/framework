"""Declare durable terminal failure inspection and removal."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.queues.entities.failed_job import FailedJob
    from orionis.queues.entities.reserved_job import ReservedJob

class IFailedJobRepository(ABC):
    """Declare durable terminal failure inspection and removal."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    async def record(
        self,
        reserved: ReservedJob,
        connection: str,
        exception: BaseException,
    ) -> FailedJob:
        """
        Persist the original payload and exception before acknowledgement.

        Parameters
        ----------
        reserved : orionis.queues.entities.reserved_job.ReservedJob
            Failed claim, including corrupt wire data when applicable.
        connection : str
            Queue connection name.
        exception : BaseException
            Original execution or deserialization failure.

        Returns
        -------
        orionis.queues.entities.failed_job.FailedJob
            Durable failure record.
        """

    @abstractmethod
    async def all(self) -> tuple[FailedJob, ...]:
        """
        List persisted failures in creation order.

        Returns
        -------
        tuple[orionis.queues.entities.failed_job.FailedJob, ``...``]
            Failure records available for inspection.
        """

    @abstractmethod
    async def find(self, failed_id: str) -> FailedJob | None:
        """
        Find a persisted failure by its identifier.

        Parameters
        ----------
        failed_id : str
            Failure identifier.

        Returns
        -------
        orionis.queues.entities.failed_job.FailedJob | None
            Matching failure, if present.
        """

    @abstractmethod
    async def forget(self, failed_id: str) -> bool:
        """
        Delete a persisted failure by its identifier.

        Parameters
        ----------
        failed_id : str
            Failure identifier.

        Returns
        -------
        bool
            Whether a record was removed.
        """

    @abstractmethod
    async def close(self) -> None:
        """
        Close resources owned by the repository.

        Returns
        -------
        None
            Release repository-owned resources.
        """
