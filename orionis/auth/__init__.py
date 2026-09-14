from orionis.auth.authorization.policy import Policy
from orionis.auth.authorization.snapshot import AuthorizationSnapshot
from orionis.auth.concerns.authenticatable import Authenticatable
from orionis.auth.concerns.authorizable import Authorizable
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.entities.access_token import AccessToken
from orionis.auth.entities.new_access_token import NewAccessToken
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

# ``AuthManager``, ``AuthProvider`` and the guards are not re-exported
# here on purpose: they depend on the HTTP and ORM stacks, while this
# package is imported very early through ``orionis.support.facades``.
# Import them from their own modules when you need them.

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
    "NewAccessToken",
    "Policy",
    "PolicyNotFoundException",
    "TokenException",
]
