from __future__ import annotations
import tests.orm.relations.test_mixin as relation_fixtures

class TestHasManyRelation(relation_fixtures._RelationsTestCase):
    async def testLazyGetReturnsAllRelatedRows(self) -> None:
        """Retrieve every row owned by the parent instance.

        Validates the basic hasMany lazy-loading path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await relation_fixtures.Author.create({"name": "Ana"})
        await relation_fixtures.Book.create({"title": "One", "author_id": author.id})
        await relation_fixtures.Book.create({"title": "Two", "author_id": author.id})

        books = await author.books().get()
        self.assertEqual(len(books), 2)
        self.assertEqual({b.title for b in books}, {"One", "Two"})

    async def testEmptyRelationReturnsEmptyCollection(self) -> None:
        """Return an empty collection when no related rows exist.

        Validates the empty-relationship edge case.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await relation_fixtures.Author.create({"name": "Ana"})
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
        ana = await relation_fixtures.Author.create({"name": "Ana"})
        bob = await relation_fixtures.Author.create({"name": "Bob"})
        await relation_fixtures.Book.create(
            {"title": "Ana's book", "author_id": ana.id},
        )
        await relation_fixtures.Book.create(
            {"title": "Bob's book", "author_id": bob.id},
        )

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
        author = await relation_fixtures.Author.create({"name": "Ana"})
        await relation_fixtures.Book.create(
            {"title": "B", "author_id": author.id, "published": True},
        )
        await relation_fixtures.Book.create(
            {"title": "A", "author_id": author.id, "published": True},
        )
        await relation_fixtures.Book.create(
            {"title": "C", "author_id": author.id, "published": False},
        )

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
        author = await relation_fixtures.Author.create({"name": "Ana"})
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
        writer = await relation_fixtures.Writer.create({"name": "Mark"})
        await relation_fixtures.Article.create(
            {"title": "Piece", "writer_ref": writer.writer_id},
        )

        articles = await writer.articles().get()
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "Piece")

    async def testUpdateThroughRelationOnlyAffectsOwnRows(self) -> None:
        """Mass update through a relationship only touches the parent's rows.

        Validates that mutation terminals inherit the relation constraint.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        ana = await relation_fixtures.Author.create({"name": "Ana"})
        bob = await relation_fixtures.Author.create({"name": "Bob"})
        await relation_fixtures.Book.create(
            {"title": "X", "author_id": ana.id, "published": False},
        )
        await relation_fixtures.Book.create(
            {"title": "Y", "author_id": bob.id, "published": False},
        )

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
        ana = await relation_fixtures.Author.create({"name": "Ana"})
        bob = await relation_fixtures.Author.create({"name": "Bob"})
        await relation_fixtures.Book.create({"title": "X", "author_id": ana.id})
        await relation_fixtures.Book.create({"title": "Y", "author_id": bob.id})

        deleted = await ana.books().delete()
        self.assertEqual(deleted, 1)
        self.assertEqual(len(await relation_fixtures.Book.all()), 1)
        self.assertEqual((await relation_fixtures.Book.all())[0].author_id, bob.id)

    async def testUnsavedParentReturnsEmptyWithoutError(self) -> None:
        """Return an empty collection for a parent without a primary key.

        Validates the ``None``-key guard avoids matching orphaned rows.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await relation_fixtures.Book.create({"title": "Orphan", "author_id": None})
        unsaved = relation_fixtures.Author({"name": "Draft"})
        books = await unsaved.books().get()
        self.assertEqual(len(books), 0)
