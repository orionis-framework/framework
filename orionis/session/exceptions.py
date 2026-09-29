from __future__ import annotations

class SessionException(Exception):
    """Base class for all session-related exceptions."""

class SessionStorageException(SessionException):
    """Raised when a backing-store operation fails unexpectedly."""
