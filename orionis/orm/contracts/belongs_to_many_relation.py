from __future__ import annotations
from abc import abstractmethod
from typing import TYPE_CHECKING, Any
from orionis.orm.contracts.relation import IRelation

if TYPE_CHECKING:
    from collections.abc import Iterable

class IBelongsToManyRelation(IRelation):
    """
    Contract for a many-to-many relationship backed by a pivot table.

    Extends :class:`IRelation` with the pivot-specific operations that
    have no equivalent on the single-table relationship kinds.
    """

    @abstractmethod
    def wherePivot(
        self,
        column: str,
        *args: Any,  # noqa: ANN401
    ) -> IBelongsToManyRelation:
        """
        Filter the pivot rows considered by this relationship query.

        Parameters
        ----------
        column : str
            Pivot table column name.
        *args : Any
            Either the bound value, or an operator followed by a value.

        Returns
        -------
        IBelongsToManyRelation
            The same relationship, enabling fluent chaining.
        """

    @abstractmethod
    async def attach(
        self,
        ids: Any,  # noqa: ANN401
        attributes: dict[str, Any] | None = None,
    ) -> int:
        """
        Link the parent to the given related records via the pivot table.

        Parameters
        ----------
        ids : Any
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
    async def detach(self, ids: Any = None) -> int:  # noqa: ANN401
        """
        Unlink the parent from the given related records.

        Parameters
        ----------
        ids : Any, optional
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
        ids : Iterable
            Related ids or model instances that must remain attached.

        Returns
        -------
        dict of str to list
            ``"attached"`` and ``"detached"`` related id lists.
        """

    @abstractmethod
    async def toggle(self, ids: Iterable[Any]) -> dict[str, list[Any]]:
        """
        Attach ids not currently linked, detach ids that already are.

        Parameters
        ----------
        ids : Iterable
            Related ids or model instances to toggle.

        Returns
        -------
        dict of str to list
            ``"attached"`` and ``"detached"`` related id lists.
        """
