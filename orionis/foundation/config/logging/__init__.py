from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.foundation.config.logging.entities.channels import Channels
    from orionis.foundation.config.logging.entities.chunked import Chunked
    from orionis.foundation.config.logging.entities.daily import Daily
    from orionis.foundation.config.logging.entities.hourly import Hourly
    from orionis.foundation.config.logging.entities.logging import Logging
    from orionis.foundation.config.logging.entities.monthly import Monthly
    from orionis.foundation.config.logging.entities.stack import Stack
    from orionis.foundation.config.logging.entities.weekly import Weekly
    from orionis.foundation.config.logging.enums.levels import Level

__all__ = [
    "Channels",
    "Chunked",
    "Daily",
    "Hourly",
    "Level",
    "Logging",
    "Monthly",
    "Stack",
    "Weekly",
]

_EXPORTS = {
    "Channels": ("orionis.foundation.config.logging.entities.channels", "Channels"),
    "Chunked": ("orionis.foundation.config.logging.entities.chunked", "Chunked"),
    "Daily": ("orionis.foundation.config.logging.entities.daily", "Daily"),
    "Hourly": ("orionis.foundation.config.logging.entities.hourly", "Hourly"),
    "Level": ("orionis.foundation.config.logging.enums.levels", "Level"),
    "Logging": ("orionis.foundation.config.logging.entities.logging", "Logging"),
    "Monthly": ("orionis.foundation.config.logging.entities.monthly", "Monthly"),
    "Stack": ("orionis.foundation.config.logging.entities.stack", "Stack"),
    "Weekly": ("orionis.foundation.config.logging.entities.weekly", "Weekly"),
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
