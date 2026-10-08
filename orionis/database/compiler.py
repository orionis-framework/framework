from __future__ import annotations
import operator
from typing import TYPE_CHECKING, Any, ClassVar
import sqlalchemy
from sqlalchemy import Column as SqlColumn
from sqlalchemy import ForeignKey, MetaData, Table, and_, func, or_
from sqlalchemy.dialects.oracle import FLOAT
from sqlalchemy.exc import NoSuchModuleError
from sqlalchemy.schema import CreateTable, DropTable
from sqlalchemy.sql import CompoundSelect
from sqlalchemy.sql.elements import ClauseElement
from orionis.database.dialect import missing_dependency_error
from orionis.database.exceptions import QueryException
from orionis.orm.query.expressions import (
    COLUMNLESS_WHERE_TYPES,
    AggregateFunction,
    JoinType,
    LockMode,
    RawExpression,
    SelectPlan,
    SortDirection,
    SubQueryColumn,
    WhereType,
)
from orionis.orm.schema.types import ColumnType

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from sqlalchemy.sql import Delete, Insert, Select, Update
    from sqlalchemy.sql.elements import ColumnElement
    from sqlalchemy.sql.expression import Executable
    from sqlalchemy.types import TypeEngine
    from orionis.orm.query.expressions import (
        AggregateClause,
        DeletePlan,
        InsertPlan,
        JoinCondition,
        JoinExpression,
        UpdatePlan,
        WhereClause,
    )
    from orionis.orm.schema.column import ColumnDefinition
    from orionis.orm.schema.constraints import ForeignReference
    from orionis.orm.schema.table import TableDefinition

    # A resolvable FROM/JOIN source: either the raw engine Table or an
    # aliased projection of it (``Table.alias(name)``).
    type SqlSource = Any
    # Table sources reachable by qualified column references, keyed by
    # alias when present or by logical table name otherwise.
    type SourceMap = dict[str, SqlSource]

# Comparison operators for basic where clauses.
_COMPARATORS: dict[str, Callable[[Any, Any], Any]] = {
    "=": operator.eq,
    "==": operator.eq,
    "!=": operator.ne,
    "<>": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}

# Operators whose NULL comparison must compile to IS / IS NOT.
_EQUALITY_OPERATORS: frozenset[str] = frozenset({"=", "=="})
_INEQUALITY_OPERATORS: frozenset[str] = frozenset({"!=", "<>"})

# Pattern-matching operators accepted by basic where clauses.
_PATTERN_OPERATORS: dict[str, Callable[[Any, Any], Any]] = {
    "like": lambda col, val: col.like(val),
    "not like": lambda col, val: col.not_like(val),
    "ilike": lambda col, val: col.ilike(val),
    "not ilike": lambda col, val: col.not_ilike(val),
}

# Number of boundaries required by a BETWEEN condition.
_BETWEEN_BOUNDS: int = 2

# Handlers for where clause kinds with a single-expression translation.
_SIMPLE_CLAUSES: dict[WhereType, Callable[[Any, Any], Any]] = {
    WhereType.IN: lambda col, val: col.in_(() if val is None else val),
    WhereType.NOT_IN: lambda col, val: col.not_in(() if val is None else val),
    WhereType.NULL: lambda col, _val: col.is_(None),
    WhereType.NOT_NULL: lambda col, _val: col.is_not(None),
    WhereType.LIKE: lambda col, val: col.like(val),
    WhereType.NOT_LIKE: lambda col, val: col.not_like(val),
    WhereType.ILIKE: lambda col, val: col.ilike(val),
    WhereType.NOT_ILIKE: lambda col, val: col.not_ilike(val),
    WhereType.STARTS_WITH: lambda col, val: col.startswith(val),
    WhereType.ENDS_WITH: lambda col, val: col.endswith(val),
    WhereType.CONTAINS: lambda col, val: col.contains(val),
    WhereType.REGEXP: lambda col, val: col.regexp_match(val),
}

class SQLCompiler:
    """
    Translate Orionis query plans into engine-executable statements.

    This is the only component, together with the connection and the
    dialect helpers, aware of the underlying SQL toolkit. It converts
    :class:`TableDefinition` objects into engine table metadata (cached
    per compiler) and query plans into executable statements.
    """

    __slots__ = ("_definitions", "_driver", "_metadata", "_prefix", "_tables")

    # Builders translating logical column types into engine types.
    _TYPE_BUILDERS: ClassVar[
        dict[ColumnType, Callable[[ColumnDefinition], TypeEngine[Any]]]
    ] = {
        # Generic "CamelCase" types.
        ColumnType.INTEGER: lambda _c: sqlalchemy.Integer(),
        ColumnType.BIG_INTEGER: lambda _c: sqlalchemy.BigInteger(),
        ColumnType.SMALL_INTEGER: lambda _c: sqlalchemy.SmallInteger(),
        ColumnType.STRING: lambda c: sqlalchemy.String(c.length, c.collation),
        ColumnType.TEXT: lambda c: sqlalchemy.Text(c.length, c.collation),
        ColumnType.UNICODE: lambda c: sqlalchemy.Unicode(c.length, c.collation),
        ColumnType.UNICODE_TEXT: lambda c: sqlalchemy.UnicodeText(
            c.length, c.collation,
        ),
        ColumnType.BOOLEAN: lambda c: sqlalchemy.Boolean(
            create_constraint=c.create_constraint,
            name=c.constraint_name,
        ),
        ColumnType.FLOAT: lambda c: sqlalchemy.Float(
            c.precision, asdecimal=c.as_decimal,
            decimal_return_scale=c.decimal_return_scale,
        ),
        ColumnType.DOUBLE: lambda c: sqlalchemy.Double(
            c.precision, asdecimal=c.as_decimal,
            decimal_return_scale=c.decimal_return_scale,
        ),
        ColumnType.NUMERIC: lambda c: sqlalchemy.Numeric(
            c.precision, c.scale, c.decimal_return_scale, asdecimal=c.as_decimal,
        ),
        ColumnType.DATE: lambda _c: sqlalchemy.Date(),
        ColumnType.TIME: lambda _c: sqlalchemy.Time(),
        ColumnType.DATETIME: lambda c: sqlalchemy.DateTime(timezone=c.timezone),
        ColumnType.INTERVAL: lambda c: sqlalchemy.Interval(
            native=c.native,
            second_precision=c.second_precision,
            day_precision=c.day_precision,
        ),
        ColumnType.LARGE_BINARY: lambda c: sqlalchemy.LargeBinary(c.length),
        ColumnType.UUID: lambda c: sqlalchemy.Uuid(
            as_uuid=c.as_uuid, native_uuid=c.native_uuid,
        ),
        ColumnType.PICKLE_TYPE: lambda c: sqlalchemy.PickleType(
            protocol=c.protocol,
        ),
        ColumnType.ENUM: lambda c: sqlalchemy.Enum(
            *c.enum_values,
            name=c.enum_name,
            native_enum=c.native_enum,
            create_constraint=c.create_constraint,
            length=(
                c.length if c.length is not None
                else max(len(value) for value in c.enum_values)
            ),
            validate_strings=c.validate_strings,
        ),

        # SQL standard and multiple vendor "UPPERCASE" types.
        ColumnType.BIGINT: lambda _c: sqlalchemy.BIGINT(),
        ColumnType.SMALLINT: lambda _c: sqlalchemy.SMALLINT(),
        ColumnType.INT: lambda _c: sqlalchemy.INTEGER(),
        ColumnType.CHAR: lambda c: sqlalchemy.CHAR(c.length, c.collation),
        ColumnType.VARCHAR: lambda c: sqlalchemy.VARCHAR(c.length, c.collation),
        ColumnType.NCHAR: lambda c: sqlalchemy.NCHAR(c.length, c.collation),
        ColumnType.NVARCHAR: lambda c: sqlalchemy.NVARCHAR(c.length, c.collation),
        ColumnType.CLOB: lambda c: sqlalchemy.CLOB(c.length, c.collation),
        ColumnType.REAL: lambda c: sqlalchemy.REAL(
            c.precision, asdecimal=c.as_decimal,
            decimal_return_scale=c.decimal_return_scale,
        ),
        ColumnType.DOUBLE_PRECISION: lambda c: sqlalchemy.DOUBLE_PRECISION(
            c.precision, asdecimal=c.as_decimal,
            decimal_return_scale=c.decimal_return_scale,
        ),
        ColumnType.DECIMAL: lambda c: sqlalchemy.DECIMAL(
            c.precision, c.scale, c.decimal_return_scale, asdecimal=c.as_decimal,
        ),
        ColumnType.TIMESTAMP: lambda c: sqlalchemy.TIMESTAMP(timezone=c.timezone),
        ColumnType.BINARY: lambda c: sqlalchemy.BINARY(c.length),
        ColumnType.VARBINARY: lambda c: sqlalchemy.VARBINARY(c.length),
        ColumnType.BLOB: lambda c: sqlalchemy.BLOB(c.length),
        ColumnType.JSON: lambda c: sqlalchemy.JSON(none_as_null=c.none_as_null),
    }

    def __init__(self, prefix: str = "", *, driver: str | None = None) -> None:
        """
        Initialize backend settings and compiler-owned table metadata.

        Parameters
        ----------
        prefix : str, optional
            Text prepended to logical table names; empty by default.
        driver : str or None, optional
            Orionis backend name for native type, identity, and locking options.

        Returns
        -------
        None
            Store the settings and create empty metadata and table caches.
        """
        self._prefix = prefix or ""
        self._driver = driver
        self._metadata = MetaData()
        self._tables: dict[str, Table] = {}
        self._definitions: dict[str, TableDefinition] = {}

    # ── Statement compilation ───────────────────────────────────────────────

    def compileSelect(self, plan: SelectPlan) -> Select[Any] | CompoundSelect:
        """
        Compile a SELECT plan, including aggregates and union branches.

        Use a derived query for ``COUNT(*)`` over distinct, grouped, or unioned
        results.

        Parameters
        ----------
        plan : SelectPlan
            Projection, sources, conditions, grouping, unions, paging, and locks.

        Returns
        -------
        Select or CompoundSelect
            Executable SELECT; union branches are wrapped in a derived table.

        Raises
        ------
        QueryException
            If sources or columns are unknown, clauses are invalid, or a Redshift
            row lock is requested.
        """
        self._validateSelectLock(plan)
        if (
            plan.aggregate is not None
            and plan.aggregate.function is AggregateFunction.COUNT
            and plan.aggregate.column == "*"
            and (plan.distinct or plan.groups or plan.havings or plan.unions)
        ):
            probe = plan.clone()
            probe.aggregate = None
            probe.orders = []
            probe.limit_value = None
            probe.offset_value = None
            probe.lock = None
            if probe.groups and not probe.columns:
                probe.columns = tuple(probe.groups)
            return sqlalchemy.select(func.count()).select_from(
                self.compileSelect(probe).subquery(),
            )
        if not plan.unions:
            return self._buildSelect(plan, {})
        base = plan.clone()
        base.unions = []
        base.orders = []
        base.limit_value = None
        base.offset_value = None
        statement = self._buildSelect(base, {})
        return self._applyUnions(statement, plan)

    def _applyUnions(
        self,
        statement: Select[Any],
        plan: SelectPlan,
    ) -> Select[Any]:
        """
        Combine union branches and apply global ordering and pagination.

        Flatten consecutive operators of the same kind; preserve left-to-right
        grouping when switching between ``UNION`` and ``UNION ALL``.

        Parameters
        ----------
        statement : Select
            Base SELECT without the owning plan's unions, ordering, or paging.
        plan : SelectPlan
            SELECT plan containing at least one union branch.

        Returns
        -------
        Select
            SELECT over combined rows with the owning plan's order and bounds.
        """
        branches: list[Any] = [statement]
        all_rows = plan.unions[0].all_rows
        for union in plan.unions:
            if union.all_rows != all_rows:
                combine = sqlalchemy.union_all if all_rows else sqlalchemy.union
                branches = [sqlalchemy.select(combine(*branches).subquery())]
                all_rows = union.all_rows
            branch = self.compileSelect(union.plan)
            if isinstance(branch, CompoundSelect):
                branch = sqlalchemy.select(branch.subquery())
            branches.append(branch)
        combine = sqlalchemy.union_all if all_rows else sqlalchemy.union
        derived = combine(*branches).subquery()
        sources = {plan.alias or plan.table.name: derived}
        return self._applyOrderingAndPaging(
            sources, derived, sqlalchemy.select(derived), plan,
        )

    def _buildSelect(
        self,
        plan: SelectPlan,
        outer_sources: SourceMap,
    ) -> Select[Any]:
        """
        Build a SELECT and resolve references to enclosing query sources.

        Parameters
        ----------
        plan : SelectPlan
            SELECT description whose sources and clauses are compiled.
        outer_sources : SourceMap
            Source lookup from the enclosing query, or an empty mapping.

        Returns
        -------
        Select
            SELECT with projection, filters, grouping, paging, and requested locks.

        Raises
        ------
        QueryException
            If references or clauses are invalid, or a Redshift lock is requested.
        """
        self._validateSelectLock(plan)
        self._ensureSelectRawColumns(plan)
        default, own_sources, from_clause = self._resolveSources(plan)
        sources: SourceMap = (
            {**outer_sources, **own_sources} if outer_sources else own_sources
        )
        statement = self._selectProjection(default, sources, plan)
        if plan.joins:
            statement = statement.select_from(from_clause)
        if plan.distinct and plan.aggregate is None:
            statement = statement.distinct()

        # Apply filtering conditions.
        condition = self._whereExpression(sources, default, plan.wheres)
        if condition is not None:
            statement = statement.where(condition)

        # Apply grouping and post-grouping conditions.
        if plan.groups:
            groups = [
                self._resolveColumn(sources, default, name)
                for name in plan.groups
            ]
            statement = statement.group_by(*groups)
        having = self._whereExpression(sources, default, plan.havings)
        if having is not None:
            statement = statement.having(having)

        # Ordering and pagination are meaningless for aggregates.
        if plan.aggregate is None:
            statement = self._applyOrderingAndPaging(
                sources, default, statement, plan,
            )

        if plan.lock is not None:
            if self._driver == "sqlserver":
                # SQL Server ignores Core's FOR UPDATE clause. Retain physical
                # row locks until transaction end with native table hints.
                hints = (
                    "WITH (HOLDLOCK, ROWLOCK)" if plan.lock is LockMode.SHARE
                    else "WITH (UPDLOCK, ROWLOCK)"
                )
                statement = statement.with_hint(default, hints, dialect_name="mssql")
            else:
                statement = statement.with_for_update(
                    read=plan.lock is LockMode.SHARE,
                )

        return statement

    def _validateSelectLock(self, plan: SelectPlan) -> None:
        """
        Reject a SELECT row lock when the backend is Redshift.

        Parameters
        ----------
        plan : SelectPlan
            Current SELECT plan whose lock setting is checked.

        Returns
        -------
        None
            Continue compilation without modifying the plan.

        Raises
        ------
        QueryException
            If ``plan.lock`` is set for the Redshift backend.
        """
        if self._driver == "redshift" and plan.lock is not None:
            message = "Amazon Redshift does not support row-level SELECT locks."
            raise QueryException(message)

    # ── Schemaless (raw) table support ──────────────────────────────────────

    def _bareNameForIdentifier(self, name: str, identifier: str) -> str | None:
        """
        Extract a bare column name for a matching source identifier.

        Parameters
        ----------
        name : str
            Unqualified or dot-qualified column reference.
        identifier : str
            Alias or logical table name accepted as the qualifier.

        Returns
        -------
        str or None
            Bare name for unqualified or matching references; otherwise ``None``.
        """
        qualifier, column = self._splitQualifiedColumn(name)
        if qualifier is None or qualifier == identifier:
            return column
        return None

    def _collectClauseColumnNames(
        self,
        clauses: Sequence[WhereClause],
        names: set[str],
    ) -> None:
        """
        Collect explicit column references from conditions and nested groups.

        Parameters
        ----------
        clauses : Sequence of WhereClause
            WHERE or HAVING conditions to inspect recursively.
        names : set of str
            Mutable accumulator for left-hand and column-comparison references.

        Returns
        -------
        None
            Update ``names`` in place; skip raw SQL and EXISTS subqueries.
        """
        for clause in clauses:
            if clause.where_type is WhereType.NESTED:
                self._collectClauseColumnNames(clause.value or (), names)
                continue
            if clause.where_type in COLUMNLESS_WHERE_TYPES:
                continue
            names.add(clause.column)
            if clause.where_type is WhereType.COLUMN:
                names.add(str(clause.value))

    def _collectPlanColumnNames(self, plan: SelectPlan) -> set[str]:
        """
        Collect explicit column references from the current SELECT plan.

        Inspect projection names, conditions, ordering, grouping, aggregates,
        and joins without parsing raw SQL or traversing subquery plans.

        Parameters
        ----------
        plan : SelectPlan
            SELECT plan whose direct references will be collected.

        Returns
        -------
        set of str
            Qualified and unqualified names used by the current plan's clauses.
        """
        names: set[str] = {
            column for column in plan.columns if isinstance(column, str)
        }
        self._collectClauseColumnNames(plan.wheres, names)
        self._collectClauseColumnNames(plan.havings, names)
        names.update(order.column for order in plan.orders)
        names.update(plan.groups)
        if plan.aggregate is not None and plan.aggregate.column != "*":
            names.add(plan.aggregate.column)
        for join in plan.joins:
            for condition in join.conditions:
                names.add(condition.first)
                names.add(condition.second)
        return names

    def _ensureRawColumns(
        self,
        table: TableDefinition,
        alias: str | None,
        names: set[str],
    ) -> None:
        """
        Declare missing referenced columns on a schemaless table.

        Declare columns before creating aliases, whose column collections are
        cached.

        Parameters
        ----------
        table : TableDefinition
            Table definition; declared schemas are left unchanged.
        alias : str or None
            Query alias used to match qualified references, or ``None``.
        names : set of str
            Collected qualified or unqualified references from the owning plan.

        Returns
        -------
        None
            Append matching names to cached table metadata without assigning types.
        """
        if table.columns:
            return

        identifier = alias or table.name
        bare_names = {
            column
            for name in names
            if (column := self._bareNameForIdentifier(name, identifier)) is not None
        }
        if not bare_names:
            return

        engine_table = self._sqlTable(table)
        for column in bare_names:
            if column not in engine_table.c:
                engine_table.append_column(SqlColumn(column))

    def _ensureSelectRawColumns(self, plan: SelectPlan) -> None:
        """
        Declare referenced columns for schemaless SELECT and JOIN sources.

        Parameters
        ----------
        plan : SelectPlan
            SELECT plan supplying source definitions and column references.

        Returns
        -------
        None
            Update raw table metadata before alias creation; skip subquery joins.
        """
        # Collect references only when a source has no declared columns.
        if plan.table.columns and all(
            isinstance(join.table, SelectPlan) or join.table.columns
            for join in plan.joins
        ):
            return
        names = self._collectPlanColumnNames(plan)
        self._ensureRawColumns(plan.table, plan.alias, names)
        for join in plan.joins:
            if not isinstance(join.table, SelectPlan):
                self._ensureRawColumns(join.table, join.alias, names)

    def _resolveSources(
        self,
        plan: SelectPlan,
    ) -> tuple[SqlSource, SourceMap, SqlSource]:
        """
        Build SELECT sources and assemble the FROM clause.

        Index each source by its alias, or by its logical table name when no
        alias is supplied.

        Parameters
        ----------
        plan : SelectPlan
            Main table, optional alias, and ordered join descriptions.

        Returns
        -------
        tuple of (SqlSource, SourceMap, SqlSource)
            Main source, source lookup map, and complete FROM/JOIN expression.

        Raises
        ------
        QueryException
            If a joined source or its ON conditions cannot be compiled.
        """
        table = self._sqlTable(plan.table)
        default = table.alias(plan.alias) if plan.alias else table
        sources: SourceMap = {plan.alias or plan.table.name: default}

        from_clause = default
        for join in plan.joins:
            from_clause, joined_name, joined_source = self._applyJoin(
                from_clause, sources, join,
            )
            sources[joined_name] = joined_source

        return default, sources, from_clause

    def _joinSource(self, join: JoinExpression) -> tuple[str, SqlSource]:
        """
        Build a joined table or an aliased subquery source.

        Parameters
        ----------
        join : JoinExpression
            Table or SELECT plan to join, with an optional source alias.

        Returns
        -------
        tuple of (str, SqlSource)
            Source identifier and table, table alias, or compiled derived query.

        Raises
        ------
        QueryException
            If a subquery has no alias or its SELECT plan cannot be compiled.
        """
        if isinstance(join.table, SelectPlan):
            if not join.alias:
                error_msg = "A subquery join requires an alias."
                raise QueryException(error_msg)
            return join.alias, self._buildSelect(join.table, {}).subquery(join.alias)

        joined_table = self._sqlTable(join.table)
        source = joined_table.alias(join.alias) if join.alias else joined_table
        return join.alias or join.table.name, source

    def _applyJoin(
        self,
        from_clause: SqlSource,
        sources: SourceMap,
        join: JoinExpression,
    ) -> tuple[SqlSource, str, SqlSource]:
        """
        Extend a FROM clause with the requested join type.

        Emulate RIGHT JOIN by swapping sources in a LEFT JOIN.

        Parameters
        ----------
        from_clause : SqlSource
            FROM/JOIN expression built before this join.
        sources : SourceMap
            Existing sources used to resolve ON-clause column references.
        join : JoinExpression
            Joined source, join type, and optional ON conditions.

        Returns
        -------
        tuple of (SqlSource, str, SqlSource)
            Extended FROM clause, joined identifier, and joined source.

        Raises
        ------
        QueryException
            If a subquery alias is missing or ON conditions are absent or invalid.
        """
        joined_name, joined_source = self._joinSource(join)

        if join.join_type is JoinType.CROSS:
            return from_clause.join(joined_source, sqlalchemy.true()), \
                joined_name, joined_source

        condition = self._joinCondition(sources, joined_name, joined_source, join)
        if join.join_type is JoinType.INNER:
            joined = from_clause.join(joined_source, condition)
        elif join.join_type is JoinType.LEFT:
            joined = from_clause.join(joined_source, condition, isouter=True)
        elif join.join_type is JoinType.FULL:
            joined = from_clause.join(joined_source, condition, full=True)
        else:
            # The SQL toolkit has no native RIGHT JOIN construct; a LEFT
            # JOIN with both sides swapped is its exact equivalent.
            joined = joined_source.join(from_clause, condition, isouter=True)
        return joined, joined_name, joined_source

    def _joinCondition(
        self,
        sources: SourceMap,
        joined_name: str,
        joined_source: SqlSource,
        join: JoinExpression,
    ) -> ColumnElement[bool]:
        """
        Combine a join's ON conditions into one boolean expression.

        Parameters
        ----------
        sources : SourceMap
            Sources available before adding the joined source.
        joined_name : str
            Identifier used to qualify columns from the new source.
        joined_source : SqlSource
            Table or derived query introduced by this join.
        join : JoinExpression
            Join description containing one or more ON conditions.

        Returns
        -------
        ColumnElement
            ON expression, using the joined source for unqualified column names.

        Raises
        ------
        QueryException
            If ON conditions are absent, references are unknown, or operators are
            unsupported.
        """
        if not join.conditions:
            error_msg = (
                f"Join on '{joined_name}' requires at least one ON condition."
            )
            raise QueryException(error_msg)

        local_sources: SourceMap = {**sources, joined_name: joined_source}
        return self._combineExpressions(
            self._joinConditionExpression,
            local_sources,
            joined_source,
            join.conditions,
        )

    def _joinConditionExpression(
        self,
        sources: SourceMap,
        default: SqlSource,
        condition: JoinCondition,
    ) -> ColumnElement[bool]:
        """
        Compile an ON condition as a comparison between two columns.

        Parameters
        ----------
        sources : SourceMap
            Sources indexed by alias or logical table name.
        default : SqlSource
            Source used to resolve unqualified column names.
        condition : JoinCondition
            Left reference, comparison operator, and right reference.

        Returns
        -------
        ColumnElement
            Boolean comparison between the resolved column expressions.

        Raises
        ------
        QueryException
            If either reference is unknown or the comparison operator is unsupported.
        """
        left = self._resolveColumn(sources, default, condition.first)
        right = self._resolveColumn(sources, default, condition.second)
        comparator = _COMPARATORS.get(condition.operator.strip().lower())
        if comparator is None:
            error_msg = f"Unsupported join operator '{condition.operator}'."
            raise QueryException(error_msg)
        return comparator(left, right)

    def _selectProjection(
        self,
        default: SqlSource,
        sources: SourceMap,
        plan: SelectPlan,
    ) -> Select[Any]:
        """
        Build a SELECT projection from an aggregate or projected entries.

        Parameters
        ----------
        default : SqlSource
            Main query source and fallback for unqualified references.
        sources : SourceMap
            Sources indexed by alias or logical table name.
        plan : SelectPlan
            Aggregate, explicit projections, or default table selection.

        Returns
        -------
        Select
            SELECT of the requested projection; use literal ``*`` for raw tables.
        """
        # An explicit FROM is only added when the plan has no joins: with
        # joins the caller sets the composed FROM clause instead, and
        # declaring the main table twice would duplicate it.
        if plan.aggregate is not None:
            statement = sqlalchemy.select(
                self._aggregateExpression(sources, default, plan.aggregate),
            )
            return statement if plan.joins else statement.select_from(default)
        if plan.columns:
            projected = [
                self._projectionElement(sources, default, entry)
                for entry in plan.columns
            ]
            statement = sqlalchemy.select(*projected)
            return statement if plan.joins else statement.select_from(default)
        if not plan.table.columns:
            # Schemaless table: its real column list is unknowable up
            # front, so project literally instead of guessing a subset.
            return sqlalchemy.select(
                sqlalchemy.literal_column("*"),
            ).select_from(default)
        return sqlalchemy.select(default)

    @staticmethod
    def _rawElement(raw: RawExpression) -> ColumnElement[Any]:
        """
        Compile trusted SQL text with named bindings and an optional alias.

        Treat SQL text as trusted input; only values in ``bindings`` are
        parameterized. Aliased expressions remain addressable in derived queries.

        Parameters
        ----------
        raw : RawExpression
            SQL fragment, named parameter values, and optional projection alias.

        Returns
        -------
        ColumnElement or TextClause
            Text clause or labeled expression; supplied bindings use unique
            parameters.
        """
        if raw.alias and not raw.bindings:
            return sqlalchemy.literal_column(raw.sql).label(raw.alias)
        element = sqlalchemy.text(raw.sql)
        if raw.bindings:
            element = element.bindparams(*(
                sqlalchemy.bindparam(name, value, unique=True)
                for name, value in raw.bindings.items()
            ))
        if raw.alias:
            # Group the bound fragment and expose its projection name.
            return (
                element.columns(sqlalchemy.column(raw.alias))
                .scalar_subquery()
                .label(raw.alias)
            )
        return element

    def _projectionElement(
        self,
        sources: SourceMap,
        default: SqlSource,
        entry: str | SubQueryColumn | RawExpression,
    ) -> ColumnElement[Any]:
        """
        Compile one projection entry into a SQL expression.

        Parameters
        ----------
        sources : SourceMap
            Sources indexed by alias or logical table name.
        default : SqlSource
            Fallback source for unqualified column names.
        entry : str or SubQueryColumn or RawExpression
            Column reference, correlated scalar subquery, or trusted SQL fragment.

        Returns
        -------
        ColumnElement or TextClause
            Resolved column, labeled scalar subquery, or compiled raw expression.
        """
        if isinstance(entry, SubQueryColumn):
            subquery = self._buildSelect(entry.plan, sources)
            return subquery.scalar_subquery().label(entry.alias)
        if isinstance(entry, RawExpression):
            return self._rawElement(entry)
        return self._resolveColumn(sources, default, entry)

    def _applyOrderingAndPaging(
        self,
        sources: SourceMap,
        default: SqlSource,
        statement: Select[Any],
        plan: SelectPlan,
    ) -> Select[Any]:
        """
        Apply a plan's ordering, limit, and offset to a SELECT.

        Parameters
        ----------
        sources : SourceMap
            Sources indexed by alias or logical table name.
        default : SqlSource
            Fallback source for unqualified ordering columns.
        statement : Select
            SELECT statement to extend without mutating it.
        plan : SelectPlan
            Ordering clauses and optional limit and offset values.

        Returns
        -------
        Select
            SELECT with all requested sorting and pagination clauses applied.

        Raises
        ------
        QueryException
            If an ordering column or its source cannot be resolved.
        """
        if len(plan.orders) == 1:
            order = plan.orders[0]
            column = self._resolveColumn(sources, default, order.column)
            statement = statement.order_by(
                column.desc() if order.direction is SortDirection.DESC
                else column.asc(),
            )
        elif plan.orders:
            orders = []
            for order in plan.orders:
                column = self._resolveColumn(sources, default, order.column)
                orders.append(
                    column.desc()
                    if order.direction is SortDirection.DESC
                    else column.asc(),
                )
            statement = statement.order_by(*orders)
        if plan.limit_value is not None:
            statement = statement.limit(plan.limit_value)
        if plan.offset_value is not None:
            statement = statement.offset(plan.offset_value)
        return statement

    @staticmethod
    def supportsBatchInsert(plan: InsertPlan) -> bool:
        """
        Check whether multiple rows share a parameter-only batch shape.

        Check row shapes and values without compiling the INSERT statement.

        Parameters
        ----------
        plan : InsertPlan
            Insert plan with row mappings and optional declared table columns.

        Returns
        -------
        bool
            ``True`` when the batch precheck accepts multiple rows with matching
            keys and no SQLAlchemy expressions; ``False`` otherwise.
        """
        rows = plan.values
        if len(rows) <= 1:
            return False
        keys = rows[0].keys()
        if plan.table.columns and keys > plan.table.columns.keys():
            return False
        for row in rows:
            if row.keys() != keys or any(
                isinstance(value, ClauseElement) for value in row.values()
            ):
                return False
        return True

    def compileInsert(
        self,
        plan: InsertPlan,
        *,
        parameterized: bool = False,
    ) -> Insert:
        """
        Compile row mappings into an executable INSERT statement.

        Parameters
        ----------
        plan : InsertPlan
            Target table and one or more row mappings.
        parameterized : bool, optional
            Leave values to execution-time bindings. Defaults to ``False``.

        Returns
        -------
        Insert
            INSERT with attached row values, or a parameterized template.
            Parameterized PostgreSQL statements include ``RETURNING 1``.

        Raises
        ------
        QueryException
            If the plan has no rows or a column type has no SQL type builder.
        """
        if not plan.values:
            error_msg = "Cannot compile an INSERT statement without values."
            raise QueryException(error_msg)

        # Schemaless tables need their referenced columns backfilled first;
        # model-backed tables already declare them, so this is skipped.
        if not plan.table.columns:
            names: set[str] = set()
            for row in plan.values:
                names.update(row)
            self._ensureRawColumns(plan.table, None, names)

        table = self._sqlTable(plan.table)
        if parameterized:
            statement = sqlalchemy.insert(table)
            if self._driver == "pgsql":
                statement = statement.returning(
                    sqlalchemy.literal_column("1"),
                )
            return statement
        rows = plan.values if len(plan.values) > 1 else plan.values[0]
        return sqlalchemy.insert(table).values(rows)

    def compileUpdate(self, plan: UpdatePlan) -> Update:
        """
        Compile replacement values and filters into an UPDATE statement.

        Parameters
        ----------
        plan : UpdatePlan
            Target table, nonempty assignment mapping, and WHERE conditions.

        Returns
        -------
        Update
            UPDATE filtered by the plan's conditions, or unrestricted without them.

        Raises
        ------
        QueryException
            If assignments are empty or columns, types, or conditions are invalid.
        """
        if not plan.values:
            error_msg = "Cannot compile an UPDATE statement without values."
            raise QueryException(error_msg)

        if not plan.table.columns:
            names = set(plan.values)
            self._collectClauseColumnNames(plan.wheres, names)
            self._ensureRawColumns(plan.table, None, names)

        table = self._sqlTable(plan.table)
        sources: SourceMap = {plan.table.name: table}
        statement = sqlalchemy.update(table).values(plan.values)
        condition = self._whereExpression(sources, table, plan.wheres)
        if condition is not None:
            statement = statement.where(condition)
        return statement

    def compileDelete(self, plan: DeletePlan) -> Delete:
        """
        Compile filtering conditions into a DELETE statement.

        Parameters
        ----------
        plan : DeletePlan
            Target table and WHERE conditions selecting rows to delete.

        Returns
        -------
        Delete
            DELETE filtered by the plan's conditions, or unrestricted without them.

        Raises
        ------
        QueryException
            If column references, types, or filtering conditions cannot be compiled.
        """
        if not plan.table.columns:
            names: set[str] = set()
            self._collectClauseColumnNames(plan.wheres, names)
            self._ensureRawColumns(plan.table, None, names)

        table = self._sqlTable(plan.table)
        sources: SourceMap = {plan.table.name: table}
        statement = sqlalchemy.delete(table)
        condition = self._whereExpression(sources, table, plan.wheres)
        if condition is not None:
            statement = statement.where(condition)
        return statement

    def compileCreateTable(
        self,
        definition: TableDefinition,
        *,
        if_not_exists: bool = True,
    ) -> Executable:
        """
        Compile table metadata into a CREATE TABLE DDL object.

        Parameters
        ----------
        definition : TableDefinition
            Logical table name, columns, constraints, schema, and comment.
        if_not_exists : bool, optional
            Request ``IF NOT EXISTS`` in the generated DDL. Defaults to ``True``.

        Returns
        -------
        Executable
            CREATE TABLE object using the compiler's prefix and cached metadata.

        Raises
        ------
        QueryException
            If a declared column type has no SQL type builder.
        """
        table = self._sqlTable(definition)
        return CreateTable(table, if_not_exists=if_not_exists)

    def compileDropTable(
        self,
        name: str,
        schema: str | None = None,
        *,
        if_exists: bool = True,
    ) -> Executable:
        """
        Compile a DROP TABLE DDL object for a logical table name.

        Parameters
        ----------
        name : str
            Logical name to prefix before resolving table metadata.
        schema : str or None, optional
            Owning schema, or ``None`` to use the default schema.
        if_exists : bool, optional
            Request ``IF EXISTS`` in the generated DDL. Defaults to ``True``.

        Returns
        -------
        Executable
            DROP TABLE object using cached metadata or a lightweight table stub.
        """
        physical = self._physicalName(name)
        table = self._tables.get(self._cacheKey(physical, schema))
        if table is None:
            # Build a lightweight standalone table object for the DDL.
            table = Table(physical, MetaData(), schema=schema)
        return DropTable(table, if_exists=if_exists)

    # ── Table and column resolution ─────────────────────────────────────────

    def _physicalName(self, name: str) -> str:
        """
        Build a physical table name by prepending the configured prefix.

        Parameters
        ----------
        name : str
            Logical table name, without the connection prefix.

        Returns
        -------
        str
            Configured prefix concatenated with ``name`` without normalization.
        """
        return f"{self._prefix}{name}"

    def _cacheKey(self, physical: str, schema: str | None) -> str:
        """
        Build a table cache key from its physical name and optional schema.

        Parameters
        ----------
        physical : str
            Table name including the configured prefix.
        schema : str or None
            Schema qualifier, or ``None`` for an unqualified cache key.

        Returns
        -------
        str
            Schema-qualified physical name, or the physical name without a schema.
        """
        return f"{schema}.{physical}" if schema else physical

    def _sqlTable(self, definition: TableDefinition) -> Table:
        """
        Resolve cached table metadata or rebuild it for a new definition.

        Reuse metadata for raw definitions or the same declared definition
        instance; rebuild it for a different definition with declared columns.

        Parameters
        ----------
        definition : TableDefinition
            Logical table description, including columns, constraints, and schema.

        Returns
        -------
        Table
            Prefixed table registered in this compiler's metadata and table cache.

        Raises
        ------
        QueryException
            If a column type has no registered SQL type builder.
        """
        physical = self._physicalName(definition.name)
        cache_key = self._cacheKey(physical, definition.schema)
        cached = self._tables.get(cache_key)
        if cached is not None and (
            not definition.columns or self._definitions.get(cache_key) is definition
        ):
            return cached

        # Replace metadata when a different declared schema version is supplied.
        if cached is not None:
            self._metadata.remove(cached)

        # Pre-register referenced tables so foreign key DDL can resolve
        # them even when their models are compiled later.
        for column in definition.columns.values():
            if column.foreign_ref is not None:
                self._ensureReferencedTable(column.foreign_ref)
        for foreign_key in definition.foreign_keys:
            self._ensureReferencedColumns(
                foreign_key.ref_table, foreign_key.ref_columns,
            )

        columns = [
            self._sqlColumn(column, name)
            for name, column in definition.columns.items()
        ]
        table = Table(
            physical,
            self._metadata,
            *columns,
            *self._tableConstraints(definition),
            schema=definition.schema,
            comment=definition.comment,
            extend_existing=True,
        )
        self._tables[cache_key] = table
        if definition.columns:
            self._definitions[cache_key] = definition
        return table

    def _tableConstraints(self, definition: TableDefinition) -> list[Any]:
        """
        Build table-level keys, foreign keys, and indexes.

        Parameters
        ----------
        definition : TableDefinition
            Composite primary key, unique constraints, foreign keys, and indexes.

        Returns
        -------
        list of Any
            SQLAlchemy schema items with prefixed foreign-key targets and generated
            names for unnamed indexes.
        """
        constraints: list[Any] = []
        if definition.composite_primary_key:
            constraints.append(
                sqlalchemy.PrimaryKeyConstraint(*definition.composite_primary_key),
            )
        constraints.extend(
            sqlalchemy.UniqueConstraint(*unique.columns, name=unique.name)
            for unique in definition.unique_constraints
        )
        for foreign_key in definition.foreign_keys:
            schema, separator, table_name = foreign_key.ref_table.rpartition(".")
            if not separator:
                table_name = foreign_key.ref_table
            ref_table = self._cacheKey(self._physicalName(table_name), schema or None)
            ref_columns = [
                f"{ref_table}.{column}"
                for column in foreign_key.ref_columns
            ]
            constraints.append(
                sqlalchemy.ForeignKeyConstraint(
                    foreign_key.columns, ref_columns, name=foreign_key.name,
                ),
            )
        for index in definition.indexes:
            name = index.name or f"ix_{definition.name}_{'_'.join(index.columns)}"
            constraints.append(
                sqlalchemy.Index(name, *index.columns, unique=index.unique),
            )
        return constraints

    def _ensureReferencedTable(self, reference: ForeignReference) -> None:
        """
        Register missing metadata for a single-column foreign-key target.

        Parameters
        ----------
        reference : ForeignReference
            Logical target table, optional schema qualifier, and referenced column.

        Returns
        -------
        None
            Create an integer primary-key placeholder only when target metadata
            is absent.
        """
        self._ensureReferencedColumns(reference.table, (reference.column,))

    def _ensureReferencedColumns(
        self,
        table_name: str,
        columns: Sequence[str],
    ) -> None:
        """
        Register missing table metadata for foreign-key target columns.

        Parameters
        ----------
        table_name : str
            Logical table name, optionally qualified as ``schema.table``.
        columns : Sequence of str
            Target columns to declare as integer primary-key placeholders.

        Returns
        -------
        None
            Add a prefixed metadata table if absent; leave existing metadata
            unchanged.
        """
        schema, separator, logical = table_name.rpartition(".")
        if not separator:
            logical = table_name
        physical = self._physicalName(logical)
        if self._cacheKey(physical, schema or None) in self._metadata.tables:
            return
        Table(
            physical,
            self._metadata,
            *(
                SqlColumn(column, sqlalchemy.Integer(), primary_key=True)
                for column in columns
            ),
            schema=schema or None,
        )

    def _sqlColumn( # NOSONAR
        self,
        definition: ColumnDefinition,
        name: str | None = None,
    ) -> SqlColumn[Any]:
        """
        Translate a column definition into SQLAlchemy column metadata.

        Apply backend identity options and emit non-null static defaults both as
        client defaults and SQL server defaults.

        Parameters
        ----------
        definition : ColumnDefinition
            Type options, constraints, foreign key, defaults, and identity settings.
        name : str or None, optional
            Override the definition's name; use ``definition.name`` when ``None``.

        Returns
        -------
        Column
            Column with resolved type, constraints, defaults, and backend options.

        Raises
        ------
        QueryException
            If the logical column type has no registered SQL type builder.
        MissingDatabaseDependencyException
            If Redshift column options require a missing dialect package.
        """
        args: list[Any] = [
            definition.name if name is None else name,
            self._sqlType(definition),
        ]
        if self._driver == "oracle" and definition.is_auto_increment:
            args.append(sqlalchemy.Identity())
        if definition.foreign_ref is not None:
            reference = definition.foreign_ref
            schema, separator, table_name = reference.table.rpartition(".")
            if not separator:
                table_name = reference.table
            target = self._cacheKey(self._physicalName(table_name), schema or None)
            args.append(
                ForeignKey(f"{target}.{reference.column}"),
            )

        options: dict[str, Any] = {
            "primary_key": definition.is_primary,
            "nullable": definition.is_nullable and not definition.is_primary,
            "unique": definition.is_unique or None,
            "index": definition.has_index or None,
            "autoincrement": True if definition.is_auto_increment else "auto",
            "comment": definition.comment_text,
        }
        if self._driver == "sqlserver" and not definition.is_auto_increment:
            # mssql's implicit "auto" turns an ordinary integer primary key
            # into IDENTITY, preventing updates of client-managed keys.
            options["autoincrement"] = False
        if self._driver == "redshift" and definition.is_auto_increment:
            options["redshift_identity"] = (1, 1)
        if definition.hasDefault():
            value = definition.default_value
            options["default"] = value
            # Static defaults are also emitted in the DDL, so rows written
            # without the column still receive the declared value.
            if value is not None and not callable(value):
                options["server_default"] = sqlalchemy.literal(value, args[1])

        try:
            return SqlColumn(*args, **options)
        except (ImportError, NoSuchModuleError) as error:
            if self._driver == "redshift":
                raise missing_dependency_error(self._driver, error) from error
            raise

    def _sqlType(self, definition: ColumnDefinition) -> TypeEngine[Any]:
        """
        Build a SQLAlchemy type with any required backend variants.

        Parameters
        ----------
        definition : ColumnDefinition
            Logical column type and its conversion or precision options.

        Returns
        -------
        TypeEngine
            Configured type, with Oracle FLOAT precision or SQLite auto-increment
            variants when applicable.

        Raises
        ------
        QueryException
            If no builder is registered for the declared column type.
        """
        builder = self._TYPE_BUILDERS.get(definition.column_type)
        if builder is None:
            error_msg = (
                f"No SQL type registered for column type "
                f"'{definition.column_type}'."
            )
            raise QueryException(error_msg)

        column_type = builder(definition)

        if (
            self._driver == "oracle"
            and definition.column_type is ColumnType.FLOAT
            and definition.precision is not None
        ):
            # Follow SQLAlchemy's decimal-to-binary precision estimate for
            # Oracle FLOAT, retaining the result conversion options.
            return column_type.with_variant(
                FLOAT(
                    binary_precision=int(definition.precision / 0.30103),
                    asdecimal=definition.as_decimal,
                    decimal_return_scale=definition.decimal_return_scale,
                ),
                "oracle",
            )

        # SQLite only treats a single-column primary key as an alias of
        # ROWID when its declared type is literally INTEGER, so a BIGINT
        # key would never auto-increment there. The variant keeps BIGINT
        # on every other backend.
        if (
            definition.is_primary
            and definition.is_auto_increment
            and isinstance(column_type, sqlalchemy.BigInteger)
        ):
            return column_type.with_variant(sqlalchemy.Integer(), "sqlite")

        return column_type

    def _splitQualifiedColumn(self, name: str) -> tuple[str | None, str]:
        """
        Split a column reference at its last qualifier separator.

        Parameters
        ----------
        name : str
            Bare column name or dot-qualified source and column reference.

        Returns
        -------
        tuple of (str or None, str)
            Qualifier and final column segment, with ``None`` for a bare name.
        """
        if "." in name:
            qualifier, _, column = name.rpartition(".")
            return qualifier, column
        return None, name

    def _resolveColumn(
        self,
        sources: SourceMap,
        default: SqlSource,
        name: str,
    ) -> ColumnElement[Any]:
        """
        Resolve a column by source qualifier or default table.

        Look up qualified references in ``sources`` and unqualified names in
        ``default``.

        Parameters
        ----------
        sources : SourceMap
            Available tables or derived sources indexed by query identifier.
        default : SqlSource
            Source used for unqualified column names.
        name : str
            Bare column name or dot-qualified source reference.

        Returns
        -------
        ColumnElement
            Column exposed by the selected source's column collection.

        Raises
        ------
        QueryException
            If the source identifier or column name is unknown.
        """
        qualifier, column = self._splitQualifiedColumn(name)
        if qualifier is None:
            source = default
        else:
            source = sources.get(qualifier)
            if source is None:
                error_msg = f"Unknown table reference '{qualifier}' in '{name}'."
                raise QueryException(error_msg)
        try:
            return source.c[column]
        except KeyError as exc:
            origin = qualifier or getattr(default, "name", "?")
            error_msg = f"Unknown column '{column}' on table '{origin}'."
            raise QueryException(error_msg) from exc

    # ── Clause compilation ──────────────────────────────────────────────────

    def _whereExpression(
        self,
        sources: SourceMap,
        default: SqlSource,
        clauses: Sequence[WhereClause],
    ) -> ColumnElement[bool] | None:
        """
        Compile ordered WHERE or HAVING clauses into one predicate.

        Use each clause after the first to select its ``AND`` or ``OR`` connector.

        Parameters
        ----------
        sources : SourceMap
            Sources indexed by alias or logical table name.
        default : SqlSource
            Fallback source for unqualified column names.
        clauses : Sequence of WhereClause
            Ordered conditions and their boolean connectors.

        Returns
        -------
        ColumnElement or TextClause or None
            Compiled predicate, or ``None`` when no clauses are supplied.

        Raises
        ------
        QueryException
            If a condition has unknown references or unsupported clause semantics.
        """
        if not clauses:
            return None
        if len(clauses) == 1:
            return self._clauseExpression(sources, default, clauses[0])
        return self._combineExpressions(
            self._clauseExpression, sources, default, clauses,
        )

    @staticmethod
    def _combineExpressions(
        compile_clause: Callable[..., ColumnElement[bool]],
        sources: SourceMap,
        default: SqlSource,
        clauses: Sequence[WhereClause] | Sequence[JoinCondition],
    ) -> ColumnElement[bool] | None:
        """
        Combine compiled clauses while preserving left-to-right grouping.

        Ignore the first clause's connector; later connectors join successive
        clauses.

        Parameters
        ----------
        compile_clause : Callable
            Callable receiving ``sources``, ``default``, and one condition.
        sources : SourceMap
            Source lookup supplied unchanged to each clause compiler.
        default : SqlSource
            Fallback source supplied to the clause compiler.
        clauses : Sequence of WhereClause or Sequence of JoinCondition
            Conditions to compile and combine in their declared order.

        Returns
        -------
        ColumnElement or TextClause or None
            Combined predicate, or ``None`` for an empty sequence.
        """
        iterator = iter(clauses)
        first = next(iterator, None)
        if first is None:
            return None
        expression = compile_clause(sources, default, first)
        if len(clauses) == 1:
            return expression

        pieces = [expression]
        previous_boolean = None
        for clause in iterator:
            boolean = clause.boolean
            if previous_boolean is not None and boolean != previous_boolean:
                combine = or_ if previous_boolean == "or" else and_
                pieces = [combine(*pieces)]
            pieces.append(compile_clause(sources, default, clause))
            previous_boolean = boolean
        combine = or_ if previous_boolean == "or" else and_
        return combine(*pieces)

    def _columnlessExpression(
        self,
        sources: SourceMap,
        default: SqlSource,
        clause: WhereClause,
    ) -> ColumnElement[bool] | None:
        """
        Compile nested groups, raw predicates, and EXISTS subqueries.

        Represent an empty nested group as a true predicate.

        Parameters
        ----------
        sources : SourceMap
            Sources available for column resolution and subquery correlation.
        default : SqlSource
            Fallback source for unqualified names inside nested conditions.
        clause : WhereClause
            Condition whose type determines whether this helper can handle it.

        Returns
        -------
        ColumnElement or TextClause or None
            Predicate for a supported kind, or ``None`` for a column-based kind.
        """
        kind = clause.where_type
        if kind is WhereType.NESTED:
            nested = self._whereExpression(sources, default, clause.value or ())
            # An empty group must not change the truth of the query.
            return sqlalchemy.true() if nested is None else nested.self_group()
        if kind is WhereType.RAW:
            return self._rawElement(clause.value)
        if kind in (WhereType.EXISTS, WhereType.NOT_EXISTS):
            subquery = self._buildSelect(clause.value, sources).exists()
            return ~subquery if kind is WhereType.NOT_EXISTS else subquery
        return None

    def _clauseExpression(
        self,
        sources: SourceMap,
        default: SqlSource,
        clause: WhereClause,
    ) -> ColumnElement[bool]:
        """
        Dispatch a WHERE condition to its matching SQL predicate builder.

        Parameters
        ----------
        sources : SourceMap
            Sources indexed by alias or logical table name.
        default : SqlSource
            Fallback source for unqualified column names.
        clause : WhereClause
            Condition type, column reference, operator, and comparison value.

        Returns
        -------
        ColumnElement or TextClause
            Compiled condition, including nested, raw, and subquery predicates.

        Raises
        ------
        QueryException
            If the clause type, references, comparison operator, or range shape
            is invalid.
        """
        kind = clause.where_type
        if kind in COLUMNLESS_WHERE_TYPES:
            return self._columnlessExpression(sources, default, clause)

        column = self._resolveColumn(sources, default, clause.column)

        if kind is WhereType.BASIC:
            return self._basicExpression(column, clause)
        if kind is WhereType.COLUMN:
            return self._columnComparison(sources, default, column, clause)
        if kind in (WhereType.BETWEEN, WhereType.NOT_BETWEEN):
            return self._betweenExpression(column, clause)

        handler = _SIMPLE_CLAUSES.get(kind)
        if handler is None:
            error_msg = f"Unsupported where clause type '{kind}'."
            raise QueryException(error_msg)
        return handler(column, self._clauseValue(sources, clause.value))

    def _clauseValue(self, sources: SourceMap, value: Any) -> Any:  # noqa: ANN401
        """
        Compile a SELECT value or return a non-query value unchanged.

        Parameters
        ----------
        sources : SourceMap
            Enclosing query sources available for subquery correlation.
        value : Any
            Condition value, which may itself be a SELECT plan.

        Returns
        -------
        Any
            Compiled SELECT for a plan value; the original object otherwise.

        Raises
        ------
        QueryException
            If a nested SELECT contains invalid clauses or unresolved references.
        """
        if isinstance(value, SelectPlan):
            return self._buildSelect(value, sources)
        return value

    @staticmethod
    def _betweenExpression(
        column: ColumnElement[Any],
        clause: WhereClause,
    ) -> ColumnElement[bool]:
        """
        Compile BETWEEN or NOT BETWEEN with exactly two bounds.

        Parameters
        ----------
        column : ColumnElement
            Left-hand column expression tested against the range.
        clause : WhereClause
            Range condition with lower and upper boundary values.

        Returns
        -------
        ColumnElement
            Inclusive range predicate, negated for ``NOT BETWEEN``.

        Raises
        ------
        QueryException
            If the supplied value does not contain exactly two boundaries.
        """
        bounds = tuple(clause.value or ())
        if len(bounds) != _BETWEEN_BOUNDS:
            error_msg = "BETWEEN conditions require exactly two boundary values."
            raise QueryException(error_msg)
        expression = column.between(bounds[0], bounds[1])
        if clause.where_type is WhereType.NOT_BETWEEN:
            return ~expression
        return expression

    def _columnComparison(
        self,
        sources: SourceMap,
        default: SqlSource,
        column: ColumnElement[Any],
        clause: WhereClause,
    ) -> ColumnElement[bool]:
        """
        Compare two resolved columns using the clause's operator.

        Parameters
        ----------
        sources : SourceMap
            Sources indexed by alias or logical table name.
        default : SqlSource
            Fallback source for the right-hand column reference.
        column : ColumnElement
            Already-resolved left-hand column expression.
        clause : WhereClause
            Comparison operator and right-hand column reference.

        Returns
        -------
        ColumnElement
            Boolean comparison between the two column expressions.

        Raises
        ------
        QueryException
            If the right-hand column cannot be resolved or the operator is
            unsupported.
        """
        other = self._resolveColumn(sources, default, str(clause.value))
        comparator = _COMPARATORS.get(clause.operator.strip().lower())
        if comparator is None:
            error_msg = f"Unsupported comparison operator '{clause.operator}'."
            raise QueryException(error_msg)
        return comparator(column, other)

    def _basicExpression(
        self,
        column: ColumnElement[Any],
        clause: WhereClause,
    ) -> ColumnElement[bool]:
        """
        Compile a column-to-value comparison with backend-specific handling.

        Translate ``None`` equality into ``IS NULL`` or ``IS NOT NULL``.
        Use ``DBMS_LOB.COMPARE`` for Oracle text equality.

        Parameters
        ----------
        column : ColumnElement
            Column expression, including its SQL type for backend handling.
        clause : WhereClause
            Comparison operator and bound value, including ``None``.

        Returns
        -------
        ColumnElement
            NULL check, text comparison, pattern predicate, or ordinary comparison.

        Raises
        ------
        QueryException
            If the comparison operator has no supported handler.
        """
        op = clause.operator.strip().lower()

        # Promote NULL equality checks to IS NULL / IS NOT NULL semantics.
        if clause.value is None and op in _EQUALITY_OPERATORS:
            return column.is_(None)
        if clause.value is None and op in _INEQUALITY_OPERATORS:
            return column.is_not(None)

        if (
            self._driver == "oracle"
            and isinstance(column.type, sqlalchemy.Text)
            and op in _EQUALITY_OPERATORS | _INEQUALITY_OPERATORS
        ):
            # Oracle CLOB values cannot use ordinary SQL equality. Typed text
            # predicates also back the cache store's compare-and-swap update.
            comparison = func.dbms_lob.compare(
                column, sqlalchemy.literal(clause.value, type_=column.type),
            )
            return comparison == 0 if op in _EQUALITY_OPERATORS else comparison != 0

        pattern_handler = _PATTERN_OPERATORS.get(op)
        if pattern_handler is not None:
            return pattern_handler(column, clause.value)

        comparator = _COMPARATORS.get(op)
        if comparator is None:
            error_msg = f"Unsupported comparison operator '{clause.operator}'."
            raise QueryException(error_msg)
        return comparator(column, clause.value)

    def _aggregateExpression(
        self,
        sources: SourceMap,
        default: SqlSource,
        aggregate: AggregateClause,
    ) -> ColumnElement[Any]:
        """
        Compile an aggregate function over a column or all rows.

        Parameters
        ----------
        sources : SourceMap
            Sources indexed by alias or logical table name.
        default : SqlSource
            Fallback source for an unqualified aggregate column.
        aggregate : AggregateClause
            Aggregate function and column reference, or ``*`` for COUNT.

        Returns
        -------
        ColumnElement
            COUNT expression or the requested function applied to a resolved column.

        Raises
        ------
        QueryException
            If a non-COUNT aggregate targets ``*`` or a column cannot be resolved.
        """
        if aggregate.function is AggregateFunction.COUNT:
            if aggregate.column == "*":
                return func.count()
            return func.count(
                self._resolveColumn(sources, default, aggregate.column),
            )

        if aggregate.column == "*":
            error_msg = (
                f"Aggregate '{aggregate.function}' requires a column name."
            )
            raise QueryException(error_msg)

        column = self._resolveColumn(sources, default, aggregate.column)
        builder = getattr(func, aggregate.function.value)
        return builder(column)
