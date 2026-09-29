from orionis.auth.concerns.authorizable import Authorizable
from orionis.auth.contracts.authorizable import IAuthorizable
from orionis.test import TestCase

class _Meta:
    """Model metadata double publishing a primary key name."""

    __slots__ = ("primary_key",)

    def __init__(self, primary_key: str) -> None:
        """Store the primary key name advertised by the metadata.

        Parameters
        ----------
        primary_key : str
            Name of the model's primary key.

        Returns
        -------
        None
            Initializes the metadata double.
        """
        self.primary_key = primary_key

class _Owner(Authorizable):
    """Permission owner relying on the derived polymorphic type."""

    __slots__ = ("id",)

    def __init__(self, identifier: int) -> None:
        """Store the identifier written in pivot tables.

        Parameters
        ----------
        identifier : int
            Owner identifier.

        Returns
        -------
        None
            Initializes the permission owner.
        """
        self.id = identifier

class _RenamedOwner(Authorizable):
    """Permission owner pinning its polymorphic type explicitly."""

    __slots__ = ("uuid",)

    __meta__ = _Meta("uuid")

    AUTHORIZABLE_TYPE = "tests.CustomIdentity"

    def __init__(self, uuid: str) -> None:
        """Store the custom primary key value.

        Parameters
        ----------
        uuid : str
            Owner's UUID value.

        Returns
        -------
        None
            Initializes the renamed permission owner.
        """
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

        Returns
        -------
        None
            Asserts virtual contract registration without MRO inheritance.
        """
        self.assertTrue(issubclass(Authorizable, IAuthorizable))
        self.assertNotIn(IAuthorizable, Authorizable.__mro__)

    def testStaysDictionaryFree(self) -> None:
        """Read the ``__slots__`` declared by the mixin.

        Validates that mixing it into a slotted model never reintroduces
        a per instance dictionary.

        Returns
        -------
        None
            Asserts that the mixin preserves slotted instance layout.
        """
        self.assertEqual(Authorizable.__slots__, ())
        self.assertFalse(hasattr(_Owner(7), "__dict__"))

class TestAuthorizableAccessors(TestCase):
    """Validate the polymorphic pair stored in the pivot tables."""

    def testDerivesThePolymorphicTypeFromTheClass(self) -> None:
        """Query an owner that declares no explicit type.

        Validates the default dotted path written in the ``model_type``
        column.

        Returns
        -------
        None
            Asserts the derived polymorphic type and owner identifier.
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

        Returns
        -------
        None
            Asserts the explicit polymorphic type and UUID are returned.
        """
        owner = _RenamedOwner("abc")
        self.assertEqual(owner.getAuthorizableType(), "tests.CustomIdentity")
        self.assertEqual(owner.getAuthorizableId(), "abc")

    def testAnUnsavedOwnerHasNoIdentifier(self) -> None:
        """Query an owner whose key attribute was never assigned.

        Validates that the accessor answers ``None`` so the repository
        can refuse to write an orphan row.

        Returns
        -------
        None
            Asserts that an unsaved owner has no identifier.
        """
        self.assertIsNone(_UnsavedOwner().getAuthorizableId())
