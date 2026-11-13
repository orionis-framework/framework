# ruff: noqa: ANN401, TC001
# Declare heterogeneous relation results and runtime-resolvable model types.
"""Contract for a query builder bound to a parent model instance."""

import orionis.orm as _orm
from abc import abstractmethod
from typing import Any
from orionis.orm.contracts.builder import IModelQueryBuilder

from orionis.support.types.collection import Collection


class IRelation(IModelQueryBuilder):
    """
    Contract for a query builder bound to a parent model instance.

    Every relationship kind (``hasOne``, ``hasMany``, ``belongsTo``,
    ``belongsToMany``, and future ones such as polymorphic or
    through-relations) implements this template so eager loading can
    drive any of them without knowing its concrete type.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    def addConstraints(self) -> None:
        """
        Constrain the query to the bound parent instance.

        Applied once during construction, unless constraints are
        suspended for eager loading.

        Returns
        -------
        None
            No return value.
        """

    @abstractmethod
    def addEagerConstraints(self, models: list[_orm.Model]) -> None:
        """
        Constrain the query to every parent instance of an eager batch.

        Parameters
        ----------
        models : list of orionis.orm.Model
            Parent instances being eager loaded together.

        Returns
        -------
        None
            No return value.
        """

    @abstractmethod
    async def getResults(self) -> Any:
        """
        Execute the relationship query for its bound parent instance.

        Returns
        -------
        typing.Any
            A single model, ``None``, or an Orionis
            :class:`orionis.support.types.Collection`,
            depending on the relationship kind.
        """

    @abstractmethod
    async def getEager(self) -> Collection:
        """
        Execute the relationship query assembled for eager loading.

        Returns
        -------
        orionis.support.types.Collection
            Every related row across the whole eager-loaded batch.
        """

    @abstractmethod
    def match(
        self,
        models: list[_orm.Model],
        results: Collection,
        name: str,
    ) -> None:
        """
        Group eager-loaded results and attach them to their parents.

        Parameters
        ----------
        models : list of orionis.orm.Model
            Parent instances being eager loaded together.
        results : orionis.support.types.Collection
            Rows produced by :meth:`orionis.orm.contracts.relation.IRelation.getEager`.
        name : str
            Relationship name the results are stored under.

        Returns
        -------
        None
            No return value.
        """
