from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.foundation.config.app.entities.app import App
    from orionis.foundation.config.app.enums.ciphers import Cipher
    from orionis.foundation.config.app.enums.environments import Environments

__all__ = [
    "App",
    "Cipher",
    "Environments",
]

_EXPORTS = {
    "App": ("orionis.foundation.config.app.entities.app", "App"),
    "Cipher": ("orionis.foundation.config.app.enums.ciphers", "Cipher"),
    "Environments": ("orionis.foundation.config.app.enums.environments", "Environments"),
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
