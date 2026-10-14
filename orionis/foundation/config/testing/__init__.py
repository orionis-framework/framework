from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.foundation.config.testing.entities.testing import Testing
    from orionis.foundation.config.testing.enums import VerbosityMode

__all__ = [
    "Testing",
    "VerbosityMode",
]

_EXPORTS = {
    "Testing": ("orionis.foundation.config.testing.entities.testing", "Testing"),
    "VerbosityMode": ("orionis.foundation.config.testing.enums", "VerbosityMode"),
}

def __getattr__(name: str) -> object:
    """
    Resolve and cache a public package export.

    Parameters
    ----------
    name : str
        Public attribute requested from this package.

    Returns
    -------
    object
        Exported object from its defining module.

    Raises
    ------
    AttributeError
        If the requested attribute is not exported.
    """
    return _resolve_export(globals(), _EXPORTS, name)

def __dir__() -> list[str]:
    """
    List loaded attributes and declared public exports.

    Returns
    -------
    list[str]
        Sorted attribute names available on this package.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
