from collections.abc import Sized
from decimal import Decimal

# Bytes per kilobyte, the unit size rules use to express file sizes.
KILOBYTE = 1024

# Attributes an uploaded file exposes, used for structural detection so the
# schema layer stays decoupled from the HTTP payload package.
_FILE_ATTRIBUTES = ("read", "size", "filename")

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

def read_content(value: object) -> bytes | None:
    """
    Read the whole content of an uploaded file.

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
        content = reader()
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
