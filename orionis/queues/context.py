from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING
from orionis.queues.entities.reserved_job import ReservedJob
from orionis.queues.exceptions import QueueLeaseError
from orionis.queues.functions import validate_seconds

type FailureCallback = Callable[[ReservedJob, Exception], Awaitable[bool]]

if TYPE_CHECKING:
    from orionis.queues.contracts.driver import IQueueDriver

class JobContext:
    """Expose the current reservation and explicit lifecycle operations."""

    __slots__ = (
        "_connection",
        "_driver",
        "_fail",
        "_failure",
        "_finished",
        "_reserved",
    )

    def __init__(
        self,
        driver: IQueueDriver,
        reserved: ReservedJob,
        connection: str,
        fail: FailureCallback,
    ) -> None:
        """
        Bind operational state to one job execution.

        Parameters
        ----------
        driver : IQueueDriver
            Driver owning the reservation.
        reserved : ReservedJob
            Current fenced reservation.
        connection : str
            Logical connection name.
        fail : FailureCallback
            Callback persisting a terminal failure.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self._driver = driver
        self._reserved = reserved
        self._connection = connection
        self._fail = fail
        self._finished = False
        self._failure: Exception | None = None

    @property
    def id(self) -> str:
        """
        Return the immutable job identifier.

        Returns
        -------
        str
            Dispatch identifier.
        """
        return self._reserved.id

    @property
    def attempts(self) -> int:
        """
        Return the number of reservations including this execution.

        Returns
        -------
        int
            One-based attempt count.
        """
        return self._reserved.attempts

    @property
    def queue(self) -> str:
        """
        Return the logical queue name.

        Returns
        -------
        str
            Channel containing the job.
        """
        return self._reserved.queue

    @property
    def connection(self) -> str:
        """
        Return the logical backend connection name.

        Returns
        -------
        str
            Configured connection name.
        """
        return self._connection

    @property
    def finished(self) -> bool:
        """
        Report whether an explicit lifecycle operation completed.

        Returns
        -------
        bool
            Whether automatic worker acknowledgement must be skipped.
        """
        return self._finished

    @property
    def failure(self) -> Exception | None:
        """
        Return an explicitly reported terminal exception.

        Returns
        -------
        Exception | None
            Error passed to ``fail``.
        """
        return self._failure

    def _requireActive(self) -> None:
        """
        Reject repeated transitions on a completed context.

        Returns
        -------
        None
            Complete the documented operation without returning a value.

        Raises
        ------
        QueueLeaseError
            If a lifecycle operation already completed.
        """
        if self._finished:
            message = "The job context has already completed its reservation."
            raise QueueLeaseError(message)

    async def release(self, delay: float = 0.0) -> None:
        """
        Release the reservation for another attempt.

        Parameters
        ----------
        delay : float, optional
            Nonnegative delay in seconds.

        Returns
        -------
        None
            Complete the documented operation without returning a value.

        Raises
        ------
        QueueConfigurationError
            If the delay is invalid.
        QueueLeaseError
            If the reservation is no longer owned by this execution.
        """
        self._requireActive()
        validate_seconds(delay, "Job release delay")
        if not await self._driver.release(self._reserved, delay):
            message = "The reservation expired before the job was released."
            raise QueueLeaseError(message)
        self._finished = True

    async def delete(self) -> None:
        """
        Acknowledge the job and remove its reservation.

        Returns
        -------
        None
            Complete the documented operation without returning a value.

        Raises
        ------
        QueueLeaseError
            If the reservation is no longer owned by this execution.
        """
        self._requireActive()
        if not await self._driver.delete(self._reserved):
            message = "The reservation expired before the job was deleted."
            raise QueueLeaseError(message)
        self._finished = True

    async def fail(self, exception: Exception) -> None:
        """
        Persist a terminal error and acknowledge the reservation.

        Parameters
        ----------
        exception : Exception
            Original application exception.

        Returns
        -------
        None
            Complete the documented operation without returning a value.

        Raises
        ------
        QueueLeaseError
            If the reservation is no longer owned by this execution.
        """
        self._requireActive()
        if not await self._fail(self._reserved, exception):
            message = "The reservation expired before the job was failed."
            raise QueueLeaseError(message)
        self._failure = exception
        self._finished = True
