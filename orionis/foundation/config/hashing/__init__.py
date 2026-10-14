from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.foundation.config.hashing.entities.argon2 import Argon2
    from orionis.foundation.config.hashing.entities.bcrypt import Bcrypt
    from orionis.foundation.config.hashing.entities.hashing import Hashing
    from orionis.foundation.config.hashing.enums.drivers import Drivers

__all__ = [
    "Argon2",
    "Bcrypt",
    "Drivers",
    "Hashing",
]

_EXPORTS = {
    "Argon2": ("orionis.foundation.config.hashing.entities.argon2", "Argon2"),
    "Bcrypt": ("orionis.foundation.config.hashing.entities.bcrypt", "Bcrypt"),
    "Drivers": ("orionis.foundation.config.hashing.enums.drivers", "Drivers"),
    "Hashing": ("orionis.foundation.config.hashing.entities.hashing", "Hashing"),
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
