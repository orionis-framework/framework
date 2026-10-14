from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.support.types.collection import Collection
    from orionis.support.types.dot_dict import DotDict
    from orionis.support.types.sentinel import MISSING
    from orionis.support.types.stringable import Stringable
    from orionis.support.types.std import StdClass

__all__ = [
    "MISSING",
    "Collection",
    "DotDict",
    "StdClass",
    "Stringable",
]

_EXPORTS = {
    "MISSING": ("orionis.support.types.sentinel", "MISSING"),
    "Collection": ("orionis.support.types.collection", "Collection"),
    "DotDict": ("orionis.support.types.dot_dict", "DotDict"),
    "StdClass": ("orionis.support.types.std", "StdClass"),
    "Stringable": ("orionis.support.types.stringable", "Stringable"),
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
