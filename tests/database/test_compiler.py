from __future__ import annotations
from sqlalchemy.dialects import registry as sqlalchemy_registry
from orionis.database.compiler import SQLCompiler
from orionis.database.exceptions import QueryException
from orionis.orm.query.expressions import (
    AggregateClause,
    AggregateFunction,
    DeletePlan,
    InsertPlan,
    JoinCondition,
    JoinExpression,
    JoinType,
    OrderClause,
    SelectPlan,
    SortDirection,
    UpdatePlan,
    WhereClause,
    WhereType,
)
from orionis.orm.schema.constraints import (
    CompositeForeignKey,
    TableIndex,
    UniqueConstraint,
)
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    Integer,
    NumericCommon,
    SmallInteger,
    StrictBinary,
    StrictDecimal,
    StrictJson,
    StrictTimestamp,
    String,
    Text,
    Time,
    Uuid,
)
from orionis.test import TestCase

def _makeTable() -> TableDefinition:
    """Build a small table definition used across the compiler tests."""
    columns = {
        "id": Integer().primary().autoIncrement(),
        "name": String(),
        "active": Boolean(),
    }
    for key, column in columns.items():
        column.name = key
    return TableDefinition(name="users", columns=columns, primary_key="id")

class TestSQLCompiler(TestCase):

    def setUp(self) -> None:
        """
        Create a fresh compiler and table definition per test.

        Guarantees isolation of the internal table cache.
        """
        self._compiler = SQLCompiler()
        self._table = _makeTable()

    def _sql(self, statement) -> str:
        """Render a statement to normalized lowercase SQL."""
        return str(statement.compile()).lower()

    # ── SELECT ────────────────────────────────────────────────────────────────

    def testCompileSelectAllColumns(self) -> None:
        """
        Compile a bare select into SELECT ... FROM table.

        Validates the default full projection.
        """
        sql = self._sql(self._compiler.compileSelect(SelectPlan(table=self._table)))
        self.assertIn("select", sql)
        self.assertIn("from users", sql)

    def testCompileSelectProjectsColumns(self) -> None:
        """
        Compile an explicit projection into a column list.

        Validates that only the requested columns are projected.
        """
        plan = SelectPlan(table=self._table, columns=("name",))
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("users.name", sql)
        self.assertNotIn("users.active", sql)

    def testCompileSelectWithWhereAndOrConnector(self) -> None:
        """
        Fold consecutive clauses honoring their boolean connectors.

        Validates AND/OR folding order in the where expression.
        """
        plan = SelectPlan(table=self._table)
        plan.wheres.append(WhereClause(column="active", value=True))
        plan.wheres.append(
            WhereClause(column="name", value="john", boolean="or"),
        )
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("where", sql)
        self.assertIn("or", sql)

    def testCompileSelectNullPromotion(self) -> None:
        """
        Promote equality with None to IS NULL.

        Validates the NULL comparison promotion rule.
        """
        plan = SelectPlan(table=self._table)
        plan.wheres.append(WhereClause(column="name", value=None))
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("is null", sql)

    def testCompileSelectInClause(self) -> None:
        """
        Compile IN conditions with bound value lists.

        Validates the IN clause expansion.
        """
        plan = SelectPlan(table=self._table)
        plan.wheres.append(
            WhereClause(column="id", where_type=WhereType.IN, value=(1, 2)),
        )
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("in", sql)

    def testCompileSelectBetweenRequiresTwoBounds(self) -> None:
        """
        Raise QueryException for malformed BETWEEN boundaries.

        Validates the boundary arity check.
        """
        plan = SelectPlan(table=self._table)
        plan.wheres.append(
            WhereClause(column="id", where_type=WhereType.BETWEEN, value=(1,)),
        )
        with self.assertRaises(QueryException):
            self._compiler.compileSelect(plan)

    def testCompileSelectOrderLimitOffset(self) -> None:
        """
        Compile ordering and pagination into the statement.

        Validates ORDER BY, LIMIT, and OFFSET emission.
        """
        plan = SelectPlan(table=self._table)
        plan.orders.append(
            OrderClause(column="name", direction=SortDirection.DESC),
        )
        plan.limit_value = 10
        plan.offset_value = 5
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("order by", sql)
        self.assertIn("desc", sql)
        self.assertIn("limit", sql)
        self.assertIn("offset", sql)

    def testCompileSelectUnknownColumnRaises(self) -> None:
        """
        Raise QueryException for references to unknown columns.

        Validates the descriptive column resolution error.
        """
        plan = SelectPlan(table=self._table)
        plan.wheres.append(WhereClause(column="ghost", value=1))
        with self.assertRaises(QueryException):
            self._compiler.compileSelect(plan)

    def testCompileSelectCountAggregate(self) -> None:
        """
        Compile COUNT(*) aggregates into the projection.

        Validates the aggregate projection replacement.
        """
        plan = SelectPlan(
            table=self._table,
            aggregate=AggregateClause(function=AggregateFunction.COUNT),
        )
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("count", sql)

    def testCompileSelectAggregateStarRequiresCount(self) -> None:
        """
        Reject non-count aggregates targeting the star column.

        Validates the aggregate column requirement.
        """
        plan = SelectPlan(
            table=self._table,
            aggregate=AggregateClause(function=AggregateFunction.MAX),
        )
        with self.assertRaises(QueryException):
            self._compiler.compileSelect(plan)

    # ── INSERT / UPDATE / DELETE ─────────────────────────────────────────────

    def testCompileInsertSingleRow(self) -> None:
        """
        Compile a single-row insert statement.

        Validates the INSERT statement shape.
        """
        plan = InsertPlan(table=self._table, values=[{"name": "john"}])
        sql = self._sql(self._compiler.compileInsert(plan))
        self.assertIn("insert into users", sql)

    def testCompileInsertWithoutValuesRaises(self) -> None:
        """
        Raise QueryException for inserts without any row.

        Validates the empty insert guard.
        """
        with self.assertRaises(QueryException):
            self._compiler.compileInsert(InsertPlan(table=self._table))

    def testCompileUpdateWithWhere(self) -> None:
        """
        Compile an update restricted by conditions.

        Validates SET and WHERE emission.
        """
        plan = UpdatePlan(
            table=self._table,
            values={"name": "peter"},
            wheres=[WhereClause(column="id", value=1)],
        )
        sql = self._sql(self._compiler.compileUpdate(plan))
        self.assertIn("update users", sql)
        self.assertIn("where", sql)

    def testCompileUpdateWithoutValuesRaises(self) -> None:
        """
        Raise QueryException for updates without values.

        Validates the empty update guard.
        """
        with self.assertRaises(QueryException):
            self._compiler.compileUpdate(UpdatePlan(table=self._table))

    def testCompileDeleteWithWhere(self) -> None:
        """
        Compile a delete restricted by conditions.

        Validates DELETE and WHERE emission.
        """
        plan = DeletePlan(
            table=self._table,
            wheres=[WhereClause(column="id", value=1)],
        )
        sql = self._sql(self._compiler.compileDelete(plan))
        self.assertIn("delete from users", sql)
        self.assertIn("where", sql)

    # ── Prefix and DDL ────────────────────────────────────────────────────────

    def testPrefixIsAppliedToPhysicalTables(self) -> None:
        """
        Prepend the configured prefix to physical table names.

        Validates prefix application at compile time.
        """
        compiler = SQLCompiler(prefix="app_")
        sql = str(
            compiler.compileSelect(SelectPlan(table=self._table)).compile(),
        ).lower()
        self.assertIn("app_users", sql)

    def testNotLikeOperatorCompiles(self) -> None:
        """
        Compile the "not like" comparison operator.

        Validates the negated pattern comparison.
        """
        plan = SelectPlan(table=self._table)
        plan.wheres.append(
            WhereClause(column="name", operator="not like", value="a%"),
        )
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("not like", sql)

    def testIlikeOperatorCompiles(self) -> None:
        """
        Compile the "ilike" comparison operator.

        Validates the case-insensitive pattern comparison.
        """
        plan = SelectPlan(table=self._table)
        plan.wheres.append(
            WhereClause(column="name", operator="ilike", value="a%"),
        )
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("lower", sql)

    def testNotIlikeOperatorCompiles(self) -> None:
        """
        Compile the "not ilike" comparison operator.

        Validates the negated case-insensitive pattern comparison.
        """
        plan = SelectPlan(table=self._table)
        plan.wheres.append(
            WhereClause(column="name", operator="not ilike", value="a%"),
        )
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("not", sql)
        self.assertIn("lower", sql)

    def testTextMatcherWhereTypesCompileToLike(self) -> None:
        """
        Compile STARTS_WITH/ENDS_WITH/CONTAINS clauses into LIKE.

        Validates the literal pattern where-clause kinds. The bound
        pattern is concatenated with wildcards rather than inlined, so
        assertions check for the ``||`` concatenation markers.

        """
        cases = (
            (WhereType.STARTS_WITH, ("like", "|| '%'")),
            (WhereType.ENDS_WITH, ("like", "'%' ||")),
            (WhereType.CONTAINS, ("like", "'%' ||", "|| '%'")),
        )
        for where_type, expected_fragments in cases:
            plan = SelectPlan(table=self._table)
            plan.wheres.append(
                WhereClause(column="name", where_type=where_type, value="abc"),
            )
            sql = self._sql(self._compiler.compileSelect(plan))
            for fragment in expected_fragments:
                self.assertIn(fragment, sql)

    def testRegexpWhereTypeCompiles(self) -> None:
        """
        Compile REGEXP where clauses into an engine regexp match.

        Validates the regular-expression where-clause kind.
        """
        plan = SelectPlan(table=self._table)
        plan.wheres.append(
            WhereClause(column="name", where_type=WhereType.REGEXP, value="^a"),
        )
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("regexp", sql)

    def testDistinctAddsSelectDistinct(self) -> None:
        """
        Apply SELECT DISTINCT when the plan requests it.

        Validates the distinct flag compilation.
        """
        plan = SelectPlan(table=self._table, distinct=True)
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("distinct", sql)

    def testNotInClauseCompiles(self) -> None:
        """
        Compile NOT IN conditions with bound value lists.

        Validates the NOT IN clause expansion.
        """
        plan = SelectPlan(table=self._table)
        plan.wheres.append(
            WhereClause(column="id", where_type=WhereType.NOT_IN, value=(1,)),
        )
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("not in", sql)

    def testNullChecksCompileToIsExpressions(self) -> None:
        """
        Compile NULL and NOT NULL checks into IS expressions.

        Validates both nullability clause kinds.
        """
        plan = SelectPlan(table=self._table)
        plan.wheres.append(
            WhereClause(column="name", where_type=WhereType.NULL),
        )
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("is null", sql)

        plan_not = SelectPlan(table=self._table)
        plan_not.wheres.append(
            WhereClause(column="name", where_type=WhereType.NOT_NULL),
        )
        sql_not = self._sql(self._compiler.compileSelect(plan_not))
        self.assertIn("is not null", sql_not)

    def testInequalityWithNonePromotesToIsNotNull(self) -> None:
        """
        Promote inequality with None to IS NOT NULL.

        Validates the negative NULL promotion rule.
        """
        plan = SelectPlan(table=self._table)
        plan.wheres.append(
            WhereClause(column="name", operator="!=", value=None),
        )
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("is not null", sql)

    def testUnsupportedOperatorRaises(self) -> None:
        """
        Raise QueryException for unsupported comparison operators.

        Validates the operator guard at compile time.
        """
        plan = SelectPlan(table=self._table)
        plan.wheres.append(
            WhereClause(column="name", operator="~", value="x"),
        )
        with self.assertRaises(QueryException):
            self._compiler.compileSelect(plan)

    def testGroupByAndHavingCompile(self) -> None:
        """
        Compile grouping columns and post-grouping conditions.

        Validates GROUP BY and HAVING emission.
        """
        plan = SelectPlan(table=self._table)
        plan.groups.append("active")
        plan.havings.append(WhereClause(column="active", value=True))
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("group by", sql)
        self.assertIn("having", sql)

    def testAggregateAppliesWhereConditions(self) -> None:
        """
        Apply filtering conditions to aggregate projections.

        Validates the aggregate + where combination.
        """
        plan = SelectPlan(
            table=self._table,
            aggregate=AggregateClause(
                function=AggregateFunction.SUM,
                column="id",
            ),
        )
        plan.wheres.append(WhereClause(column="active", value=True))
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("sum", sql)
        self.assertIn("where", sql)

    def testEveryColumnTypeCompilesInDdl(self) -> None:
        """
        Compile a table using every supported column type.

        Validates the complete logical-to-engine type registry.
        """
        columns = {
            "id": Integer().primary().autoIncrement(),
            "big": BigInteger(),
            "small": SmallInteger(),
            "name": String(50),
            "body": Text(),
            "flag": Boolean(),
            "ratio": Float(),
            "price": StrictDecimal(10, 2),
            "born": Date(),
            "at": Time(),
            "seen": DateTime(),
            "stamped": StrictTimestamp(),
            "payload": StrictJson(),
            "token": Uuid(),
            "blob": StrictBinary(),
            "state": Enum("draft", "published"),
        }
        for key, column in columns.items():
            column.name = key
        table = TableDefinition(name="samples", columns=columns, primary_key="id")

        ddl = str(SQLCompiler().compileCreateTable(table)).lower()
        for key in columns:
            self.assertIn(key, ddl)
        self.assertIn("varchar(50)", ddl)
        self.assertIn("decimal(10, 2)", ddl)

    def testForeignKeyAppearsInDdlWithPrefix(self) -> None:
        """
        Emit prefixed foreign key references in the DDL.

        Validates foreign key propagation and prefixing.
        """
        columns = {
            "id": Integer().primary(),
            "company_id": Integer().foreign("companies.id"),
        }
        for key, column in columns.items():
            column.name = key
        table = TableDefinition(name="staff", columns=columns, primary_key="id")

        ddl = str(SQLCompiler(prefix="app_").compileCreateTable(table)).lower()
        self.assertIn("foreign key", ddl)
        self.assertIn("app_companies", ddl)

    def testDefaultValueIsAppliedOnInsertCompilation(self) -> None:
        """
        Keep column defaults available in the engine metadata.

        Validates that declared defaults reach the engine column so
        the execution context applies them on insert.
        """
        columns = {
            "id": Integer().primary().autoIncrement(),
            "status": String().default("draft"),
        }
        for key, column in columns.items():
            column.name = key
        table = TableDefinition(name="drafts", columns=columns, primary_key="id")

        compiler = SQLCompiler()
        engine_table = compiler._sqlTable(table)
        self.assertEqual(engine_table.c["status"].default.arg, "draft")


    def testCompileCreateTableEmitsColumns(self) -> None:
        """
        Compile the table definition into a CREATE TABLE statement.

        Validates the DDL generation used by the schema helpers.
        """
        ddl = str(self._compiler.compileCreateTable(self._table)).lower()
        self.assertIn("create table", ddl)
        self.assertIn("id", ddl)
        self.assertIn("name", ddl)

    def testCompileDropTableTargetsName(self) -> None:
        """
        Compile a DROP TABLE statement for a logical name.

        Validates the drop DDL generation.
        """
        ddl = str(self._compiler.compileDropTable("users")).lower()
        self.assertIn("drop table", ddl)
        self.assertIn("users", ddl)

    # ── Error scenarios and less common table metadata ───────────────────────

    def testNoSqlTypeRegisteredRaises(self) -> None:
        """
        Raise QueryException for column types without a registered builder.

        Validates the guard for mixin-only types such as NumericCommon,
        which exist only to be inherited from and have no SQL type of
        their own.
        """
        column = NumericCommon()
        column.name = "value"
        table = TableDefinition(
            name="mixins", columns={"value": column}, primary_key="value",
        )
        with self.assertRaises(QueryException):
            SQLCompiler().compileCreateTable(table)

    def testDistinctIsIgnoredWhenAggregateIsSet(self) -> None:
        """
        Skip DISTINCT when the plan also carries an aggregate.

        Validates that aggregate projections never combine with a
        dangling DISTINCT flag.
        """
        plan = SelectPlan(
            table=self._table,
            distinct=True,
            aggregate=AggregateClause(function=AggregateFunction.COUNT),
        )
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertNotIn("distinct", sql)

    def testCompositePrimaryKeyRendersInDdl(self) -> None:
        """
        Render a multi-column primary key constraint.

        Validates that composite_primary_key takes precedence over the
        single-column primary_key field for DDL purposes.
        """
        columns = {"tenant_id": Integer(), "user_id": Integer()}
        for key, column in columns.items():
            column.name = key
        table = TableDefinition(
            name="memberships",
            columns=columns,
            composite_primary_key=("tenant_id", "user_id"),
        )
        ddl = str(SQLCompiler().compileCreateTable(table)).lower()
        self.assertIn("primary key", ddl)
        self.assertIn("tenant_id", ddl)
        self.assertIn("user_id", ddl)

    def testUniqueConstraintRendersInDdl(self) -> None:
        """
        Render a composite UNIQUE constraint spanning multiple columns.

        Validates unique_constraints propagation to the table DDL.
        """
        columns = {
            "id": Integer().primary().autoIncrement(),
            "tenant_id": Integer(),
            "slug": String(),
        }
        for key, column in columns.items():
            column.name = key
        table = TableDefinition(
            name="pages",
            columns=columns,
            primary_key="id",
            unique_constraints=(
                UniqueConstraint(
                    columns=("tenant_id", "slug"), name="uq_pages_slug",
                ),
            ),
        )
        ddl = str(SQLCompiler().compileCreateTable(table)).lower()
        self.assertIn("unique", ddl)
        self.assertIn("uq_pages_slug", ddl)

    def testCompositeForeignKeyRendersInDdl(self) -> None:
        """
        Render a multi-column foreign key constraint.

        Validates foreign_keys propagation to the table DDL, including
        prefix application on the referenced table.
        """
        columns = {"order_id": Integer(), "product_id": Integer()}
        for key, column in columns.items():
            column.name = key
        table = TableDefinition(
            name="order_items",
            columns=columns,
            foreign_keys=(
                CompositeForeignKey(
                    columns=("order_id", "product_id"),
                    ref_table="order_products",
                    ref_columns=("order_id", "product_id"),
                    name="fk_order_items",
                ),
            ),
        )
        ddl = str(SQLCompiler(prefix="app_").compileCreateTable(table)).lower()
        self.assertIn("foreign key", ddl)
        self.assertIn("app_order_products", ddl)

    def testAutoIncrementBigIntegerKeyBecomesIntegerOnSqlite(self) -> None:
        """
        Render a BIGINT identity column as INTEGER on SQLite.

        Validates the dialect variant applied to auto-incrementing
        primary keys: SQLite only aliases a single-column primary key to
        ROWID when the declared type is literally INTEGER, so a BIGINT
        key would never auto-increment there.
        """
        columns = {"id": BigInteger().primary().autoIncrement()}
        columns["id"].name = "id"
        table = TableDefinition(
            name="probes", columns=columns, primary_key="id",
        )

        engine_table = SQLCompiler()._sqlTable(table)
        rendered = engine_table.c.id.type.compile(
            dialect=sqlalchemy_registry.load("sqlite")(),
        )

        self.assertEqual(rendered.upper(), "INTEGER")

    def testAutoIncrementBigIntegerKeyStaysBigIntElsewhere(self) -> None:
        """
        Keep a BIGINT identity column wide on every other backend.

        Validates that the SQLite variant never narrows the key on the
        server engines, where a 64-bit identity is the whole point.
        """
        columns = {"id": BigInteger().primary().autoIncrement()}
        columns["id"].name = "id"
        table = TableDefinition(
            name="probes", columns=columns, primary_key="id",
        )

        engine_table = SQLCompiler()._sqlTable(table)
        for dialect_name in ("postgresql", "mysql"):
            rendered = engine_table.c.id.type.compile(
                dialect=sqlalchemy_registry.load(dialect_name)(),
            )
            self.assertIn("BIGINT", rendered.upper(), dialect_name)

    def testPlainBigIntegerColumnsKeepTheirTypeOnSqlite(self) -> None:
        """
        Leave non identity BIGINT columns untouched.

        Validates that the variant only applies to auto-incrementing
        primary keys, so foreign keys pointing at them stay BIGINT.
        """
        columns = {"owner_id": BigInteger()}
        columns["owner_id"].name = "owner_id"
        table = TableDefinition(name="probes", columns=columns)

        engine_table = SQLCompiler()._sqlTable(table)
        rendered = engine_table.c.owner_id.type.compile(
            dialect=sqlalchemy_registry.load("sqlite")(),
        )

        self.assertEqual(rendered.upper(), "BIGINT")

    def testTableIndexIsRegisteredOnEngineTable(self) -> None:
        """
        Register a composite index on the engine table metadata.

        Validates that indexes reach the engine Table object, since
        CREATE TABLE DDL alone does not render index statements.
        """
        columns = {
            "id": Integer().primary().autoIncrement(),
            "first_name": String(),
            "last_name": String(),
        }
        for key, column in columns.items():
            column.name = key
        table = TableDefinition(
            name="people",
            columns=columns,
            primary_key="id",
            indexes=(
                TableIndex(columns=("first_name", "last_name"), name="ix_name"),
            ),
        )
        engine_table = SQLCompiler()._sqlTable(table)
        index_names = {index.name for index in engine_table.indexes}
        self.assertIn("ix_name", index_names)

    def testTableSchemaAndCommentPropagateToEngineTable(self) -> None:
        """
        Propagate the schema and comment fields to the engine table.

        Validates metadata that does not affect column rendering but is
        still consumed from the table definition.
        """
        columns = {"id": Integer().primary().autoIncrement()}
        for key, column in columns.items():
            column.name = key
        table = TableDefinition(
            name="audit",
            columns=columns,
            primary_key="id",
            schema="reporting",
            comment="Audit trail table.",
        )
        engine_table = SQLCompiler()._sqlTable(table)
        self.assertEqual(engine_table.schema, "reporting")
        self.assertEqual(engine_table.comment, "Audit trail table.")


def _makePostsTable() -> TableDefinition:
    """Build a small "posts" table definition referencing "users"."""
    columns = {
        "id": Integer().primary().autoIncrement(),
        "user_id": Integer(),
        "title": String(),
    }
    for key, column in columns.items():
        column.name = key
    return TableDefinition(name="posts", columns=columns, primary_key="id")


class TestSQLCompilerJoins(TestCase):
    """Compile SELECT plans spanning multiple table sources."""

    def setUp(self) -> None:
        """Create a fresh compiler and both table definitions per test."""
        self._compiler = SQLCompiler()
        self._users = _makeTable()
        self._posts = _makePostsTable()

    def _sql(self, statement) -> str:
        """Render a statement to normalized lowercase SQL."""
        return str(statement.compile()).lower()

    def testInnerJoinCompilesWithQualifiedCondition(self) -> None:
        """
        Compile an INNER JOIN using a column-to-column ON condition.

        Validates that qualified references ("users.id"/"posts.user_id")
        resolve against their own table instead of the main one.
        """
        plan = SelectPlan(
            table=self._users,
            joins=[
                JoinExpression(
                    join_type=JoinType.INNER,
                    table=self._posts,
                    conditions=[
                        JoinCondition(first="users.id", second="posts.user_id"),
                    ],
                ),
            ],
        )
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("join posts", sql)
        self.assertIn("users.id = posts.user_id", sql)

    def testLeftJoinCompilesAsOuterJoin(self) -> None:
        """
        Compile a LEFT JOIN as a SQL LEFT OUTER JOIN.

        Validates the outer join flag reaches the rendered statement.
        """
        plan = SelectPlan(
            table=self._users,
            joins=[
                JoinExpression(
                    join_type=JoinType.LEFT,
                    table=self._posts,
                    conditions=[
                        JoinCondition(first="users.id", second="posts.user_id"),
                    ],
                ),
            ],
        )
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("left outer join posts", sql)

    def testCrossJoinCompilesWithoutConditions(self) -> None:
        """
        Compile a CROSS JOIN without requiring any ON condition.

        Validates the cross join escape hatch in the join compiler.
        """
        plan = SelectPlan(
            table=self._users,
            joins=[JoinExpression(join_type=JoinType.CROSS, table=self._posts)],
        )
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("join posts", sql)

    def testJoinRespectsAliasesOnBothSides(self) -> None:
        """
        Resolve qualified columns through table and join aliases.

        Validates that ``TableReference``-style aliasing threads through
        the source map used for column resolution.
        """
        plan = SelectPlan(
            table=self._users,
            alias="u",
            joins=[
                JoinExpression(
                    join_type=JoinType.INNER,
                    table=self._posts,
                    alias="p",
                    conditions=[JoinCondition(first="u.id", second="p.user_id")],
                ),
            ],
        )
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("as u", sql)
        self.assertIn("as p", sql)
        self.assertIn("u.id = p.user_id", sql)

    def testJoinWithoutConditionsRaises(self) -> None:
        """
        Raise QueryException when a non-cross join declares no ON clause.

        Validates the guard preventing an accidental Cartesian product.
        """
        plan = SelectPlan(
            table=self._users,
            joins=[JoinExpression(join_type=JoinType.INNER, table=self._posts)],
        )
        with self.assertRaises(QueryException):
            self._compiler.compileSelect(plan)

    def testJoinWithUnknownTableReferenceRaises(self) -> None:
        """
        Raise QueryException when an ON condition references an unknown table.

        Validates that column resolution stays scoped to known sources.
        """
        plan = SelectPlan(
            table=self._users,
            joins=[
                JoinExpression(
                    join_type=JoinType.INNER,
                    table=self._posts,
                    conditions=[
                        JoinCondition(first="users.id", second="comments.post_id"),
                    ],
                ),
            ],
        )
        with self.assertRaises(QueryException):
            self._compiler.compileSelect(plan)

    def testRightJoinCompilesAsSwappedOuterJoin(self) -> None:
        """
        Compile a RIGHT JOIN through an equivalent swapped LEFT JOIN.

        Validates that the toolkit's missing RIGHT JOIN construct is
        emulated without changing the produced result set.
        """
        plan = SelectPlan(
            table=self._users,
            joins=[
                JoinExpression(
                    join_type=JoinType.RIGHT,
                    table=self._posts,
                    conditions=[
                        JoinCondition(first="users.id", second="posts.user_id"),
                    ],
                ),
            ],
        )
        sql = str(self._compiler.compileSelect(plan))
        self.assertIn("LEFT OUTER JOIN", sql)
        self.assertIn("posts", sql)
        self.assertIn("users", sql)

    def testFullJoinCompilesAsFullOuterJoin(self) -> None:
        """
        Compile a FULL JOIN into a full outer join statement.

        Validates the direct mapping onto the toolkit's ``full`` flag.
        """
        plan = SelectPlan(
            table=self._users,
            joins=[
                JoinExpression(
                    join_type=JoinType.FULL,
                    table=self._posts,
                    conditions=[
                        JoinCondition(first="users.id", second="posts.user_id"),
                    ],
                ),
            ],
        )
        sql = str(self._compiler.compileSelect(plan))
        self.assertIn("FULL OUTER JOIN", sql)

    def testWhereClauseCanQualifyColumnAcrossJoinedTables(self) -> None:
        """
        Filter by a qualified column belonging to a joined table.

        Validates that ``WhereClause`` benefits from the same qualified
        resolution used by ON conditions, without any special-casing.
        """
        plan = SelectPlan(
            table=self._users,
            joins=[
                JoinExpression(
                    join_type=JoinType.INNER,
                    table=self._posts,
                    conditions=[
                        JoinCondition(first="users.id", second="posts.user_id"),
                    ],
                ),
            ],
        )
        plan.wheres.append(WhereClause(column="posts.title", value="Hello"))
        sql = self._sql(self._compiler.compileSelect(plan))
        self.assertIn("where posts.title", sql)

