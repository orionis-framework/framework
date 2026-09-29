from __future__ import annotations
from abc import abstractmethod
from typing import TYPE_CHECKING, Any
from orionis.orm.contracts.builder import IModelQueryBuilder

if TYPE_CHECKING:
    from orionis.orm.model import Model
    from orionis.support.types.collection import Collection

class IRelation(IModelQueryBuilder):
    """
    Contract for a query builder bound to a parent model instance.

    Every relationship kind (``hasOne``, ``hasMany``, ``belongsTo``,
    ``belongsToMany``, and future ones such as polymorphic or
    through-relations) implements this template so eager loading can
    drive any of them without knowing its concrete type.
    """

    @abstractmethod
    def addConstraints(self) -> None:
        """
        Constrain the query to the bound parent instance.

        Applied once during construction, unless constraints are
        suspended for eager loading.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    def addEagerConstraints(self, models: list[Model]) -> None:
        """
        Constrain the query to every parent instance of an eager batch.

        Parameters
        ----------
        models : list of Model
            Parent instances being eager loaded together.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    async def getResults(self) -> Any:  # noqa: ANN401
        """
        Execute the relationship query for its bound parent instance.

        Returns
        -------
        Any
            A single model, ``None``, or a :class:`Collection`,
            depending on the relationship kind.
        """

    @abstractmethod
    async def getEager(self) -> Collection:
        """
        Execute the relationship query assembled for eager loading.

        Returns
        -------
        Collection
            Every related row across the whole eager-loaded batch.
        """

    @abstractmethod
    def match(
        self,
        models: list[Model],
        results: Collection,
        name: str,
    ) -> None:
        """
        Group eager-loaded results and attach them to their parents.

        Parameters
        ----------
        models : list of Model
            Parent instances being eager loaded together.
        results : Collection
            Rows produced by :meth:`getEager`.
        name : str
            Relationship name the results are stored under.

        Returns
        -------
        None
            This method does not return a value.
        """
