from orionis.auth.concerns.authenticatable import Authenticatable
from orionis.auth.contracts.authenticatable import IAuthenticatable
from orionis.test import TestCase


class _Meta:
    """Model metadata double publishing a primary key name."""

    __slots__ = ("primary_key",)

    def __init__(self, primary_key: str) -> None:
        """Store the primary key name the metadata advertises."""
        self.primary_key = primary_key


class _Identity(Authenticatable):
    """Identity using the default ``id`` and ``password`` attributes."""

    __slots__ = ("id", "password")

    def __init__(self, identifier: int, stored_hash: object) -> None:
        """Store the identifier and the value kept in the hash column."""
        self.id = identifier
        self.password = stored_hash


class _CustomKeyIdentity(Authenticatable):
    """Identity whose key and hash columns carry non default names."""

    __slots__ = ("credential_hash", "uuid")

    __meta__ = _Meta("uuid")

    AUTH_PASSWORD = "credential_hash"  # noqa: S105

    def __init__(self, uuid: str, stored_hash: str) -> None:
        """Store the custom key and the custom hash column."""
        self.uuid = uuid
        self.credential_hash = stored_hash


class _UnsavedIdentity(Authenticatable):
    """Identity that was never persisted, so it holds no key."""

    __slots__ = ()


class TestAuthenticatableLayout(TestCase):
    """Validate how the mixin is attached to an application model."""

    def testIsAVirtualImplementationOfTheContract(self) -> None:
        """Compare the mixin against the contract it fulfils.

        Validates the registration strategy: inheriting from the abstract
        base would clash with the metaclass of every Orionis model, so
        the mixin is registered as a virtual subclass instead.
        """
        self.assertTrue(issubclass(Authenticatable, IAuthenticatable))
        self.assertNotIn(IAuthenticatable, Authenticatable.__mro__)

    def testStaysDictionaryFree(self) -> None:
        """Read the ``__slots__`` declared by the mixin.

        Validates that mixing it into a slotted model never reintroduces
        a per instance dictionary.
        """
        self.assertEqual(Authenticatable.__slots__, ())
        self.assertFalse(hasattr(_Identity(7, "hashed"), "__dict__"))


class TestAuthenticatableAccessors(TestCase):
    """Validate the values the guards read from an identity."""

    def testReadsTheDefaultPrimaryKey(self) -> None:
        """Query an identity that relies on the default metadata.

        Validates that a model without ORM metadata still answers with
        the conventional ``id`` attribute.
        """
        identity = _Identity(7, "hashed")
        self.assertEqual(identity.getAuthIdentifierName(), "id")
        self.assertEqual(identity.getAuthIdentifier(), 7)

    def testReadsTheStoredHash(self) -> None:
        """Query the password accessor of a persisted identity.

        Validates the value handed to the hashing module when verifying
        submitted credentials.
        """
        self.assertEqual(_Identity(7, "hashed").getAuthPassword(), "hashed")

    def testHonoursACustomPrimaryKeyAndHashColumn(self) -> None:
        """Query an identity declaring both overrides.

        Validates that models are free to use a UUID key and to store the
        hash under a column of their choosing.
        """
        identity = _CustomKeyIdentity("abc", "hashed")
        self.assertEqual(identity.getAuthIdentifierName(), "uuid")
        self.assertEqual(identity.getAuthIdentifier(), "abc")
        self.assertEqual(identity.getAuthPassword(), "hashed")

    def testAnUnsavedIdentityHasNoIdentifier(self) -> None:
        """Query an identity whose key attribute was never assigned.

        Validates that the accessor answers ``None`` instead of raising,
        so the guards can reject it explicitly.
        """
        self.assertIsNone(_UnsavedIdentity().getAuthIdentifier())

    def testANonTextualHashIsNeverHandedToTheHasher(self) -> None:
        """Query the password accessor of a row with an empty column.

        Validates the defensive answer: the hashing module always
        receives a string, never ``None`` or another type.
        """
        self.assertEqual(_Identity(7, None).getAuthPassword(), "")
        self.assertEqual(_Identity(7, 1234).getAuthPassword(), "")
