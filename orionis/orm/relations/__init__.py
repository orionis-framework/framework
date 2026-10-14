from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.orm.relations.belongs_to import BelongsToRelation
    from orionis.orm.relations.belongs_to_many import BelongsToManyRelation
    from orionis.orm.relations.has_many import HasManyRelation
    from orionis.orm.relations.has_one import HasOneRelation
    from orionis.orm.relations.has_one_or_many import HasOneOrManyRelation
    from orionis.orm.relations.mixin import RelationsMixin
    from orionis.orm.relations.relation import Relation

__all__ = [
    "BelongsToManyRelation",
    "BelongsToRelation",
    "HasManyRelation",
    "HasOneOrManyRelation",
    "HasOneRelation",
    "Relation",
    "RelationsMixin",
]

_EXPORTS = {
    "BelongsToManyRelation": ("orionis.orm.relations.belongs_to_many", "BelongsToManyRelation"),
    "BelongsToRelation": ("orionis.orm.relations.belongs_to", "BelongsToRelation"),
    "HasManyRelation": ("orionis.orm.relations.has_many", "HasManyRelation"),
    "HasOneOrManyRelation": ("orionis.orm.relations.has_one_or_many", "HasOneOrManyRelation"),
    "HasOneRelation": ("orionis.orm.relations.has_one", "HasOneRelation"),
    "Relation": ("orionis.orm.relations.relation", "Relation"),
    "RelationsMixin": ("orionis.orm.relations.mixin", "RelationsMixin"),
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
