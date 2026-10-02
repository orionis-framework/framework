from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.validation import validate_integer, validate_seconds
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True, slots=True)
class Worker(BaseEntity):
    """
    Configure strictly validated queue worker defaults.

    Parameters
    ----------
    concurrency : int
        Maximum concurrent jobs read from ``QUEUE_WORKER_CONCURRENCY``.
    sleep : float
        Positive polling seconds read from ``QUEUE_WORKER_SLEEP``.
    timeout : float
        Positive execution seconds read from ``QUEUE_WORKER_TIMEOUT``.
    tries : int
        Maximum attempts read from ``QUEUE_WORKER_TRIES``.
    backoff : tuple[float, ...] | list[float]
        Nonnegative retry delays read from ``QUEUE_WORKER_BACKOFF``.
    """

    concurrency: int = field(
        default_factory=lambda: Env.get("QUEUE_WORKER_CONCURRENCY", 1),
        metadata={
            "description": "Maximum concurrent jobs.",
            "default": 1,
        },
    )

    sleep: float = field(
        default_factory=lambda: Env.get("QUEUE_WORKER_SLEEP", 1.0),
        metadata={
            "description": "Worker polling interval in seconds.",
            "default": 1.0,
        },
    )

    timeout: float = field(
        default_factory=lambda: Env.get("QUEUE_WORKER_TIMEOUT", 60.0),
        metadata={
            "description": "Job execution timeout in seconds.",
            "default": 60.0,
        },
    )

    tries: int = field(
        default_factory=lambda: Env.get("QUEUE_WORKER_TRIES", 3),
        metadata={
            "description": "Maximum job attempts.",
            "default": 3,
        },
    )

    backoff: tuple[float, ...] | list[float] = field(
        default_factory=lambda: Env.get("QUEUE_WORKER_BACKOFF", (0.0,)),
        metadata={
            "description": "Retry delays in seconds.",
            "default": (0.0,),
        },
    )

    def __post_init__(self) -> None:
        """
        Validate worker limits and own the immutable retry schedule.

        Returns
        -------
        None
            Store validated worker settings with tuple backoff values.

        Raises
        ------
        TypeError
            If limits, durations, or the retry schedule have invalid types.
        ValueError
            If limits or durations are outside their allowed ranges.
        """
        super().__post_init__()
        validate_integer(self.concurrency, "worker.concurrency", minimum=1)
        validate_integer(self.tries, "worker.tries", minimum=1)
        validate_seconds(self.sleep, "worker.sleep", positive=True)
        validate_seconds(self.timeout, "worker.timeout", positive=True)
        if not isinstance(self.backoff, (tuple, list)) or not self.backoff:
            message = "'worker.backoff' must be a nonempty sequence of seconds."
            raise TypeError(message)
        for delay in self.backoff:
            validate_seconds(delay, "worker.backoff")
        object.__setattr__(self, "backoff", tuple(self.backoff))
