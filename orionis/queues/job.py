from typing import ClassVar
from orionis.queues.contracts.job import IJob

class BaseJob(IJob):
    """
    Declare serializable job fields and asynchronous service dependencies.

    Attributes
    ----------
    tries : int | None
        Maximum reservations, or the configured worker default.
    timeout : float | None
        Cooperative execution timeout, or the configured worker default.
    backoff : tuple[float, ...] | None
        Delay after each failed attempt, or the configured worker default.
    """

    __slots__ = ()

    tries: ClassVar[int | None] = None
    timeout: ClassVar[float | None] = None
    backoff: ClassVar[tuple[float, ...] | None] = None

    def retryUntil(self) -> float | None:
        """
        Return an optional absolute retry deadline.

        Returns
        -------
        float | None
            Epoch seconds from DateTime, or no deadline.
        """
        return None
