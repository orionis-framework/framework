from __future__ import annotations
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Self
from orionis.orm.contracts.base_builder import IQueryBuilderBase

if TYPE_CHECKING:
    from orionis.orm.collections.paginator import Paginator
    from orionis.support.types.collection import Collection

class IRawQueryBuilder(IQueryBuilderBase):
    """
    Contract for the model-less query builder over a plain table name.

    It inherits the whole query language from :class:`IQueryBuilderBase`
    and only adds what is specific to running without a model: choosing
    the target table and connection, and returning plain dictionaries
    instead of hydrated instances.
    """

    # ruff: noqa: ANN401

    __slots__ = ()

    @abstractmethod
    def connection(self, name: str) -> Self:
        """
        Change the connection this builder runs against.

        Parameters
        ----------
        name : str
            Named connection to run the query against.

        Returns
        -------
        IRawQueryBuilder
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def table(self, name: str, *, alias: str | None = None) -> Self:
        """
        Change the table this builder queries against.

        Parameters
        ----------
        name : str
            Logical table name, without the connection prefix.
        alias : str or None, optional
            Alias the table is referred to by inside the query.

        Returns
        -------
        IRawQueryBuilder
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    async def get(self) -> Collection:
        """
        Execute the query and return every matching row.

        Returns
        -------
        Collection
            Collection of plain dictionaries, one per row.
        """

    @abstractmethod
    async def first(self) -> dict[str, Any] | None:
        """
        Execute the query and return only the first matching row.

        Returns
        -------
        dict or None
            First matching row, or ``None`` without matches.
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
        Any
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
        Collection
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
        Paginator
            Page of rows with pagination metadata.
        """
