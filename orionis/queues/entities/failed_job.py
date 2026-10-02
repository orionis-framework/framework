import msgspec

class FailedJob(msgspec.Struct, frozen=True, kw_only=True):
    """Preserve the payload and exception associated with terminal failure."""

    id: str
    job_id: str
    connection: str
    queue: str
    payload: bytes
    exception_type: str
    exception_message: str
    traceback: str
    failed_at: float
    attempts: int
