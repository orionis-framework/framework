from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.foundation.config.auth.entities.auth import Auth
    from orionis.foundation.config.auth.entities.identity import Identity
    from orionis.foundation.config.auth.entities.password_reset import PasswordReset
    from orionis.foundation.config.auth.entities.remember import RememberAuth
    from orionis.foundation.config.auth.entities.session import SessionAuth
    from orionis.foundation.config.auth.entities.tokens import Tokens
    from orionis.foundation.config.auth.enums.guards import Guards

__all__ = [
    "Auth",
    "Guards",
    "Identity",
    "PasswordReset",
    "RememberAuth",
    "SessionAuth",
    "Tokens",
]

_EXPORTS = {
    "Auth": ("orionis.foundation.config.auth.entities.auth", "Auth"),
    "Guards": ("orionis.foundation.config.auth.enums.guards", "Guards"),
    "Identity": ("orionis.foundation.config.auth.entities.identity", "Identity"),
    "PasswordReset": ("orionis.foundation.config.auth.entities.password_reset", "PasswordReset"),
    "RememberAuth": ("orionis.foundation.config.auth.entities.remember", "RememberAuth"),
    "SessionAuth": ("orionis.foundation.config.auth.entities.session", "SessionAuth"),
    "Tokens": ("orionis.foundation.config.auth.entities.tokens", "Tokens"),
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
