# ruff: noqa: TC001
# Keep model and collection annotations available to runtime introspection.
"""One-to-one relationship: the related table owns the foreign key."""

import orionis.orm as _orm
from orionis.orm.relations.has_one_or_many import HasOneOrManyRelation

from orionis.support.types.collection import Collection


class HasOneRelation[TRelated: _orm.Model](HasOneOrManyRelation[TRelated]):
    """
    One-to-one relationship: the related table owns the foreign key.

    Mirrors Eloquent's ``HasOne``: the parent is the "one" side (for
    instance ``User`` owning a single ``Profile``), while the foreign
    key lives on the related table.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    async def getResults(self) -> TRelated | None:
        """
        Retrieve the single related row owned by the parent instance.

        Returns
        -------
        orionis.orm.Model or None
            Related model, or ``None`` when the parent has no key or no
            row references it.
        """
        if getattr(self._parent, self._local_key) is None:
            return None
        return await self.first()

    def match(
        self,
        models: list[_orm.Model],
        results: Collection,
        name: str,
    ) -> None:
        """
        Attach the first matching related row to each parent instance.

        Parameters
        ----------
        models : list of orionis.orm.Model
            Parent instances being eager loaded together.
        results : orionis.support.types.Collection
            Related rows produced by ``getEager``.
        name : str
            Relationship name the result is stored under.

        Returns
        -------
        None
            No return value.
        """
        first_by_key = {}
        foreign_key = self._foreign_key
        for row in results:
            first_by_key.setdefault(getattr(row, foreign_key), row)
        for model in models:
            model.setRelation(name, first_by_key.get(getattr(model, self._local_key)))
