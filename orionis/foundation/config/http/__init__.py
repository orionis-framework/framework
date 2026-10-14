from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.foundation.config.http.entitites.body import HTTPBodyLimits
    from orionis.foundation.config.http.entitites.cors import Cors
    from orionis.foundation.config.http.entitites.csrf import HTTPCsrf
    from orionis.foundation.config.http.entitites.http import HTTP
    from orionis.foundation.config.http.entitites.proxies import HTTPProxies
    from orionis.foundation.config.http.entitites.rate_limit import HTTPRateLimit
    from orionis.foundation.config.http.entitites.redis import Redis
    from orionis.foundation.config.http.entitites.security import HTTPSecurity
    from orionis.foundation.config.http.entitites.websocket import HTTPWebSocket

__all__ = [
    "HTTP",
    "Cors",
    "HTTPBodyLimits",
    "HTTPCsrf",
    "HTTPProxies",
    "HTTPRateLimit",
    "HTTPSecurity",
    "HTTPWebSocket",
    "Redis",
]

_EXPORTS = {
    "HTTP": ("orionis.foundation.config.http.entitites.http", "HTTP"),
    "Cors": ("orionis.foundation.config.http.entitites.cors", "Cors"),
    "HTTPBodyLimits": ("orionis.foundation.config.http.entitites.body", "HTTPBodyLimits"),
    "HTTPCsrf": ("orionis.foundation.config.http.entitites.csrf", "HTTPCsrf"),
    "HTTPProxies": ("orionis.foundation.config.http.entitites.proxies", "HTTPProxies"),
    "HTTPRateLimit": ("orionis.foundation.config.http.entitites.rate_limit", "HTTPRateLimit"),
    "HTTPSecurity": ("orionis.foundation.config.http.entitites.security", "HTTPSecurity"),
    "HTTPWebSocket": ("orionis.foundation.config.http.entitites.websocket", "HTTPWebSocket"),
    "Redis": ("orionis.foundation.config.http.entitites.redis", "Redis"),
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
