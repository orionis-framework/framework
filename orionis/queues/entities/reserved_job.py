"""Describe a backend claim and its opaque fencing token."""

import msgspec

class ReservedJob(msgspec.Struct, frozen=True, kw_only=True):
    """Describe a backend claim and its opaque fencing token."""

    id: str
    """Identifier used to correlate or locate this protocol or storage record."""
    payload: bytes
    """Serialized data required to execute or restore the job."""
    queue: str
    """Name of the queue receiving or storing the job."""
    attempts: int
    """Number of execution attempts already made for the job."""
    token: str
    """Token identifying the current reservation or protected operation."""
    reserved_until: float
    """Deadline at which the job reservation expires."""
