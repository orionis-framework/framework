# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from orionis.support.types.std import StdClass
from orionis.test import TestCase


class TestStdClass(TestCase):
    # ------------------------------------------------ __init__ / update

    def testInitWithNoArguments(self) -> None:
        """Initialize StdClass with no arguments.

        Validates that a StdClass created without keyword arguments
        has an empty attribute dictionary.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass()
        self.assertEqual(obj.toDict(), {})

    def testInitSetsAttributesFromKwargs(self) -> None:
        """Initialize StdClass with keyword arguments.

        Validates that keyword arguments passed at construction
        are stored as object attributes.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(name="orionis", version=1)
        self.assertEqual(obj.name, "orionis")
        self.assertEqual(obj.version, 1)

    def testInitWithNoneValue(self) -> None:
        """Initialize StdClass with None as a value.

        Validates that None can be stored as an attribute value
        and is retrieved correctly.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(value=None)
        self.assertIsNone(obj.value)

    def testUpdateAddsNewAttributes(self) -> None:
        """Add new attributes via update.

        Validates that update creates new object attributes
        from the provided keyword arguments.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass()
        obj.update(x=10, y=20)
        self.assertEqual(obj.x, 10)
        self.assertEqual(obj.y, 20)

    def testUpdateOverwritesExistingAttribute(self) -> None:
        """Overwrite an existing attribute via update.

        Validates that update replaces the value of an
        already-existing attribute.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(key="old")
        obj.update(key="new")
        self.assertEqual(obj.key, "new")

    def testUpdateRaisesOnDunderAttribute(self) -> None:
        """Raise ValueError when setting a dunder attribute.

        Validates that update raises ValueError when given
        a key surrounded by double underscores.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass()
        with self.assertRaises(ValueError):
            obj.update(__reserved__="bad")

    def testUpdateRaisesOnClassMethodConflict(self) -> None:
        """Raise ValueError when attribute conflicts with class method.

        Validates that update raises ValueError when the key
        matches an existing method name on StdClass.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass()
        with self.assertRaises(ValueError):
            obj.update(toDict="conflict")

    def testUpdateRejectsRemoveMethodConflict(self) -> None:
        """Raise on the first conflicting attribute in update.

        Validates that update stops at the first violation when
        multiple conflicting keys are provided.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass()
        with self.assertRaises(ValueError):
            obj.update(remove="bad")

    # ------------------------------------------------ remove

    def testRemoveDeletesAttribute(self) -> None:
        """Remove an existing attribute from the object.

        Validates that remove deletes the attribute from the
        object and the attribute is no longer accessible.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(x=1, y=2)
        obj.remove("x")
        self.assertFalse(hasattr(obj, "x"))
        self.assertTrue(hasattr(obj, "y"))

    def testRemoveMultipleAttributes(self) -> None:
        """Remove multiple attributes at once.

        Validates that remove accepts multiple names and
        deletes all of them from the object.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(a=1, b=2, c=3)
        obj.remove("a", "b")
        self.assertFalse(hasattr(obj, "a"))
        self.assertFalse(hasattr(obj, "b"))
        self.assertTrue(hasattr(obj, "c"))

    def testRemoveRaisesAttributeErrorForMissingAttr(self) -> None:
        """Raise AttributeError when removing a nonexistent attribute.

        Validates that attempting to remove an attribute that
        does not exist raises an AttributeError.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass()
        with self.assertRaises(AttributeError):
            obj.remove("nonexistent")

    def testRemoveErrorMessageContainsAttributeName(self) -> None:
        """Include attribute name in the AttributeError message.

        Validates that the raised AttributeError message contains
        the name of the missing attribute.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass()
        with self.assertRaises(AttributeError) as ctx:
            obj.remove("missing_attr")
        self.assertIn("missing_attr", str(ctx.exception))

    def testRemoveAllAttributesLeavesEmptyDict(self) -> None:
        """Produce an empty dict after removing all attributes.

        Validates that removing every attribute results in
        an empty toDict() return.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(a=1, b=2)
        obj.remove("a", "b")
        self.assertEqual(obj.toDict(), {})

    # ------------------------------------------------ toDict

    def testToDictReturnsShallowCopy(self) -> None:
        """Return a shallow copy from toDict.

        Validates that toDict produces a copy and that
        mutating it does not affect the original object.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(x=1)
        d = obj.toDict()
        d["x"] = 999
        self.assertEqual(obj.x, 1)

    def testToDictContainsAllAttributes(self) -> None:
        """Include all set attributes in toDict output.

        Validates that toDict returns a dict with every
        attribute name and value stored in the object.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(name="test", flag=True, count=3)
        result = obj.toDict()
        self.assertEqual(result, {"name": "test", "flag": True, "count": 3})

    def testToDictIsPlainDict(self) -> None:
        """Return a plain dict from toDict.

        Validates that the returned value is an instance
        of the built-in dict type.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(a=1)
        self.assertIsInstance(obj.toDict(), dict)

    def testToDictAfterUpdateReflectsNewAttributes(self) -> None:
        """Reflect updated attributes in toDict.

        Validates that attributes added via update appear
        in the toDict output.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(x=1)
        obj.update(y=2)
        self.assertIn("y", obj.toDict())

    def testToDictAfterRemoveExcludesRemovedAttribute(self) -> None:
        """Exclude removed attributes from toDict.

        Validates that an attribute deleted via remove no
        longer appears in the toDict output.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(a=1, b=2)
        obj.remove("a")
        self.assertNotIn("a", obj.toDict())

    # ------------------------------------------------ fromDict

    def testFromDictCreatesInstance(self) -> None:
        """Create a StdClass instance from a dictionary.

        Validates that fromDict produces a StdClass with
        attributes matching the provided dictionary.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass.fromDict({"x": 10, "y": 20})
        self.assertIsInstance(obj, StdClass)
        self.assertEqual(obj.x, 10)
        self.assertEqual(obj.y, 20)

    def testFromDictWithEmptyDict(self) -> None:
        """Create an empty StdClass from an empty dictionary.

        Validates that fromDict with an empty dict produces
        an object with no attributes.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass.fromDict({})
        self.assertEqual(obj.toDict(), {})

    def testFromDictPreservesValueTypes(self) -> None:
        """Preserve value types when creating from dict.

        Validates that fromDict correctly stores different
        Python types as attributes.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass.fromDict({"n": 1, "s": "text", "b": True, "lst": [1, 2]})
        self.assertEqual(obj.n, 1)
        self.assertEqual(obj.s, "text")
        self.assertTrue(obj.b)
        self.assertEqual(obj.lst, [1, 2])

    def testFromDictRoundtrip(self) -> None:
        """Produce equal data in fromDict-toDict roundtrip.

        Validates that converting a dict to StdClass and back
        yields the original dictionary.

        Returns
        -------
        None
            No return value.
        """
        original = {"a": 1, "b": "hello"}
        obj = StdClass.fromDict(original)
        self.assertEqual(obj.toDict(), original)

    # ------------------------------------------------ __eq__

    def testEqualityWithSameAttributes(self) -> None:
        """Compare equal objects with identical attributes.

        Validates that two StdClass instances with the same
        attributes and values are considered equal.

        Returns
        -------
        None
            No return value.
        """
        a = StdClass(x=1, y=2)
        b = StdClass(x=1, y=2)
        self.assertEqual(a, b)

    def testInequalityWithDifferentValues(self) -> None:
        """Distinguish objects with different attribute values.

        Validates that StdClass instances with different values
        for the same attribute are not equal.

        Returns
        -------
        None
            No return value.
        """
        a = StdClass(x=1)
        b = StdClass(x=2)
        self.assertNotEqual(a, b)

    def testInequalityWithDifferentKeys(self) -> None:
        """Distinguish objects with different attribute names.

        Validates that StdClass instances with different attribute
        names are not considered equal.

        Returns
        -------
        None
            No return value.
        """
        a = StdClass(x=1)
        b = StdClass(y=1)
        self.assertNotEqual(a, b)

    def testInequalityWithNonStdClassObject(self) -> None:
        """Return False when comparing with a non-StdClass object.

        Validates that equality check against a plain dict or
        other types returns False.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(x=1)
        self.assertNotEqual(obj, {"x": 1})
        self.assertNotEqual(obj, None)
        self.assertNotEqual(obj, 42)

    def testEmptyObjectsAreEqual(self) -> None:
        """Treat two empty StdClass instances as equal.

        Validates that two StdClass objects with no attributes
        compare as equal.

        Returns
        -------
        None
            No return value.
        """
        a = StdClass()
        b = StdClass()
        self.assertEqual(a, b)

    # ------------------------------------------------ __hash__

    def testHashIsConsistentForSameAttributes(self) -> None:
        """Return consistent hash for identical attributes.

        Validates that two StdClass instances with the same
        attributes produce the same hash value.

        Returns
        -------
        None
            No return value.
        """
        a = StdClass(x=1, y=2)
        b = StdClass(x=1, y=2)
        self.assertEqual(hash(a), hash(b))

    def testHashChangesAfterAttributeUpdate(self) -> None:
        """Change hash value after attribute update.

        Validates that modifying attributes alters the hash
        since the hash is based on the attribute dictionary.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(x=1)
        h1 = hash(obj)
        obj.update(x=99)
        h2 = hash(obj)
        self.assertNotEqual(h1, h2)

    def testEmptyObjectHasConsistentHash(self) -> None:
        """Produce consistent hash for empty objects.

        Validates that two empty StdClass instances have
        the same hash value.

        Returns
        -------
        None
            No return value.
        """
        a = StdClass()
        b = StdClass()
        self.assertEqual(hash(a), hash(b))

    # ------------------------------------------------ __repr__ / __str__

    def testReprContainsClassName(self) -> None:
        """Include class name in repr output.

        Validates that the repr of a StdClass instance starts
        with the class name.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(a=1)
        self.assertIn("StdClass", repr(obj))

    def testReprContainsAttributes(self) -> None:
        """Include attribute values in repr output.

        Validates that the repr output contains the attribute
        names and their values.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(x=42)
        self.assertIn("x", repr(obj))
        self.assertIn("42", repr(obj))

    def testStrReturnsAttributeString(self) -> None:
        """Return attribute dict string from str conversion.

        Validates that converting a StdClass to str returns
        a string representation of its attribute dictionary.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(a=1)
        self.assertIn("a", str(obj))
        self.assertIn("1", str(obj))

    def testReprIsString(self) -> None:
        """Return a string type from repr.

        Validates that repr produces a str instance.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass()
        self.assertIsInstance(repr(obj), str)

    def testStrIsString(self) -> None:
        """Return a string type from str conversion.

        Validates that str conversion produces a str instance.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass()
        self.assertIsInstance(str(obj), str)

    # ------------------------------------------------ attribute access

    def testDirectAttributeAccess(self) -> None:
        """Access attributes directly via dot notation.

        Validates that attributes set via keyword arguments
        can be retrieved using standard attribute access.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(color="blue", count=5)
        self.assertEqual(obj.color, "blue")
        self.assertEqual(obj.count, 5)

    def testAttributeModificationViaSetattr(self) -> None:
        """Modify attributes via direct setattr.

        Validates that attributes stored in StdClass can be
        updated directly without going through update().

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(x=1)
        obj.x = 99
        self.assertEqual(obj.x, 99)

    def testHasAttrReturnsTrueForSetAttribute(self) -> None:
        """Return True from hasattr for existing attributes.

        Validates that hasattr correctly identifies attributes
        that have been set on the StdClass.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(present=True)
        self.assertTrue(hasattr(obj, "present"))

    def testHasAttrReturnsFalseForMissingAttribute(self) -> None:
        """Return False from hasattr for absent attributes.

        Validates that hasattr returns False for attribute
        names that were never set.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass()
        self.assertFalse(hasattr(obj, "absent"))

    # ------------------------------------------------ edge cases

    def testUpdateWithEmptyKwargsHasNoEffect(self) -> None:
        """Produce no change when update is called with no arguments.

        Validates that calling update with no keyword arguments
        leaves the object's attributes unchanged.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(a=1)
        obj.update()
        self.assertEqual(obj.toDict(), {"a": 1})

    def testUpdateRaisesOnUpdateMethodConflict(self) -> None:
        """Raise ValueError when 'update' itself is used as a key.

        Validates that the reserved method name 'update' cannot
        be set as an attribute.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass()
        with self.assertRaises(ValueError):
            obj.update(update="bad")

    def testRemoveRaisesOnDunderAttrName(self) -> None:
        """Raise AttributeError when removing a non-existent dunder name.

        Validates that attempting to remove an attribute named
        with dunders raises AttributeError since it was never set.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass()
        with self.assertRaises(AttributeError):
            obj.remove("__not_there__")

    def testFromDictWithNoneValues(self) -> None:
        """Handle None values in fromDict correctly.

        Validates that None values in the source dictionary are
        stored and retrieved as None attributes.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass.fromDict({"x": None, "y": 0})
        self.assertIsNone(obj.x)
        self.assertEqual(obj.y, 0)

    def testMultipleUpdateCallsAccumulate(self) -> None:
        """Accumulate attributes across multiple update calls.

        Validates that successive update calls add to the
        existing attributes rather than replacing them.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass()
        obj.update(a=1)
        obj.update(b=2)
        obj.update(c=3)
        self.assertEqual(obj.toDict(), {"a": 1, "b": 2, "c": 3})

    def testObjectIsHashable(self) -> None:
        """Confirm StdClass instances are hashable.

        Validates that a StdClass instance can be used as a
        dictionary key or added to a set.

        Returns
        -------
        None
            No return value.
        """
        obj = StdClass(x=1)
        d = {obj: "value"}
        self.assertEqual(d[obj], "value")

    def testObjectUsableInSet(self) -> None:
        """Allow StdClass instances in sets.

        Validates that StdClass objects with the same attributes
        are deduplicated when added to a set.

        Returns
        -------
        None
            No return value.
        """
        a = StdClass(x=1)
        b = StdClass(x=1)
        s = {a, b}
        self.assertEqual(len(s), 1)
