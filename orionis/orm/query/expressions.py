from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from orionis.orm.schema.table import TableDefinition

# Comparison operators accepted by basic where clauses.
SUPPORTED_OPERATORS: frozenset[str] = frozenset(
    {
        "=", "==", "!=", "<>", "<", "<=", ">", ">=",
        "like", "not like", "ilike", "not ilike",
    },
)

class WhereType(StrEnum):
    """Kinds of where clauses supported by the query language."""

    BASIC = "basic"
    IN = "in"
    NOT_IN = "not_in"
    NULL = "null"
    NOT_NULL = "not_null"
    BETWEEN = "between"
    NOT_BETWEEN = "not_between"
    LIKE = "like"
    NOT_LIKE = "not_like"
    ILIKE = "ilike"
    NOT_ILIKE = "not_ilike"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    CONTAINS = "contains"
    REGEXP = "regexp"
    NESTED = "nested"
    COLUMN = "column"
    RAW = "raw"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"

# Clause kinds whose ``column`` field carries no column reference.
COLUMNLESS_WHERE_TYPES: frozenset[WhereType] = frozenset({
    WhereType.NESTED,
    WhereType.RAW,
    WhereType.EXISTS,
    WhereType.NOT_EXISTS,
})

class LockMode(StrEnum):
    """Row locking modes supported by select plans."""

    UPDATE = "update"
    SHARE = "share"

class SortDirection(StrEnum):
    """Sort directions supported by order clauses."""

    ASC = "asc"
    DESC = "desc"

class AggregateFunction(StrEnum):
    """Aggregate functions supported by the query language."""

    COUNT = "count"
    MAX = "max"
    MIN = "min"
    AVG = "avg"
    SUM = "sum"

class JoinType(StrEnum):
    """Join kinds supported by the query language."""

    INNER = "inner"
    LEFT = "left"
    RIGHT = "right"
    FULL = "full"
    CROSS = "cross"

@dataclass(slots=True, frozen=True)
class RawExpression:
    """
    Developer-authored SQL fragment with its bound parameters.

    The fragment itself is never built from user input by the builder;
    every value must travel through ``bindings`` so the driver escapes
    it, which is what keeps raw clauses injection-safe.

    Attributes
    ----------
    sql : str
        SQL fragment using named ``:param`` placeholders.
    bindings : dict
        Values bound to the placeholders of the fragment.
    alias : str or None
        Name the fragment is projected under; required for the value to
        stay addressable when the query becomes a derived table.
    """

    sql: str
    bindings: dict[str, Any] = field(default_factory=dict)
    alias: str | None = None

@dataclass(slots=True, frozen=True)
class SubQueryColumn:
    """
    Scalar subquery projected as a single aliased column.

    Attributes
    ----------
    plan : SelectPlan
        Subquery producing exactly one column and one row.
    alias : str
        Name the projected value is exposed under.
    """

    plan: SelectPlan
    alias: str

@dataclass(slots=True)
class WhereClause:
    """
    Single filtering condition inside a query plan.

    Attributes
    ----------
    column : str
        Column the condition applies to; empty for clause kinds listed
        in :data:`COLUMNLESS_WHERE_TYPES`.
    where_type : WhereType
        Kind of condition (basic comparison, in, null, between, like,
        nested group, column comparison, raw fragment, or exists).
    operator : str
        Comparison operator for basic and column conditions.
    value : Any
        Bound value; a sequence for ``IN`` and ``BETWEEN``, a nested
        clause list for ``NESTED``, a :class:`SelectPlan` for ``EXISTS``
        and subquery ``IN``, or a :class:`RawExpression` for ``RAW``.
    boolean : str
        Logical connector with the previous clause: ``"and"`` or ``"or"``.
    """

    column: str
    where_type: WhereType = WhereType.BASIC
    operator: str = "="
    value: Any = None
    boolean: str = "and"

@dataclass(slots=True)
class OrderClause:
    """
    Single ordering rule inside a query plan.

    Attributes
    ----------
    column : str
        Column to sort by.
    direction : SortDirection
        Sort direction, ascending by default.
    """

    column: str
    direction: SortDirection = SortDirection.ASC

@dataclass(slots=True)
class AggregateClause:
    """
    Aggregate projection applied to a select plan.

    Attributes
    ----------
    function : AggregateFunction
        Aggregate function to apply.
    column : str
        Target column, or ``"*"`` for ``COUNT``.
    """

    function: AggregateFunction
    column: str = "*"

@dataclass(slots=True)
class JoinCondition:
    """
    Single ON condition comparing two column references.

    Both sides may be qualified as ``"table.column"`` to disambiguate
    across the tables participating in the query; an unqualified side
    defaults to the table being joined.

    Attributes
    ----------
    first : str
        Left-hand column reference.
    operator : str
        Comparison operator relating both sides.
    second : str
        Right-hand column reference.
    boolean : str
        Logical connector with the previous condition: ``"and"`` or
        ``"or"``.
    """

    first: str
    operator: str = "="
    second: str = ""
    boolean: str = "and"

@dataclass(slots=True)
class JoinExpression:
    """
    Single JOIN source attached to a select plan.

    Attributes
    ----------
    join_type : JoinType
        Kind of join to perform.
    table : TableDefinition or SelectPlan
        Joined table description, or a subquery joined as a derived
        table. A table definition carries its own columns so the
        compiler can resolve qualified references without guessing.
    alias : str or None
        Name the joined source is referred to by inside the query, or
        ``None`` to use its logical table name. Required for subqueries.
    conditions : list of JoinCondition
        ON conditions combined left to right.
    """

    join_type: JoinType
    table: TableDefinition | SelectPlan
    alias: str | None = None
    conditions: list[JoinCondition] = field(default_factory=list)

@dataclass(slots=True)
class UnionClause:
    """
    Select plan combined with the owning query through ``UNION``.

    Attributes
    ----------
    plan : SelectPlan
        Query whose rows are appended to the owning query.
    all_rows : bool
        Whether duplicates are kept (``UNION ALL``) or collapsed.
    """

    plan: SelectPlan
    all_rows: bool = False

@dataclass(slots=True)
class SelectPlan:
    """
    Complete, engine-agnostic description of a SELECT query.

    Attributes
    ----------
    table : TableDefinition
        Table the query runs against.
    alias : str or None
        Name the main table is referred to by inside the query, or
        ``None`` to use its logical table name. Required to self-join a
        table against itself once joins are composed on top of a plan.
    joins : list of JoinExpression
        Additional table sources joined onto the main table.
    columns : tuple of str
        Projected columns; empty means all columns. Entries may be
        qualified as ``"table.column"`` once ``joins`` is non-empty.
    wheres : list of WhereClause
        Filtering conditions combined left to right.
    orders : list of OrderClause
        Ordering rules.
    groups : list of str
        Grouping columns.
    havings : list of WhereClause
        Conditions applied after grouping.
    limit_value : int or None
        Maximum number of rows to return.
    offset_value : int or None
        Number of rows to skip.
    aggregate : AggregateClause or None
        Aggregate projection replacing the column list when present.
    distinct : bool
        Whether duplicate rows are collapsed via ``SELECT DISTINCT``.
    lock : LockMode or None
        Row locking mode requested for the selected rows.
    unions : list of UnionClause
        Queries appended to this one through ``UNION``.
    """

    table: TableDefinition
    alias: str | None = None
    joins: list[JoinExpression] = field(default_factory=list)
    columns: tuple[str | SubQueryColumn | RawExpression, ...] = ()
    wheres: list[WhereClause] = field(default_factory=list)
    orders: list[OrderClause] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    havings: list[WhereClause] = field(default_factory=list)
    limit_value: int | None = None
    offset_value: int | None = None
    aggregate: AggregateClause | None = None
    distinct: bool = False
    lock: LockMode | None = None
    unions: list[UnionClause] = field(default_factory=list)

    def clone(self) -> SelectPlan:
        """
        Return an independent copy of the plan.

        Mutable clause lists are shallow-copied so the clone can be
        modified without affecting the original plan.

        Returns
        -------
        SelectPlan
            Detached copy of this plan.
        """
        return SelectPlan(
            table=self.table,
            alias=self.alias,
            joins=self.joins.copy(),
            columns=self.columns,
            wheres=self.wheres.copy(),
            orders=self.orders.copy(),
            groups=self.groups.copy(),
            havings=self.havings.copy(),
            limit_value=self.limit_value,
            offset_value=self.offset_value,
            aggregate=self.aggregate,
            distinct=self.distinct,
            lock=self.lock,
            unions=self.unions.copy(),
        )

@dataclass(slots=True)
class InsertPlan:
    """
    Engine-agnostic description of an INSERT statement.

    Attributes
    ----------
    table : TableDefinition
        Table receiving the rows.
    values : list of dict
        One dictionary of column values per row to insert.
    """

    table: TableDefinition
    values: list[dict[str, Any]] = field(default_factory=list)

@dataclass(slots=True)
class UpdatePlan:
    """
    Engine-agnostic description of an UPDATE statement.

    Attributes
    ----------
    table : TableDefinition
        Table to update.
    values : dict
        Column values to assign.
    wheres : list of WhereClause
        Conditions restricting the affected rows.
    """

    table: TableDefinition
    values: dict[str, Any] = field(default_factory=dict)
    wheres: list[WhereClause] = field(default_factory=list)

@dataclass(slots=True)
class DeletePlan:
    """
    Engine-agnostic description of a DELETE statement.

    Attributes
    ----------
    table : TableDefinition
        Table to delete from.
    wheres : list of WhereClause
        Conditions restricting the affected rows.
    """

    table: TableDefinition
    wheres: list[WhereClause] = field(default_factory=list)
