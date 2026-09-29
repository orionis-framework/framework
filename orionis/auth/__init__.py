from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.auth.authorization.policy import Policy
    from orionis.auth.authorization.snapshot import AuthorizationSnapshot
    from orionis.auth.concerns.authenticatable import Authenticatable
    from orionis.auth.concerns.authorizable import Authorizable
    from orionis.auth.context.context import AuthenticationContext
    from orionis.auth.entities.access_token import AccessToken
    from orionis.auth.entities.new_access_token import NewAccessToken
    from orionis.auth.concerns.must_verify_email import MustVerifyEmail
    from orionis.auth.exceptions import (
        AuthConfigurationException,
        AuthenticationException,
        AuthException,
        AuthorizationException,
        GuardNotFoundException,
        IdentityProviderException,
        PolicyNotFoundException,
        TokenException,
    )

__all__ = [
    "AccessToken",
    "AuthConfigurationException",
    "AuthException",
    "Authenticatable",
    "AuthenticationContext",
    "AuthenticationException",
    "Authorizable",
    "AuthorizationException",
    "AuthorizationSnapshot",
    "GuardNotFoundException",
    "IdentityProviderException",
    "MustVerifyEmail",
    "NewAccessToken",
    "Policy",
    "PolicyNotFoundException",
    "TokenException",
]

_EXPORTS = {
    "AccessToken": ("orionis.auth.entities.access_token", "AccessToken"),
    "AuthConfigurationException": ("orionis.auth.exceptions", "AuthConfigurationException"),  # NOSONAR
    "AuthException": ("orionis.auth.exceptions", "AuthException"),
    "Authenticatable": ("orionis.auth.concerns.authenticatable", "Authenticatable"),
    "AuthenticationContext": ("orionis.auth.context.context", "AuthenticationContext"),
    "AuthenticationException": ("orionis.auth.exceptions", "AuthenticationException"),
    "Authorizable": ("orionis.auth.concerns.authorizable", "Authorizable"),
    "AuthorizationException": ("orionis.auth.exceptions", "AuthorizationException"),
    "AuthorizationSnapshot": ("orionis.auth.authorization.snapshot", "AuthorizationSnapshot"),
    "GuardNotFoundException": ("orionis.auth.exceptions", "GuardNotFoundException"),
    "IdentityProviderException": ("orionis.auth.exceptions", "IdentityProviderException"),
    "MustVerifyEmail": ("orionis.auth.concerns.must_verify_email", "MustVerifyEmail"),
    "NewAccessToken": ("orionis.auth.entities.new_access_token", "NewAccessToken"),
    "Policy": ("orionis.auth.authorization.policy", "Policy"),
    "PolicyNotFoundException": ("orionis.auth.exceptions", "PolicyNotFoundException"),
    "TokenException": ("orionis.auth.exceptions", "TokenException"),
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
