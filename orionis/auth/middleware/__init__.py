"""Group the auth middleware components and public imports."""

from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.auth.middleware.authenticate import (
        AuthenticateMiddleware,
        AuthenticateSessionMiddleware,
        AuthenticateTokenMiddleware,
    )
    from orionis.auth.middleware.authorize import (
        RequirePermissionMiddleware,
        RequireRoleMiddleware,
    )
    from orionis.auth.middleware.guest import GuestMiddleware
    from orionis.auth.middleware.policy import RequirePolicyMiddleware
    from orionis.auth.middleware.resolve_identity import (
        ResolveIdentityMiddleware,
        ResolveSessionIdentityMiddleware,
        ResolveTokenIdentityMiddleware,
    )

__all__ = [
    "AuthenticateMiddleware",
    "AuthenticateSessionMiddleware",
    "AuthenticateTokenMiddleware",
    "GuestMiddleware",
    "RequirePermissionMiddleware",
    "RequirePolicyMiddleware",
    "RequireRoleMiddleware",
    "ResolveIdentityMiddleware",
    "ResolveSessionIdentityMiddleware",
    "ResolveTokenIdentityMiddleware",
]

_AUTHENTICATE_MODULE = "orionis.auth.middleware.authenticate"
"""Module defining authentication-required middleware variants."""
_RESOLVE_MODULE = "orionis.auth.middleware.resolve_identity"
"""Module defining optional identity-resolution middleware variants."""

_EXPORTS = {
    "AuthenticateMiddleware": (_AUTHENTICATE_MODULE, "AuthenticateMiddleware"),
    "AuthenticateSessionMiddleware": (
        _AUTHENTICATE_MODULE,
        "AuthenticateSessionMiddleware",
    ),
    "AuthenticateTokenMiddleware": (
        _AUTHENTICATE_MODULE,
        "AuthenticateTokenMiddleware",
    ),
    "GuestMiddleware": ("orionis.auth.middleware.guest", "GuestMiddleware"),
    "RequirePermissionMiddleware": (
        "orionis.auth.middleware.authorize",
        "RequirePermissionMiddleware",
    ),
    "RequirePolicyMiddleware": (
        "orionis.auth.middleware.policy",
        "RequirePolicyMiddleware",
    ),
    "RequireRoleMiddleware": (
        "orionis.auth.middleware.authorize",
        "RequireRoleMiddleware",
    ),
    "ResolveIdentityMiddleware": (_RESOLVE_MODULE, "ResolveIdentityMiddleware"),
    "ResolveSessionIdentityMiddleware": (
        _RESOLVE_MODULE,
        "ResolveSessionIdentityMiddleware",
    ),
    "ResolveTokenIdentityMiddleware": (
        _RESOLVE_MODULE,
        "ResolveTokenIdentityMiddleware",
    ),
}
"""Public export names mapped to their defining modules and attributes."""


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
