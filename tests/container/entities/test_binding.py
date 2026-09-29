from __future__ import annotations
from dataclasses import FrozenInstanceError
from orionis.test import TestCase
from orionis.container.entities.binding import Binding
from orionis.container.enums.lifetimes import Lifetime

class TestBinding(TestCase):

    # ------------------------------------------------------------------
    # Instantiation — default values
    # ------------------------------------------------------------------

    def testDefaultInstantiationAllNoneFields(self) -> None:
        """
        Test that a Binding created with no arguments uses expected defaults.

        Verifies that contract, concrete, instance, and alias default to None,
        and that lifetime defaults to Lifetime.TRANSIENT.

        Returns
        -------
        None
            This method does not return a value.
        """
        binding = Binding()

        self.assertIsNone(binding.contract)
        self.assertIsNone(binding.concrete)
        self.assertIsNone(binding.instance)
        self.assertIsNone(binding.alias)
        self.assertIs(binding.lifetime, Lifetime.TRANSIENT)

    # ------------------------------------------------------------------
    # Instantiation — explicit values
    # ------------------------------------------------------------------

    def testInstantiationWithContract(self) -> None:
        """
        Test that the contract field stores the supplied type correctly.

        Returns
        -------
        None
            This method does not return a value.
        """
        class IService:
            pass

        binding = Binding(contract=IService)
        self.assertIs(binding.contract, IService)

    def testInstantiationWithConcrete(self) -> None:
        """
        Test that the concrete field stores the supplied implementation type.

        Returns
        -------
        None
            This method does not return a value.
        """
        class ServiceImpl:
            pass

        binding = Binding(concrete=ServiceImpl)
        self.assertIs(binding.concrete, ServiceImpl)

    def testInstantiationWithInstance(self) -> None:
        """
        Test that the instance field stores any arbitrary object.

        Returns
        -------
        None
            This method does not return a value.
        """
        obj = object()
        binding = Binding(instance=obj)
        self.assertIs(binding.instance, obj)

    def testInstantiationWithAlias(self) -> None:
        """
        Test that the alias field stores the supplied string.

        Returns
        -------
        None
            This method does not return a value.
        """
        binding = Binding(alias="my_service")
        self.assertEqual(binding.alias, "my_service")

    def testInstantiationWithAllLifetimes(self) -> None:
        """
        Test that each Lifetime enum value is accepted without error.

        Iterates over TRANSIENT, SINGLETON, and SCOPED to confirm the
        field stores the exact enum member supplied.

        Returns
        -------
        None
            This method does not return a value.
        """
        for lt in Lifetime:
            binding = Binding(lifetime=lt)
            self.assertIs(binding.lifetime, lt)

    def testInstantiationWithAllFieldsSet(self) -> None:
        """
        Test that all fields can be provided simultaneously with correct storage.

        Returns
        -------
        None
            This method does not return a value.
        """
        class IFoo:
            pass

        class FooImpl(IFoo):
            pass

        instance = FooImpl()
        binding = Binding(
            contract=IFoo,
            concrete=FooImpl,
            instance=instance,
            lifetime=Lifetime.SINGLETON,
            alias="foo",
        )

        self.assertIs(binding.contract, IFoo)
        self.assertIs(binding.concrete, FooImpl)
        self.assertIs(binding.instance, instance)
        self.assertIs(binding.lifetime, Lifetime.SINGLETON)
        self.assertEqual(binding.alias, "foo")

    # ------------------------------------------------------------------
    # Frozen dataclass — immutability
    # ------------------------------------------------------------------

    def testFrozenDataclassPreventsAttributeMutation(self) -> None:
        """
        Verify a frozen Binding raises FrozenInstanceError when a field is reassigned.

        Confirms the dataclass is truly immutable (frozen=True).

        Returns
        -------
        None
            This method does not return a value.
        """
        binding = Binding(alias="original")

        with self.assertRaises(FrozenInstanceError):
            binding.alias = "modified"  # type: ignore[misc]

    def testFrozenDataclassPreventsAddingNewAttributes(self) -> None:
        """
        Verify adding a new attribute to a frozen Binding raises FrozenInstanceError.

        Returns
        -------
        None
            This method does not return a value.
        """
        binding = Binding()
        with self.assertRaises(FrozenInstanceError):
            binding.new_field = "value"  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # __post_init__ validation
    # ------------------------------------------------------------------

    def testInvalidLifetimeTypeRaisesTypeError(self) -> None:
        """
        Verify that a non-Lifetime value for the lifetime field raises TypeError.

        Confirms the __post_init__ guard rejects invalid types such as strings
        or integers.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(TypeError):
            Binding(lifetime="singleton")  # type: ignore[arg-type]

    def testInvalidLifetimeIntRaisesTypeError(self) -> None:
        """
        Test that providing an integer for lifetime raises TypeError.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(TypeError):
            Binding(lifetime=1)  # type: ignore[arg-type]

    def testValidLifetimeEnumDoesNotRaise(self) -> None:
        """
        Test that each valid Lifetime enum member passes __post_init__ validation.

        Returns
        -------
        None
            This method does not return a value.
        """
        for lt in Lifetime:
            try:
                Binding(lifetime=lt)
            except TypeError:
                self.fail(f"Binding raised TypeError for valid lifetime {lt!r}")

    # ------------------------------------------------------------------
    # Equality and hashing (frozen dataclass behaviour)
    # ------------------------------------------------------------------

    def testEqualBindingsAreEqual(self) -> None:
        """
        Test that two Binding instances with identical fields compare as equal.

        Frozen dataclasses implement __eq__ by comparing all fields.

        Returns
        -------
        None
            This method does not return a value.
        """
        class Svc:
            pass

        b1 = Binding(contract=Svc, lifetime=Lifetime.SINGLETON, alias="svc")
        b2 = Binding(contract=Svc, lifetime=Lifetime.SINGLETON, alias="svc")
        self.assertEqual(b1, b2)

    def testDifferentBindingsAreNotEqual(self) -> None:
        """
        Test that Binding instances with differing fields are not equal.

        Returns
        -------
        None
            This method does not return a value.
        """
        b1 = Binding(alias="a")
        b2 = Binding(alias="b")
        self.assertNotEqual(b1, b2)

    def testFrozenBindingIsHashable(self) -> None:
        """
        Verify a frozen Binding instance can be used as a dictionary key or set member.

        Returns
        -------
        None
            This method does not return a value.
        """
        binding = Binding(alias="hashable")
        result = {binding: "value"}
        self.assertEqual(result[binding], "value")

        s = {binding}
        self.assertIn(binding, s)

    # ------------------------------------------------------------------
    # toDict (inherited from BaseEntity)
    # ------------------------------------------------------------------

    def testToDictContainsAllFieldNames(self) -> None:
        """
        Test that toDict() returns a dict with all five expected keys.

        Returns
        -------
        None
            This method does not return a value.
        """
        binding = Binding()
        result = binding.toDict()
        for key in ("contract", "concrete", "instance", "lifetime", "alias"):
            self.assertIn(key, result)

    def testToDictSerializesLifetimeToIntValue(self) -> None:
        """
        Test that toDict() converts the Lifetime enum to its integer value.

        BaseEntity serializes Enum members via their .value attribute.

        Returns
        -------
        None
            This method does not return a value.
        """
        binding = Binding(lifetime=Lifetime.SINGLETON)
        result = binding.toDict()
        self.assertEqual(result["lifetime"], Lifetime.SINGLETON.value)

    def testToDictNoneFieldsRemainNone(self) -> None:
        """
        Test that optional None fields are preserved as None in the toDict() output.

        Returns
        -------
        None
            This method does not return a value.
        """
        binding = Binding()
        result = binding.toDict()
        self.assertIsNone(result["contract"])
        self.assertIsNone(result["concrete"])
        self.assertIsNone(result["instance"])
        self.assertIsNone(result["alias"])

    def testToDictWithAliasReflectsCorrectValue(self) -> None:
        """
        Test that toDict() reflects the alias string stored in the Binding.

        Returns
        -------
        None
            This method does not return a value.
        """
        binding = Binding(alias="my_alias")
        self.assertEqual(binding.toDict()["alias"], "my_alias")

    # ------------------------------------------------------------------
    # getFields (inherited from BaseEntity)
    # ------------------------------------------------------------------

    def testGetFieldsReturnsList(self) -> None:
        """
        Test that getFields() returns a list.

        Returns
        -------
        None
            This method does not return a value.
        """
        binding = Binding()
        result = binding.getFields()
        self.assertIsInstance(result, list)

    def testGetFieldsLengthMatchesNumberOfFields(self) -> None:
        """
        Test that getFields() returns an entry for each declared dataclass field.

        Binding declares five fields: contract, concrete, instance, lifetime, alias.

        Returns
        -------
        None
            This method does not return a value.
        """
        binding = Binding()
        self.assertEqual(len(binding.getFields()), 5)

    def testGetFieldsContainsExpectedFieldNames(self) -> None:
        """
        Test that getFields() includes entries for all five declared field names.

        Returns
        -------
        None
            This method does not return a value.
        """
        binding = Binding()
        names = [f["name"] for f in binding.getFields()]
        for expected in ("contract", "concrete", "instance", "lifetime", "alias"):
            self.assertIn(expected, names)

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def testAliasEmptyStringIsAccepted(self) -> None:
        """
        Test that an empty string is a valid alias value.

        Returns
        -------
        None
            This method does not return a value.
        """
        binding = Binding(alias="")
        self.assertEqual(binding.alias, "")

    def testContractCanBeBuiltinType(self) -> None:
        """
        Test that built-in types like str, int, or list are valid contract values.

        Returns
        -------
        None
            This method does not return a value.
        """
        for builtin in (str, int, list, dict):
            binding = Binding(contract=builtin)
            self.assertIs(binding.contract, builtin)

    def testInstanceCanBeAnyObject(self) -> None:
        """
        Test that the instance field accepts arbitrary Python objects.

        Covers strings, integers, lists, and custom class instances.

        Returns
        -------
        None
            This method does not return a value.
        """
        for obj in ("a string", 42, [1, 2], {"k": "v"}):
            binding = Binding(instance=obj)
            self.assertEqual(binding.instance, obj)
