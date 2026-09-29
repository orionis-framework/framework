from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from collections.abc import Iterable
    from orionis.database.entities.result import InsertResult
    from orionis.orm.query.expressions import SelectPlan
    from orionis.orm.schema.table import TableDefinition

class IQueryBuilderBase(ABC):
    """
    Contract of the query language shared by every Orionis builder.

    It declares the fluent clause surface (projection, conditions,
    joins, grouping, ordering, paging, locking, unions) and the
    terminals whose result does not depend on how rows are represented.
    Model-bound and model-less builders both honor it, which is what
    guarantees ``DB.table(...)`` and ``Model.query()`` speak the same
    language.
    """

    # ruff: noqa: ANN401

    __slots__ = ()

    # ── Plan access ─────────────────────────────────────────────────────────

    @abstractmethod
    def toPlan(self) -> SelectPlan:
        """
        Return the engine-agnostic plan assembled so far.

        Returns
        -------
        SelectPlan
            Live plan owned by this builder.
        """

    @abstractmethod
    def clone(self) -> Self:
        """
        Return an independent copy of this builder.

        Returns
        -------
        IQueryBuilderBase
            Detached copy carrying its own plan.
        """

    # ── Projection ──────────────────────────────────────────────────────────

    @abstractmethod
    def select(self, *columns: str) -> Self:
        """
        Restrict the query projection to the given columns.

        Parameters
        ----------
        *columns : str
            Column names to project; empty selects every column.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def addSelect(self, *columns: str) -> Self:
        """
        Append columns to the current projection.

        Parameters
        ----------
        *columns : str
            Column names to add to the projection.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def selectRaw(
        self,
        sql: str,
        bindings: dict[str, Any] | None = None,
        alias: str | None = None,
    ) -> Self:
        """
        Append a raw SQL fragment to the projection.

        Parameters
        ----------
        sql : str
            SQL fragment using named ``:param`` placeholders.
        bindings : dict or None, optional
            Values bound to the placeholders of the fragment.
        alias : str or None, optional
            Name the fragment is projected under.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def selectSub(self, query: Any, alias: str) -> Self:
        """
        Append a scalar subquery to the projection under an alias.

        Parameters
        ----------
        query : Any
            Callable receiving a fresh builder, another builder, or a
            ready-made select plan.
        alias : str
            Name the projected value is exposed under.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def distinct(self) -> Self:
        """
        Collapse duplicate rows from the query results.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    # ── Where clauses ───────────────────────────────────────────────────────

    @abstractmethod
    def where(self, column: Any, *args: Any) -> Self:
        """
        Add an AND-combined filtering condition.

        Parameters
        ----------
        column : Any
            Column name, mapping of equality pairs, or a callable
            receiving a nested builder whose conditions are grouped in
            parentheses.
        *args : Any
            Either the bound value, or an operator followed by a value.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def orWhere(self, column: Any, *args: Any) -> Self:
        """
        Add an OR-combined filtering condition.

        Parameters
        ----------
        column : Any
            Column name, mapping of equality pairs, or grouping callable.
        *args : Any
            Either the bound value, or an operator followed by a value.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereIn(self, column: str, values: Any) -> Self:
        """
        Filter rows whose column value belongs to the given set.

        Parameters
        ----------
        column : str
            Column name to filter by.
        values : Any
            Accepted values, or a subquery producing them.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def orWhereIn(self, column: str, values: Any) -> Self:
        """
        Add an OR-combined set-membership condition.

        Parameters
        ----------
        column : str
            Column name to filter by.
        values : Any
            Accepted values, or a subquery producing them.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereNotIn(self, column: str, values: Any) -> Self:
        """
        Filter rows whose column value is outside the given set.

        Parameters
        ----------
        column : str
            Column name to filter by.
        values : Any
            Rejected values, or a subquery producing them.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def orWhereNotIn(self, column: str, values: Any) -> Self:
        """
        Add an OR-combined set-exclusion condition.

        Parameters
        ----------
        column : str
            Column name to filter by.
        values : Any
            Rejected values, or a subquery producing them.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereNull(self, column: str) -> Self:
        """
        Filter rows whose column value is ``NULL``.

        Parameters
        ----------
        column : str
            Column name to filter by.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def orWhereNull(self, column: str) -> Self:
        """
        Add an OR-combined ``IS NULL`` condition.

        Parameters
        ----------
        column : str
            Column name to filter by.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereNotNull(self, column: str) -> Self:
        """
        Filter rows whose column value is not ``NULL``.

        Parameters
        ----------
        column : str
            Column name to filter by.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def orWhereNotNull(self, column: str) -> Self:
        """
        Add an OR-combined ``IS NOT NULL`` condition.

        Parameters
        ----------
        column : str
            Column name to filter by.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereBetween(self, column: str, bounds: Iterable[Any]) -> Self:
        """
        Filter rows whose column value lies between two boundaries.

        Parameters
        ----------
        column : str
            Column name to filter by.
        bounds : Iterable
            Exactly two values: the lower and upper boundaries.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereNotBetween(self, column: str, bounds: Iterable[Any]) -> Self:
        """
        Filter rows whose column value lies outside two boundaries.

        Parameters
        ----------
        column : str
            Column name to filter by.
        bounds : Iterable
            Exactly two values: the lower and upper boundaries.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereLike(self, column: str, pattern: str) -> Self:
        """
        Filter rows whose column value matches an SQL LIKE pattern.

        Parameters
        ----------
        column : str
            Column name to filter by.
        pattern : str
            SQL LIKE pattern, using ``%`` and ``_`` wildcards.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereNotLike(self, column: str, pattern: str) -> Self:
        """
        Filter rows not matching an SQL LIKE pattern.

        Parameters
        ----------
        column : str
            Column name to filter by.
        pattern : str
            SQL LIKE pattern, using ``%`` and ``_`` wildcards.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereILike(self, column: str, pattern: str) -> Self:
        """
        Filter rows matching a case-insensitive SQL LIKE pattern.

        Parameters
        ----------
        column : str
            Column name to filter by.
        pattern : str
            SQL LIKE pattern, using ``%`` and ``_`` wildcards.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereNotILike(self, column: str, pattern: str) -> Self:
        """
        Filter rows not matching a case-insensitive LIKE pattern.

        Parameters
        ----------
        column : str
            Column name to filter by.
        pattern : str
            SQL LIKE pattern, using ``%`` and ``_`` wildcards.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereStartsWith(self, column: str, value: str) -> Self:
        """
        Filter rows whose column value starts with the given text.

        Parameters
        ----------
        column : str
            Column name to filter by.
        value : str
            Literal prefix to match.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereEndsWith(self, column: str, value: str) -> Self:
        """
        Filter rows whose column value ends with the given text.

        Parameters
        ----------
        column : str
            Column name to filter by.
        value : str
            Literal suffix to match.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereContains(self, column: str, value: str) -> Self:
        """
        Filter rows whose column value contains the given text.

        Parameters
        ----------
        column : str
            Column name to filter by.
        value : str
            Literal substring to match.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereRegexpMatch(self, column: str, pattern: str) -> Self:
        """
        Filter rows whose column value matches a regular expression.

        Parameters
        ----------
        column : str
            Column name to filter by.
        pattern : str
            Regular expression pattern.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereColumn(self, first: str, operator: str, second: str) -> Self:
        """
        Compare two columns of the query against each other.

        Parameters
        ----------
        first : str
            Left-hand column reference, optionally qualified.
        operator : str
            Comparison operator relating both sides.
        second : str
            Right-hand column reference, optionally qualified.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def orWhereColumn(self, first: str, operator: str, second: str) -> Self:
        """
        Add an OR-combined comparison between two columns.

        Parameters
        ----------
        first : str
            Left-hand column reference, optionally qualified.
        operator : str
            Comparison operator relating both sides.
        second : str
            Right-hand column reference, optionally qualified.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereRaw(
        self,
        sql: str,
        bindings: dict[str, Any] | None = None,
    ) -> Self:
        """
        Add an AND-combined raw SQL condition.

        Parameters
        ----------
        sql : str
            SQL fragment using named ``:param`` placeholders.
        bindings : dict or None, optional
            Values bound to the placeholders of the fragment.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def orWhereRaw(
        self,
        sql: str,
        bindings: dict[str, Any] | None = None,
    ) -> Self:
        """
        Add an OR-combined raw SQL condition.

        Parameters
        ----------
        sql : str
            SQL fragment using named ``:param`` placeholders.
        bindings : dict or None, optional
            Values bound to the placeholders of the fragment.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereExists(self, query: Any) -> Self:
        """
        Keep rows for which a correlated subquery returns any row.

        Parameters
        ----------
        query : Any
            Callable receiving a fresh builder, another builder, or a
            ready-made select plan.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def orWhereExists(self, query: Any) -> Self:
        """
        Add an OR-combined ``EXISTS`` condition.

        Parameters
        ----------
        query : Any
            Subquery source producing the correlated rows.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def whereNotExists(self, query: Any) -> Self:
        """
        Keep rows for which a correlated subquery returns no row.

        Parameters
        ----------
        query : Any
            Subquery source producing the correlated rows.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def orWhereNotExists(self, query: Any) -> Self:
        """
        Add an OR-combined ``NOT EXISTS`` condition.

        Parameters
        ----------
        query : Any
            Subquery source producing the correlated rows.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    # ── Joins ───────────────────────────────────────────────────────────────

    @abstractmethod
    def join(
        self,
        table: str | TableDefinition,
        first: Any = None,
        operator: str | None = None,
        second: str | None = None,
        *,
        alias: str | None = None,
    ) -> Self:
        """
        Add an INNER JOIN to the query.

        Parameters
        ----------
        table : str or TableDefinition
            Table name to join, or its full definition.
        first : Any, optional
            Left-hand column of the ON condition, or a callable
            receiving a join clause to declare several conditions.
        operator : str or None, optional
            Comparison operator relating both sides.
        second : str or None, optional
            Right-hand column of the ON condition.
        alias : str or None, optional
            Alias the joined table is referred to by.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def leftJoin(
        self,
        table: str | TableDefinition,
        first: Any = None,
        operator: str | None = None,
        second: str | None = None,
        *,
        alias: str | None = None,
    ) -> Self:
        """
        Add a LEFT OUTER JOIN to the query.

        Parameters
        ----------
        table : str or TableDefinition
            Table name to join, or its full definition.
        first : Any, optional
            Left-hand column of the ON condition, or a join callable.
        operator : str or None, optional
            Comparison operator relating both sides.
        second : str or None, optional
            Right-hand column of the ON condition.
        alias : str or None, optional
            Alias the joined table is referred to by.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def rightJoin(
        self,
        table: str | TableDefinition,
        first: Any = None,
        operator: str | None = None,
        second: str | None = None,
        *,
        alias: str | None = None,
    ) -> Self:
        """
        Add a RIGHT OUTER JOIN to the query.

        Parameters
        ----------
        table : str or TableDefinition
            Table name to join, or its full definition.
        first : Any, optional
            Left-hand column of the ON condition, or a join callable.
        operator : str or None, optional
            Comparison operator relating both sides.
        second : str or None, optional
            Right-hand column of the ON condition.
        alias : str or None, optional
            Alias the joined table is referred to by.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def fullJoin(
        self,
        table: str | TableDefinition,
        first: Any = None,
        operator: str | None = None,
        second: str | None = None,
        *,
        alias: str | None = None,
    ) -> Self:
        """
        Add a FULL OUTER JOIN to the query.

        Parameters
        ----------
        table : str or TableDefinition
            Table name to join, or its full definition.
        first : Any, optional
            Left-hand column of the ON condition, or a join callable.
        operator : str or None, optional
            Comparison operator relating both sides.
        second : str or None, optional
            Right-hand column of the ON condition.
        alias : str or None, optional
            Alias the joined table is referred to by.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def crossJoin(
        self,
        table: str | TableDefinition,
        *,
        alias: str | None = None,
    ) -> Self:
        """
        Add a CROSS JOIN to the query.

        Parameters
        ----------
        table : str or TableDefinition
            Table name to join, or its full definition.
        alias : str or None, optional
            Alias the joined table is referred to by.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def joinSub(
        self,
        query: Any,
        alias: str,
        first: Any = None,
        operator: str | None = None,
        second: str | None = None,
    ) -> Self:
        """
        Join a subquery as a derived table with an INNER JOIN.

        Parameters
        ----------
        query : Any
            Subquery source producing the derived table.
        alias : str
            Name the derived table is referred to by.
        first : Any, optional
            Left-hand column of the ON condition, or a join callable.
        operator : str or None, optional
            Comparison operator relating both sides.
        second : str or None, optional
            Right-hand column of the ON condition.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def leftJoinSub(
        self,
        query: Any,
        alias: str,
        first: Any = None,
        operator: str | None = None,
        second: str | None = None,
    ) -> Self:
        """
        Join a subquery as a derived table with a LEFT OUTER JOIN.

        Parameters
        ----------
        query : Any
            Subquery source producing the derived table.
        alias : str
            Name the derived table is referred to by.
        first : Any, optional
            Left-hand column of the ON condition, or a join callable.
        operator : str or None, optional
            Comparison operator relating both sides.
        second : str or None, optional
            Right-hand column of the ON condition.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def rightJoinSub(
        self,
        query: Any,
        alias: str,
        first: Any = None,
        operator: str | None = None,
        second: str | None = None,
    ) -> Self:
        """
        Join a subquery as a derived table with a RIGHT OUTER JOIN.

        Parameters
        ----------
        query : Any
            Subquery source producing the derived table.
        alias : str
            Name the derived table is referred to by.
        first : Any, optional
            Left-hand column of the ON condition, or a join callable.
        operator : str or None, optional
            Comparison operator relating both sides.
        second : str or None, optional
            Right-hand column of the ON condition.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    # ── Ordering, grouping, paging ──────────────────────────────────────────

    @abstractmethod
    def orderBy(self, column: str, direction: str = "asc") -> Self:
        """
        Add an ordering rule to the query.

        Parameters
        ----------
        column : str
            Column to sort by.
        direction : str, optional
            ``"asc"`` or ``"desc"``. Defaults to ascending.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def latest(self, column: str | None = None) -> Self:
        """
        Order the query by a timestamp column in descending order.

        Parameters
        ----------
        column : str or None, optional
            Column to sort by; defaults to the creation timestamp.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def oldest(self, column: str | None = None) -> Self:
        """
        Order the query by a timestamp column in ascending order.

        Parameters
        ----------
        column : str or None, optional
            Column to sort by; defaults to the creation timestamp.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def groupBy(self, *columns: str) -> Self:
        """
        Add grouping columns to the query.

        Parameters
        ----------
        *columns : str
            Columns to group by.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def having(self, column: Any, *args: Any) -> Self:
        """
        Add a post-grouping condition to the query.

        Parameters
        ----------
        column : Any
            Column name, mapping of equality pairs, or grouping callable.
        *args : Any
            Either the bound value, or an operator followed by a value.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def orHaving(self, column: Any, *args: Any) -> Self:
        """
        Add an OR-combined post-grouping condition to the query.

        Parameters
        ----------
        column : Any
            Column name, mapping of equality pairs, or grouping callable.
        *args : Any
            Either the bound value, or an operator followed by a value.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def havingRaw(
        self,
        sql: str,
        bindings: dict[str, Any] | None = None,
    ) -> Self:
        """
        Add a raw SQL post-grouping condition.

        Parameters
        ----------
        sql : str
            SQL fragment using named ``:param`` placeholders.
        bindings : dict or None, optional
            Values bound to the placeholders of the fragment.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def limit(self, value: int) -> Self:
        """
        Limit the number of rows returned by the query.

        Parameters
        ----------
        value : int
            Maximum number of rows, must not be negative.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def offset(self, value: int) -> Self:
        """
        Skip the given number of rows before returning results.

        Parameters
        ----------
        value : int
            Number of rows to skip, must not be negative.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def take(self, value: int) -> Self:
        """
        Limit the number of rows returned; alias of ``limit``.

        Parameters
        ----------
        value : int
            Maximum number of rows, must not be negative.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def skip(self, value: int) -> Self:
        """
        Skip the given number of rows; alias of ``offset``.

        Parameters
        ----------
        value : int
            Number of rows to skip, must not be negative.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def forPage(self, page: int, per_page: int = 15) -> Self:
        """
        Limit the query to a single page of results.

        Parameters
        ----------
        page : int
            Page number starting at 1.
        per_page : int, optional
            Number of items per page. Defaults to 15.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    # ── Locking and compounds ───────────────────────────────────────────────

    @abstractmethod
    def lockForUpdate(self) -> Self:
        """
        Lock the selected rows against concurrent writes.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def sharedLock(self) -> Self:
        """
        Lock the selected rows in shared mode.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def union(self, query: Any) -> Self:
        """
        Append another query's rows, collapsing duplicates.

        Parameters
        ----------
        query : Any
            Subquery source whose rows are appended.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    @abstractmethod
    def unionAll(self, query: Any) -> Self:
        """
        Append another query's rows, keeping duplicates.

        Parameters
        ----------
        query : Any
            Subquery source whose rows are appended.

        Returns
        -------
        IQueryBuilderBase
            The same builder, enabling fluent chaining.
        """

    # ── Aggregate terminals ─────────────────────────────────────────────────

    @abstractmethod
    async def count(self, column: str = "*") -> int:
        """
        Count the rows matched by the query.

        Parameters
        ----------
        column : str, optional
            Column to count; ``"*"`` counts every matching row.

        Returns
        -------
        int
            Number of matching rows.
        """

    @abstractmethod
    async def exists(self) -> bool:
        """
        Report whether the query matches at least one row.

        Returns
        -------
        bool
            ``True`` when a matching row exists.
        """

    @abstractmethod
    async def doesntExist(self) -> bool:
        """
        Report whether the query matches no rows.

        Returns
        -------
        bool
            ``True`` when no matching row exists.
        """

    @abstractmethod
    async def max(self, column: str) -> Any:
        """
        Return the maximum value of a column among matching rows.

        Parameters
        ----------
        column : str
            Column to aggregate.

        Returns
        -------
        Any
            Maximum value, or ``None`` without matches.
        """

    @abstractmethod
    async def min(self, column: str) -> Any:
        """
        Return the minimum value of a column among matching rows.

        Parameters
        ----------
        column : str
            Column to aggregate.

        Returns
        -------
        Any
            Minimum value, or ``None`` without matches.
        """

    @abstractmethod
    async def avg(self, column: str) -> float | None:
        """
        Return the average value of a column among matching rows.

        Parameters
        ----------
        column : str
            Column to aggregate.

        Returns
        -------
        float or None
            Average value, or ``None`` without matches.
        """

    @abstractmethod
    async def sum(self, column: str) -> Any:
        """
        Return the sum of a column among matching rows.

        Parameters
        ----------
        column : str
            Column to aggregate.

        Returns
        -------
        Any
            Sum of the values, or ``0`` without matches.
        """

    # ── Mutation terminals ──────────────────────────────────────────────────

    @abstractmethod
    async def insert(
        self,
        values: dict[str, Any] | list[dict[str, Any]],
    ) -> InsertResult:
        """
        Insert one or many rows into the target table.

        Parameters
        ----------
        values : dict or list of dict
            Column values for one row, or a list of rows.

        Returns
        -------
        InsertResult
            Result carrying the generated key and affected row count.
        """

    @abstractmethod
    async def update(self, values: dict[str, Any]) -> int:
        """
        Mass update the rows matched by the query.

        Parameters
        ----------
        values : dict
            Column values to assign.

        Returns
        -------
        int
            Number of affected rows.
        """

    @abstractmethod
    async def delete(self) -> int:
        """
        Delete the rows matched by the query.

        Returns
        -------
        int
            Number of affected rows.
        """
