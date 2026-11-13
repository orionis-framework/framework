# ruff: noqa: TC001
# Resolve model and collection annotations through the lazy public package.
"""Inverse relationship: the foreign key lives on the parent row."""

import orionis.orm as _orm
from orionis.orm.metaclass import snake_case
from orionis.orm.relations.relation import Relation

from orionis.support.types.collection import Collection


class BelongsToRelation[TRelated: _orm.Model](Relation[TRelated]):
    """
    Inverse relationship: the foreign key lives on the parent row.

    Mirrors Eloquent's ``BelongsTo``: for instance ``Post belongsTo
    User``, where ``posts.user_id`` points back at ``users.id``. Unlike
    ``hasOne``/``hasMany``, the foreign key is read from the parent
    instance itself, never queried on the related table.
    """

    __slots__ = ("_foreign_key", "_owner_key")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self,
        parent: _orm.Model,
        related: type[TRelated],
        foreign_key: str | None,
        owner_key: str | None,
    ) -> None:
        """
        Bind the relationship.

        Parameters
        ----------
        parent : orionis.orm.Model
            Model instance the relationship is accessed from.
        related : type of orionis.orm.Model
            Model class the relationship targets.
        foreign_key : str or None
            Column on the parent referencing the related row; defaults
            to ``snake_case(RelatedClass) + "_id"``.
        owner_key : str or None
            Column on the related table identifying the owning row;
            defaults to the related model's primary key.

        Returns
        -------
        None
            No return value.
        """
        self._foreign_key = foreign_key or f"{snake_case(related.__name__)}_id"
        """
        Column on the parent referencing the related row; defaults to
        ``snake_case(RelatedClass) + "_id"``.
        """
        self._owner_key = owner_key or related.__meta__.primary_key
        """
        Column on the related table identifying the owning row; defaults to the
        related model's primary key.
        """
        super().__init__(parent, related)

    def addConstraints(self) -> None:
        """
        Constrain the query to the row owning the parent's foreign key.

        Returns
        -------
        None
            No return value.
        """
        value = getattr(self._parent, self._foreign_key)
        if value is None:
            # A NULL foreign key never owns a row; avoid matching one
            # whose primary key happens to be NULL through IS NULL.
            self.whereIn(self._owner_key, ())
        else:
            self.where(self._owner_key, value)

    def addEagerConstraints(self, models: list[_orm.Model]) -> None:
        """
        Constrain the query to the rows owning every child's foreign key.

        Parameters
        ----------
        models : list of orionis.orm.Model
            Child instances being eager loaded together.

        Returns
        -------
        None
            No return value.
        """
        keys = {
            value
            for model in models
            if (value := getattr(model, self._foreign_key)) is not None
        }
        self._eager_keys_empty = not keys
        """Whether eager loading has no parent keys to query."""
        self.whereIn(self._owner_key, keys)

    async def getResults(self) -> TRelated | None:
        """
        Retrieve the owning row referenced by the parent's foreign key.

        Returns
        -------
        orionis.orm.Model or None
            Owning model, or ``None`` when the foreign key is unset or
            references no row.
        """
        if getattr(self._parent, self._foreign_key) is None:
            return None
        return await self.first()

    def match(
        self,
        models: list[_orm.Model],
        results: Collection,
        name: str,
    ) -> None:
        """
        Attach the owning row to each child instance.

        Parameters
        ----------
        models : list of orionis.orm.Model
            Child instances being eager loaded together.
        results : orionis.support.types.Collection
            Owning rows produced by ``getEager``.
        name : str
            Relationship name the result is stored under.

        Returns
        -------
        None
            No return value.
        """
        by_owner_key = {getattr(row, self._owner_key): row for row in results}
        for model in models:
            key = getattr(model, self._foreign_key)
            model.setRelation(name, by_owner_key.get(key))
