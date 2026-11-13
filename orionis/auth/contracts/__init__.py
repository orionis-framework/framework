"""Resolve authentication contracts without creating entity import cycles."""

from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.auth.contracts.authenticatable import IAuthenticatable
    from orionis.auth.contracts.authorizable import IAuthorizable
    from orionis.auth.contracts.authorizer import IAuthorizer
    from orionis.auth.contracts.context import IAuthenticationContext
    from orionis.auth.contracts.guard import IGuard
    from orionis.auth.contracts.identity_provider import IIdentityProvider
    from orionis.auth.contracts.manager import IAuthManager
    from orionis.auth.contracts.permission_repository import IPermissionRepository
    from orionis.auth.contracts.policy import IPolicy
    from orionis.auth.contracts.session_guard import ISessionGuard
    from orionis.auth.contracts.snapshot import IAuthorizationSnapshot
    from orionis.auth.contracts.token_repository import IAccessTokenRepository

__all__ = [
    "IAccessTokenRepository",
    "IAuthManager",
    "IAuthenticatable",
    "IAuthenticationContext",
    "IAuthorizable",
    "IAuthorizationSnapshot",
    "IAuthorizer",
    "IGuard",
    "IIdentityProvider",
    "IPermissionRepository",
    "IPolicy",
    "ISessionGuard",
]

_EXPORTS = {
    "IAccessTokenRepository": (
        "orionis.auth.contracts.token_repository",
        "IAccessTokenRepository",
    ),
    "IAuthManager": ("orionis.auth.contracts.manager", "IAuthManager"),
    "IAuthenticatable": ("orionis.auth.contracts.authenticatable", "IAuthenticatable"),
    "IAuthenticationContext": (
        "orionis.auth.contracts.context",
        "IAuthenticationContext",
    ),
    "IAuthorizable": ("orionis.auth.contracts.authorizable", "IAuthorizable"),
    "IAuthorizationSnapshot": (
        "orionis.auth.contracts.snapshot",
        "IAuthorizationSnapshot",
    ),
    "IAuthorizer": ("orionis.auth.contracts.authorizer", "IAuthorizer"),
    "IGuard": ("orionis.auth.contracts.guard", "IGuard"),
    "IIdentityProvider": (
        "orionis.auth.contracts.identity_provider",
        "IIdentityProvider",
    ),
    "IPermissionRepository": (
        "orionis.auth.contracts.permission_repository",
        "IPermissionRepository",
    ),
    "IPolicy": ("orionis.auth.contracts.policy", "IPolicy"),
    "ISessionGuard": ("orionis.auth.contracts.session_guard", "ISessionGuard"),
}
"""Public contract names mapped to their defining modules and attributes."""


def __getattr__(name: str) -> object:
    """
    Resolve a public contract on first access.

    Parameters
    ----------
    name : str
        Public export to resolve.

    Returns
    -------
    object
        Exported contract retaining its original module identity.

    Raises
    ------
    AttributeError
        If the name is not a public export.
    """
    return _resolve_export(globals(), _EXPORTS, name)


def __dir__() -> list[str]:
    """
    Include unloaded contracts in package introspection.

    Returns
    -------
    list[str]
        Sorted package attributes and public contract names.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
