from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.queues.entities.envelope import JobEnvelope
    from orionis.queues.entities.reserved_job import ReservedJob

class IQueueDriver(ABC):
    """Declare persistence and fenced transitions for a queue connection."""

    __slots__ = ()

    @abstractmethod
    async def push(self, envelope: JobEnvelope, delay: float = 0) -> str:
        """
        Persist an envelope until its scheduled availability.

        Parameters
        ----------
        envelope : JobEnvelope
            Immutable execution data.
        delay : float, optional
            Seconds before the job becomes eligible.

        Returns
        -------
        str
            The persisted job identifier.
        """

    @abstractmethod
    async def reserve(
        self,
        queues: tuple[str, ...],
        retry_after: float,
    ) -> ReservedJob | None:
        """
        Acquire one eligible job in queue priority order.

        Parameters
        ----------
        queues : tuple[str, ...]
            Logical queues ordered from highest to lowest priority.
        retry_after : float
            Duration of the reservation lease.

        Returns
        -------
        ReservedJob | None
            The exclusive claim, or no eligible job.
        """

    @abstractmethod
    async def release(self, reserved: ReservedJob, delay: float = 0) -> bool:
        """
        Release the current claim for a later attempt.

        Parameters
        ----------
        reserved : ReservedJob
            Claim whose token must still own the lease.
        delay : float, optional
            Seconds before another reservation becomes eligible.

        Returns
        -------
        bool
            Whether the claim still owned an unexpired lease.
        """

    @abstractmethod
    async def delete(self, reserved: ReservedJob) -> bool:
        """
        Acknowledge a job only while its claim owns the lease.

        Parameters
        ----------
        reserved : ReservedJob
            Current claim.

        Returns
        -------
        bool
            Whether the fenced acknowledgement removed the job.
        """

    @abstractmethod
    async def size(self, queue: str) -> int:
        """
        Count ready, delayed, and reserved jobs in a logical queue.

        Parameters
        ----------
        queue : str
            Logical channel.

        Returns
        -------
        int
            Number of stored jobs.
        """

    @abstractmethod
    async def clear(self, queue: str) -> int:
        """
        Remove all stored jobs from a logical queue.

        Parameters
        ----------
        queue : str
            Logical channel.

        Returns
        -------
        int
            Number of removed jobs, including active reservations.
        """

    @abstractmethod
    async def close(self) -> None:
        """
        Close resources owned by this driver.

        Returns
        -------
        None
            Release driver-owned resources.
        """
