from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.orm.query.builder import ModelQueryBuilder
    from orionis.orm.query.expressions import (
        AggregateClause,
        AggregateFunction,
        DeletePlan,
        InsertPlan,
        OrderClause,
        SelectPlan,
        SortDirection,
        UpdatePlan,
        WhereClause,
        WhereType,
    )

__all__ = [
    "AggregateClause",
    "AggregateFunction",
    "DeletePlan",
    "InsertPlan",
    "ModelQueryBuilder",
    "OrderClause",
    "SelectPlan",
    "SortDirection",
    "UpdatePlan",
    "WhereClause",
    "WhereType",
]

_EXPORTS = {
    "AggregateClause": ("orionis.orm.query.expressions", "AggregateClause"),
    "AggregateFunction": ("orionis.orm.query.expressions", "AggregateFunction"),
    "DeletePlan": ("orionis.orm.query.expressions", "DeletePlan"),
    "InsertPlan": ("orionis.orm.query.expressions", "InsertPlan"),
    "ModelQueryBuilder": ("orionis.orm.query.builder", "ModelQueryBuilder"),
    "OrderClause": ("orionis.orm.query.expressions", "OrderClause"),
    "SelectPlan": ("orionis.orm.query.expressions", "SelectPlan"),
    "SortDirection": ("orionis.orm.query.expressions", "SortDirection"),
    "UpdatePlan": ("orionis.orm.query.expressions", "UpdatePlan"),
    "WhereClause": ("orionis.orm.query.expressions", "WhereClause"),
    "WhereType": ("orionis.orm.query.expressions", "WhereType"),
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
