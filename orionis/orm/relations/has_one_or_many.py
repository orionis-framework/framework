from __future__ import annotations
from typing import TYPE_CHECKING, Any
from orionis.orm.metaclass import snake_case
from orionis.orm.relations.relation import Relation

if TYPE_CHECKING:
    from orionis.orm.model import Model
    from orionis.support.types.collection import Collection

class HasOneOrManyRelation[TRelated: "Model"](Relation[TRelated]):
    """
    Shared machinery for the ``hasOne``/``hasMany`` relationship kinds.

    The related table holds the foreign key pointing back at the
    parent's local key. The two concrete kinds
    (:class:`~orionis.orm.relations.has_one.HasOneRelation` and
    :class:`~orionis.orm.relations.has_many.HasManyRelation`) only
    differ in how many rows they resolve to.
    """

    __slots__ = ("_foreign_key", "_local_key")

    def __init__(
        self,
        parent: Model,
        related: type[TRelated],
        foreign_key: str | None,
        local_key: str | None,
    ) -> None:
        """
        Bind the relationship.

        Parameters
        ----------
        parent : Model
            Model instance the relationship is accessed from.
        related : type of Model
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
            This method does not return a value.
        """
        self._foreign_key = foreign_key or f"{snake_case(type(parent).__name__)}_id"
        self._local_key = local_key or type(parent).__meta__.primary_key
        super().__init__(parent, related)

    def addConstraints(self) -> None:
        """
        Constrain the query to the rows owned by the parent instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        value = getattr(self._parent, self._local_key)
        if value is None:
            # An unsaved or keyless parent must never match rows whose
            # foreign key happens to be NULL; force an empty result set.
            self.whereIn(self._foreign_key, ())
        else:
            self.where(self._foreign_key, value)

    def addEagerConstraints(self, models: list[Model]) -> None:
        """
        Constrain the query to the rows owned by every parent instance.

        Parameters
        ----------
        models : list of Model
            Parent instances being eager loaded together.

        Returns
        -------
        None
            This method does not return a value.
        """
        keys = {
            value
            for model in models
            if (value := getattr(model, self._local_key)) is not None
        }
        self.whereIn(self._foreign_key, keys)

    def _groupByForeignKey(
        self,
        results: Collection,
    ) -> dict[Any, list[TRelated]]:
        """
        Group related rows by their foreign key value.

        Parameters
        ----------
        results : Collection
            Related rows produced by an eager query.

        Returns
        -------
        dict
            Related rows grouped by the parent key they belong to.
        """
        groups: dict[Any, list[TRelated]] = {}
        for row in results:
            groups.setdefault(getattr(row, self._foreign_key), []).append(row)
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
        Model
            Persisted related model, already linked to the parent.

        Raises
        ------
        MassAssignmentException
            If an attribute (including the foreign key) violates the
            related model's fillable/guarded rules.
        """
        payload = dict(attributes)
        payload[self._foreign_key] = getattr(self._parent, self._local_key)
        return await self._model.create(payload)
