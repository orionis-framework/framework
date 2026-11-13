# ruff: noqa: ANN401, TC001, TC003
# Accept dynamic pivot identities and retain runtime iterable annotations.
"""Contract for a many-to-many relationship backed by a pivot table."""

from abc import abstractmethod
from typing import Any
from orionis.orm.contracts.relation import IRelation
from orionis.support.types.collection import Collection

from collections.abc import Iterable


class IBelongsToManyRelation(IRelation):
    """
    Contract for a many-to-many relationship backed by a pivot table.

    Extends :class:`orionis.orm.contracts.relation.IRelation` with the pivot-specific
    operations that
    have no equivalent on the single-table relationship kinds.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    async def getResults(self) -> Collection:
        """
        Retrieve every related model linked to the bound parent.

        Returns
        -------
        orionis.support.types.Collection
            Related models selected by this pivot query.
        """

    @abstractmethod
    def wherePivot(
        self,
        column: str,
        *args: Any,
    ) -> IBelongsToManyRelation:
        """
        Filter the pivot rows considered by this relationship query.

        Parameters
        ----------
        column : str
            Pivot table column name.
        *args : typing.Any
            Either the bound value, or an operator followed by a value.

        Returns
        -------
        orionis.orm.contracts.belongs_to_many_relation.IBelongsToManyRelation
            The same relationship, enabling fluent chaining.
        """

    @abstractmethod
    async def attach(
        self,
        ids: Any,
        attributes: dict[str, Any] | None = None,
    ) -> int:
        """
        Link the parent to the given related records via the pivot table.

        Parameters
        ----------
        ids : typing.Any
            A related id, model instance, iterable of either, or a
            mapping of id to per-row pivot attributes.
        attributes : dict or None, optional
            Extra pivot column values applied to every inserted row when
            ``ids`` is not already a mapping.

        Returns
        -------
        int
            Number of pivot rows inserted.
        """

    @abstractmethod
    async def detach(self, ids: Any = None) -> int:
        """
        Unlink the parent from the given related records.

        Parameters
        ----------
        ids : typing.Any, optional
            A related id, model instance, or iterable of either;
            ``None`` detaches every related record.

        Returns
        -------
        int
            Number of pivot rows deleted.
        """

    @abstractmethod
    async def sync(self, ids: Iterable[Any]) -> dict[str, list[Any]]:
        """
        Attach exactly the given records, detaching every other one.

        Parameters
        ----------
        ids : collections.abc.Iterable
            Related ids or model instances that must remain attached.

        Returns
        -------
        dict of str ``to`` list
            ``"attached"`` and ``"detached"`` related id lists.
        """

    @abstractmethod
    async def toggle(self, ids: Iterable[Any]) -> dict[str, list[Any]]:
        """
        Attach ids not currently linked, detach ids that already are.

        Parameters
        ----------
        ids : collections.abc.Iterable
            Related ids or model instances to toggle.

        Returns
        -------
        dict of str ``to`` list
            ``"attached"`` and ``"detached"`` related id lists.
        """
