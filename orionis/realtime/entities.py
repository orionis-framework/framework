"""Count delivered and failed recipients without retaining connections."""

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class BroadcastResult:
    """Count delivered and failed recipients without retaining connections."""

    sent: int = 0
    """Sent value used by ``BroadcastResult``."""
    failed: int = 0
    """Failed value used by ``BroadcastResult``."""
