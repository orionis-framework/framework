from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.foundation.config.scheduler.entities.database import Database
    from orionis.foundation.config.scheduler.entities.memory import Memory
    from orionis.foundation.config.scheduler.entities.redis import Redis
    from orionis.foundation.config.scheduler.entities.scheduler import Scheduler
    from orionis.foundation.config.scheduler.entities.stores import Stores
    from orionis.foundation.config.scheduler.enums.drivers import Drivers

__all__ = [
    "Database",
    "Drivers",
    "Memory",
    "Redis",
    "Scheduler",
    "Stores",
]

_EXPORTS = {
    "Database": ("orionis.foundation.config.scheduler.entities.database", "Database"),
    "Drivers": ("orionis.foundation.config.scheduler.enums.drivers", "Drivers"),
    "Memory": ("orionis.foundation.config.scheduler.entities.memory", "Memory"),
    "Redis": ("orionis.foundation.config.scheduler.entities.redis", "Redis"),
    "Scheduler": ("orionis.foundation.config.scheduler.entities.scheduler", "Scheduler"),
    "Stores": ("orionis.foundation.config.scheduler.entities.stores", "Stores"),
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
