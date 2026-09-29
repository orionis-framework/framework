from __future__ import annotations
from orionis.orm import Integer, Model, String, StrictTimestamp
from orionis.orm.contracts.builder import IModelQueryBuilder
from orionis.orm.exceptions import InvalidQueryException
from orionis.orm.query.expressions import SortDirection, WhereType
from orionis.support.types.collection import Collection
from orionis.test import TestCase

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

    def testBuilderImplementsContract(self) -> None:
        """Implement the IModelQueryBuilder contract.

        Validates the builder class hierarchy.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(_Item.query(), IModelQueryBuilder)

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

    def testForwardedClassEntryPointsStartBuilders(self) -> None:
        """Start builders from forwarded class-level entry points.

        Validates the metaclass forwarding whitelist.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        builder = _Item.where("name", "a")
        self.assertEqual(len(builder._plan.wheres), 1)
        chained = _Item.orderBy("name").limit(1)
        self.assertEqual(chained._plan.limit_value, 1)

    def testUnknownClassAttributeRaises(self) -> None:
        """Raise AttributeError for non-forwarded class attributes.

        Validates the metaclass forwarding guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(AttributeError):
            _ = _Item.notAQueryMethod
