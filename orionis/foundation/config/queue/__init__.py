from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.foundation.config.queue.entities.connections import Connections
    from orionis.foundation.config.queue.entities.database import Database
    from orionis.foundation.config.queue.entities.failed import Failed
    from orionis.foundation.config.queue.entities.queue import Queue
    from orionis.foundation.config.queue.entities.redis import Redis
    from orionis.foundation.config.queue.entities.sync import Sync
    from orionis.foundation.config.queue.entities.worker import Worker
    from orionis.foundation.config.queue.enums.drivers import Drivers

__all__ = [
    "Connections",
    "Database",
    "Drivers",
    "Failed",
    "Queue",
    "Redis",
    "Sync",
    "Worker",
]

_EXPORTS = {
    "Connections": ("orionis.foundation.config.queue.entities.connections", "Connections"),
    "Database": ("orionis.foundation.config.queue.entities.database", "Database"),
    "Drivers": ("orionis.foundation.config.queue.enums.drivers", "Drivers"),
    "Failed": ("orionis.foundation.config.queue.entities.failed", "Failed"),
    "Queue": ("orionis.foundation.config.queue.entities.queue", "Queue"),
    "Redis": ("orionis.foundation.config.queue.entities.redis", "Redis"),
    "Sync": ("orionis.foundation.config.queue.entities.sync", "Sync"),
    "Worker": ("orionis.foundation.config.queue.entities.worker", "Worker"),
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
