from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.foundation.application import Application
    from orionis.foundation.contracts.application import IApplication

__all__ = [
    "Application",
    "IApplication",
]

_EXPORTS = {
    "Application": ("orionis.foundation.application", "Application"),
    "IApplication": ("orionis.foundation.contracts.application", "IApplication"),
}

def __getattr__(name: str) -> object:
    """Resolve and cache a public package export.

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
    """List loaded attributes and declared public exports.

    Returns
    -------
    list[str]
        Sorted attribute names available on this package.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
