from __future__ import annotations
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
from orionis.orm.query_builder import QueryBuilder
from orionis.orm.resolver import ConnectionResolver
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
        previous_manager = ConnectionResolver._manager
        self.addCleanup(ConnectionResolver.setManager, previous_manager)
        self.addCleanup(setattr, DB, "_pinned_instance", DB._pinned_instance)
        self._manager = ConnectionManager(_StubApp())
        ConnectionResolver.setManager(self._manager)
        DB._pinned_instance = QueryBuilder(self._manager)
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

    def testConcreteRelationsNeverExposeInstanceDictionaries(self) -> None:
        """Keep every relation's declared state in slots across its interfaces.

        Returns
        -------
        None
            Verify has-one, has-many, inverse, and pivot relations are slotted.
        """
        author = Author({"id": 1, "name": "author"})
        book = Book._newFromDatabase({"id": 1, "title": "book", "author_id": 1})
        relations = (author.books(), author.profile(), book.author(), book.tags())
        for relation in relations:
            self.assertFalse(hasattr(relation, "__dict__"), type(relation).__name__)
