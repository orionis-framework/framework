import msgspec

class ReservedJob(msgspec.Struct, frozen=True, kw_only=True):
    """Describe a backend claim and its opaque fencing token."""

    id: str
    payload: bytes
    queue: str
    attempts: int
    token: str
    reserved_until: float
