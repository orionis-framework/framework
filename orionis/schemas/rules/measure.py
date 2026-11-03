"""Measure field values and recognize empty data without consuming it."""

import asyncio
from collections.abc import Sized
from decimal import Decimal
from numbers import Number

# Bytes per kilobyte, the unit size rules use to express file sizes.
KILOBYTE = 1024
"""Bytes per kilobyte, the unit size rules use to express file sizes."""

# Attributes an uploaded file exposes, used for structural detection so the
# schema layer stays decoupled from the HTTP payload package.
_FILE_ATTRIBUTES = ("read", "size", "filename")
"""
Attributes an uploaded file exposes, used for structural detection so the schema
layer stays decoupled from the HTTP payload package.
"""

def is_file(value: object) -> bool:
    """
    Report whether a value behaves like an uploaded file.

    Parameters
    ----------
    value : object
        Value to inspect.

    Returns
    -------
    bool
        Return ``True`` when the value exposes the uploaded-file protocol.
    """
    return all(hasattr(value, name) for name in _FILE_ATTRIBUTES)

def is_empty(value: object) -> bool:
    """
    Recognize empty text, containers, numbers and uploaded files.

    Treat ``None``, whitespace-only strings, numeric zero and ``False`` as
    empty. Sized values are empty when their length is zero, and uploaded
    files when their byte size is zero. Do not consume unsized iterables.

    Parameters
    ----------
    value : object
        Value whose emptiness is checked without changing its contents.

    Returns
    -------
    bool
        Whether the value satisfies the shared emptiness definition.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, Decimal):
        return value.is_zero()
    if isinstance(value, Number):
        return value == 0
    if is_file(value):
        return getattr(value, "size", None) == 0
    return isinstance(value, Sized) and len(value) == 0

async def read_content(value: object) -> bytes | None:
    """
    Read uploaded-file content without blocking the event loop.

    Parameters
    ----------
    value : object
        Uploaded file to read.

    Returns
    -------
    bytes | None
        Raw content, or ``None`` when the value is not a readable file.
    """
    if not is_file(value):
        return None

    reader = getattr(value, "read", None)
    if not callable(reader):
        return None

    try:
        content = await asyncio.to_thread(reader)
    except OSError:
        return None

    return content if isinstance(content, bytes) else None

def measure(value: object) -> float | None:
    """
    Compute the comparable size of a value.

    Numbers are compared by their own magnitude, strings and collections by
    their length, and uploaded files by their size in kilobytes.

    Parameters
    ----------
    value : object
        Value whose size is required.

    Returns
    -------
    float | None
        Comparable size, or ``None`` when the value has no measurable size.
    """
    # Booleans are integers in Python but never carry a comparable size.
    if isinstance(value, bool):
        return None

    if isinstance(value, int | float):
        return value

    if isinstance(value, Decimal):
        return float(value)

    if is_file(value):
        size = getattr(value, "size", None)
        return size / KILOBYTE if isinstance(size, int) else None

    if isinstance(value, Sized):
        return len(value)

    return None
