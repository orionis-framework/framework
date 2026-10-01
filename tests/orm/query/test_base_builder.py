from __future__ import annotations
from orionis.database.compiler import SQLCompiler
from orionis.database.connection_manager import ConnectionManager
from orionis.database.exceptions import QueryException
from orionis.orm import StrictTimestamp
from orionis.orm.exceptions import InvalidQueryException
from orionis.orm.model import Model
from orionis.orm.query.expressions import SortDirection, WhereType
from orionis.orm.query.raw_builder import RawQueryBuilder
from orionis.orm.query_builder import QueryBuilder
from orionis.orm.resolver import ConnectionResolver
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Boolean, Integer, String
from orionis.support.facades.db import DB
from orionis.support.types.collection import Collection
from orionis.test import TestCase
from tests.orm.relations import test_mixin as fixtures

class _Item(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    created_at = StrictTimestamp().nullable()
    updated_at = StrictTimestamp().nullable()

class _Plain(Model):
    id = Integer().primary()
    name = String()
    timestamps = False

class TestBuilderPlans(TestCase):
    def testSelectSetsProjection(self) -> None:
        """Store the projected columns on the plan.

        Validates the select clause accumulation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        builder = _Item.query().select("id", "name")
        self.assertEqual(builder._plan.columns, ("id", "name"))

    def testWhereMappingFormExpandsToEqualities(self) -> None:
        """Expand mapping conditions into equality clauses.

        Validates the dict-based where form.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        builder = _Item.query().where({"name": "a", "id": 1})
        wheres = builder._plan.wheres
        self.assertEqual(len(wheres), 2)
        self.assertTrue(all(w.operator == "=" for w in wheres))

    def testWhereMappingRejectsExtraArguments(self) -> None:
        """Reject extra arguments combined with mapping conditions.

        Validates the mapping form guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(InvalidQueryException):
            _Item.query().where({"name": "a"}, "=")

    def testOrWhereMarksOrConnector(self) -> None:
        """Mark OR-combined clauses with the or connector.

        Validates the boolean connector accumulation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        builder = _Item.query().where("name", "a").orWhere("name", "b")
        self.assertEqual(builder._plan.wheres[1].boolean, "or")

    def testWhereOperatorFormIsNormalized(self) -> None:
        """Normalize explicit operators to lowercase.

        Validates the operator form parsing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        builder = _Item.query().where("name", "LIKE", "a%")
        clause = builder._plan.wheres[0]
        self.assertEqual(clause.operator, "like")
        self.assertEqual(clause.value, "a%")

    def testWhereNotInBuildsClause(self) -> None:
        """Build NOT IN clauses from iterables.

        Validates the whereNotIn accumulation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        builder = _Item.query().whereNotIn("id", [1, 2])
        clause = builder._plan.wheres[0]
        self.assertIs(clause.where_type, WhereType.NOT_IN)
        self.assertEqual(clause.value, (1, 2))

    def testWhereInUnwrapsCollections(self) -> None:
        """Unwrap Collection values into plain tuples.

        Validates the collection materialization rule.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        builder = _Item.query().whereIn("id", Collection([1, 2]))
        self.assertEqual(builder._plan.wheres[0].value, (1, 2))

    def testWhereBetweenRequiresTwoBounds(self) -> None:
        """Reject BETWEEN calls without exactly two boundaries.

        Validates the boundary arity guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(InvalidQueryException):
            _Item.query().whereBetween("id", (1,))

    def testWhereLikeVariantsBuildExpectedClauses(self) -> None:
        """Build LIKE/ILIKE clauses with their negated counterparts.

        Validates the pattern-matching where builders.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cases = (
            ("whereLike", WhereType.LIKE),
            ("whereNotLike", WhereType.NOT_LIKE),
            ("whereILike", WhereType.ILIKE),
            ("whereNotILike", WhereType.NOT_ILIKE),
        )
        for method_name, expected_type in cases:
            builder = getattr(_Item.query(), method_name)("name", "a%")
            clause = builder._plan.wheres[0]
            self.assertIs(clause.where_type, expected_type)
            self.assertEqual(clause.value, "a%")

    def testWhereTextMatchersBuildExpectedClauses(self) -> None:
        """Build startswith/endswith/contains/regexp clauses.

        Validates the literal and regular-expression where builders.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cases = (
            ("whereStartsWith", WhereType.STARTS_WITH),
            ("whereEndsWith", WhereType.ENDS_WITH),
            ("whereContains", WhereType.CONTAINS),
            ("whereRegexpMatch", WhereType.REGEXP),
        )
        for method_name, expected_type in cases:
            builder = getattr(_Item.query(), method_name)("name", "abc")
            clause = builder._plan.wheres[0]
            self.assertIs(clause.where_type, expected_type)
            self.assertEqual(clause.value, "abc")

    def testDistinctMarksPlan(self) -> None:
        """Mark the plan as requiring duplicate row collapsing.

        Validates the distinct() fluent method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        builder = _Item.query().distinct()
        self.assertTrue(builder._plan.distinct)

    def testGroupByAndHavingAccumulate(self) -> None:
        """Accumulate grouping columns and having conditions.

        Validates the grouping clause storage.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        builder = _Item.query().groupBy("name").having("id", ">", 1)
        self.assertEqual(builder._plan.groups, ["name"])
        self.assertEqual(builder._plan.havings[0].operator, ">")

    def testTakeAndSkipAliasLimitAndOffset(self) -> None:
        """Alias take/skip onto limit/offset.

        Validates the pagination aliases.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        builder = _Item.query().take(5).skip(10)
        self.assertEqual(builder._plan.limit_value, 5)
        self.assertEqual(builder._plan.offset_value, 10)

    def testNegativeLimitAndOffsetRaise(self) -> None:
        """Reject negative limit and offset values.

        Validates the pagination guards.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(InvalidQueryException):
            _Item.query().limit(-1)
        with self.assertRaises(InvalidQueryException):
            _Item.query().offset(-1)

    def testLatestUsesCreatedColumnWhenAvailable(self) -> None:
        """Default latest() to the created timestamp column.

        Validates the timestamp-aware ordering default.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        builder = _Item.query().latest()
        order = builder._plan.orders[0]
        self.assertEqual(order.column, "created_at")
        self.assertIs(order.direction, SortDirection.DESC)

    def testLatestFallsBackToPrimaryKey(self) -> None:
        """Fall back to the primary key without timestamp columns.

        Validates the ordering default fallback.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        builder = _Plain.query().latest()
        self.assertEqual(builder._plan.orders[0].column, "id")

    def testOldestOrdersAscending(self) -> None:
        """Order oldest() ascending on the resolved column.

        Validates the ascending ordering default.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        builder = _Plain.query().oldest("name")
        order = builder._plan.orders[0]
        self.assertEqual(order.column, "name")
        self.assertIs(order.direction, SortDirection.ASC)

    async def testInsertRejectsEmptyPayloads(self) -> None:
        """Reject insert calls without any row.

        Validates the insert guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(InvalidQueryException):
            await _Item.query().insert([])

    async def testUpdateRejectsEmptyPayloads(self) -> None:
        """Reject mass updates without values.

        Validates the update guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(InvalidQueryException):
            await _Item.query().update({})

    async def testPaginateRejectsInvalidArguments(self) -> None:
        """Reject non-positive page and page-size arguments.

        Validates the pagination argument guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(InvalidQueryException):
            await _Item.query().paginate(page=0)
        with self.assertRaises(InvalidQueryException):
            await _Item.query().paginate(per_page=0)

class _StubApp:
    """Minimal application stub exposing the database configuration."""

    __slots__ = ()

    def config(self, key: str) -> dict:  # noqa: ARG002
        """Run the config helper.

        Parameters
        ----------
        key : str
            Value supplied for ``key``.

        Returns
        -------
        dict
            Value produced by the helper.
        """
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {
                    "driver": "sqlite",
                    "database": ":memory:",
                    "prefix": "",
                },
            },
        }

def _table(name: str, columns: dict) -> TableDefinition:
    """
    Build a table definition whose columns already carry their name.

    Parameters
    ----------
    name : str
        Logical table name.
    columns : dict
        Column definitions keyed by column name.

    Returns
    -------
    TableDefinition
        Definition ready to be created on a connection.
    """
    for key, column in columns.items():
        column.name = key
    return TableDefinition(name=name, columns=columns, primary_key="id")

def _users_table() -> TableDefinition:
    """
    Build the physical "users" table used by every test.

    Returns
    -------
    TableDefinition
        Definition of the users table.
    """
    return _table(
        "users",
        {
            "id": Integer().primary().autoIncrement(),
            "name": String(),
            "role": String(),
            "country": String(),
            "age": Integer(),
            "active": Boolean(),
        },
    )

def _posts_table() -> TableDefinition:
    """
    Build the physical "posts" table used by the join tests.

    Returns
    -------
    TableDefinition
        Definition of the posts table.
    """
    return _table(
        "posts",
        {
            "id": Integer().primary().autoIncrement(),
            "user_id": Integer(),
            "title": String(),
            "views": Integer(),
        },
    )

class _QueryLanguageTestCase(TestCase):
    """Shared fixture creating the users/posts schema on sqlite."""

    async def asyncSetUp(self) -> None:
        """Wire an isolated in-memory manager and create both tables.

        Returns
        -------
        None
            Completes the operation described above.
        """
        previous_manager = ConnectionResolver._manager
        self.addCleanup(ConnectionResolver.setManager, previous_manager)
        self.addCleanup(setattr, DB, "_pinned_instance", DB._pinned_instance)
        self._manager = ConnectionManager(_StubApp())
        ConnectionResolver.setManager(self._manager)
        DB._pinned_instance = QueryBuilder(self._manager)
        connection = self._manager.connection()
        await connection.createTable(_users_table())
        await connection.createTable(_posts_table())

    async def asyncTearDown(self) -> None:
        """Dispose the manager and clear the resolver after each test.

        Returns
        -------
        None
            Completes the operation described above.
        """
        await self._manager.disconnect()
        ConnectionResolver.clear()

    async def seedUsers(self) -> None:
        """Insert the reference user rows shared by several tests.

        Returns
        -------
        None
            Completes the operation described above.
        """
        await DB.table("users").insert(
            [
                {
                    "name": "Ada",
                    "role": "admin",
                    "country": "CO",
                    "age": 30,
                    "active": True,
                },
                {
                    "name": "Ben",
                    "role": "manager",
                    "country": "MX",
                    "age": 45,
                    "active": True,
                },
                {
                    "name": "Cid",
                    "role": "guest",
                    "country": "CO",
                    "age": 17,
                    "active": False,
                },
                {
                    "name": "Dot",
                    "role": "guest",
                    "country": "AR",
                    "age": 70,
                    "active": True,
                },
            ],
        )

    def names(self, rows: object) -> list[str]:
        """
        Extract the ``name`` column of a result set, sorted.

        Parameters
        ----------
        rows : object
            Collection of row dictionaries.

        Returns
        -------
        list of str
            Sorted names.
        """
        return sorted(row["name"] for row in rows)

class _User(Model):
    """Model mapped onto the shared ``users`` fixture table."""

    table = "users"
    timestamps = False

    id = Integer().primary().autoIncrement()
    name = String()
    role = String()
    country = String()
    age = Integer()
    active = Boolean()

class TestNestedConditions(_QueryLanguageTestCase):
    """Condition grouping through callbacks, at any nesting depth."""

    async def testGroupIsAndCombinedWithOuterCondition(self) -> None:
        """Wrap a callback group in parentheses joined by AND.

        Validates ``where(a).where(fn: b OR c)`` keeps ``a AND (b OR c)``
        instead of degrading into ``a AND b OR c``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        rows = await (
            DB.table("users")
            .where("active", True)
            .where(
                lambda query: query.where("role", "admin").orWhere("role", "manager"),
            )
            .get()
        )
        self.assertEqual(self.names(rows), ["Ada", "Ben"])

    async def testTwoGroupsAreCombinedIndependently(self) -> None:
        """Combine two sibling groups with AND.

        Validates ``(a OR b) AND (c AND d)`` evaluation order.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        rows = await (
            DB.table("users")
            .where(
                lambda query: query.where("country", "CO").orWhere("country", "MX"),
            )
            .where(
                lambda query: query.where("age", ">=", 18).where("age", "<=", 60),
            )
            .get()
        )
        self.assertEqual(self.names(rows), ["Ada", "Ben"])

    async def testOrGroupIsCombinedWithOuterCondition(self) -> None:
        """Attach a group through OR.

        Validates ``a OR (b AND c)`` keeps the group atomic.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        rows = await (
            DB.table("users")
            .where("country", "AR")
            .orWhere(
                lambda query: query.where("role", "admin").where("active", True),
            )
            .get()
        )
        self.assertEqual(self.names(rows), ["Ada", "Dot"])

    async def testGroupsNestArbitrarily(self) -> None:
        """Nest groups several levels deep.

        Validates that nesting is recursive rather than one level deep.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        rows = await (
            DB.table("users")
            .where("active", True)
            .where(
                lambda level1: level1.where("country", "CO").orWhere(
                    lambda level2: level2.where("country", "MX").where(
                        lambda level3: level3.where("age", ">", 40).orWhere(
                            "role",
                            "admin",
                        ),
                    ),
                ),
            )
            .get()
        )
        self.assertEqual(self.names(rows), ["Ada", "Ben"])

    def testGroupRendersParentheses(self) -> None:
        """Render explicit parentheses around a group.

        Validates the generated SQL, not only the returned rows.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        builder = (
            RawQueryBuilder()
            .table("users")
            .where("active", True)
            .where(
                lambda query: query.where("role", "admin").orWhere("role", "manager"),
            )
        )
        sql = str(SQLCompiler().compileSelect(builder.toPlan()))
        self.assertIn("AND (", sql)
        self.assertIn(" OR ", sql)

    async def testEmptyGroupDoesNotFilterAnything(self) -> None:
        """Ignore a group whose callback declares no condition.

        Validates the neutral element of an empty parenthesis group.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        rows = await DB.table("users").where(lambda _query: None).get()
        self.assertEqual(len(rows), 4)

class TestConditionSurface(_QueryLanguageTestCase):
    """Conditions beyond plain comparisons."""

    async def testWhereColumnComparesTwoColumns(self) -> None:
        """Compare two columns of the same row.

        Validates ``whereColumn``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await DB.table("posts").insert(
            [
                {"user_id": 1, "title": "a", "views": 1},
                {"user_id": 2, "title": "b", "views": 5},
            ],
        )
        rows = await DB.table("posts").whereColumn("views", ">", "user_id").get()
        self.assertEqual([row["title"] for row in rows], ["b"])

    async def testWhereNotBetweenExcludesTheRange(self) -> None:
        """Exclude an inclusive range.

        Validates ``whereNotBetween``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        rows = await DB.table("users").whereNotBetween("age", (18, 60)).get()
        self.assertEqual(self.names(rows), ["Cid", "Dot"])

    async def testWhereRawBindsItsParameters(self) -> None:
        """Bind every value of a raw fragment.

        Validates that raw conditions never inline literals.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        rows = await DB.table("users").whereRaw("age > :floor", {"floor": 40}).get()
        self.assertEqual(self.names(rows), ["Ben", "Dot"])

    async def testOrWhereVariantsCombineWithOr(self) -> None:
        """Combine the ``or`` variants of the typed conditions.

        Validates ``orWhereIn`` and ``orWhereNull``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        rows = await (
            DB.table("users").where("role", "admin").orWhereIn("country", ["MX"]).get()
        )
        self.assertEqual(self.names(rows), ["Ada", "Ben"])

    async def testUnsupportedOperatorIsRejected(self) -> None:
        """Reject an operator outside the supported set.

        Validates that the builder never forwards arbitrary text into
        the generated SQL.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(InvalidQueryException):
            DB.table("users").where("name", "; DROP TABLE users; --", "x")

class TestSubqueries(_QueryLanguageTestCase):
    """Subquery support across projections, conditions, and joins."""

    async def testWhereInAcceptsASubquery(self) -> None:
        """Filter rows against the result of another query.

        Validates ``whereIn`` with a callable subquery.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        await DB.table("posts").insert(
            [{"user_id": 1, "title": "hello", "views": 10}],
        )
        rows = await (
            DB.table("users")
            .whereIn(
                "id",
                lambda query: query.table("posts").select("user_id"),
            )
            .get()
        )
        self.assertEqual(self.names(rows), ["Ada"])

    async def testWhereExistsCorrelatesWithTheOuterQuery(self) -> None:
        """Keep rows having at least one related row.

        Validates that a correlated ``EXISTS`` resolves outer columns.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        await DB.table("posts").insert(
            [{"user_id": 2, "title": "hello", "views": 10}],
        )
        rows = await (
            DB.table("users")
            .whereExists(
                lambda query: (
                    query.table("posts")
                    .select("id")
                    .whereColumn("posts.user_id", "=", "users.id")
                ),
            )
            .get()
        )
        self.assertEqual(self.names(rows), ["Ben"])

    async def testWhereNotExistsIsTheComplement(self) -> None:
        """Keep rows without any related row.

        Validates ``whereNotExists``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        await DB.table("posts").insert(
            [{"user_id": 2, "title": "hello", "views": 10}],
        )
        rows = await (
            DB.table("users")
            .whereNotExists(
                lambda query: (
                    query.table("posts")
                    .select("id")
                    .whereColumn("posts.user_id", "=", "users.id")
                ),
            )
            .get()
        )
        self.assertEqual(self.names(rows), ["Ada", "Cid", "Dot"])

    async def testSelectSubProjectsAScalarSubquery(self) -> None:
        """Project an aggregate of a related table as a column.

        Validates ``selectSub``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        await DB.table("posts").insert(
            [
                {"user_id": 1, "title": "a", "views": 3},
                {"user_id": 1, "title": "b", "views": 4},
            ],
        )
        rows = await (
            DB.table("users")
            .select("name")
            .selectSub(
                lambda query: (
                    query.table("posts")
                    .selectRaw("count(*)")
                    .whereColumn("posts.user_id", "=", "users.id")
                ),
                "posts_count",
            )
            .where("name", "Ada")
            .get()
        )
        self.assertEqual(rows[0]["posts_count"], 2)

    async def testJoinSubJoinsADerivedTable(self) -> None:
        """Join an aggregated subquery as a derived table.

        Validates ``joinSub`` and its mandatory alias.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        await DB.table("posts").insert(
            [
                {"user_id": 1, "title": "a", "views": 3},
                {"user_id": 1, "title": "b", "views": 4},
            ],
        )
        rows = await (
            DB.table("users")
            .select("users.name", "stats.total")
            .joinSub(
                lambda query: (
                    query.table("posts")
                    .select("user_id")
                    .selectRaw("sum(views)", alias="total")
                    .groupBy("user_id")
                ),
                "stats",
                "stats.user_id",
                "=",
                "users.id",
            )
            .get()
        )
        self.assertEqual(rows[0]["total"], 7)

    def testSubqueryJoinWithoutAliasIsRejected(self) -> None:
        """Reject a derived table that cannot be referenced.

        Validates the alias guard of subquery joins.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        builder = (
            RawQueryBuilder()
            .table("users")
            .joinSub(
                lambda query: query.table("posts").select("user_id"),
                "",
                "sub.user_id",
                "=",
                "users.id",
            )
        )
        with self.assertRaises(QueryException):
            SQLCompiler().compileSelect(builder.toPlan())

class TestJoins(_QueryLanguageTestCase):
    """Every join flavour exposed by the shared engine."""

    async def seedJoinable(self) -> None:
        """Insert users and posts linked by ``user_id``.

        Returns
        -------
        None
            Completes the operation described above.
        """
        await self.seedUsers()
        await DB.table("posts").insert(
            [
                {"user_id": 1, "title": "first", "views": 3},
                {"user_id": 2, "title": "second", "views": 4},
            ],
        )

    async def testInnerJoinKeepsOnlyMatchingRows(self) -> None:
        """Join two tables keeping only linked rows.

        Validates the INNER JOIN path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedJoinable()
        rows = await (
            DB.table("users")
            .select("users.name", "posts.title")
            .join("posts", "posts.user_id", "=", "users.id")
            .orderBy("posts.id")
            .get()
        )
        self.assertEqual([row["title"] for row in rows], ["first", "second"])

    async def testLeftJoinKeepsUnmatchedRows(self) -> None:
        """Keep rows of the main table without a match.

        Validates the LEFT OUTER JOIN path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedJoinable()
        rows = await (
            DB.table("users")
            .select("users.name", "posts.title")
            .leftJoin("posts", "posts.user_id", "=", "users.id")
            .get()
        )
        self.assertEqual(len(rows), 4)

    async def testJoinAcceptsSeveralConditionsThroughACallback(self) -> None:
        """Declare a multi-condition ON clause through a callback.

        Validates the ``JoinClause`` calling convention.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedJoinable()
        rows = await (
            DB.table("users")
            .select("users.name", "posts.title")
            .join(
                "posts",
                lambda join: join.on("posts.user_id", "=", "users.id").on(
                    "posts.views",
                    ">",
                    "users.id",
                ),
            )
            .get()
        )
        self.assertEqual([row["title"] for row in rows], ["first", "second"])

    async def testJoinSupportsAliases(self) -> None:
        """Join a table under an alias.

        Validates alias-qualified column resolution.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedJoinable()
        rows = await (
            DB.table("users", alias="u")
            .select("u.name", "p.title")
            .join("posts", "p.user_id", "=", "u.id", alias="p")
            .orderBy("p.id")
            .get()
        )
        self.assertEqual([row["name"] for row in rows], ["Ada", "Ben"])

    async def testCrossJoinProducesTheCartesianProduct(self) -> None:
        """Combine every row of both tables.

        Validates the CROSS JOIN path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedJoinable()
        rows = await DB.table("users").select("users.id").crossJoin("posts").get()
        self.assertEqual(len(rows), 8)

    def testJoinWithoutConditionIsRejected(self) -> None:
        """Reject an incomplete ON clause.

        Validates the guard preventing accidental cartesian products.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(InvalidQueryException):
            RawQueryBuilder().table("users").join("posts", "posts.user_id")

class TestCompoundsAndLocks(_QueryLanguageTestCase):
    """Unions, locking, and builder reuse."""

    async def testUnionAllAppendsBothResultSets(self) -> None:
        """Append the rows of another query keeping duplicates.

        Validates ``unionAll``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        rows = await (
            DB.table("users")
            .select("name")
            .where("country", "CO")
            .unionAll(
                lambda query: (
                    query.table("users").select("name").where("country", "MX")
                ),
            )
            .get()
        )
        self.assertEqual(self.names(rows), ["Ada", "Ben", "Cid"])

    async def testThreeUnionBranchesCompileWithoutNestedParentheses(self) -> None:
        """Execute three UNION arms using the shared query engine.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        base = DB.table("users").select("name").where("country", "CO")
        middle = DB.table("users").select("name").where("country", "MX")
        last = DB.table("users").select("name").where("country", "AR")
        rows = await base.union(middle).union(last).get()
        self.assertEqual(self.names(rows), ["Ada", "Ben", "Cid", "Dot"])

    async def testMixedUnionOperatorsPreserveLeftToRightSemantics(self) -> None:
        """Preserve duplicates appended after a distinct compound result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        first = DB.table("users").select("name").where("name", "Ada")
        second = first.clone()
        third = first.clone()
        rows = await first.union(second).unionAll(third).get()
        self.assertEqual(self.names(rows), ["Ada", "Ada"])

    def testLockForUpdateRendersRowLocking(self) -> None:
        """Request row locking on the selected rows.

        Validates the generated SQL, since sqlite ignores row locks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        builder = RawQueryBuilder().table("users").lockForUpdate()
        sql = str(SQLCompiler().compileSelect(builder.toPlan()))
        self.assertIn("FOR UPDATE", sql)

    def testCloneDetachesThePlan(self) -> None:
        """Branch a builder without mutating the original.

        Validates builder reuse and composition.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        base = RawQueryBuilder().table("users").where("active", True)
        branch = base.clone().where("role", "admin")
        self.assertEqual(len(base.toPlan().wheres), 1)
        self.assertEqual(len(branch.toPlan().wheres), 2)

    async def testAggregatesShareTheSameEngine(self) -> None:
        """Run every aggregate terminal over a model-less query.

        Validates that aggregates are available outside models too.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        query = DB.table("users")
        self.assertEqual(await query.clone().count(), 4)
        self.assertEqual(await query.clone().max("age"), 70)
        self.assertEqual(await query.clone().min("age"), 17)
        self.assertEqual(await query.clone().sum("age"), 162)
        self.assertTrue(await query.clone().exists())
        self.assertFalse(
            await DB.table("users").where("name", "Ghost").exists(),
        )

    async def testRunningWithoutATableIsRejected(self) -> None:
        """Reject a query that never selected a table.

        Validates the target guard of the model-less builder.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(InvalidQueryException):
            await RawQueryBuilder().get()

class TestPaginationGuards(TestCase):
    """Check terminal guards and execution-context isolation."""

    async def testInvalidPaginationDoesNotIssueQueries(self) -> None:
        """Reject invalid page types and values before connection resolution.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for invalid in (0, -1, 1.5, True, "1", None):
            for builder in (RawQueryBuilder().table("books"), fixtures.Book.query()):
                with self.subTest(invalid=invalid, builder=type(builder)):
                    with self.assertRaises(InvalidQueryException):
                        await builder.paginate(page=invalid)
                    with self.assertRaises(InvalidQueryException):
                        await builder.paginate(per_page=invalid)
