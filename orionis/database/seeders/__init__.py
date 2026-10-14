from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.database.seeders.events import SeederEvents
    from orionis.database.seeders.runner import SeederRunner
    from orionis.database.seeders.seeder import Seeder

__all__ = [
    "Seeder",
    "SeederEvents",
    "SeederRunner",
]

_EXPORTS = {
    "Seeder": ("orionis.database.seeders.seeder", "Seeder"),
    "SeederEvents": ("orionis.database.seeders.events", "SeederEvents"),
    "SeederRunner": ("orionis.database.seeders.runner", "SeederRunner"),
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
