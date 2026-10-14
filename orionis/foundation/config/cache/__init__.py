from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.foundation.config.cache.entities.cache import Cache
    from orionis.foundation.config.cache.entities.database import Database
    from orionis.foundation.config.cache.entities.file import File
    from orionis.foundation.config.cache.entities.memcached import Memcached
    from orionis.foundation.config.cache.entities.memory import Memory
    from orionis.foundation.config.cache.entities.redis import Redis
    from orionis.foundation.config.cache.entities.stores import Stores
    from orionis.foundation.config.cache.enums.drivers import Drivers

__all__ = [
    "Cache",
    "Database",
    "Drivers",
    "File",
    "Memcached",
    "Memory",
    "Redis",
    "Stores",
]

_EXPORTS = {
    "Cache": ("orionis.foundation.config.cache.entities.cache", "Cache"),
    "Database": ("orionis.foundation.config.cache.entities.database", "Database"),
    "Drivers": ("orionis.foundation.config.cache.enums.drivers", "Drivers"),
    "File": ("orionis.foundation.config.cache.entities.file", "File"),
    "Memcached": ("orionis.foundation.config.cache.entities.memcached", "Memcached"),
    "Memory": ("orionis.foundation.config.cache.entities.memory", "Memory"),
    "Redis": ("orionis.foundation.config.cache.entities.redis", "Redis"),
    "Stores": ("orionis.foundation.config.cache.entities.stores", "Stores"),
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
