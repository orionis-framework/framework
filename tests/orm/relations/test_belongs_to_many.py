from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING
import tests.orm.relations.test_mixin as relation_fixtures
from orionis.orm.relations.belongs_to_many import BelongsToManyRelation
from orionis.support.facades.db import DB
from tests.orm.relations import test_mixin as fixtures

if TYPE_CHECKING:
    from orionis.orm.query.raw_builder import RawQueryBuilder

class _RecordingPivotRelation(BelongsToManyRelation[fixtures.Tag]):
    """Record pivot preparation while executing the real database operations."""

    __slots__ = ("pivot_calls", "pivot_queries")

    def __init__(self, parent: fixtures.Book) -> None:
        """Bind the recording relation to the fixture's pivot table.

        Parameters
        ----------
        parent : Book
            Book whose tag membership is queried.

        Returns
        -------
        None
            Initialize relation state and independent query observations.
        """
        super().__init__(
            parent,
            fixtures.Tag,
            "book_tag",
            "book_id",
            "tag_id",
            "id",
            "id",
        )
        self.pivot_calls = 0
        self.pivot_queries: list[RawQueryBuilder] = []

    def _pivotQuery(self) -> RawQueryBuilder:
        """Record the pivot builder created by the ordinary relation path.

        Returns
        -------
        RawQueryBuilder
            Fresh builder targeting the real pivot table.
        """
        builder = super()._pivotQuery()
        self.pivot_queries.append(builder)
        return builder

    async def _resolvePivotMap(self) -> dict[object, list[object]]:
        """Count pivot resolutions and allow concurrent terminals to enter.

        Returns
        -------
        dict of object to list of object
            Membership obtained from the real pivot table.
        """
        self.pivot_calls += 1
        await asyncio.sleep(0)
        return await super()._resolvePivotMap()

class TestBelongsToManyRelation(relation_fixtures._RelationsTestCase):
    async def testAttachLinksRecords(self) -> None:
        """Link records through the pivot table via ``attach()``.

        Validates the basic belongsToMany attach path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await relation_fixtures.Book.create({"title": "One"})
        fiction = await relation_fixtures.Tag.create({"name": "fiction"})
        drama = await relation_fixtures.Tag.create({"name": "drama"})

        await book.tags().attach([fiction.id, drama.id])
        tags = await book.tags().get()
        self.assertEqual({t.name for t in tags}, {"fiction", "drama"})

    async def testAttachAcceptsModelInstances(self) -> None:
        """Accept related model instances directly, not only raw ids.

        Validates the ergonomic ``attach(model)`` overload.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await relation_fixtures.Book.create({"title": "One"})
        fiction = await relation_fixtures.Tag.create({"name": "fiction"})

        await book.tags().attach(fiction)
        tags = await book.tags().get()
        self.assertEqual([t.name for t in tags], ["fiction"])

    async def testAttachWithExtraPivotAttributes(self) -> None:
        """Insert extra pivot columns shared by every attached record.

        Validates ``attach(ids, attributes=...)``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await relation_fixtures.Book.create({"title": "One"})
        fiction = await relation_fixtures.Tag.create({"name": "fiction"})
        await book.tags().attach([fiction.id], attributes={"featured": 1})

        pivot_rows = await DB.table("book_tag").get()
        self.assertEqual(pivot_rows[0]["featured"], 1)

    async def testAttachEmptyIdsReturnsZero(self) -> None:
        """Return zero without touching the pivot table for empty input.

        Validates the empty-input edge case for ``attach()``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await relation_fixtures.Book.create({"title": "One"})
        inserted = await book.tags().attach([])
        self.assertEqual(inserted, 0)

    async def testDetachSpecificIds(self) -> None:
        """Unlink only the given related records.

        Validates the targeted ``detach(ids)`` path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await relation_fixtures.Book.create({"title": "One"})
        fiction = await relation_fixtures.Tag.create({"name": "fiction"})
        drama = await relation_fixtures.Tag.create({"name": "drama"})
        await book.tags().attach([fiction.id, drama.id])

        await book.tags().detach(fiction.id)
        tags = await book.tags().get()
        self.assertEqual([t.name for t in tags], ["drama"])

    async def testDetachAllWhenIdsNone(self) -> None:
        """Unlink every related record when no ids are given.

        Validates the "detach all" path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await relation_fixtures.Book.create({"title": "One"})
        fiction = await relation_fixtures.Tag.create({"name": "fiction"})
        drama = await relation_fixtures.Tag.create({"name": "drama"})
        await book.tags().attach([fiction.id, drama.id])

        await book.tags().detach()
        tags = await book.tags().get()
        self.assertEqual(len(tags), 0)

    async def testSyncAddsAndRemovesToMatchGivenIds(self) -> None:
        """Synchronize the pivot rows to match exactly the given ids.

        Validates ``sync()`` both attaches and detaches as needed.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await relation_fixtures.Book.create({"title": "One"})
        fiction = await relation_fixtures.Tag.create({"name": "fiction"})
        drama = await relation_fixtures.Tag.create({"name": "drama"})
        horror = await relation_fixtures.Tag.create({"name": "horror"})
        await book.tags().attach([fiction.id, drama.id])

        result = await book.tags().sync([drama.id, horror.id])
        self.assertEqual(result["attached"], [horror.id])
        self.assertEqual(result["detached"], [fiction.id])

        tags = await book.tags().get()
        self.assertEqual({t.name for t in tags}, {"drama", "horror"})

    async def testToggleFlipsMembership(self) -> None:
        """Attach ids not currently linked, detach ids that already are.

        Validates the ``toggle()`` behavior.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await relation_fixtures.Book.create({"title": "One"})
        fiction = await relation_fixtures.Tag.create({"name": "fiction"})
        drama = await relation_fixtures.Tag.create({"name": "drama"})
        await book.tags().attach([fiction.id])

        result = await book.tags().toggle([fiction.id, drama.id])
        self.assertEqual(result["attached"], [drama.id])
        self.assertEqual(result["detached"], [fiction.id])

        tags = await book.tags().get()
        self.assertEqual([t.name for t in tags], ["drama"])

    async def testEmptyRelationReturnsEmptyCollection(self) -> None:
        """Return an empty collection when nothing is attached yet.

        Validates the empty-relationship edge case for belongsToMany.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await relation_fixtures.Book.create({"title": "One"})
        tags = await book.tags().get()
        self.assertEqual(len(tags), 0)

    async def testDefaultPivotTableAndKeysInference(self) -> None:
        """Infer the pivot table and keys by Laravel-style convention.

        Validates ``book_tag``/``book_id``/``tag_id`` defaults.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await relation_fixtures.Book.create({"title": "One"})
        relation = book.tags()
        self.assertEqual(relation._table, "book_tag")
        self.assertEqual(relation._foreign_pivot_key, "book_id")
        self.assertEqual(relation._related_pivot_key, "tag_id")

    async def testCustomPivotTableAndKeys(self) -> None:
        """Honor an explicit pivot table and custom pivot/parent/related keys.

        Validates the fully custom belongsToMany configuration end to end.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        student = await relation_fixtures.Student.create({"name": "Alice"})
        course = await relation_fixtures.Course.create({"name": "Math"})

        await student.courses().attach(course.course_id)
        courses = await student.courses().get()
        self.assertEqual([c.name for c in courses], ["Math"])

    async def testInverseRelationWorksBothWays(self) -> None:
        """Resolve the many-to-many relationship from either side.

        Validates that the pivot links both directions symmetrically.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await relation_fixtures.Book.create({"title": "One"})
        fiction = await relation_fixtures.Tag.create({"name": "fiction"})
        await book.tags().attach(fiction.id)

        books_for_tag = await fiction.books().get()
        self.assertEqual([b.title for b in books_for_tag], ["One"])

    async def testWherePivotFiltersRows(self) -> None:
        """Filter the linked records by a pivot column condition.

        Validates ``wherePivot()`` against the intermediate table.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await relation_fixtures.Book.create({"title": "One"})
        fiction = await relation_fixtures.Tag.create({"name": "fiction"})
        drama = await relation_fixtures.Tag.create({"name": "drama"})
        await book.tags().attach(
            {fiction.id: {"featured": 1}, drama.id: {"featured": 0}},
        )

        featured = await book.tags().wherePivot("featured", 1).get()
        self.assertEqual([t.name for t in featured], ["fiction"])

    async def testChainedWhereOnRelatedTable(self) -> None:
        """Chain a condition on the related table's own columns.

        Validates that belongsToMany stays a fully functional builder.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await relation_fixtures.Book.create({"title": "One"})
        fiction = await relation_fixtures.Tag.create({"name": "fiction"})
        drama = await relation_fixtures.Tag.create({"name": "drama"})
        await book.tags().attach([fiction.id, drama.id])

        matched = await book.tags().where("name", "drama").get()
        self.assertEqual([t.name for t in matched], ["drama"])

    async def testCountReflectsPivotConstraint(self) -> None:
        """Count only the related rows actually linked through the pivot.

        Validates the ``count()`` terminal override.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await relation_fixtures.Book.create({"title": "One"})
        fiction = await relation_fixtures.Tag.create({"name": "fiction"})
        await relation_fixtures.Tag.create({"name": "unrelated"})
        await book.tags().attach(fiction.id)

        self.assertEqual(await book.tags().count(), 1)

    async def testExistsReflectsPivotConstraint(self) -> None:
        """Report existence based on the pivot-linked rows only.

        Validates the ``exists()``/``doesntExist()`` terminal overrides.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await relation_fixtures.Book.create({"title": "One"})
        self.assertFalse(await book.tags().exists())
        self.assertTrue(await book.tags().doesntExist())

        fiction = await relation_fixtures.Tag.create({"name": "fiction"})
        await book.tags().attach(fiction.id)
        self.assertTrue(await book.tags().exists())
        self.assertFalse(await book.tags().doesntExist())

class TestPivotTerminalIsolation(fixtures._RelationsTestCase):
    """Exercise repeated terminals and relation writes against SQLite."""

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
        relation = _RecordingPivotRelation(book)
        await relation.attach(tag.id)
        first, second = await asyncio.gather(relation.get(), relation.get())
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertEqual(relation.pivot_calls, 1)
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
        relation = _RecordingPivotRelation(book)
        self.assertEqual(len(await relation.get()), 0)
        self.assertEqual(len(relation.pivot_queries), 1)
        builder = relation.pivot_queries[0]
        self.assertEqual(builder.toPlan().columns, ("book_id", "tag_id"))
