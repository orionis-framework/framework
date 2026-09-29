from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, Mock, patch
from orionis.orm.collections.paginator import Paginator
from orionis.orm.exceptions import InvalidQueryException
from orionis.orm.query.builder import ModelQueryBuilder
from orionis.orm.query.raw_builder import RawQueryBuilder
from orionis.orm.relations.belongs_to_many import BelongsToManyRelation
from orionis.orm.relations.relation import Relation
from orionis.support.types.collection import Collection
from orionis.test import TestCase
from tests.orm import test_relations as fixtures

class TestQueryGuards(TestCase):
    """Check terminal guards and execution-context isolation."""

    def testPaginationUsesExactIntegerArithmetic(self) -> None:
        """Keep page counts exact beyond floating-point integer precision.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        paginator = Paginator(Collection(), total=2**60 + 1, page=1, per_page=2)
        self.assertEqual(paginator.lastPage, 2**59 + 1)
        self.assertTrue(paginator.hasNext)
        self.assertFalse(paginator.hasPrevious)

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

    def testConstraintSuppressionIsIsolatedBetweenThreads(self) -> None:
        """Keep parent constraints on relationships built by another thread.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parent = fixtures.Author({"id": 9, "name": "author"})
        with ThreadPoolExecutor(max_workers=1) as executor:

            def build_template():
                """Resolve a query while the parent thread holds the scope context.

                Returns
                -------
                object
                    Value produced by the helper.
                """
                constrained = executor.submit(parent.books).result(timeout=5)
                self.assertEqual(len(constrained.toPlan().wheres), 1)
                self.assertEqual(constrained.toPlan().wheres[0].value, 9)
                return parent.books()

            template = Relation.noConstraints(build_template)
        self.assertEqual(template.toPlan().wheres, [])
        self.assertEqual(len(parent.books().toPlan().wheres), 1)

    def testConstraintSuppressionRestoresAfterFailure(self) -> None:
        """Restore parent constraints when the relation factory raises.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parent = fixtures.Author({"id": 9, "name": "author"})
        callback = Mock(side_effect=ValueError("factory failed"))
        with self.assertRaises(ValueError):
            Relation.noConstraints(callback)
        self.assertEqual(len(parent.books().toPlan().wheres), 1)

    async def testKeylessEagerBatchSkipsRelatedQuery(self) -> None:
        """Return an empty related set without querying a keyless batch.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parent = fixtures.Author({"name": "author"})
        relation = Relation.noConstraints(parent.books)
        relation.addEagerConstraints([parent])
        with patch.object(ModelQueryBuilder, "get", new_callable=AsyncMock) as get:
            self.assertEqual(len(await relation.getEager()), 0)
        get.assert_not_awaited()

    def testClonedEagerLoadsAreIndependentAndUnique(self) -> None:
        """Preserve load order and isolate later registrations on clones.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        query = fixtures.Author.query().withRelations("books", "books")
        clone = query.clone().withRelations("profile", "books")
        self.assertEqual(list(query._eager_loads), ["books"])
        self.assertEqual(list(clone._eager_loads), ["books", "profile"])

class TestQueryTerminalIsolation(fixtures._RelationsTestCase):
    """Exercise repeated terminals and relation writes against SQLite."""

    async def testFirstDoesNotLimitLaterGet(self) -> None:
        """Keep the original result limit when retrieving only one model.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await fixtures.Book.create({"title": "first"})
        await fixtures.Book.create({"title": "second"})
        query = fixtures.Book.query().orderBy("id")
        self.assertEqual((await query.first()).title, "first")
        self.assertIsNone(query.toPlan().limit_value)
        self.assertEqual(len(await query.get()), 2)

    async def testDuplicateEagerLoadsIssueOneRelatedQuery(self) -> None:
        """Load a repeated relationship name once for the entire batch.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await fixtures.Author.create({"name": "author"})
        connection = self._manager.connection()
        with patch.object(
            type(connection), "select", wraps=connection.select,
        ) as select:
            result = await fixtures.Author.withRelations("books", "books").get()
        self.assertEqual(len(result), 1)
        self.assertEqual(select.await_count, 2)

    async def testPivotPreparationIsIdempotent(self) -> None:
        """Reuse the pivot membership without accumulating WHERE clauses.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await fixtures.Book.create({"title": "book"})
        tag = await fixtures.Tag.create({"name": "linked"})
        relation = book.tags()
        await relation.attach(tag.id)
        await relation.get()
        clause = relation.toPlan().wheres[0]
        for _ in range(3):
            self.assertEqual(await relation.count(), 1)
            self.assertTrue(await relation.exists())
        self.assertEqual(len(relation.toPlan().wheres), 1)
        self.assertIs(relation.toPlan().wheres[0], clause)

    async def testConcurrentPivotPreparationIssuesOneQuery(self) -> None:
        """Share one pivot resolution among concurrent read terminals.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await fixtures.Book.create({"title": "book"})
        tag = await fixtures.Tag.create({"name": "linked"})
        relation = book.tags()
        await relation.attach(tag.id)
        with patch.object(
            BelongsToManyRelation,
            "_resolvePivotMap",
            new_callable=AsyncMock,
            return_value={book.id: [tag.id]},
        ) as resolve:
            first, second = await asyncio.gather(relation.get(), relation.get())
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertEqual(resolve.await_count, 1)
        self.assertEqual(len(relation.toPlan().wheres), 1)

    async def testPivotCacheIsInvalidatedByAttachAndDetach(self) -> None:
        """Reflect pivot writes on an already executed relationship builder.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await fixtures.Book.create({"title": "book"})
        tag = await fixtures.Tag.create({"name": "linked"})
        relation = book.tags()
        self.assertEqual(len(await relation.get()), 0)
        await relation.attach(tag.id)
        self.assertEqual(len(await relation.get()), 1)
        await relation.detach(tag.id)
        self.assertEqual(len(await relation.get()), 0)
        self.assertEqual(len(relation.toPlan().wheres), 1)

    async def testPivotFiltersInvalidateOnlyTheirOwnClone(self) -> None:
        """Apply new pivot filters without changing a previously built query.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await fixtures.Book.create({"title": "book"})
        first = await fixtures.Tag.create({"name": "first"})
        second = await fixtures.Tag.create({"name": "second"})
        relation = book.tags()
        await relation.attach({first.id: {"featured": 1}, second.id: {"featured": 0}})
        self.assertEqual(len(await relation.get()), 2)
        clone = relation.clone().wherePivot("featured", 1)
        self.assertEqual([tag.id for tag in await clone.get()], [first.id])
        self.assertEqual(len(await relation.get()), 2)

    async def testPivotAggregatesExcludeUnrelatedRows(self) -> None:
        """Apply membership constraints before every aggregate terminal.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await fixtures.Book.create({"title": "book"})
        linked = await fixtures.Tag.create({"name": "linked"})
        await fixtures.Tag.create({"name": "unrelated"})
        await book.tags().attach(linked.id)
        self.assertEqual(await book.tags().max("id"), linked.id)
        self.assertEqual(await book.tags().sum("id"), linked.id)
        self.assertEqual(await book.tags().count("id"), 1)

    async def testPivotUpdateExcludesUnrelatedRows(self) -> None:
        """Constrain bulk updates to linked rows before executing SQL.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await fixtures.Book.create({"title": "book"})
        linked = await fixtures.Tag.create({"name": "linked"})
        unrelated = await fixtures.Tag.create({"name": "unrelated"})
        await book.tags().attach(linked.id)
        self.assertEqual(await book.tags().update({"name": "updated"}), 1)
        self.assertEqual((await fixtures.Tag.find(unrelated.id)).name, "unrelated")

    async def testPivotDeleteExcludesUnrelatedRows(self) -> None:
        """Constrain deletions to linked rows on a fresh relation builder.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await fixtures.Book.create({"title": "book"})
        linked = await fixtures.Tag.create({"name": "linked"})
        unrelated = await fixtures.Tag.create({"name": "unrelated"})
        await book.tags().attach(linked.id)
        self.assertEqual(await book.tags().delete(), 1)
        self.assertIsNotNone(await fixtures.Tag.find(unrelated.id))

    async def testEmptyPivotWritesDoNotAffectAnyRows(self) -> None:
        """Keep empty relationships from modifying unrelated records.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await fixtures.Book.create({"title": "book"})
        tag = await fixtures.Tag.create({"name": "unrelated"})
        self.assertEqual(await book.tags().update({"name": "updated"}), 0)
        self.assertEqual(await book.tags().forceDelete(), 0)
        self.assertIsNotNone(await fixtures.Tag.find(tag.id))

    async def testAttachAcceptsGeneratorIds(self) -> None:
        """Consume general iterable ids when writing pivot records.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await fixtures.Book.create({"title": "book"})
        tag = await fixtures.Tag.create({"name": "linked"})
        self.assertEqual(await book.tags().attach(item for item in [tag.id]), 1)
        self.assertEqual(await book.tags().count(), 1)

    async def testPivotQueryProjectsOnlyItsKeys(self) -> None:
        """Fetch only the columns needed to match pivot memberships.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await fixtures.Book.create({"title": "book"})
        builder = RawQueryBuilder().table("book_tag")
        with patch.object(RawQueryBuilder, "get", new_callable=AsyncMock) as get:
            get.return_value = Collection()
            relation = book.tags()
            with patch.object(
                BelongsToManyRelation, "_pivotQuery", return_value=builder,
            ) as query:
                await relation.get()
        self.assertEqual(query.call_count, 1)
        self.assertEqual(builder.toPlan().columns, ("book_id", "tag_id"))
