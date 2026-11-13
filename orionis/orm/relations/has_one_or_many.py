# ruff: noqa: TC001
# Keep model and collection annotations available to runtime introspection.
"""Shared machinery for the ``hasOne``/``hasMany`` relationship kinds."""

import orionis.orm as _orm
from collections import defaultdict
from typing import Any
from orionis.orm.metaclass import snake_case
from orionis.orm.relations.relation import Relation

from orionis.support.types.collection import Collection


class HasOneOrManyRelation[TRelated: _orm.Model](Relation[TRelated]):
    """
    Shared machinery for the ``hasOne``/``hasMany`` relationship kinds.

    The related table holds the foreign key pointing back at the
    parent's local key. The two concrete kinds
    (:class:`orionis.orm.relations.HasOneRelation` and
    :class:`orionis.orm.relations.HasManyRelation`) only
    differ in how many rows they resolve to.
    """

    __slots__ = ("_foreign_key", "_local_key")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self,
        parent: _orm.Model,
        related: type[TRelated],
        foreign_key: str | None,
        local_key: str | None,
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
            Column on the related table referencing the parent; defaults
            to ``snake_case(ParentClass) + "_id"``.
        local_key : str or None
            Column on the parent compared against the foreign key;
            defaults to the parent's primary key.

        Returns
        -------
        None
            No return value.
        """
        self._foreign_key = foreign_key or f"{snake_case(type(parent).__name__)}_id"
        """
        Column on the related table referencing the parent; defaults to
        ``snake_case(ParentClass) + "_id"``.
        """
        self._local_key = local_key or type(parent).__meta__.primary_key
        """
        Column on the parent compared against the foreign key; defaults to the
        parent's primary key.
        """
        super().__init__(parent, related)

    def addConstraints(self) -> None:
        """
        Constrain the query to the rows owned by the parent instance.

        Returns
        -------
        None
            No return value.
        """
        value = getattr(self._parent, self._local_key)
        if value is None:
            # An unsaved or keyless parent must never match rows whose
            # foreign key happens to be NULL; force an empty result set.
            self.whereIn(self._foreign_key, ())
        else:
            self.where(self._foreign_key, value)

    def addEagerConstraints(self, models: list[_orm.Model]) -> None:
        """
        Constrain the query to the rows owned by every parent instance.

        Parameters
        ----------
        models : list of orionis.orm.Model
            Parent instances being eager loaded together.

        Returns
        -------
        None
            No return value.
        """
        keys = {
            value
            for model in models
            if (value := getattr(model, self._local_key)) is not None
        }
        self._eager_keys_empty = not keys
        """Whether eager loading has no parent keys to query."""
        self.whereIn(self._foreign_key, keys)

    def _groupByForeignKey(
        self,
        results: Collection,
    ) -> dict[Any, list[TRelated]]:
        """
        Group related rows by their foreign key value.

        Parameters
        ----------
        results : orionis.support.types.Collection
            Related rows produced by an eager query.

        Returns
        -------
        dict
            Related rows grouped by the parent key they belong to.
        """
        groups: dict[Any, list[TRelated]] = defaultdict(list)
        foreign_key = self._foreign_key
        for row in results:
            groups[getattr(row, foreign_key)].append(row)
        return groups

    async def create(self, attributes: dict[str, Any]) -> TRelated:
        """
        Create and persist a new related model, auto-linking it via the foreign key.

        Equivalent to Eloquent's ``$parent->relation()->create($attrs)``.

        Parameters
        ----------
        attributes : dict
            Attributes to mass assign on the new related model.

        Returns
        -------
        orionis.orm.Model
            Related model linked to the parent and saved on this relationship's
            connection, unless a model event vetoes persistence.

        Raises
        ------
        orionis.orm.exceptions.MassAssignmentException
            If an attribute (including the foreign key) violates the
            related model's fillable/guarded rules.
        """
        payload = dict(attributes)
        payload[self._foreign_key] = getattr(self._parent, self._local_key)
        model = self._model(payload)
        object.__setattr__(model, "_read_connection", self._connection())
        await model.save()
        return model
