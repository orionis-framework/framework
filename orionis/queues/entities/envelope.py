import math
from uuid import UUID
import msgspec
from orionis.queues.exceptions import QueuePayloadError
from orionis.queues.functions import validate_name, validate_seconds

class JobEnvelope(
    msgspec.Struct, frozen=True, kw_only=True, forbid_unknown_fields=True,
):
    """Carry immutable, versioned job data independently of backend state."""

    id: str
    job: str
    payload: bytes
    connection: str
    queue: str
    max_tries: int
    timeout: float | None
    backoff: tuple[float, ...]
    retry_until: float | None = None
    version: int = 1

    def __post_init__(self) -> None:
        """
        Reject invalid immutable execution options.

        Returns
        -------
        None
            Validate the envelope without mutating its fields.
        """
        if type(self.version) is not int or self.version != 1:
            message = "Unsupported queue envelope version."
            raise QueuePayloadError(message)
        try:
            UUID(self.id)
        except (ValueError, TypeError, AttributeError) as error:
            message = "Queue envelope id must be a UUID."
            raise QueuePayloadError(message) from error
        if not isinstance(self.job, str) or ":" not in self.job:
            message = "Queue envelope job must identify a registered module and class."
            raise QueuePayloadError(message)
        if not isinstance(self.payload, bytes):
            message = "Queue envelope payload must be bytes."
            raise QueuePayloadError(message)
        validate_name(self.connection, "Connection")
        validate_name(self.queue, "Queue")
        if (
            isinstance(self.max_tries, bool)
            or not isinstance(self.max_tries, int)
            or self.max_tries < 1
        ):
            message = "Queue envelope max_tries must be a positive integer."
            raise QueuePayloadError(message)
        if self.timeout is not None:
            validate_seconds(self.timeout, "Job timeout", positive=True)
        if not isinstance(self.backoff, tuple) or not self.backoff:
            message = "Queue envelope backoff must be a nonempty tuple."
            raise QueuePayloadError(message)
        for delay in self.backoff:
            validate_seconds(delay, "Job backoff")
        if self.retry_until is not None and (
            isinstance(self.retry_until, bool)
            or not isinstance(self.retry_until, (int, float))
            or not math.isfinite(self.retry_until)
        ):
            message = "Queue envelope retry_until must be a finite epoch timestamp."
            raise QueuePayloadError(message)
