from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.view.globals.app import _global_app
    from orionis.view.globals.asset import _global_asset, _global_secure_asset
    from orionis.view.globals.auth import _global_auth
    from orionis.view.globals.bcrypt import _global_decrypt, _global_encrypt
    from orionis.view.globals.cache import _global_cache
    from orionis.view.globals.collection import _global_collect
    from orionis.view.globals.config import _global_config
    from orionis.view.globals.csrf import _global_csrf_field, _global_csrf_token
    from orionis.view.globals.datetime import _global_now, _global_today
    from orionis.view.globals.dump import _global_dump
    from orionis.view.globals.errors import _global_errors
    from orionis.view.globals.flash import _global_flash
    from orionis.view.globals.lang import (
        _global_choice,
        _global_locale,
        _global_locales,
        _global_trans,
    )
    from orionis.view.globals.old import _global_old
    from orionis.view.globals.request import _global_request
    from orionis.view.globals.route import _global_route
    from orionis.view.globals.session import _global_session
    from orionis.view.globals.stringable import _global_stringable
    from orionis.view.globals.url import _global_secure_url, _global_url
    from orionis.view.globals.version import (
        _global_framework_version,
        _global_python_version,
    )

__all__ = [
    "_global_app",
    "_global_asset",
    "_global_auth",
    "_global_cache",
    "_global_choice",
    "_global_collect",
    "_global_config",
    "_global_csrf_field",
    "_global_csrf_token",
    "_global_decrypt",
    "_global_dump",
    "_global_encrypt",
    "_global_errors",
    "_global_flash",
    "_global_framework_version",
    "_global_locale",
    "_global_locales",
    "_global_now",
    "_global_old",
    "_global_python_version",
    "_global_request",
    "_global_route",
    "_global_secure_asset",
    "_global_secure_url",
    "_global_session",
    "_global_stringable",
    "_global_today",
    "_global_trans",
    "_global_url",
]

_EXPORTS = {
    "_global_app": ("orionis.view.globals.app", "_global_app"),
    "_global_asset": ("orionis.view.globals.asset", "_global_asset"),
    "_global_auth": ("orionis.view.globals.auth", "_global_auth"),
    "_global_cache": ("orionis.view.globals.cache", "_global_cache"),
    "_global_choice": ("orionis.view.globals.lang", "_global_choice"),
    "_global_collect": ("orionis.view.globals.collection", "_global_collect"),
    "_global_config": ("orionis.view.globals.config", "_global_config"),
    "_global_csrf_field": ("orionis.view.globals.csrf", "_global_csrf_field"),
    "_global_csrf_token": ("orionis.view.globals.csrf", "_global_csrf_token"),
    "_global_decrypt": ("orionis.view.globals.bcrypt", "_global_decrypt"),
    "_global_dump": ("orionis.view.globals.dump", "_global_dump"),
    "_global_encrypt": ("orionis.view.globals.bcrypt", "_global_encrypt"),
    "_global_errors": ("orionis.view.globals.errors", "_global_errors"),
    "_global_flash": ("orionis.view.globals.flash", "_global_flash"),
    "_global_framework_version": ("orionis.view.globals.version", "_global_framework_version"),
    "_global_locale": ("orionis.view.globals.lang", "_global_locale"),
    "_global_locales": ("orionis.view.globals.lang", "_global_locales"),
    "_global_now": ("orionis.view.globals.datetime", "_global_now"),
    "_global_old": ("orionis.view.globals.old", "_global_old"),
    "_global_python_version": ("orionis.view.globals.version", "_global_python_version"),
    "_global_request": ("orionis.view.globals.request", "_global_request"),
    "_global_route": ("orionis.view.globals.route", "_global_route"),
    "_global_secure_asset": ("orionis.view.globals.asset", "_global_secure_asset"),
    "_global_secure_url": ("orionis.view.globals.url", "_global_secure_url"),
    "_global_session": ("orionis.view.globals.session", "_global_session"),
    "_global_stringable": ("orionis.view.globals.stringable", "_global_stringable"),
    "_global_today": ("orionis.view.globals.datetime", "_global_today"),
    "_global_trans": ("orionis.view.globals.lang", "_global_trans"),
    "_global_url": ("orionis.view.globals.url", "_global_url"),
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
