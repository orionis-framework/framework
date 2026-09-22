from orionis.auth.entities.guard_result import GuardResult
from orionis.test import TestCase


class TestGuardResult(TestCase):
    """Validate the transport object returned by a guard."""

    def testStaysImmutableAndSlotted(self) -> None:
        """Build a result and try to mutate it.

        Validates that the object created once per request can never be
        rewritten nor grow an instance dictionary.
        """
        result = GuardResult(identity=object(), guard="session")
        self.assertFalse(hasattr(result, "__dict__"))
        with self.assertRaises(AttributeError):
            result.guard = "token"

    def testDefaultsToAnUnrestrictedCredential(self) -> None:
        """Read the optional fields of a minimal result.

        Validates that a guard without revocable credentials reports no
        ability restriction, which keeps the identity authorization
        untouched.
        """
        result = GuardResult(identity=object(), guard="session")
        self.assertIsNone(result.abilities)
        self.assertIsNone(result.credential_id)

    def testCarriesTheCredentialRestrictions(self) -> None:
        """Read the optional fields of a token backed result.

        Validates the values the identity middleware copies into the
        authentication context.
        """
        identity = object()
        result = GuardResult(
            identity=identity,
            guard="token",
            abilities=frozenset({"users.view"}),
            credential_id=17,
        )
        self.assertIs(result.identity, identity)
        self.assertEqual(result.guard, "token")
        self.assertEqual(result.abilities, frozenset({"users.view"}))
        self.assertEqual(result.credential_id, 17)

    def testIsBuiltWithKeywordsOnly(self) -> None:
        """Try to build a result with positional arguments.

        Validates the keyword only contract that keeps call sites
        readable as the entity grows.
        """
        with self.assertRaises(TypeError):
            GuardResult(object(), "session")  # type: ignore[misc]
