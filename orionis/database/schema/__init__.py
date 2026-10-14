from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.database.schema.blueprint import Blueprint
    from orionis.database.schema.column import Column
    from orionis.database.schema.comment import Comment
    from orionis.database.schema.foreign import ForeignKey
    from orionis.database.schema.index import Index
    from orionis.database.schema.primary import PrimaryKey
    from orionis.database.schema.unique import Unique
    from orionis.database.schema.timestamp import Timestamps

__all__ = [
    "Blueprint",
    "Column",
    "Comment",
    "ForeignKey",
    "Index",
    "PrimaryKey",
    "Timestamps",
    "Unique",
]

_EXPORTS = {
    "Blueprint": ("orionis.database.schema.blueprint", "Blueprint"),
    "Column": ("orionis.database.schema.column", "Column"),
    "Comment": ("orionis.database.schema.comment", "Comment"),
    "ForeignKey": ("orionis.database.schema.foreign", "ForeignKey"),
    "Index": ("orionis.database.schema.index", "Index"),
    "PrimaryKey": ("orionis.database.schema.primary", "PrimaryKey"),
    "Timestamps": ("orionis.database.schema.timestamp", "Timestamps"),
    "Unique": ("orionis.database.schema.unique", "Unique"),
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
