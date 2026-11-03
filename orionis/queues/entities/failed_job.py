"""Preserve the payload and exception associated with terminal failure."""

import msgspec

class FailedJob(msgspec.Struct, frozen=True, kw_only=True):
    """Preserve the payload and exception associated with terminal failure."""

    id: str
    """Identifier used to correlate or locate this protocol or storage record."""
    job_id: str
    """Identifier of the original queued job."""
    connection: str
    """Configured connection used to store or dispatch the operation."""
    queue: str
    """Name of the queue receiving or storing the job."""
    payload: bytes
    """Serialized data required to execute or restore the job."""
    exception_type: str
    """Type name of the exception that caused the job failure."""
    exception_message: str
    """Message describing the exception that caused the job failure."""
    traceback: str
    """Formatted traceback retained for failure diagnostics."""
    failed_at: float
    """Timestamp at which the job was recorded as failed."""
    attempts: int
    """Number of execution attempts already made for the job."""
