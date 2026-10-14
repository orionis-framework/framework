from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.orm.schema.constraints.composite_foreign_key import CompositeForeignKey
    from orionis.orm.schema.constraints.foreign_reference import ForeignReference
    from orionis.orm.schema.constraints.table_index import TableIndex
    from orionis.orm.schema.constraints.unique_constraint import UniqueConstraint

__all__ = [
    "CompositeForeignKey",
    "ForeignReference",
    "TableIndex",
    "UniqueConstraint",
]

_EXPORTS = {
    "CompositeForeignKey": ("orionis.orm.schema.constraints.composite_foreign_key", "CompositeForeignKey"),
    "ForeignReference": ("orionis.orm.schema.constraints.foreign_reference", "ForeignReference"),
    "TableIndex": ("orionis.orm.schema.constraints.table_index", "TableIndex"),
    "UniqueConstraint": ("orionis.orm.schema.constraints.unique_constraint", "UniqueConstraint"),
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
