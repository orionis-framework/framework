from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.hashing.hash_manager import HashManager
    from orionis.hashing.hashers.argon2_hasher import Argon2Hasher
    from orionis.hashing.hashers.bcrypt_hasher import BcryptHasher

__all__ = [
    "Argon2Hasher",
    "BcryptHasher",
    "HashManager",
]

_EXPORTS = {
    "Argon2Hasher": ("orionis.hashing.hashers.argon2_hasher", "Argon2Hasher"),
    "BcryptHasher": ("orionis.hashing.hashers.bcrypt_hasher", "BcryptHasher"),
    "HashManager": ("orionis.hashing.hash_manager", "HashManager"),
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
