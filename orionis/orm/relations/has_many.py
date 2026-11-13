"""One-to-many relationship: the related table owns the foreign key."""

import orionis.orm as _orm
from orionis.orm.relations.has_one_or_many import HasOneOrManyRelation
from orionis.support.types.collection import Collection


class HasManyRelation[TRelated: _orm.Model](HasOneOrManyRelation[TRelated]):
    """
    One-to-many relationship: the related table owns the foreign key.

    Mirrors Eloquent's ``HasMany``: the parent owns zero or more related
    rows (for instance ``User`` owning many ``Post`` rows), the foreign
    key living on the related table.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    async def getResults(self) -> Collection:
        """
        Retrieve every related row owned by the parent instance.

        Returns
        -------
        orionis.support.types.Collection
            Related models; empty when the parent has no key or no row
            references it.
        """
        if getattr(self._parent, self._local_key) is None:
            return Collection([])
        return await self.get()

    def match(
        self,
        models: list[_orm.Model],
        results: Collection,
        name: str,
    ) -> None:
        """
        Attach every matching related row to each parent instance.

        Parameters
        ----------
        models : list of orionis.orm.Model
            Parent instances being eager loaded together.
        results : orionis.support.types.Collection
            Related rows produced by ``getEager``.
        name : str
            Relationship name the results are stored under.

        Returns
        -------
        None
            No return value.
        """
        groups = self._groupByForeignKey(results)
        for model in models:
            key = getattr(model, self._local_key)
            model.setRelation(name, Collection(groups.get(key)))
