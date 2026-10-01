from __future__ import annotations
import tests.orm.relations.test_mixin as relation_fixtures

class TestHasManyCreation(relation_fixtures._RelationsTestCase):
    async def testCreateAutoLinksForeignKey(self) -> None:
        """Create a related row through the relationship, injecting the key.

        Validates the ``create()`` convenience mirroring Eloquent.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await relation_fixtures.Author.create({"name": "Ana"})
        book = await author.books().create({"title": "New"})
        self.assertEqual(book.author_id, author.id)
        self.assertTrue(book._exists)

        reloaded = await author.books().get()
        self.assertEqual([b.title for b in reloaded], ["New"])

class TestHasOneCreation(relation_fixtures._RelationsTestCase):
    async def testCreateAutoLinksForeignKey(self) -> None:
        """Create the related row through the relationship, injecting the key.

        Validates the ``create()`` convenience for hasOne.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await relation_fixtures.Author.create({"name": "Ana"})
        profile = await author.profile().create({"bio": "Fresh"})
        self.assertEqual(profile.author_id, author.id)

        reloaded = await author.profile()
        self.assertEqual(reloaded.bio, "Fresh")
