from __future__ import annotations
import copy
from typing import TYPE_CHECKING, Any, Self
from orionis.orm.collections.paginator import Paginator
from orionis.orm.exceptions import InvalidQueryException
from orionis.orm.query.expressions import (
    SUPPORTED_OPERATORS,
    AggregateClause,
    AggregateFunction,
    DeletePlan,
    InsertPlan,
    JoinCondition,
    JoinExpression,
    JoinType,
    LockMode,
    OrderClause,
    RawExpression,
    SelectPlan,
    SortDirection,
    SubQueryColumn,
    UnionClause,
    UpdatePlan,
    WhereClause,
    WhereType,
)
from orionis.orm.query.join_clause import JoinClause
from orionis.orm.schema.table import TableDefinition
from orionis.support.types.collection import Collection

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from orionis.database.contracts.connection import IConnection
    from orionis.database.entities.result import InsertResult

# Number of arguments in the (operator, value) where form.
_WHERE_WITH_OPERATOR: int = 2

# Number of values required by a BETWEEN boundary pair.
_BETWEEN_BOUNDS: int = 2

# Default page size used by pagination.
_DEFAULT_PER_PAGE: int = 15

# Column name assumed by latest()/oldest() without a declared timestamp.
_DEFAULT_TIMESTAMP_COLUMN: str = "created_at"


class QueryBuilderBase:
    """
    Engine shared by every Orionis query builder.

    It owns the mutable :class:`SelectPlan` and the whole fluent clause
    surface (projection, conditions, joins, grouping, ordering, paging,
    locking, unions) plus the terminals that do not depend on how rows
    are represented. Model-bound and model-less builders both derive
    from it, so ``DB.table(...)`` and ``Model.query()`` share one single
    implementation of the query language and one single SQL pipeline.

    Subclasses only provide how the query reaches the database
    (:meth:`_connection`), how rows are represented (``get``/``first``),
    and how values are serialized before being written.
    """

    # ruff: noqa: ANN401

    __slots__ = ("_connection_name", "_plan")

    def __init__(self, table: TableDefinition | None = None) -> None:
        """
        Initialize the builder with a plan for the supplied table.

        Parameters
        ----------
        table : TableDefinition or None, optional
            Query target, or an empty definition until a table is selected.

        Returns
        -------
        None
            This method does not return a value.
        """
        self._connection_name: str | None = None
        self._plan = SelectPlan(
            table=table if table is not None else TableDefinition(name=""),
        )

    # ── Plan access ─────────────────────────────────────────────────────────

    def toPlan(self) -> SelectPlan:
        """
        Return the engine-agnostic plan assembled so far.

        The plan is the only contract between the fluent API and the SQL
        compiler; exposing it lets a builder be embedded as a subquery
        of another one.

        Returns
        -------
        SelectPlan
            Live plan owned by this builder.
        """
        return self._plan

    def clone(self) -> Self:
        """
        Return an independent copy of this builder.

        The copy carries a detached plan, so refining it never mutates
        the query it was branched from.

        Returns
        -------
        QueryBuilderBase
            Detached copy sharing the same target and connection.
        """
        duplicate = self._shallowCopy()
        duplicate.adoptPlan(self._plan.clone())
        return duplicate

    def adoptPlan(self, plan: SelectPlan) -> Self:
        """
        Replace the plan this builder assembles.

        Parameters
        ----------
        plan : SelectPlan
            Plan the builder continues refining.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        self._plan = plan
        return self

    def _shallowCopy(self) -> Self:
        """
        Build a twin of this builder still sharing its plan.

        Returns
        -------
        QueryBuilderBase
            Instance of the same class carrying the same bound state,
            including the slots declared by subclasses.
        """
        return copy.copy(self)

    def adoptConnection(self, name: str | None) -> Self:
        """
        Bind the builder to a named connection.

        Parameters
        ----------
        name : str or None
            Named connection, or ``None`` for the default one.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        self._connection_name = name
        return self

    # ── Subclass hooks ──────────────────────────────────────────────────────

    def _connection(self) -> IConnection:
        """
        Resolve the database connection this builder runs against.

        Returns
        -------
        IConnection
            Connection used to execute the compiled statements.

        Raises
        ------
        NotImplementedError
            If the concrete builder does not resolve a connection.
        """
        error_msg = f"{type(self).__name__} must implement _connection()."
        raise NotImplementedError(error_msg)

    def _newQuery(self) -> QueryBuilderBase:
        """
        Create a sibling builder used for nested groups and subqueries.

        Returns
        -------
        QueryBuilderBase
            Fresh builder targeting the same table and connection.
        """
        # Imported here because the model-less builder derives from this
        # class, so importing it at module level would cycle.
        from orionis.orm.query.raw_builder import RawQueryBuilder  # noqa: PLC0415

        builder = RawQueryBuilder(self._plan.table)
        builder.adoptConnection(self._connection_name)
        builder.toPlan().alias = self._plan.alias
        return builder

    def _serializeValues(self, values: dict[str, Any]) -> dict[str, Any]:
        """
        Prepare a value mapping for storage.

        Parameters
        ----------
        values : dict
            Column values to write.

        Returns
        -------
        dict
            Values ready to be bound by the driver.
        """
        return values

    def _prepareUpdate(self, values: dict[str, Any]) -> dict[str, Any]:
        """
        Adjust an update payload before it is serialized.

        Parameters
        ----------
        values : dict
            Column values to assign.

        Returns
        -------
        dict
            Possibly augmented payload.
        """
        return values

    def _existsColumns(self) -> tuple[str, ...]:
        """
        Return the projection used by existence probes.

        Returns
        -------
        tuple of str
            Column names to project, empty to keep the whole row.
        """
        return ()

    def _defaultTimestampColumn(self) -> str:
        """
        Return the column :meth:`latest` and :meth:`oldest` default to.

        Returns
        -------
        str
            Timestamp column name.
        """
        return _DEFAULT_TIMESTAMP_COLUMN

    def _beforeExecute(self) -> None:
        """
        Finalize the plan right before a terminal runs it.

        Every terminal calls this hook, which is where model-aware
        builders inject the constraints that must apply to the query no
        matter how it was assembled, such as global scopes.

        Returns
        -------
        None
            This method does not return a value.
        """

    # ── Projection ──────────────────────────────────────────────────────────

    def select(self, *columns: str) -> Self:
        """
        Restrict the query projection to the given columns.

        Parameters
        ----------
        *columns : str
            Column names to project; empty selects every column.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        self._plan.columns = columns
        return self

    def addSelect(self, *columns: str) -> Self:
        """
        Append columns to the current projection.

        Parameters
        ----------
        *columns : str
            Column names to add to the projection.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        self._plan.columns = (*self._plan.columns, *columns)
        return self

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
            Name the fragment is projected under; required for the value
            to be addressable when the query is joined as a derived
            table.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        expression = RawExpression(
            sql=sql, bindings=bindings.copy() if bindings else {}, alias=alias,
        )
        self._plan.columns = (*self._plan.columns, expression)
        return self

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        column = SubQueryColumn(plan=self._resolvePlan(query), alias=alias)
        self._plan.columns = (*self._plan.columns, column)
        return self

    def distinct(self) -> Self:
        """
        Collapse duplicate rows from the query results.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        self._plan.distinct = True
        return self

    # ── Where clauses ───────────────────────────────────────────────────────

    def where(self, column: Any, *args: Any) -> Self:
        """
        Add an AND-combined filtering condition.

        Accepts ``where("col", value)``, ``where("col", op, value)``, a
        mapping of equality conditions, or a callable receiving a nested
        builder whose conditions are grouped in parentheses.

        Parameters
        ----------
        column : Any
            Column name, mapping of equality pairs, or grouping callable.
        *args : Any
            Either the bound value, or an operator followed by a value.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the arguments do not match a supported form.
        """
        self._addWhere(self._plan.wheres, column, args, boolean="and")
        return self

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the arguments do not match a supported form.
        """
        self._addWhere(self._plan.wheres, column, args, boolean="or")
        return self

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addMembership(column, values, WhereType.IN, "and")

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addMembership(column, values, WhereType.IN, "or")

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addMembership(column, values, WhereType.NOT_IN, "and")

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addMembership(column, values, WhereType.NOT_IN, "or")

    def whereNull(self, column: str) -> Self:
        """
        Filter rows whose column value is ``NULL``.

        Parameters
        ----------
        column : str
            Column name to filter by.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addTyped(column, WhereType.NULL, None, "and")

    def orWhereNull(self, column: str) -> Self:
        """
        Add an OR-combined ``IS NULL`` condition.

        Parameters
        ----------
        column : str
            Column name to filter by.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addTyped(column, WhereType.NULL, None, "or")

    def whereNotNull(self, column: str) -> Self:
        """
        Filter rows whose column value is not ``NULL``.

        Parameters
        ----------
        column : str
            Column name to filter by.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addTyped(column, WhereType.NOT_NULL, None, "and")

    def orWhereNotNull(self, column: str) -> Self:
        """
        Add an OR-combined ``IS NOT NULL`` condition.

        Parameters
        ----------
        column : str
            Column name to filter by.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addTyped(column, WhereType.NOT_NULL, None, "or")

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the boundaries are not exactly two values.
        """
        return self._addTyped(
            column, WhereType.BETWEEN, self._boundaryPair(bounds), "and",
        )

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the boundaries are not exactly two values.
        """
        return self._addTyped(
            column, WhereType.NOT_BETWEEN, self._boundaryPair(bounds), "and",
        )

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addTyped(column, WhereType.LIKE, pattern, "and")

    def whereNotLike(self, column: str, pattern: str) -> Self:
        """
        Filter rows whose column value does not match an SQL LIKE pattern.

        Parameters
        ----------
        column : str
            Column name to filter by.
        pattern : str
            SQL LIKE pattern, using ``%`` and ``_`` wildcards.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addTyped(column, WhereType.NOT_LIKE, pattern, "and")

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addTyped(column, WhereType.ILIKE, pattern, "and")

    def whereNotILike(self, column: str, pattern: str) -> Self:
        """
        Filter rows not matching a case-insensitive SQL LIKE pattern.

        Parameters
        ----------
        column : str
            Column name to filter by.
        pattern : str
            SQL LIKE pattern, using ``%`` and ``_`` wildcards.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addTyped(column, WhereType.NOT_ILIKE, pattern, "and")

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addTyped(column, WhereType.STARTS_WITH, value, "and")

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addTyped(column, WhereType.ENDS_WITH, value, "and")

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addTyped(column, WhereType.CONTAINS, value, "and")

    def whereRegexpMatch(self, column: str, pattern: str) -> Self:
        """
        Filter rows whose column value matches a regular expression.

        The exact regular expression dialect depends on the underlying
        database engine.

        Parameters
        ----------
        column : str
            Column name to filter by.
        pattern : str
            Regular expression pattern.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addTyped(column, WhereType.REGEXP, pattern, "and")

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the operator is not supported.
        """
        return self._addColumnComparison(first, operator, second, "and")

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the operator is not supported.
        """
        return self._addColumnComparison(first, operator, second, "or")

    def whereRaw(
        self,
        sql: str,
        bindings: dict[str, Any] | None = None,
    ) -> Self:
        """
        Add an AND-combined raw SQL condition.

        Values must be supplied through ``bindings`` so the driver binds
        and escapes them; interpolating them into ``sql`` would open the
        query to injection.

        Parameters
        ----------
        sql : str
            SQL fragment using named ``:param`` placeholders.
        bindings : dict or None, optional
            Values bound to the placeholders of the fragment.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addRaw(self._plan.wheres, sql, bindings, "and")

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addRaw(self._plan.wheres, sql, bindings, "or")

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addExists(query, WhereType.EXISTS, "and")

    def orWhereExists(self, query: Any) -> Self:
        """
        Add an OR-combined ``EXISTS`` condition.

        Parameters
        ----------
        query : Any
            Callable receiving a fresh builder, another builder, or a
            ready-made select plan.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addExists(query, WhereType.EXISTS, "or")

    def whereNotExists(self, query: Any) -> Self:
        """
        Keep rows for which a correlated subquery returns no row.

        Parameters
        ----------
        query : Any
            Callable receiving a fresh builder, another builder, or a
            ready-made select plan.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addExists(query, WhereType.NOT_EXISTS, "and")

    def orWhereNotExists(self, query: Any) -> Self:
        """
        Add an OR-combined ``NOT EXISTS`` condition.

        Parameters
        ----------
        query : Any
            Callable receiving a fresh builder, another builder, or a
            ready-made select plan.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addExists(query, WhereType.NOT_EXISTS, "or")

    # ── Joins ───────────────────────────────────────────────────────────────

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
            Table name to join, or its full definition when it declares
            a real schema (for instance ``Model.__meta__.table``).
        first : Any, optional
            Left-hand column of the ON condition, or a callable
            receiving a :class:`JoinClause` to declare several ones.
        operator : str or None, optional
            Comparison operator relating both sides.
        second : str or None, optional
            Right-hand column of the ON condition.
        alias : str or None, optional
            Alias the joined table is referred to by inside the query.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the ON condition is incomplete.
        """
        return self._addJoin(
            JoinType.INNER, table, (first, operator, second), alias,
        )

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
            Left-hand column of the ON condition, or a callable
            receiving a :class:`JoinClause`.
        operator : str or None, optional
            Comparison operator relating both sides.
        second : str or None, optional
            Right-hand column of the ON condition.
        alias : str or None, optional
            Alias the joined table is referred to by inside the query.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the ON condition is incomplete.
        """
        return self._addJoin(
            JoinType.LEFT, table, (first, operator, second), alias,
        )

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
            Left-hand column of the ON condition, or a callable
            receiving a :class:`JoinClause`.
        operator : str or None, optional
            Comparison operator relating both sides.
        second : str or None, optional
            Right-hand column of the ON condition.
        alias : str or None, optional
            Alias the joined table is referred to by inside the query.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the ON condition is incomplete.
        """
        return self._addJoin(
            JoinType.RIGHT, table, (first, operator, second), alias,
        )

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
            Left-hand column of the ON condition, or a callable
            receiving a :class:`JoinClause`.
        operator : str or None, optional
            Comparison operator relating both sides.
        second : str or None, optional
            Right-hand column of the ON condition.
        alias : str or None, optional
            Alias the joined table is referred to by inside the query.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the ON condition is incomplete.
        """
        return self._addJoin(
            JoinType.FULL, table, (first, operator, second), alias,
        )

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
            Alias the joined table is referred to by inside the query.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        self._plan.joins.append(
            JoinExpression(
                join_type=JoinType.CROSS,
                table=self._resolveJoinTable(table),
                alias=alias,
            ),
        )
        return self

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
            Callable receiving a fresh builder, another builder, or a
            ready-made select plan.
        alias : str
            Name the derived table is referred to by.
        first : Any, optional
            Left-hand column of the ON condition, or a callable
            receiving a :class:`JoinClause`.
        operator : str or None, optional
            Comparison operator relating both sides.
        second : str or None, optional
            Right-hand column of the ON condition.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the ON condition is incomplete.
        """
        return self._addJoin(
            JoinType.INNER, self._resolvePlan(query), (first, operator, second),
            alias,
        )

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
            Callable receiving a fresh builder, another builder, or a
            ready-made select plan.
        alias : str
            Name the derived table is referred to by.
        first : Any, optional
            Left-hand column of the ON condition, or a callable
            receiving a :class:`JoinClause`.
        operator : str or None, optional
            Comparison operator relating both sides.
        second : str or None, optional
            Right-hand column of the ON condition.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the ON condition is incomplete.
        """
        return self._addJoin(
            JoinType.LEFT, self._resolvePlan(query), (first, operator, second),
            alias,
        )

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
            Callable receiving a fresh builder, another builder, or a
            ready-made select plan.
        alias : str
            Name the derived table is referred to by.
        first : Any, optional
            Left-hand column of the ON condition, or a callable
            receiving a :class:`JoinClause`.
        operator : str or None, optional
            Comparison operator relating both sides.
        second : str or None, optional
            Right-hand column of the ON condition.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the ON condition is incomplete.
        """
        return self._addJoin(
            JoinType.RIGHT, self._resolvePlan(query), (first, operator, second),
            alias,
        )

    # ── Ordering, grouping, paging ──────────────────────────────────────────

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the direction is not ``"asc"`` or ``"desc"``.
        """
        normalized = str(direction).strip().lower()
        try:
            resolved = SortDirection(normalized)
        except ValueError as exc:
            error_msg = f"Invalid sort direction '{direction}'; use 'asc' or 'desc'."
            raise InvalidQueryException(error_msg) from exc
        self._plan.orders.append(OrderClause(column=column, direction=resolved))
        return self

    def latest(self, column: str | None = None) -> Self:
        """
        Order the query by a timestamp column in descending order.

        Parameters
        ----------
        column : str or None, optional
            Column to sort by; defaults to the creation timestamp.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self.orderBy(column or self._defaultTimestampColumn(), "desc")

    def oldest(self, column: str | None = None) -> Self:
        """
        Order the query by a timestamp column in ascending order.

        Parameters
        ----------
        column : str or None, optional
            Column to sort by; defaults to the creation timestamp.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self.orderBy(column or self._defaultTimestampColumn(), "asc")

    def groupBy(self, *columns: str) -> Self:
        """
        Add grouping columns to the query.

        Parameters
        ----------
        *columns : str
            Columns to group by.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        self._plan.groups.extend(columns)
        return self

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the arguments do not match a supported form.
        """
        self._addWhere(self._plan.havings, column, args, boolean="and")
        return self

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the arguments do not match a supported form.
        """
        self._addWhere(self._plan.havings, column, args, boolean="or")
        return self

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
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self._addRaw(self._plan.havings, sql, bindings, "and")

    def limit(self, value: int) -> Self:
        """
        Limit the number of rows returned by the query.

        Parameters
        ----------
        value : int
            Maximum number of rows, must not be negative.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the value is negative.
        """
        if value < 0:
            error_msg = "Limit must not be negative."
            raise InvalidQueryException(error_msg)
        self._plan.limit_value = value
        return self

    def offset(self, value: int) -> Self:
        """
        Skip the given number of rows before returning results.

        Parameters
        ----------
        value : int
            Number of rows to skip, must not be negative.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the value is negative.
        """
        if value < 0:
            error_msg = "Offset must not be negative."
            raise InvalidQueryException(error_msg)
        self._plan.offset_value = value
        return self

    def take(self, value: int) -> Self:
        """
        Limit the number of rows returned; alias of :meth:`limit`.

        Parameters
        ----------
        value : int
            Maximum number of rows, must not be negative.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self.limit(value)

    def skip(self, value: int) -> Self:
        """
        Skip the given number of rows; alias of :meth:`offset`.

        Parameters
        ----------
        value : int
            Number of rows to skip, must not be negative.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        return self.offset(value)

    def forPage(self, page: int, per_page: int = _DEFAULT_PER_PAGE) -> Self:
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
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the page or page size are not positive integers.
        """
        if (
            not isinstance(page, int) or isinstance(page, bool) or page < 1
            or not isinstance(per_page, int)
            or isinstance(per_page, bool) or per_page < 1
        ):
            error_msg = "Page and per_page must be positive integers."
            raise InvalidQueryException(error_msg)
        self._plan.limit_value = per_page
        self._plan.offset_value = (page - 1) * per_page
        return self

    # ── Locking and compounds ───────────────────────────────────────────────

    def lockForUpdate(self) -> Self:
        """
        Lock the selected rows against concurrent writes.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        self._plan.lock = LockMode.UPDATE
        return self

    def sharedLock(self) -> Self:
        """
        Lock the selected rows in shared mode.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        self._plan.lock = LockMode.SHARE
        return self

    def union(self, query: Any) -> Self:
        """
        Append another query's rows, collapsing duplicates.

        Parameters
        ----------
        query : Any
            Callable receiving a fresh builder, another builder, or a
            ready-made select plan.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        self._plan.unions.append(UnionClause(plan=self._resolvePlan(query)))
        return self

    def unionAll(self, query: Any) -> Self:
        """
        Append another query's rows, keeping duplicates.

        Parameters
        ----------
        query : Any
            Callable receiving a fresh builder, another builder, or a
            ready-made select plan.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        self._plan.unions.append(
            UnionClause(plan=self._resolvePlan(query), all_rows=True),
        )
        return self

    # ── Aggregate terminals ─────────────────────────────────────────────────

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
        return int(await self._aggregate(AggregateFunction.COUNT, column) or 0)

    async def exists(self) -> bool:
        """
        Report whether the query matches at least one row.

        Returns
        -------
        bool
            ``True`` when a matching row exists.
        """
        self._beforeExecute()
        probe = self._plan.clone()
        probe.columns = self._existsColumns()
        probe.orders = []
        probe.limit_value = 1
        probe.offset_value = None
        rows = await self._connection().select(probe)
        return bool(rows)
    async def doesntExist(self) -> bool:
        """
        Report whether the query matches no rows.

        Returns
        -------
        bool
            ``True`` when no matching row exists.
        """
        return not await self.exists()

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
        return await self._aggregate(AggregateFunction.MAX, column)

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
        return await self._aggregate(AggregateFunction.MIN, column)

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
        value = await self._aggregate(AggregateFunction.AVG, column)
        return float(value) if value is not None else None

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
        value = await self._aggregate(AggregateFunction.SUM, column)
        return value if value is not None else 0

    # ── Mutation terminals ──────────────────────────────────────────────────

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

        Raises
        ------
        InvalidQueryException
            If no values are provided.
        """
        rows = values if isinstance(values, list) else [values]
        if not rows:
            error_msg = "Cannot insert without values."
            raise InvalidQueryException(error_msg)
        plan = InsertPlan(
            table=self._plan.table,
            values=[self._serializeValues(row) for row in rows],
        )
        return await self._connection().insert(plan)

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

        Raises
        ------
        InvalidQueryException
            If no values are provided.
        """
        if not values:
            error_msg = "Cannot update without values."
            raise InvalidQueryException(error_msg)
        self._beforeExecute()
        payload = self._prepareUpdate(dict(values))
        plan = UpdatePlan(
            table=self._plan.table,
            values=self._serializeValues(payload),
            wheres=list(self._plan.wheres),
        )
        return await self._connection().update(plan)

    async def delete(self) -> int:
        """
        Delete the rows matched by the query.

        Returns
        -------
        int
            Number of affected rows.
        """
        self._beforeExecute()
        plan = DeletePlan(
            table=self._plan.table,
            wheres=list(self._plan.wheres),
        )
        return await self._connection().delete(plan)

    # ── Internal helpers ────────────────────────────────────────────────────

    def _paginator(
        self,
        items: Collection,
        total: int,
        page: int,
        size: int,
    ) -> Paginator:
        """
        Wrap a page of results together with its pagination metadata.

        Parameters
        ----------
        items : Collection
            Rows of the requested page.
        total : int
            Total number of rows matched by the query.
        page : int
            Page number starting at 1.
        size : int
            Number of items per page.

        Returns
        -------
        Paginator
            Length-aware page of results.
        """
        return Paginator(items=items, total=total, page=page, per_page=size)

    async def _aggregate(
        self,
        function: AggregateFunction,
        column: str,
    ) -> Any:
        """
        Execute an aggregate projection over the current plan.

        Parameters
        ----------
        function : AggregateFunction
            Aggregate function to apply.
        column : str
            Target column, or ``"*"`` for ``COUNT``.

        Returns
        -------
        Any
            Aggregate scalar value.
        """
        self._beforeExecute()
        probe = self._plan.clone()
        probe.aggregate = AggregateClause(function=function, column=column)
        probe.orders = []
        probe.limit_value = None
        probe.offset_value = None
        return await self._connection().scalar(probe)

    def _resolvePlan(self, query: Any) -> SelectPlan:
        """
        Normalize a subquery argument into a select plan.

        Parameters
        ----------
        query : Any
            Callable receiving a fresh builder, another builder exposing
            ``toPlan()``, or a ready-made select plan.

        Returns
        -------
        SelectPlan
            Plan describing the subquery.

        Raises
        ------
        InvalidQueryException
            If the argument is not a supported subquery source.
        """
        if isinstance(query, SelectPlan):
            return query
        if callable(query):
            builder = self._newQuery()
            query(builder)
            return builder.toPlan()
        to_plan = getattr(query, "toPlan", None)
        if callable(to_plan):
            return to_plan()
        error_msg = (
            "A subquery must be a callable, a query builder, or a select plan."
        )
        raise InvalidQueryException(error_msg)

    @staticmethod
    def _resolveJoinTable(table: str | TableDefinition) -> TableDefinition:
        """
        Normalize a join target into a :class:`TableDefinition`.

        Parameters
        ----------
        table : str or TableDefinition
            Table name to join, or its full definition.

        Returns
        -------
        TableDefinition
            A schemaless definition for a bare name, or ``table`` as is.
        """
        if isinstance(table, str):
            return TableDefinition(name=table)
        return table

    def _addJoin(
        self,
        join_type: JoinType,
        table: str | TableDefinition | SelectPlan,
        on: tuple[Any, str | None, str | None],
        alias: str | None,
    ) -> Self:
        """
        Append a join expression built from either calling convention.

        Parameters
        ----------
        join_type : JoinType
            Kind of join to perform.
        table : str or TableDefinition or SelectPlan
            Joined source.
        on : tuple
            The ``(first, operator, second)`` ON condition, where
            ``first`` may instead be a callable receiving a
            :class:`JoinClause` to declare several conditions.
        alias : str or None
            Alias the joined source is referred to by.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the ON condition is incomplete.
        """
        first, operator, second = on
        if callable(first):
            clause = JoinClause()
            first(clause)
            conditions = clause.conditions()
        elif first is None or operator is None or second is None:
            error_msg = (
                "A join requires (first, operator, second) or a callable "
                "receiving a join clause."
            )
            raise InvalidQueryException(error_msg)
        else:
            conditions = [
                JoinCondition(first=first, operator=operator, second=second),
            ]

        target = (
            table
            if isinstance(table, SelectPlan)
            else self._resolveJoinTable(table)
        )
        self._plan.joins.append(
            JoinExpression(
                join_type=join_type,
                table=target,
                alias=alias,
                conditions=conditions,
            ),
        )
        return self

    def _addTyped(
        self,
        column: str,
        where_type: WhereType,
        value: Any,
        boolean: str,
    ) -> Self:
        """
        Append a single-column condition of the given kind.

        Parameters
        ----------
        column : str
            Column name to filter by.
        where_type : WhereType
            Kind of condition to append.
        value : Any
            Bound value carried by the condition.
        boolean : str
            Logical connector with the previous clause.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        self._plan.wheres.append(
            WhereClause(
                column=column,
                where_type=where_type,
                value=value,
                boolean=boolean,
            ),
        )
        return self

    def _addMembership(
        self,
        column: str,
        values: Any,
        where_type: WhereType,
        boolean: str,
    ) -> Self:
        """
        Append a set-membership condition backed by values or a subquery.

        Parameters
        ----------
        column : str
            Column name to filter by.
        values : Any
            Bound values, or a subquery producing them.
        where_type : WhereType
            ``IN`` or ``NOT_IN``.
        boolean : str
            Logical connector with the previous clause.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        resolved: Any
        if isinstance(values, SelectPlan) or callable(values) or hasattr(
            values, "toPlan",
        ):
            resolved = self._resolvePlan(values)
        else:
            resolved = self._materializeValues(values)
        return self._addTyped(column, where_type, resolved, boolean)

    def _addColumnComparison(
        self,
        first: str,
        operator: str,
        second: str,
        boolean: str,
    ) -> Self:
        """
        Append a comparison between two columns of the query.

        Parameters
        ----------
        first : str
            Left-hand column reference.
        operator : str
            Comparison operator relating both sides.
        second : str
            Right-hand column reference.
        boolean : str
            Logical connector with the previous clause.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.

        Raises
        ------
        InvalidQueryException
            If the operator is not supported.
        """
        normalized = self._normalizeOperator(operator)
        self._plan.wheres.append(
            WhereClause(
                column=first,
                where_type=WhereType.COLUMN,
                operator=normalized,
                value=second,
                boolean=boolean,
            ),
        )
        return self

    def _addRaw(
        self,
        target: list[WhereClause],
        sql: str,
        bindings: dict[str, Any] | None,
        boolean: str,
    ) -> Self:
        """
        Append a raw SQL condition to a clause list.

        Parameters
        ----------
        target : list of WhereClause
            Clause list receiving the condition.
        sql : str
            SQL fragment using named ``:param`` placeholders.
        bindings : dict or None
            Values bound to the placeholders of the fragment.
        boolean : str
            Logical connector with the previous clause.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        target.append(
            WhereClause(
                column="",
                where_type=WhereType.RAW,
                value=RawExpression(
                    sql=sql, bindings=bindings.copy() if bindings else {},
                ),
                boolean=boolean,
            ),
        )
        return self

    def _addExists(
        self,
        query: Any,
        where_type: WhereType,
        boolean: str,
    ) -> Self:
        """
        Append an ``EXISTS`` or ``NOT EXISTS`` condition.

        Parameters
        ----------
        query : Any
            Subquery source accepted by :meth:`_resolvePlan`.
        where_type : WhereType
            ``EXISTS`` or ``NOT_EXISTS``.
        boolean : str
            Logical connector with the previous clause.

        Returns
        -------
        QueryBuilderBase
            The same builder, enabling fluent chaining.
        """
        self._plan.wheres.append(
            WhereClause(
                column="",
                where_type=where_type,
                value=self._resolvePlan(query),
                boolean=boolean,
            ),
        )
        return self

    def _addWhere(
        self,
        target: list[WhereClause],
        column: Any,
        args: tuple[Any, ...],
        boolean: str,
    ) -> None:
        """
        Parse and append a condition to a clause list.

        Supports the grouping form (a callable receiving a nested
        builder), the mapping form, ``(column, value)``, and
        ``(column, operator, value)``.

        Parameters
        ----------
        target : list of WhereClause
            Clause list receiving the condition.
        column : Any
            Column name, mapping of equality pairs, or grouping callable.
        args : tuple
            Either the bound value, or an operator followed by a value.
        boolean : str
            Logical connector with the previous clause.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        InvalidQueryException
            If the arguments do not match a supported form.
        """
        # Grouping form: nested conditions wrapped in parentheses.
        if callable(column):
            target.append(
                WhereClause(
                    column="",
                    where_type=WhereType.NESTED,
                    value=self._nestedClauses(column),
                    boolean=boolean,
                ),
            )
            return

        # Mapping form: a batch of equality conditions.
        if isinstance(column, dict):
            if args:
                error_msg = "Mapping conditions do not accept extra arguments."
                raise InvalidQueryException(error_msg)
            target.extend(
                WhereClause(column=key, value=value, boolean=boolean)
                for key, value in column.items()
            )
            return

        if len(args) == 1:
            target.append(
                WhereClause(column=column, value=args[0], boolean=boolean),
            )
            return

        if len(args) == _WHERE_WITH_OPERATOR:
            target.append(
                WhereClause(
                    column=column,
                    operator=self._normalizeOperator(args[0]),
                    value=args[1],
                    boolean=boolean,
                ),
            )
            return

        error_msg = "where() expects (column, value) or (column, operator, value)."
        raise InvalidQueryException(error_msg)

    def _nestedClauses(self, callback: Callable[[Any], Any]) -> list[WhereClause]:
        """
        Run a grouping callback and collect the conditions it declared.

        Parameters
        ----------
        callback : Callable
            Callable receiving a nested builder bound to the same table.

        Returns
        -------
        list of WhereClause
            Conditions declared inside the group, in declaration order.
        """
        nested = self._newQuery()
        callback(nested)
        return nested.toPlan().wheres

    @staticmethod
    def _normalizeOperator(operator: Any) -> str:
        """
        Validate and normalize a comparison operator.

        Parameters
        ----------
        operator : Any
            Operator supplied by the caller.

        Returns
        -------
        str
            Lowercase, trimmed operator.

        Raises
        ------
        InvalidQueryException
            If the operator is not supported.
        """
        normalized = str(operator).strip().lower()
        if normalized not in SUPPORTED_OPERATORS:
            error_msg = f"Unsupported comparison operator '{operator}'."
            raise InvalidQueryException(error_msg)
        return normalized

    @staticmethod
    def _boundaryPair(bounds: Iterable[Any]) -> tuple[Any, ...]:
        """
        Validate that a range condition carries exactly two boundaries.

        Parameters
        ----------
        bounds : Iterable
            Boundary values supplied by the caller.

        Returns
        -------
        tuple
            The two boundary values.

        Raises
        ------
        InvalidQueryException
            If the boundaries are not exactly two values.
        """
        values = tuple(bounds)
        if len(values) != _BETWEEN_BOUNDS:
            error_msg = "Range conditions require exactly two boundary values."
            raise InvalidQueryException(error_msg)
        return values

    @staticmethod
    def _materializeValues(values: Iterable[Any]) -> tuple[Any, ...]:
        """
        Materialize an iterable of bound values into a tuple.

        Parameters
        ----------
        values : Iterable
            Values to materialize; collections are unwrapped.

        Returns
        -------
        tuple
            Materialized values.
        """
        if isinstance(values, Collection):
            return tuple(values.all())
        return tuple(values)
