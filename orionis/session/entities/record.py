# ruff: noqa: TC003
# Resolve the public record's datetime annotation during native reflection.
"""Persistent representation of a single session."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class SessionRecord:
    """
    Persistent representation of a single session.

    This object is the sole exchange currency between the
    ``SessionManager`` and any ``ISessionStore`` implementation.
    It must never be exposed directly to application code.

    Attributes
    ----------
    id : str
        Unique session identifier (URL-safe random token).
    data : dict[str, typing.Any]
        Serialisable payload stored alongside the session.
    expires_at : datetime.datetime
        UTC datetime at which the record must be considered expired.
    """

    id: str
    data: dict[str, Any]
    expires_at: datetime
