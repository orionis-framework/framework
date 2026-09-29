from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.cache.cache_manager import CacheManager
    from orionis.cache.file_based_cache import FileBasedCache
    from orionis.cache.repository import CacheRepository

__all__ = [
    "CacheManager",
    "CacheRepository",
    "FileBasedCache",
]

_EXPORTS = {
    "CacheManager": ("orionis.cache.cache_manager", "CacheManager"),
    "CacheRepository": ("orionis.cache.repository", "CacheRepository"),
    "FileBasedCache": ("orionis.cache.file_based_cache", "FileBasedCache"),
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
