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

_EXPORTS = {
    "AuthenticateMiddleware": ("orionis.auth.middleware.authenticate", "AuthenticateMiddleware"),
    "AuthenticateSessionMiddleware": ("orionis.auth.middleware.authenticate", "AuthenticateSessionMiddleware"),
    "AuthenticateTokenMiddleware": ("orionis.auth.middleware.authenticate", "AuthenticateTokenMiddleware"),
    "GuestMiddleware": ("orionis.auth.middleware.guest", "GuestMiddleware"),
    "RequirePermissionMiddleware": ("orionis.auth.middleware.authorize", "RequirePermissionMiddleware"),
    "RequirePolicyMiddleware": ("orionis.auth.middleware.policy", "RequirePolicyMiddleware"),
    "RequireRoleMiddleware": ("orionis.auth.middleware.authorize", "RequireRoleMiddleware"),
    "ResolveIdentityMiddleware": ("orionis.auth.middleware.resolve_identity", "ResolveIdentityMiddleware"),
    "ResolveSessionIdentityMiddleware": ("orionis.auth.middleware.resolve_identity", "ResolveSessionIdentityMiddleware"),
    "ResolveTokenIdentityMiddleware": ("orionis.auth.middleware.resolve_identity", "ResolveTokenIdentityMiddleware"),
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
