from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.orm.relations.has_one_or_many import HasOneOrManyRelation

if TYPE_CHECKING:
    from orionis.orm.model import Model
    from orionis.support.types.collection import Collection

class HasOneRelation[TRelated: "Model"](HasOneOrManyRelation[TRelated]):
    """
    One-to-one relationship: the related table owns the foreign key.

    Mirrors Eloquent's ``HasOne``: the parent is the "one" side (for
    instance ``User`` owning a single ``Profile``), while the foreign
    key lives on the related table.
    """

    __slots__ = ()

    async def getResults(self) -> TRelated | None:
        """
        Retrieve the single related row owned by the parent instance.

        Returns
        -------
        Model or None
            Related model, or ``None`` when the parent has no key or no
            row references it.
        """
        if getattr(self._parent, self._local_key) is None:
            return None
        return await self.first()

    def match(
        self,
        models: list[Model],
        results: Collection,
        name: str,
    ) -> None:
        """
        Attach the first matching related row to each parent instance.

        Parameters
        ----------
        models : list of Model
            Parent instances being eager loaded together.
        results : Collection
            Related rows produced by :meth:`getEager`.
        name : str
            Relationship name the result is stored under.

        Returns
        -------
        None
            This method does not return a value.
        """
        first_by_key = {}
        foreign_key = self._foreign_key
        for row in results:
            first_by_key.setdefault(getattr(row, foreign_key), row)
        for model in models:
            model.setRelation(name, first_by_key.get(getattr(model, self._local_key)))
