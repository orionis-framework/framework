from __future__ import annotations
from unittest.mock import patch
from typing import TYPE_CHECKING, ClassVar
from orionis.database.connection_manager import ConnectionManager
from orionis.orm import (
    Boolean,
    Integer,
    Model,
    RelationNotFoundException,
    String,
)
from orionis.orm.exceptions import MassAssignmentException
from orionis.orm.resolver import ConnectionResolver
from orionis.orm.query_builder import QueryBuilder
from orionis.orm.schema.table import TableDefinition
from orionis.support.facades.db import DB
from orionis.test import TestCase

if TYPE_CHECKING:
    from orionis.orm.relations import (
        BelongsToManyRelation,
        BelongsToRelation,
        HasManyRelation,
        HasOneRelation,
    )

class _StubApp:
    """Minimal application stub exposing the database configuration."""

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

def _pivot_table(name: str, first: str, second: str, *extra: str) -> TableDefinition:
    """Build a bare pivot table with two integer keys and optional extras.

    Parameters
    ----------
    name : str
        Value supplied for ``name``.
    first : str
        Value supplied for ``first``.
    second : str
        Value supplied for ``second``.
    *extra : str
        Arguments passed to the wrapped callable.

    Returns
    -------
    TableDefinition
        Value produced by the helper.
    """
    columns = {first: Integer(), second: Integer()}
    for extra_name in extra:
        columns[extra_name] = Integer().nullable()
    for key, column in columns.items():
        column.name = key
    return TableDefinition(name=name, columns=columns)

# ── Default-convention fixtures (Author/Book/AuthorProfile/Tag) ─────────────

class Author(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    timestamps = False

    def books(self) -> HasManyRelation[Book]:
        """Every book written by this author.

        Returns
        -------
        HasManyRelation[Book]
            Value produced by the helper.
        """
        return self.hasMany(Book)

    def profile(self) -> HasOneRelation[AuthorProfile]:
        """Return this author's single profile row.

        Returns
        -------
        HasOneRelation[AuthorProfile]
            Value produced by the helper.
        """
        return self.hasOne(AuthorProfile)

class Book(Model):
    id = Integer().primary().autoIncrement()
    title = String()
    author_id = Integer().nullable()
    published = Boolean().nullable()
    timestamps = False

    fillable: ClassVar[list[str]] = ["title", "author_id", "published"]

    def author(self) -> BelongsToRelation[Author]:
        """Return the author owning this book.

        Returns
        -------
        BelongsToRelation[Author]
            Value produced by the helper.
        """
        return self.belongsTo(Author)

    def tags(self) -> BelongsToManyRelation[Tag]:
        """Every tag linked to this book through the pivot table.

        Returns
        -------
        BelongsToManyRelation[Tag]
            Value produced by the helper.
        """
        return self.belongsToMany(Tag)

class AuthorProfile(Model):
    id = Integer().primary().autoIncrement()
    bio = String().nullable()
    author_id = Integer().nullable()
    timestamps = False

    fillable: ClassVar[list[str]] = ["bio", "author_id"]

class Tag(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    timestamps = False

    def books(self) -> BelongsToManyRelation[Book]:
        """Every book linked to this tag through the pivot table.

        Returns
        -------
        BelongsToManyRelation[Book]
            Value produced by the helper.
        """
        return self.belongsToMany(Book)

# ── Custom-key fixtures (Writer/Article) ────────────────────────────────────

class Writer(Model):
    writer_id = Integer().primary().autoIncrement()
    name = String()
    timestamps = False

    def articles(self) -> HasManyRelation[Article]:
        """Every article written by this writer, using custom keys.

        Returns
        -------
        HasManyRelation[Article]
            Value produced by the helper.
        """
        return self.hasMany(Article, foreign_key="writer_ref", local_key="writer_id")

class Article(Model):
    id = Integer().primary().autoIncrement()
    title = String()
    writer_ref = Integer().nullable()
    timestamps = False

    def writer(self) -> BelongsToRelation[Writer]:
        """Return the writer owning this article, using custom keys.

        Returns
        -------
        BelongsToRelation[Writer]
            Value produced by the helper.
        """
        return self.belongsTo(Writer, foreign_key="writer_ref", owner_key="writer_id")

# ── Custom pivot fixtures (Student/Course via "enrollments") ────────────────

class Student(Model):
    student_id = Integer().primary().autoIncrement()
    name = String()
    timestamps = False

    def courses(self) -> BelongsToManyRelation[Course]:
        """Every course this student is enrolled in, via a custom pivot.

        Returns
        -------
        BelongsToManyRelation[Course]
            Value produced by the helper.
        """
        return self.belongsToMany(
            Course,
            table="enrollments",
            foreign_pivot_key="student_ref",
            related_pivot_key="course_ref",
            parent_key="student_id",
            related_key="course_id",
        )

class Course(Model):
    course_id = Integer().primary().autoIncrement()
    name = String()
    timestamps = False

    def students(self) -> BelongsToManyRelation[Student]:
        """Every student enrolled in this course, via a custom pivot.

        Returns
        -------
        BelongsToManyRelation[Student]
            Value produced by the helper.
        """
        return self.belongsToMany(
            Student,
            table="enrollments",
            foreign_pivot_key="course_ref",
            related_pivot_key="student_ref",
            parent_key="course_id",
            related_key="student_id",
        )

class _RelationsTestCase(TestCase):
    """Base test case wiring an isolated in-memory sqlite connection."""

    async def asyncSetUp(self) -> None:
        """Wire an isolated in-memory manager and create every table.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self._manager = ConnectionManager(_StubApp())
        ConnectionResolver.setManager(self._manager)
        facade = patch.object(DB, "_pinned_instance", QueryBuilder(self._manager))
        facade.start()
        self.addCleanup(facade.stop)
        connection = self._manager.connection()
        await connection.createTable(Author.__meta__.table)
        await connection.createTable(Book.__meta__.table)
        await connection.createTable(AuthorProfile.__meta__.table)
        await connection.createTable(Tag.__meta__.table)
        await connection.createTable(Writer.__meta__.table)
        await connection.createTable(Article.__meta__.table)
        await connection.createTable(Student.__meta__.table)
        await connection.createTable(Course.__meta__.table)
        await connection.createTable(
            _pivot_table("book_tag", "book_id", "tag_id", "featured"),
        )
        await connection.createTable(
            _pivot_table("enrollments", "student_ref", "course_ref"),
        )

    async def asyncTearDown(self) -> None:
        """Dispose the manager and clear the resolver after each test.

        Returns
        -------
        None
            Completes the operation described above.
        """
        await self._manager.disconnect()
        ConnectionResolver.clear()

class TestHasManyRelation(_RelationsTestCase):

    async def testLazyGetReturnsAllRelatedRows(self) -> None:
        """Retrieve every row owned by the parent instance.

        Validates the basic hasMany lazy-loading path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        await Book.create({"title": "One", "author_id": author.id})
        await Book.create({"title": "Two", "author_id": author.id})

        books = await author.books().get()
        self.assertEqual(len(books), 2)
        self.assertEqual({b.title for b in books}, {"One", "Two"})

    async def testAwaitShortcutEquivalentToGet(self) -> None:
        """Await a relationship directly without a terminal method.

        Validates the ``Relation.__await__`` ergonomic shortcut.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        await Book.create({"title": "One", "author_id": author.id})

        books = await author.books()
        self.assertEqual(len(books), 1)

    async def testEmptyRelationReturnsEmptyCollection(self) -> None:
        """Return an empty collection when no related rows exist.

        Validates the empty-relationship edge case.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        books = await author.books().get()
        self.assertEqual(len(books), 0)

    async def testMultipleParentsIsolateResults(self) -> None:
        """Keep each parent's related rows isolated from another parent's.

        Validates that the relationship constraint is instance-specific.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        ana = await Author.create({"name": "Ana"})
        bob = await Author.create({"name": "Bob"})
        await Book.create({"title": "Ana's book", "author_id": ana.id})
        await Book.create({"title": "Bob's book", "author_id": bob.id})

        ana_books = await ana.books().get()
        bob_books = await bob.books().get()
        self.assertEqual([b.title for b in ana_books], ["Ana's book"])
        self.assertEqual([b.title for b in bob_books], ["Bob's book"])

    async def testChainedWhereOrderByAndLimitNarrowResults(self) -> None:
        """Chain the full fluent query API on top of a relationship.

        Validates that a relationship is a fully functional query builder.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        await Book.create({"title": "B", "author_id": author.id, "published": True})
        await Book.create({"title": "A", "author_id": author.id, "published": True})
        await Book.create({"title": "C", "author_id": author.id, "published": False})

        books = (
            await author.books()
            .where("published", True)
            .orderBy("title")
            .limit(10)
            .get()
        )
        self.assertEqual([b.title for b in books], ["A", "B"])

    async def testDefaultForeignKeyAndLocalKeyInference(self) -> None:
        """Infer ``author_id``/``id`` by Laravel-style convention.

        Validates the automatic key inference for hasMany.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        relation = author.books()
        self.assertEqual(relation._foreign_key, "author_id")
        self.assertEqual(relation._local_key, "id")

    async def testCustomForeignKeyAndLocalKey(self) -> None:
        """Honor explicit foreign/local keys overriding the convention.

        Validates that custom keys work end to end, not just as metadata.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        writer = await Writer.create({"name": "Mark"})
        await Article.create({"title": "Piece", "writer_ref": writer.writer_id})

        articles = await writer.articles().get()
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "Piece")

    async def testCreateAutoLinksForeignKey(self) -> None:
        """Create a related row through the relationship, injecting the key.

        Validates the ``create()`` convenience mirroring Eloquent.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        book = await author.books().create({"title": "New"})
        self.assertEqual(book.author_id, author.id)
        self.assertTrue(book._exists)

        reloaded = await author.books().get()
        self.assertEqual([b.title for b in reloaded], ["New"])

    async def testUpdateThroughRelationOnlyAffectsOwnRows(self) -> None:
        """Mass update through a relationship only touches the parent's rows.

        Validates that mutation terminals inherit the relation constraint.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        ana = await Author.create({"name": "Ana"})
        bob = await Author.create({"name": "Bob"})
        await Book.create({"title": "X", "author_id": ana.id, "published": False})
        await Book.create({"title": "Y", "author_id": bob.id, "published": False})

        affected = await ana.books().update({"published": True})
        self.assertEqual(affected, 1)

        ana_books = await ana.books().where("published", True).get()
        bob_books = await bob.books().where("published", True).get()
        self.assertEqual(len(ana_books), 1)
        self.assertEqual(len(bob_books), 0)

    async def testDeleteThroughRelationOnlyAffectsOwnRows(self) -> None:
        """Bulk delete through a relationship only removes the parent's rows.

        Validates that mutation terminals inherit the relation constraint.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        ana = await Author.create({"name": "Ana"})
        bob = await Author.create({"name": "Bob"})
        await Book.create({"title": "X", "author_id": ana.id})
        await Book.create({"title": "Y", "author_id": bob.id})

        deleted = await ana.books().delete()
        self.assertEqual(deleted, 1)
        self.assertEqual(len(await Book.all()), 1)
        self.assertEqual((await Book.all())[0].author_id, bob.id)

    async def testUnsavedParentReturnsEmptyWithoutError(self) -> None:
        """Return an empty collection for a parent without a primary key.

        Validates the ``None``-key guard avoids matching orphaned rows.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await Book.create({"title": "Orphan", "author_id": None})
        unsaved = Author({"name": "Draft"})
        books = await unsaved.books().get()
        self.assertEqual(len(books), 0)

class TestHasOneRelation(_RelationsTestCase):

    async def testAwaitShortcutReturnsModelOrNone(self) -> None:
        """Await a hasOne relationship directly, returning a single model.

        Validates the ``Relation.__await__`` shortcut for hasOne.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        await AuthorProfile.create({"bio": "Bio", "author_id": author.id})

        profile = await author.profile()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.bio, "Bio")

    async def testLazyFirstIsEquivalentToAwait(self) -> None:
        """Resolve a hasOne relationship through the inherited ``first()``.

        Validates that the relationship is a fully functional builder.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        await AuthorProfile.create({"bio": "Bio", "author_id": author.id})

        profile = await author.profile().first()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.bio, "Bio")

    async def testEmptyRelationReturnsNone(self) -> None:
        """Return ``None`` when the parent has no related row.

        Validates the empty-relationship edge case for hasOne.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        profile = await author.profile()
        self.assertIsNone(profile)

    async def testDefaultKeysInference(self) -> None:
        """Infer ``author_id``/``id`` by Laravel-style convention.

        Validates the automatic key inference for hasOne.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        relation = author.profile()
        self.assertEqual(relation._foreign_key, "author_id")
        self.assertEqual(relation._local_key, "id")

    async def testChainedWhereNarrowsResult(self) -> None:
        """Chain extra conditions on top of a hasOne relationship.

        Validates that the relationship stays a fully functional builder.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        await AuthorProfile.create({"bio": "Nope", "author_id": author.id})

        profile = await author.profile().where("bio", "Match").first()
        self.assertIsNone(profile)

    async def testCreateAutoLinksForeignKey(self) -> None:
        """Create the related row through the relationship, injecting the key.

        Validates the ``create()`` convenience for hasOne.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        profile = await author.profile().create({"bio": "Fresh"})
        self.assertEqual(profile.author_id, author.id)

        reloaded = await author.profile()
        self.assertEqual(reloaded.bio, "Fresh")

class TestBelongsToRelation(_RelationsTestCase):

    async def testAwaitShortcutReturnsOwner(self) -> None:
        """Await a belongsTo relationship directly, returning the owner.

        Validates the ``Relation.__await__`` shortcut for belongsTo.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        book = await Book.create({"title": "One", "author_id": author.id})

        owner = await book.author()
        self.assertIsNotNone(owner)
        self.assertEqual(owner.name, "Ana")

    async def testNullForeignKeyReturnsNoneWithoutQuerying(self) -> None:
        """Return ``None`` immediately when the foreign key is unset.

        Validates the NULL-foreign-key short circuit.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await Book.create({"title": "Orphan", "author_id": None})
        owner = await book.author()
        self.assertIsNone(owner)

    async def testOwnerNotFoundReturnsNone(self) -> None:
        """Return ``None`` when the foreign key references no existing row.

        Validates a dangling foreign key does not raise.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await Book.create({"title": "Dangling", "author_id": 999})
        owner = await book.author()
        self.assertIsNone(owner)

    async def testDefaultKeysInference(self) -> None:
        """Infer ``author_id``/``id`` by Laravel-style convention.

        Validates the automatic key inference for belongsTo.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await Book.create({"title": "One", "author_id": 1})
        relation = book.author()
        self.assertEqual(relation._foreign_key, "author_id")
        self.assertEqual(relation._owner_key, "id")

    async def testCustomForeignKeyAndOwnerKey(self) -> None:
        """Honor explicit foreign/owner keys overriding the convention.

        Validates that custom keys work end to end for belongsTo.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        writer = await Writer.create({"name": "Mark"})
        article = await Article.create(
            {"title": "Piece", "writer_ref": writer.writer_id},
        )

        owner = await article.writer()
        self.assertIsNotNone(owner)
        self.assertEqual(owner.name, "Mark")

class TestBelongsToManyRelation(_RelationsTestCase):

    async def testAttachLinksRecords(self) -> None:
        """Link records through the pivot table via ``attach()``.

        Validates the basic belongsToMany attach path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await Book.create({"title": "One"})
        fiction = await Tag.create({"name": "fiction"})
        drama = await Tag.create({"name": "drama"})

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
        book = await Book.create({"title": "One"})
        fiction = await Tag.create({"name": "fiction"})

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
        book = await Book.create({"title": "One"})
        fiction = await Tag.create({"name": "fiction"})
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
        book = await Book.create({"title": "One"})
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
        book = await Book.create({"title": "One"})
        fiction = await Tag.create({"name": "fiction"})
        drama = await Tag.create({"name": "drama"})
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
        book = await Book.create({"title": "One"})
        fiction = await Tag.create({"name": "fiction"})
        drama = await Tag.create({"name": "drama"})
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
        book = await Book.create({"title": "One"})
        fiction = await Tag.create({"name": "fiction"})
        drama = await Tag.create({"name": "drama"})
        horror = await Tag.create({"name": "horror"})
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
        book = await Book.create({"title": "One"})
        fiction = await Tag.create({"name": "fiction"})
        drama = await Tag.create({"name": "drama"})
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
        book = await Book.create({"title": "One"})
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
        book = await Book.create({"title": "One"})
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
        student = await Student.create({"name": "Alice"})
        course = await Course.create({"name": "Math"})

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
        book = await Book.create({"title": "One"})
        fiction = await Tag.create({"name": "fiction"})
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
        book = await Book.create({"title": "One"})
        fiction = await Tag.create({"name": "fiction"})
        drama = await Tag.create({"name": "drama"})
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
        book = await Book.create({"title": "One"})
        fiction = await Tag.create({"name": "fiction"})
        drama = await Tag.create({"name": "drama"})
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
        book = await Book.create({"title": "One"})
        fiction = await Tag.create({"name": "fiction"})
        await Tag.create({"name": "unrelated"})
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
        book = await Book.create({"title": "One"})
        self.assertFalse(await book.tags().exists())
        self.assertTrue(await book.tags().doesntExist())

        fiction = await Tag.create({"name": "fiction"})
        await book.tags().attach(fiction.id)
        self.assertTrue(await book.tags().exists())
        self.assertFalse(await book.tags().doesntExist())

class TestEagerLoading(_RelationsTestCase):

    async def testWithLoadsHasManyForEveryModel(self) -> None:
        """Eager load a hasMany relationship across an entire result set.

        Validates ``withRelations()`` populates ``getRelation()`` for every row.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        ana = await Author.create({"name": "Ana"})
        bob = await Author.create({"name": "Bob"})
        await Book.create({"title": "Ana's book", "author_id": ana.id})

        authors = await Author.query().withRelations("books").orderBy("name").get()
        self.assertTrue(authors[0].relationLoaded("books"))
        self.assertTrue(authors[1].relationLoaded("books"))
        loaded_titles = [b.title for b in authors[0].getRelation("books")]
        self.assertEqual(loaded_titles, ["Ana's book"])
        self.assertEqual(list(authors[1].getRelation("books")), [])
        self.assertEqual(ana.name, authors[0].name)
        self.assertEqual(bob.name, authors[1].name)

    async def testLoadAliasBehavesIdenticallyToWith(self) -> None:
        """Use the ``load()`` alias interchangeably with ``withRelations()``.

        Validates both spellings resolve to the same eager-loading path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        await Book.create({"title": "One", "author_id": author.id})

        authors = await Author.query().load("books").get()
        self.assertEqual([b.title for b in authors[0].getRelation("books")], ["One"])

    async def testEagerLoadingAlsoWorksOnFirst(self) -> None:
        """Eager load a relationship when only the first row is fetched.

        Validates ``withRelations()`` integrates with the ``first()`` terminal.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        await AuthorProfile.create({"bio": "Bio", "author_id": author.id})

        fetched = await Author.query().withRelations("profile").first()
        self.assertTrue(fetched.relationLoaded("profile"))
        self.assertEqual(fetched.getRelation("profile").bio, "Bio")

    async def testEagerLoadingMultipleRelationsAtOnce(self) -> None:
        """Eager load several relationships in a single call.

        Validates that ``withRelations()`` accepts multiple relationship names.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        await Book.create({"title": "One", "author_id": author.id})
        await AuthorProfile.create({"bio": "Bio", "author_id": author.id})

        fetched = (await Author.query().withRelations("books", "profile").get())[0]
        self.assertTrue(fetched.relationLoaded("books"))
        self.assertTrue(fetched.relationLoaded("profile"))

    async def testClassLevelForwardingForWith(self) -> None:
        """Start eager loading directly from the model class.

        Validates ``Model.withRelations(...)`` forwards to ``Model.query()``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        await Book.create({"title": "One", "author_id": author.id})

        fetched = (await Author.withRelations("books").get())[0]
        self.assertTrue(fetched.relationLoaded("books"))

    async def testEagerLoadedBelongsTo(self) -> None:
        """Eager load an inverse belongsTo relationship.

        Validates eager loading works for the "many/one side" too.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        await Book.create({"title": "One", "author_id": author.id})

        books = await Book.query().withRelations("author").get()
        self.assertTrue(books[0].relationLoaded("author"))
        self.assertEqual(books[0].getRelation("author").name, "Ana")

    async def testEagerLoadedBelongsToMany(self) -> None:
        """Eager load a belongsToMany relationship across a result set.

        Validates that the pivot-backed relationship supports eager
        loading like the single-table relationship kinds.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await Book.create({"title": "One"})
        fiction = await Tag.create({"name": "fiction"})
        await book.tags().attach(fiction.id)

        books = await Book.query().withRelations("tags").get()
        self.assertTrue(books[0].relationLoaded("tags"))
        self.assertEqual([t.name for t in books[0].getRelation("tags")], ["fiction"])

    async def testRelationNotYetLoadedDefaultsToNone(self) -> None:
        """Report ``None``/``False`` for a relationship never resolved.

        Validates ``getRelation()``/``relationLoaded()`` defaults.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        self.assertFalse(author.relationLoaded("books"))
        self.assertIsNone(author.getRelation("books"))

class TestRelationConfigurationErrors(_RelationsTestCase):

    async def testUnknownRelationNameRaises(self) -> None:
        """Raise a clear error when an eager-loaded name does not exist.

        Validates ``RelationNotFoundException`` for a typo'd name.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await Author.create({"name": "Ana"})
        with self.assertRaises(RelationNotFoundException):
            await Author.query().withRelations("noSuchRelation").get()

    async def testNonRelationMethodRaises(self) -> None:
        """Raise a clear error when the named method is not a relationship.

        Validates ``RelationNotFoundException`` for a non-relation method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await Book.create({"title": "One"})
        with self.assertRaises(RelationNotFoundException):
            await Book.query().withRelations("save").get()

    async def testMassAssignmentStillEnforcedThroughRelationCreate(self) -> None:
        """Enforce fillable/guarded rules when creating through a relation.

        Validates that ``create()`` on a relationship does not bypass
        the related model's mass-assignment rules.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await Author.create({"name": "Ana"})
        with self.assertRaises(MassAssignmentException):
            await author.books().create({"unknown_field": "x"})
