from datetime import UTC, datetime
from orionis.auth.entities.access_token import AccessToken
from orionis.test import TestCase


class TestAccessToken(TestCase):
    """Validate the metadata exposed for a stored token."""

    def testStaysImmutableAndSlotted(self) -> None:
        """Build a token entity and try to mutate it.

        Validates that audit metadata can never be rewritten in place.
        """
        token = AccessToken(
            id=1,
            tokenable_type="app.models.user.User",
            tokenable_id=7,
            name="ci",
        )
        self.assertFalse(hasattr(token, "__dict__"))
        with self.assertRaises(AttributeError):
            token.name = "other"

    def testDefaultsToAnUnrestrictedAndUnusedCredential(self) -> None:
        """Read the optional fields of a minimal entity.

        Validates that a token without declared abilities keeps the full
        authorization of its owner and reports no lifecycle timestamp.
        """
        token = AccessToken(
            id=1,
            tokenable_type="app.models.user.User",
            tokenable_id=7,
            name="ci",
        )
        self.assertIsNone(token.abilities)
        self.assertIsNone(token.created_at)
        self.assertIsNone(token.expires_at)
        self.assertIsNone(token.last_used_at)
        self.assertIsNone(token.revoked_at)

    def testSerialisesEveryDeclaredField(self) -> None:
        """Serialize a fully populated entity.

        Validates the payload applications render when listing the
        credentials of an identity.
        """
        issued = datetime(2026, 1, 1, tzinfo=UTC)
        token = AccessToken(
            id=1,
            tokenable_type="app.models.user.User",
            tokenable_id=7,
            name="ci",
            abilities=frozenset({"users.view"}),
            created_at=issued,
        )
        payload = token.toDict()
        self.assertEqual(payload["name"], "ci")
        self.assertEqual(payload["tokenable_id"], 7)
        self.assertEqual(payload["abilities"], frozenset({"users.view"}))
        self.assertEqual(payload["created_at"], issued)
        self.assertEqual(
            set(payload),
            {
                "id",
                "tokenable_type",
                "tokenable_id",
                "name",
                "abilities",
                "created_at",
                "expires_at",
                "last_used_at",
                "revoked_at",
            },
        )
