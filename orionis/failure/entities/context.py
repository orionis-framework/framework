# ruff: noqa: TC003
# Keep public metadata annotations available to runtime reflection.
"""Describe failures without retaining a request, scope or transport."""

from __future__ import annotations
from dataclasses import dataclass, field
from types import MappingProxyType
from collections.abc import Mapping

_SECRET_KEYS = ("password", "secret", "token", "authorization", "cookie")
"""Credential-like key fragments whose metadata values are redacted."""
_MAX_METADATA_FIELDS = 32
"""Maximum scalar metadata entries retained by one failure context."""


@dataclass(frozen=True, slots=True, kw_only=True)
class FailureContext:
    """Immutable, bounded context delivered to the application failure hook."""

    flow: str = "runtime"
    """Execution flow owning the failure, such as HTTP, CLI, or worker."""
    phase: str = "execution"
    """Stage within the owning flow at which the failure was observed."""
    operation: str | None = None
    """Optional logical operation name supplied by the execution owner."""
    correlation_id: str | None = None
    """Identifier shared by incidents within the same operation."""
    event_id: str | None = None
    """Identifier assigned to this incident when observation begins."""
    parent_event_id: str | None = None
    """Previously observed cause associated with this secondary incident."""
    expected: bool = False
    """Whether default policy should omit ordinary error logging."""
    reporting_allowed: bool = True
    """Whether logging resources remain available for deferred reporting."""
    metadata: Mapping[str, object] = field(default_factory=dict)
    """Read-only, bounded scalar metadata with credential-like values redacted."""

    def __post_init__(self) -> None:
        """
        Copy bounded metadata and redact values under credential-like keys.

        Keep at most 32 entries with string keys and supported scalar values.
        Truncate keys to 128 characters and string values to 1024 characters.
        Replace ``metadata`` with a read-only mapping of the sanitized entries.

        Returns
        -------
        None
            No return value.
        """
        values = {}
        for key, value in self.metadata.items():
            if len(values) == _MAX_METADATA_FIELDS:
                break
            if not isinstance(key, str):
                continue
            if any(secret in key.lower() for secret in _SECRET_KEYS):
                values[key[:128]] = "[REDACTED]"
            elif value is None or type(value) in (str, int, float, bool):
                values[key[:128]] = value[:1024] if isinstance(value, str) else value
        object.__setattr__(self, "metadata", MappingProxyType(values))


@dataclass(frozen=True, slots=True, kw_only=True)
class FailureReceipt:
    """Record delivery status without retaining the exception or its traceback."""

    event_id: str
    """Stable incident identifier without retaining the exception itself."""
    delivered: bool = False
    """Whether the configured application hook returned successfully."""
    reported: bool = False
    """Whether the selected logging effect completed successfully."""
    duplicate: bool = False
    """Whether this capture reused an existing incident in its operation."""
    degraded: bool = False
    """Whether reporting required fallback or could not complete normally."""
