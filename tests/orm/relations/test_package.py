from orionis.test import TestCase
from tests.orm.test_package import assert_package_exports

EXPECTED_EXPORTS = {
    "BelongsToManyRelation": (
        "orionis.orm.relations.belongs_to_many",
        "BelongsToManyRelation",
    ),
    "BelongsToRelation": ("orionis.orm.relations.belongs_to", "BelongsToRelation"),
    "HasManyRelation": ("orionis.orm.relations.has_many", "HasManyRelation"),
    "HasOneOrManyRelation": (
        "orionis.orm.relations.has_one_or_many",
        "HasOneOrManyRelation",
    ),
    "HasOneRelation": ("orionis.orm.relations.has_one", "HasOneRelation"),
    "Relation": ("orionis.orm.relations.relation", "Relation"),
    "RelationsMixin": ("orionis.orm.relations.mixin", "RelationsMixin"),
}

class TestRelationsPackage(TestCase):
    """Verify the orionis.orm.relations public export surface."""

    def testPublicExportsResolveToTheirOwningModules(self) -> None:
        """Keep public exports aligned with their declared implementation origins.

        Returns
        -------
        None
            Verify exact exported names and identities without shadowing modules.
        """
        assert_package_exports(self, "orionis.orm.relations", EXPECTED_EXPORTS)
