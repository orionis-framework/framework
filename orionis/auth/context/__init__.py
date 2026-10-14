from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.auth.context.context import GUEST_CONTEXT, AuthenticationContext
    from orionis.auth.context.functions import bind_auth_context, current_auth_context

__all__ = [
    "GUEST_CONTEXT",
    "AuthenticationContext",
    "bind_auth_context",
    "current_auth_context",
]

_EXPORTS = {
    "GUEST_CONTEXT": ("orionis.auth.context.context", "GUEST_CONTEXT"),
    "AuthenticationContext": ("orionis.auth.context.context", "AuthenticationContext"),
    "bind_auth_context": ("orionis.auth.context.functions", "bind_auth_context"),
    "current_auth_context": ("orionis.auth.context.functions", "current_auth_context"),
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
