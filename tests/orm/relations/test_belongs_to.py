from __future__ import annotations
import tests.orm.relations.test_mixin as relation_fixtures

class TestBelongsToRelation(relation_fixtures._RelationsTestCase):
    async def testAwaitShortcutReturnsOwner(self) -> None:
        """Await a belongsTo relationship directly, returning the owner.

        Validates the ``Relation.__await__`` shortcut for belongsTo.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await relation_fixtures.Author.create({"name": "Ana"})
        book = await relation_fixtures.Book.create(
            {"title": "One", "author_id": author.id},
        )

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
        book = await relation_fixtures.Book.create(
            {"title": "Orphan", "author_id": None},
        )
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
        book = await relation_fixtures.Book.create(
            {"title": "Dangling", "author_id": 999},
        )
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
        book = await relation_fixtures.Book.create({"title": "One", "author_id": 1})
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
        writer = await relation_fixtures.Writer.create({"name": "Mark"})
        article = await relation_fixtures.Article.create(
            {"title": "Piece", "writer_ref": writer.writer_id},
        )

        owner = await article.writer()
        self.assertIsNotNone(owner)
        self.assertEqual(owner.name, "Mark")
