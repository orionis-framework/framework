
class AuthException(Exception):
    """Base exception for every failure raised by the authentication module."""

class AuthConfigurationException(AuthException):
    """Raise when the authentication configuration is missing or invalid."""

class AuthenticationException(AuthException):
    """Raise when the current request carries no valid authenticated identity."""

class AuthorizationException(AuthException):
    """Raise when an authenticated identity lacks the required authorization."""

class GuardNotFoundException(AuthException):
    """Raise when the requested authentication guard is not registered."""

class IdentityProviderException(AuthException):
    """Raise when the identity provider cannot resolve the application identity."""

class PolicyNotFoundException(AuthException):
    """Raise when no policy is registered for the requested resource type."""

class TokenException(AuthException):
    """Raise when a personal access token cannot be issued or verified."""
