"""Group the orm query components and public imports."""

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

_EXPRESSIONS_MODULE = "orionis.orm.query.expressions"
"""Module defining the public query plan entities and enumerations."""

_EXPORTS = {
    "AggregateClause": (_EXPRESSIONS_MODULE, "AggregateClause"),
    "AggregateFunction": (_EXPRESSIONS_MODULE, "AggregateFunction"),
    "DeletePlan": (_EXPRESSIONS_MODULE, "DeletePlan"),
    "InsertPlan": (_EXPRESSIONS_MODULE, "InsertPlan"),
    "ModelQueryBuilder": ("orionis.orm.query.builder", "ModelQueryBuilder"),
    "OrderClause": (_EXPRESSIONS_MODULE, "OrderClause"),
    "SelectPlan": (_EXPRESSIONS_MODULE, "SelectPlan"),
    "SortDirection": (_EXPRESSIONS_MODULE, "SortDirection"),
    "UpdatePlan": (_EXPRESSIONS_MODULE, "UpdatePlan"),
    "WhereClause": (_EXPRESSIONS_MODULE, "WhereClause"),
    "WhereType": (_EXPRESSIONS_MODULE, "WhereType"),
}
"""Public export names mapped to their defining modules and attributes."""


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
