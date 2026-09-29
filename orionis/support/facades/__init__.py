from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.support.facades.application import Application
    from orionis.support.facades.auth import Auth
    from orionis.support.facades.cache import Cache
    from orionis.support.facades.catch import Catch
    from orionis.support.facades.datetime import DateTime
    from orionis.support.facades.db import DB
    from orionis.support.facades.encrypter import Crypt
    from orionis.support.facades.hash import Hash
    from orionis.support.facades.lang import Lang
    from orionis.support.facades.logger import Log
    from orionis.support.facades.mail import Mail
    from orionis.support.facades.reactor import Reactor
    from orionis.support.facades.router import Route
    from orionis.support.facades.schedule import Schedule
    from orionis.support.facades.schema import Schema
    from orionis.support.facades.session import Session
    from orionis.support.facades.storage import Storage
    from orionis.support.facades.testing import Test
    from orionis.support.facades.view import View

__all__ = [
    "DB",
    "Application",
    "Auth",
    "Cache",
    "Catch",
    "Crypt",
    "DateTime",
    "Hash",
    "Lang",
    "Log",
    "Mail",
    "Reactor",
    "Route",
    "Schedule",
    "Schema",
    "Session",
    "Storage",
    "Test",
    "View",
]

_EXPORTS = {
    "DB": ("orionis.support.facades.db", "DB"),
    "Application": ("orionis.support.facades.application", "Application"),
    "Auth": ("orionis.support.facades.auth", "Auth"),
    "Cache": ("orionis.support.facades.cache", "Cache"),
    "Catch": ("orionis.support.facades.catch", "Catch"),
    "Crypt": ("orionis.support.facades.encrypter", "Crypt"),
    "DateTime": ("orionis.support.facades.datetime", "DateTime"),
    "Hash": ("orionis.support.facades.hash", "Hash"),
    "Lang": ("orionis.support.facades.lang", "Lang"),
    "Log": ("orionis.support.facades.logger", "Log"),
    "Mail": ("orionis.support.facades.mail", "Mail"),
    "Reactor": ("orionis.support.facades.reactor", "Reactor"),
    "Route": ("orionis.support.facades.router", "Route"),
    "Schedule": ("orionis.support.facades.schedule", "Schedule"),
    "Schema": ("orionis.support.facades.schema", "Schema"),
    "Session": ("orionis.support.facades.session", "Session"),
    "Storage": ("orionis.support.facades.storage", "Storage"),
    "Test": ("orionis.support.facades.testing", "Test"),
    "View": ("orionis.support.facades.view", "View"),
}

def __getattr__(name: str) -> object:
    """Resolve and cache a public package export.

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
    """List loaded attributes and declared public exports.

    Returns
    -------
    list[str]
        Sorted attribute names available on this package.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
