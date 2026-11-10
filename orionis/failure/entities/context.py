"""Describe failures without retaining a request, scope or transport."""

from __future__ import annotations
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

_SECRET_KEYS = ("password", "secret", "token", "authorization", "cookie")
_MAX_METADATA_FIELDS = 32

@dataclass(frozen=True, slots=True, kw_only=True)
class FailureContext:
    """Immutable, bounded context delivered to the application failure hook."""

    flow: str = "runtime"
    phase: str = "execution"
    operation: str | None = None
    correlation_id: str | None = None
    event_id: str | None = None
    parent_event_id: str | None = None
    expected: bool = False
    reporting_allowed: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """
        Copy bounded metadata and redact values under credential-like keys.

        Keep at most 32 entries with string keys and supported scalar values.
        Truncate keys to 128 characters and string values to 1024 characters.

        Returns
        -------
        None
            Replace ``metadata`` with a read-only mapping of the sanitized entries.
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
    delivered: bool = False
    reported: bool = False
    duplicate: bool = False
    degraded: bool = False
