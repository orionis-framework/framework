from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.auth.tokens.functions import generate_token_secret, hash_token_secret
    from orionis.auth.tokens.repository import AccessTokenRepository

__all__ = [
    "AccessTokenRepository",
    "generate_token_secret",
    "hash_token_secret",
]

_EXPORTS = {
    "AccessTokenRepository": ("orionis.auth.tokens.repository", "AccessTokenRepository"),
    "generate_token_secret": ("orionis.auth.tokens.functions", "generate_token_secret"),
    "hash_token_secret": ("orionis.auth.tokens.functions", "hash_token_secret"),
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
