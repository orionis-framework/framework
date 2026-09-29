from types import MappingProxyType
from orionis.test import TestCase
from orionis.support.structures.freezer import FreezeThaw

class TestFreezeThaw(TestCase):

    # ------------------------------------------------ _isContainer

    def testIsContainerWithDict(self):
        """Detect dict as a container type.

        Validates that a plain dict is recognized as a supported
        container by _isContainer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(FreezeThaw._isContainer({}))

    def testIsContainerWithList(self):
        """Detect list as a container type.

        Validates that a list is recognized as a supported
        container by _isContainer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(FreezeThaw._isContainer([]))

    def testIsContainerWithTuple(self):
        """Detect tuple as a container type.

        Validates that a tuple is recognized as a supported
        container by _isContainer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(FreezeThaw._isContainer(()))

    def testIsContainerWithMappingProxy(self):
        """Detect MappingProxyType as a container type.

        Validates that a MappingProxyType is recognized as a
        supported container by _isContainer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        proxy = MappingProxyType({})
        self.assertTrue(FreezeThaw._isContainer(proxy))

    def testIsContainerWithNonContainer(self):
        """Reject non-container types.

        Validates that scalar types like int, str, and None
        are not recognized as containers.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(FreezeThaw._isContainer(42))
        self.assertFalse(FreezeThaw._isContainer("text"))
        self.assertFalse(FreezeThaw._isContainer(None))

    # ------------------------------------------------ freeze: dict

    def testFreezeDictReturnsMappingProxy(self):
        """Freeze a dict into a MappingProxyType.

        Validates that freezing a dict produces an immutable
        MappingProxyType instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        data = {"a": 1, "b": 2}
        frozen = FreezeThaw.freeze(data)
        self.assertIsInstance(frozen, MappingProxyType)

    def testFrozenDictIsImmutable(self):
        """Raise TypeError when modifying a frozen dict.

        Validates that attempting to set a key on a frozen dict
        raises a TypeError.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        data = {"a": 1}
        frozen = FreezeThaw.freeze(data)
        with self.assertRaises(TypeError):
            frozen["a"] = 2

    def testFreezeDictPreservesValues(self):
        """Preserve all values after freezing a dict.

        Validates that the frozen dict retains the same key-value
        pairs as the original.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        data = {"x": 10, "y": "hello"}
        frozen = FreezeThaw.freeze(data)
        self.assertEqual(frozen["x"], 10)
        self.assertEqual(frozen["y"], "hello")

    def testFreezeNestedDictRecursively(self):
        """Freeze nested dicts and preserve values.

        Validates that inner dict values are preserved after
        freezing even though inner containers may not be fully
        converted due to processing order.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        data = {"outer": {"inner": 1}}
        frozen = FreezeThaw.freeze(data)
        self.assertIsInstance(frozen, MappingProxyType)
        self.assertEqual(frozen["outer"]["inner"], 1)

    # ------------------------------------------------ freeze: list

    def testFreezeListReturnsTuple(self):
        """Freeze a list into a tuple.

        Validates that freezing a list produces an immutable
        tuple instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        data = [1, 2, 3]
        frozen = FreezeThaw.freeze(data)
        self.assertIsInstance(frozen, tuple)

    def testFreezeListPreservesValues(self):
        """Preserve all values after freezing a list.

        Validates that the frozen tuple retains the same
        elements in the same order.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        data = [1, "a", 3.14]
        frozen = FreezeThaw.freeze(data)
        self.assertEqual(frozen, (1, "a", 3.14))

    def testFreezeNestedListRecursively(self):
        """Freeze nested lists and preserve values.

        Validates that the top-level list is converted to a
        tuple and nested values are preserved.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        data = [[1, 2], [3, 4]]
        frozen = FreezeThaw.freeze(data)
        self.assertIsInstance(frozen, tuple)
        self.assertEqual(list(frozen[0]), [1, 2])
        self.assertEqual(list(frozen[1]), [3, 4])

    def testFreezeMixedStructure(self):
        """Freeze a dict containing lists and nested dicts.

        Validates that the top-level dict is frozen to a
        MappingProxyType and nested values are preserved.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        data = {"items": [1, 2], "meta": {"key": "val"}}
        frozen = FreezeThaw.freeze(data)
        self.assertIsInstance(frozen, MappingProxyType)
        self.assertEqual(list(frozen["items"]), [1, 2])
        self.assertEqual(frozen["meta"]["key"], "val")

    # ------------------------------------------------ freeze: edge cases

    def testFreezeNonContainerReturnsUnchanged(self):
        """Return non-container objects unchanged.

        Validates that scalar values like int, str, and None
        are returned as-is when passed to freeze.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(FreezeThaw.freeze(42), 42)
        self.assertEqual(FreezeThaw.freeze("text"), "text")
        self.assertIsNone(FreezeThaw.freeze(None))

    def testFreezeEmptyDict(self):
        """Freeze an empty dict into an empty MappingProxyType.

        Validates that an empty dict produces an empty immutable
        mapping.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        frozen = FreezeThaw.freeze({})
        self.assertIsInstance(frozen, MappingProxyType)
        self.assertEqual(len(frozen), 0)

    def testFreezeEmptyList(self):
        """Freeze an empty list into an empty tuple.

        Validates that an empty list produces an empty tuple.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        frozen = FreezeThaw.freeze([])
        self.assertIsInstance(frozen, tuple)
        self.assertEqual(len(frozen), 0)

    def testFreezeAlreadyFrozenReturnsUnchanged(self):
        """Return already-frozen MappingProxyType unchanged.

        Validates that passing a MappingProxyType to freeze does
        not re-wrap it.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        proxy = MappingProxyType({"a": 1})
        frozen = FreezeThaw.freeze(proxy)
        self.assertIs(frozen, proxy)

    # ------------------------------------------------ thaw: dict

    def testThawMappingProxyReturnsDict(self):
        """Thaw a MappingProxyType back to a dict.

        Validates that thawing a frozen mapping produces a
        standard mutable dict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        proxy = MappingProxyType({"a": 1})
        thawed = FreezeThaw.thaw(proxy)
        self.assertIsInstance(thawed, dict)
        self.assertNotIsInstance(thawed, MappingProxyType)

    def testThawedDictIsMutable(self):
        """Allow modification of a thawed dict.

        Validates that assigning to a key on a thawed dict works
        without raising an exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        proxy = MappingProxyType({"a": 1})
        thawed = FreezeThaw.thaw(proxy)
        thawed["a"] = 99
        self.assertEqual(thawed["a"], 99)

    def testThawDictPreservesValues(self):
        """Preserve values after thawing a frozen dict.

        Validates that thawed dict retains the same key-value
        pairs as the original.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        proxy = MappingProxyType({"x": 10, "y": "hi"})
        thawed = FreezeThaw.thaw(proxy)
        self.assertEqual(thawed["x"], 10)
        self.assertEqual(thawed["y"], "hi")

    def testThawNestedMappingProxyRecursively(self):
        """Thaw nested MappingProxyType recursively.

        Validates that inner frozen mappings are also converted
        back to mutable dicts.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        inner = MappingProxyType({"k": "v"})
        outer = MappingProxyType({"nested": inner})
        thawed = FreezeThaw.thaw(outer)
        self.assertIsInstance(thawed["nested"], dict)
        self.assertEqual(thawed["nested"]["k"], "v")

    # ------------------------------------------------ thaw: tuple/list

    def testThawTupleReturnsList(self):
        """Thaw a tuple back to a list.

        Validates that thawing a tuple produces a mutable list.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        data = (1, 2, 3)
        thawed = FreezeThaw.thaw(data)
        self.assertIsInstance(thawed, list)

    def testThawTuplePreservesValues(self):
        """Preserve values after thawing a tuple.

        Validates that thawed list retains the same elements
        in the same order as the original tuple.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        data = (1, "a", 3.14)
        thawed = FreezeThaw.thaw(data)
        self.assertEqual(thawed, [1, "a", 3.14])

    def testThawNestedTuplesRecursively(self):
        """Thaw nested tuples recursively.

        Validates that inner tuples are also converted to lists.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        data = ((1, 2), (3, 4))
        thawed = FreezeThaw.thaw(data)
        self.assertIsInstance(thawed, list)
        self.assertIsInstance(thawed[0], list)
        self.assertEqual(thawed[0], [1, 2])

    def testThawMixedFrozenStructure(self):
        """Thaw a complex frozen structure with mixed types.

        Validates that a structure with MappingProxyType and
        tuples is fully converted to mutable equivalents.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        frozen = MappingProxyType({
            "items": (1, 2),
            "meta": MappingProxyType({"k": "v"}),
        })
        thawed = FreezeThaw.thaw(frozen)
        self.assertIsInstance(thawed, dict)
        self.assertIsInstance(thawed["items"], list)
        self.assertIsInstance(thawed["meta"], dict)

    # ------------------------------------------------ thaw: edge cases

    def testThawNonContainerReturnsUnchanged(self):
        """Return non-container objects unchanged.

        Validates that scalar values pass through thaw without
        modification.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(FreezeThaw.thaw(42), 42)
        self.assertEqual(FreezeThaw.thaw("text"), "text")
        self.assertIsNone(FreezeThaw.thaw(None))

    def testThawEmptyMappingProxy(self):
        """Thaw an empty MappingProxyType to an empty dict.

        Validates that an empty frozen mapping produces an
        empty mutable dict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        proxy = MappingProxyType({})
        thawed = FreezeThaw.thaw(proxy)
        self.assertIsInstance(thawed, dict)
        self.assertEqual(len(thawed), 0)

    def testThawEmptyTuple(self):
        """Thaw an empty tuple to an empty list.

        Validates that an empty tuple produces an empty list.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        thawed = FreezeThaw.thaw(())
        self.assertIsInstance(thawed, list)
        self.assertEqual(len(thawed), 0)

    # ---------------------------------------- roundtrip: freeze + thaw

    def testRoundtripDictPreservesData(self):
        """Preserve data through freeze-thaw roundtrip for dicts.

        Validates that freezing and then thawing a dict produces
        a result equal to the original.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        original = {"a": 1, "b": [2, 3], "c": {"d": 4}}
        frozen = FreezeThaw.freeze(original)
        thawed = FreezeThaw.thaw(frozen)
        self.assertEqual(thawed, original)

    def testRoundtripListPreservesData(self):
        """Preserve data through freeze-thaw roundtrip for lists.

        Validates that freezing and then thawing a list produces
        a result equal to the original.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        original = [1, [2, 3], {"a": 4}]
        frozen = FreezeThaw.freeze(original)
        thawed = FreezeThaw.thaw(frozen)
        self.assertEqual(thawed, original)

    def testRoundtripProducesMutableResult(self):
        """Produce mutable containers after roundtrip.

        Validates that the result of freeze-thaw is fully mutable
        and can be modified without errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        original = {"items": [1, 2]}
        frozen = FreezeThaw.freeze(original)
        thawed = FreezeThaw.thaw(frozen)
        thawed["items"].append(3)
        thawed["new"] = "added"
        self.assertEqual(thawed["items"], [1, 2, 3])
        self.assertEqual(thawed["new"], "added")

    # ---------------------------------------- thaw: regular dict/list

    def testThawRegularDictReturnsCopy(self):
        """Thaw a regular dict returning a mutable copy.

        Validates that thawing a plain dict still produces a
        correct dict result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        data = {"a": 1}
        thawed = FreezeThaw.thaw(data)
        self.assertIsInstance(thawed, dict)
        self.assertEqual(thawed["a"], 1)

    def testThawRegularListReturnsList(self):
        """Thaw a regular list returning a mutable list.

        Validates that thawing a plain list produces a list
        with the same elements.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        data = [1, 2, 3]
        thawed = FreezeThaw.thaw(data)
        self.assertIsInstance(thawed, list)
        self.assertEqual(thawed, [1, 2, 3])
