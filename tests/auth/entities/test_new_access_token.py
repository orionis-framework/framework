from orionis.auth.entities.access_token import AccessToken
from orionis.auth.entities.new_access_token import NewAccessToken
from orionis.test import TestCase

# Secret handed back to the client exactly once, used to assert it never
# leaks through a representation or a serialization.
_ISSUED_SECRET = "super-secret-value"  # noqa: S105


def build_issued_token() -> NewAccessToken:
    """Pair a stored token with the plain text value just issued."""
    return NewAccessToken(
        access_token=AccessToken(
            id=1,
            tokenable_type="app.models.user.User",
            tokenable_id=7,
            name="ci",
        ),
        plain_text=_ISSUED_SECRET,
    )


class TestNewAccessToken(TestCase):
    """Validate the pair returned when a token is issued."""

    def testStaysImmutableAndSlotted(self) -> None:
        """Build the pair and try to mutate it.

        Validates that the issued credential can never be swapped after
        the fact.
        """
        issued = build_issued_token()
        self.assertFalse(hasattr(issued, "__dict__"))
        with self.assertRaises(AttributeError):
            issued.plain_text = "other"

    def testExposesTheSecretOnlyThroughItsAttribute(self) -> None:
        """Read the plain text value back from the pair.

        Validates that the caller responsible for handing the credential
        to the client can still reach it.
        """
        self.assertEqual(build_issued_token().plain_text, _ISSUED_SECRET)

    def testTheSecretNeverReachesTheRepresentation(self) -> None:
        """Render the pair the way a traceback or a log would.

        Validates that the only copy of the credential never leaks
        through debugging output.
        """
        self.assertNotIn(_ISSUED_SECRET, repr(build_issued_token()))

    def testSerialisationRedactsTheSecret(self) -> None:
        """Serialize the pair for an HTTP response body.

        Validates that ``toDict`` publishes the stored metadata only, so
        issuing the credential stays an explicit decision.
        """
        issued = build_issued_token()
        payload = issued.toDict()
        self.assertEqual(set(payload), {"access_token"})
        self.assertEqual(payload["access_token"], issued.access_token.toDict())
        self.assertNotIn(_ISSUED_SECRET, str(payload))
