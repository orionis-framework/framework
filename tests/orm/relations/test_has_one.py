from __future__ import annotations
import tests.orm.relations.test_mixin as relation_fixtures

class TestHasOneRelation(relation_fixtures._RelationsTestCase):
    async def testAwaitShortcutReturnsModelOrNone(self) -> None:
        """Await a hasOne relationship directly, returning a single model.

        Validates the ``Relation.__await__`` shortcut for hasOne.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await relation_fixtures.Author.create({"name": "Ana"})
        await relation_fixtures.AuthorProfile.create(
            {"bio": "Bio", "author_id": author.id},
        )

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
        author = await relation_fixtures.Author.create({"name": "Ana"})
        await relation_fixtures.AuthorProfile.create(
            {"bio": "Bio", "author_id": author.id},
        )

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
        author = await relation_fixtures.Author.create({"name": "Ana"})
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
        author = await relation_fixtures.Author.create({"name": "Ana"})
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
        author = await relation_fixtures.Author.create({"name": "Ana"})
        await relation_fixtures.AuthorProfile.create(
            {"bio": "Nope", "author_id": author.id},
        )

        profile = await author.profile().where("bio", "Match").first()
        self.assertIsNone(profile)
