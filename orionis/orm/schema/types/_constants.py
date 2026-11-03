"""Define constants for orm schema types."""

from __future__ import annotations

# Default maximum length applied to VARCHAR-like columns.
DEFAULT_STRING_LENGTH: int = 255
"""Default maximum length applied to VARCHAR-like columns."""

# Default precision and scale applied to decimal columns.
DEFAULT_DECIMAL_PRECISION: int = 10
"""Default precision and scale applied to decimal columns."""
DEFAULT_DECIMAL_SCALE: int = 2
"""Default decimal scale value used by ``_constants``."""
