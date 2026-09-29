from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime

@dataclass(slots=True)
class SessionRecord:
    """
    Persistent representation of a single session.

    This object is the sole exchange currency between the
    ``SessionManager`` and any ``ISessionStore`` implementation.
    It must never be exposed directly to application code.

    Parameters
    ----------
    id : str
        Unique session identifier (URL-safe random token).
    data : dict[str, Any]
        Serialisable payload stored alongside the session.
    expires_at : datetime
        UTC datetime at which the record must be considered expired.
    """

    id: str
    data: dict[str, Any]
    expires_at: datetime
