from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class BroadcastResult:
    """Count delivered and failed recipients without retaining connections."""

    sent: int = 0
    failed: int = 0
