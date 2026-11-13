# ruff: noqa: PT009, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify relation ownership, eager ordering, and scoped constraints."""

import asyncio
from inspect import isfunction
from typing import get_type_hints
from unittest.mock import patch

from orionis.orm import Model
from orionis.orm.contracts.belongs_to_many_relation import IBelongsToManyRelation
from orionis.orm.contracts.relation import IRelation
from orionis.orm.relations.belongs_to import BelongsToRelation
from orionis.orm.relations.belongs_to_many import BelongsToManyRelation
from orionis.orm.relations.has_many import HasManyRelation
from orionis.orm.relations.has_one import HasOneRelation
from orionis.orm.relations.has_one_or_many import HasOneOrManyRelation
from orionis.orm.relations.mixin import RelationsMixin
from orionis.orm.relations.relation import Relation
from orionis.orm.resolver import ConnectionResolver
from orionis.support.facades.db import DB
from orionis.test import TestCase
from tests.orm.relations import test_mixin as fixtures


class ExplicitDefaultBook(fixtures.Book):
    """Retain an explicitly selected connection on a related model."""

    table = "books"
    connection = "sqlite"


def ordered_tags(book: fixtures.Book) -> BelongsToManyRelation[fixtures.Tag]:
    """Order the ordinary pivot relation by its related model's name.

    Parameters
    ----------
    book : fixtures.Book
        Parent whose tags are queried.

    Returns
    -------
    BelongsToManyRelation
        Relationship with a deterministic related-row order.
    """
    return book.belongsToMany(fixtures.Tag).orderBy("name")


class TestPivotOwnership(fixtures._RelationsTestCase):
    """Exercise pivot behavior through real SQLite queries."""

    async def testExtraAttributesCannotRetargetPivotKeys(self) -> None:
        """Keep both link keys authoritative for shared and per-row attributes.

        Returns
        -------
        None
            No return value.
        """
        parent = await fixtures.Book.create({"title": "Parent"})
        other = await fixtures.Book.create({"title": "Other"})
        selected = await fixtures.Tag.create({"name": "Selected"})
        unrelated = await fixtures.Tag.create({"name": "Unrelated"})
        extra = {"book_id": other.id, "tag_id": unrelated.id, "featured": 1}
        for mapped in (False, True):
            with self.subTest(mapped=mapped):
                await DB.table("book_tag").delete()
                relation = parent.tags()
                if mapped:
                    inserted = await relation.attach({selected.id: extra})
                else:
                    inserted = await relation.attach(selected.id, attributes=extra)
                self.assertEqual(inserted, 1)
                rows = await DB.table("book_tag").get()
                self.assertEqual(
                    rows[0],
                    {"book_id": parent.id, "tag_id": selected.id, "featured": 1},
                )
                self.assertEqual(extra["book_id"], other.id)

    async def testEagerPivotResultsPreserveLazyOrderAndCardinality(self) -> None:
        """Match lazy results when pivot order differs or contains duplicate links.

        Returns
        -------
        None
            No return value.
        """
        parent = await fixtures.Book.create({"title": "Parent"})
        last = await fixtures.Tag.create({"name": "Zulu"})
        first = await fixtures.Tag.create({"name": "Alpha"})
        await parent.tags().attach([last.id, first.id])
        with patch.object(fixtures.Book, "tags", ordered_tags):
            for duplicate in (False, True):
                with self.subTest(duplicate=duplicate):
                    if duplicate:
                        await parent.tags().attach(last.id)
                    lazy = await parent.tags().get()
                    eager = await fixtures.Book.withRelations("tags").find(parent.id)
                    self.assertEqual([row.id for row in lazy], [first.id, last.id])
                    self.assertEqual(
                        [row.id for row in eager.getRelation("tags")],
                        [row.id for row in lazy],
                    )

    async def testRelationsRetainParentReadConnectionUnlessExplicit(self) -> None:
        """Keep inherited reads and writes on the hydrated parent's owner.

        Returns
        -------
        None
            No return value.
        """
        self._manager.addConnection(
            "replica",
            {"driver": "sqlite", "database": ":memory:"},
        )
        replica = self._manager.connection("replica")
        for model in (fixtures.Author, fixtures.Book, fixtures.Tag):
            await replica.createTable(model.__meta__.table)
        await replica.createTable(
            fixtures._pivot_table("book_tag", "book_id", "tag_id"),
        )
        default_author = await fixtures.Author.create({"name": "Default author"})
        await fixtures.Book.create(
            {"title": "Default book", "author_id": default_author.id},
        )
        for model, attributes in (
            (fixtures.Author, {"id": 1, "name": "Replica author"}),
            (fixtures.Book, {"id": 1, "title": "Replica book", "author_id": 1}),
            (fixtures.Tag, {"id": 1, "name": "Replica tag"}),
        ):
            await model.query().adoptConnection("replica").insert(attributes)
        await (
            DB.connection("replica")
            .table("book_tag")
            .insert({"book_id": 1, "tag_id": 1})
        )
        author = await fixtures.Author.query().adoptConnection("replica").find(1)
        book = await fixtures.Book.query().adoptConnection("replica").find(1)
        explicit = author.hasMany(ExplicitDefaultBook, foreign_key="author_id")
        self.assertEqual([row.title for row in await explicit.get()], ["Default book"])
        relationships = (
            (author.books(), "Replica book", "title"),
            (book.author(), "Replica author", "name"),
            (book.tags(), "Replica tag", "name"),
        )
        with patch.object(ConnectionResolver, "_manager", None):
            for relation, expected, attribute in relationships:
                with self.subTest(relation=type(relation).__name__):
                    rows = await relation.get()
                    self.assertEqual(
                        [getattr(row, attribute) for row in rows],
                        [expected],
                    )

        created = await author.books().create({"title": "Created on replica"})
        self.assertEqual(await fixtures.Book.query().count(), 1)
        self.assertEqual(
            await fixtures.Book.query().adoptConnection("replica").count(),
            2,
        )
        created.title = "Updated on replica"
        self.assertTrue(await created.save())
        stored = await fixtures.Book.query().adoptConnection("replica").find(created.id)
        self.assertEqual(stored.title, "Updated on replica")
        await explicit.create({"title": "Created on explicit default"})
        self.assertEqual(await fixtures.Book.query().count(), 2)
        self.assertEqual(
            await fixtures.Book.query().adoptConnection("replica").count(),
            2,
        )


class TestRelationContext(TestCase):
    """Verify relation metadata without accessing a database."""

    async def testChildContextCannotRetainExpiredConstraintSuppression(self) -> None:
        """Restore constraints in a child that resumes after suppression exits.

        Returns
        -------
        None
            No return value.
        """
        parent = fixtures.Author({"id": 9, "name": "Parent"})
        release = asyncio.Event()
        children: list[asyncio.Task[HasManyRelation[fixtures.Book]]] = []

        async def build_later() -> HasManyRelation[fixtures.Book]:
            """Build the child query after its inherited scope has ended.

            Returns
            -------
            HasManyRelation[fixtures.Book]
                Relationship constructed for the test scenario.
            """
            await release.wait()
            return parent.books()

        def build_template() -> HasManyRelation[fixtures.Book]:
            """Fork a child context and construct the eager-loading template.

            Returns
            -------
            HasManyRelation[fixtures.Book]
                Relationship constructed for the test scenario.
            """
            children.append(asyncio.create_task(build_later()))
            return parent.books()

        try:
            template = Relation.noConstraints(build_template)
            self.assertEqual(template.toPlan().wheres, [])
            release.set()
            constrained = await asyncio.wait_for(children[0], timeout=5)
            self.assertEqual(len(constrained.toPlan().wheres), 1)
            self.assertEqual(constrained.toPlan().wheres[0].value, 9)
        finally:
            release.set()
            for child in children:
                if not child.done():
                    child.cancel()
            await asyncio.gather(*children, return_exceptions=True)

    def testDeclaredRelationAnnotationsResolveAtRuntime(self) -> None:
        """Resolve concrete contract and implementation annotations after import.

        Returns
        -------
        None
            No return value.
        """
        classes = (
            IRelation,
            IBelongsToManyRelation,
            Relation,
            RelationsMixin,
            HasOneOrManyRelation,
            HasOneRelation,
            HasManyRelation,
            BelongsToRelation,
            BelongsToManyRelation,
        )
        for cls in classes:
            for parameter in cls.__type_params__:
                self.assertIs(parameter.__bound__, Model)
            for name, member in vars(cls).items():
                function = (
                    member.__func__
                    if isinstance(member, (staticmethod, classmethod))
                    else member
                )
                if isfunction(function):
                    with self.subTest(owner=cls.__name__, method=name):
                        self.assertTrue(get_type_hints(function))
                        for parameter in function.__type_params__:
                            self.assertIs(parameter.__bound__, Model)
