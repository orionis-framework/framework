from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.console.base.command import BaseCommand
    from orionis.console.base.listener import BaseTaskListener
    from orionis.console.base.scheduler import BaseScheduler

__all__ = [
    "BaseCommand",
    "BaseScheduler",
    "BaseTaskListener",
]

_EXPORTS = {
    "BaseCommand": ("orionis.console.base.command", "BaseCommand"),
    "BaseScheduler": ("orionis.console.base.scheduler", "BaseScheduler"),
    "BaseTaskListener": ("orionis.console.base.listener", "BaseTaskListener"),
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
