from __future__ import annotations
from typing import TYPE_CHECKING, Any, Self
from orionis.orm.contracts.raw_builder import IRawQueryBuilder
from orionis.orm.exceptions import InvalidQueryException
from orionis.orm.query.base_builder import QueryBuilderBase
from orionis.orm.resolver import ConnectionResolver
from orionis.support.types.collection import Collection

if TYPE_CHECKING:
    from orionis.database.contracts.connection import IConnection
    from orionis.orm.collections.paginator import Paginator

# Default page size used by pagination.
_DEFAULT_PER_PAGE: int = 15

class RawQueryBuilder(QueryBuilderBase, IRawQueryBuilder):
    """
    Fluent query builder over a plain table name.

    Unlike :class:`orionis.orm.query.builder.ModelQueryBuilder`, it is
    not bound to a :class:`Model`: rows are returned as plain
    dictionaries and the target table carries no declared schema, so the
    SQL compiler declares each referenced column lazily. Built by
    :meth:`orionis.orm.db.DB.table`.

    Every clause method comes from :class:`QueryBuilderBase`, the same
    engine model queries run on, so both entry points speak exactly the
    same query language and compile through the same pipeline.
    """

    __slots__ = ()

    # ── Target selection ────────────────────────────────────────────────────

    def connection(self, name: str) -> Self:
        """
        Change the connection this builder runs against.

        Parameters
        ----------
        name : str
            Named connection to run the query against.

        Returns
        -------
        RawQueryBuilder
            The same builder, enabling fluent chaining.
        """
        return self.adoptConnection(name)

    def table(self, name: str, *, alias: str | None = None) -> Self:
        """
        Change the table this builder queries against.

        Only the target is replaced; clauses declared beforehand are
        preserved, so the call order never silently drops conditions.

        Parameters
        ----------
        name : str
            Logical table name, without the connection prefix.
        alias : str or None, optional
            Alias the table is referred to by inside the query.

        Returns
        -------
        RawQueryBuilder
            The same builder, enabling fluent chaining.
        """
        self._plan.table = self._resolveJoinTable(name)
        self._plan.alias = alias
        return self

    # ── Retrieval terminals ─────────────────────────────────────────────────

    async def get(self) -> Collection:
        """
        Execute the query and return every matching row.

        Returns
        -------
        Collection
            Collection of plain dictionaries, one per row.

        Raises
        ------
        InvalidQueryException
            If no table was selected.
        QueryException
            If the statement fails to compile or execute.
        """
        self._assertTarget()
        self._beforeExecute()
        rows = await self._connection().select(self._plan)
        return Collection(rows)

    async def first(self) -> dict[str, Any] | None:
        """
        Execute the query and return only the first matching row.

        Returns
        -------
        dict or None
            First matching row, or ``None`` without matches.

        Raises
        ------
        InvalidQueryException
            If no table was selected.
        QueryException
            If the statement fails to compile or execute.
        """
        self._assertTarget()
        self._beforeExecute()
        probe = self._plan.clone()
        probe.limit_value = 1
        rows = await self._connection().select(probe)
        return rows[0] if rows else None

    async def value(self, column: str) -> Any:  # noqa: ANN401
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
        row = await self.clone().select(column).first()
        key = column.rsplit(".", 1)[-1]
        return row.get(key) if row else None

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
        rows = await self.clone().select(column).get()
        key = column.rsplit(".", 1)[-1]
        return Collection([row[key] for row in rows])

    async def paginate(
        self,
        page: int = 1,
        per_page: int = _DEFAULT_PER_PAGE,
    ) -> Paginator:
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

        Raises
        ------
        InvalidQueryException
            If the page or page size are not positive integers.
        """
        self.forPage(page, per_page)
        total = await self.count()
        items = await self.get()
        return self._paginator(items, total, page, per_page)

    # ── Internal helpers ────────────────────────────────────────────────────

    def _connection(self) -> IConnection:
        """
        Resolve the database connection this builder runs against.

        Returns
        -------
        IConnection
            Named connection, or the default one.
        """
        return ConnectionResolver.connection(self._connection_name)

    def _assertTarget(self) -> None:
        """
        Ensure a table was selected before executing the query.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        InvalidQueryException
            If the builder has no target table.
        """
        if not self._plan.table.name:
            error_msg = "No table selected; call table() before running the query."
            raise InvalidQueryException(error_msg)
