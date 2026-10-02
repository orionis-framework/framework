from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.queues.entities.failed_job import FailedJob
    from orionis.queues.entities.reserved_job import ReservedJob

class IFailedJobRepository(ABC):
    """Declare durable terminal failure inspection and removal."""

    __slots__ = ()

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
        reserved : ReservedJob
            Failed claim, including corrupt wire data when applicable.
        connection : str
            Queue connection name.
        exception : BaseException
            Original execution or deserialization failure.

        Returns
        -------
        FailedJob
            Durable failure record.
        """

    @abstractmethod
    async def all(self) -> tuple[FailedJob, ...]:
        """
        List persisted failures in creation order.

        Returns
        -------
        tuple[FailedJob, ...]
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
        FailedJob | None
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
