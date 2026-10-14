from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.orm.schema.column.definition import ColumnDefinition
    from orionis.orm.schema.column.options import ColumnOptions

__all__ = [
    "ColumnDefinition",
    "ColumnOptions",
]

_EXPORTS = {
    "ColumnDefinition": ("orionis.orm.schema.column.definition", "ColumnDefinition"),
    "ColumnOptions": ("orionis.orm.schema.column.options", "ColumnOptions"),
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
