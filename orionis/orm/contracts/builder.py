"""Contract for the query builder bound to a model class."""

from __future__ import annotations
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Self
from orionis.orm.contracts.base_builder import IQueryBuilderBase

if TYPE_CHECKING:
    from orionis.orm.collections.paginator import Paginator
    from orionis.orm.model import Model
    from orionis.support.types.collection import Collection

class IModelQueryBuilder(IQueryBuilderBase):
    """
    Contract for the query builder bound to a model class.

    It inherits the whole query language from
    :class:`orionis.orm.contracts.base_builder.IQueryBuilderBase`
    and only adds what model awareness brings: hydrated results,
    primary-key lookups, and relationship eager loading.
    """

    # ruff: noqa: ANN401

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    def withRelations(self, *names: str) -> Self:
        """
        Eager load the given relationships alongside the query.

        Parameters
        ----------
        *names : str
            Relationship method names declared on the model.

        Returns
        -------
        orionis.orm.contracts.IModelQueryBuilder
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def load(self, *names: str) -> Self:
        """
        Eager load the given relationships; alias of ``withRelations``.

        Parameters
        ----------
        *names : str
            Relationship method names declared on the model.

        Returns
        -------
        orionis.orm.contracts.IModelQueryBuilder
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    async def get(self) -> Collection:
        """
        Execute the query and hydrate every matching row.

        Returns
        -------
        collections.abc.Collection
            Collection of hydrated model instances.
        """

    @abstractmethod
    async def first(self) -> Model | None:
        """
        Execute the query and hydrate only the first matching row.

        Returns
        -------
        orionis.orm.Model or None
            First matching model, or ``None`` without matches.
        """

    @abstractmethod
    async def firstOrFail(self) -> Model:
        """
        Return the first matching row or raise when none exists.

        Returns
        -------
        orionis.orm.Model
            First matching model.

        Raises
        ------
        orionis.orm.exceptions.ModelNotFoundException
            If the query yields no rows.
        """

    @abstractmethod
    async def find(self, key: Any) -> Model | None:
        """
        Retrieve a model by its primary key.

        Parameters
        ----------
        key : typing.Any
            Primary key value to look up.

        Returns
        -------
        orionis.orm.Model or None
            Matching model, or ``None`` when absent.
        """

    @abstractmethod
    async def findOrFail(self, key: Any) -> Model:
        """
        Retrieve a model by primary key or raise when absent.

        Parameters
        ----------
        key : typing.Any
            Primary key value to look up.

        Returns
        -------
        orionis.orm.Model
            Matching model.

        Raises
        ------
        orionis.orm.exceptions.ModelNotFoundException
            If no record matches the key.
        """

    @abstractmethod
    async def value(self, column: str) -> Any:
        """
        Return a single column value of the first matching row.

        Parameters
        ----------
        column : str
            Column whose value is returned.

        Returns
        -------
        typing.Any
            Column value, or ``None`` without matches.
        """

    @abstractmethod
    async def pluck(self, column: str) -> Collection:
        """
        Return one column of every matching row.

        Parameters
        ----------
        column : str
            Column whose values are collected.

        Returns
        -------
        collections.abc.Collection
            Collection of column values.
        """

    @abstractmethod
    async def paginate(self, page: int = 1, per_page: int = 15) -> Paginator:
        """
        Execute the query returning a length-aware page of results.

        Parameters
        ----------
        page : int, optional
            Page number starting at 1. Defaults to the first page.
        per_page : int, optional
            Number of items per page. Defaults to 15.

        Returns
        -------
        orionis.orm.collections.Paginator
            Page of hydrated models with pagination metadata.
        """
