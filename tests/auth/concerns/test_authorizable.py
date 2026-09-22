from orionis.auth.concerns.authorizable import Authorizable
from orionis.auth.contracts.authorizable import IAuthorizable
from orionis.test import TestCase


class _Meta:
    """Model metadata double publishing a primary key name."""

    __slots__ = ("primary_key",)

    def __init__(self, primary_key: str) -> None:
        """Store the primary key name the metadata advertises."""
        self.primary_key = primary_key


class _Owner(Authorizable):
    """Permission owner relying on the derived polymorphic type."""

    __slots__ = ("id",)

    def __init__(self, identifier: int) -> None:
        """Store the identifier written in the pivot tables."""
        self.id = identifier


class _RenamedOwner(Authorizable):
    """Permission owner pinning its polymorphic type explicitly."""

    __slots__ = ("uuid",)

    __meta__ = _Meta("uuid")

    AUTHORIZABLE_TYPE = "tests.CustomIdentity"

    def __init__(self, uuid: str) -> None:
        """Store the custom primary key value."""
        self.uuid = uuid


class _UnsavedOwner(Authorizable):
    """Permission owner that was never persisted."""

    __slots__ = ()


class TestAuthorizableLayout(TestCase):
    """Validate how the mixin is attached to an application model."""

    def testIsAVirtualImplementationOfTheContract(self) -> None:
        """Compare the mixin against the contract it fulfils.

        Validates the registration strategy that keeps ``ModelMeta`` and
        ``ABCMeta`` from clashing.
        """
        self.assertTrue(issubclass(Authorizable, IAuthorizable))
        self.assertNotIn(IAuthorizable, Authorizable.__mro__)

    def testStaysDictionaryFree(self) -> None:
        """Read the ``__slots__`` declared by the mixin.

        Validates that mixing it into a slotted model never reintroduces
        a per instance dictionary.
        """
        self.assertEqual(Authorizable.__slots__, ())
        self.assertFalse(hasattr(_Owner(7), "__dict__"))


class TestAuthorizableAccessors(TestCase):
    """Validate the polymorphic pair stored in the pivot tables."""

    def testDerivesThePolymorphicTypeFromTheClass(self) -> None:
        """Query an owner that declares no explicit type.

        Validates the default dotted path written in the ``model_type``
        column.
        """
        owner = _Owner(7)
        self.assertEqual(
            owner.getAuthorizableType(), f"{__name__}.{type(owner).__qualname__}",
        )
        self.assertEqual(owner.getAuthorizableId(), 7)

    def testHonoursAnExplicitPolymorphicType(self) -> None:
        """Query an owner pinning its own type.

        Validates the override that keeps stored rows valid when a class
        is renamed or moved to another module.
        """
        owner = _RenamedOwner("abc")
        self.assertEqual(owner.getAuthorizableType(), "tests.CustomIdentity")
        self.assertEqual(owner.getAuthorizableId(), "abc")

    def testAnUnsavedOwnerHasNoIdentifier(self) -> None:
        """Query an owner whose key attribute was never assigned.

        Validates that the accessor answers ``None`` so the repository
        can refuse to write an orphan row.
        """
        self.assertIsNone(_UnsavedOwner().getAuthorizableId())
