from orionis.test import TestCase
from orionis.support.types.dot_dict import DotDict

class TestDotDict(TestCase):

    # ------------------------------------------------ __getattr__

    def testGetAttrReturnsValue(self):
        """Return value for an existing key via attribute access.

        Validates that attribute-style access retrieves the correct
        value stored in the DotDict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"name": "orionis"})
        self.assertEqual(d.name, "orionis")

    def testGetAttrReturnsNoneForMissingKey(self):
        """Return None when the key does not exist.

        Validates that accessing a nonexistent attribute returns None
        instead of raising an exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"a": 1})
        self.assertIsNone(d.missing_key)

    def testGetAttrConvertsNestedDictToDotDict(self):
        """Convert nested plain dict to DotDict on access.

        Validates that a nested dict value is automatically wrapped
        in a DotDict to allow recursive attribute access.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"nested": {"key": "value"}})
        result = d.nested
        self.assertIsInstance(result, DotDict)
        self.assertEqual(result.key, "value")

    def testGetAttrPreservesExistingDotDict(self):
        """Preserve already-wrapped DotDict on access.

        Validates that accessing a value that is already a DotDict
        does not re-wrap it.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        inner = DotDict({"x": 10})
        d = DotDict({"inner": inner})
        self.assertIs(d.inner, inner)

    def testGetAttrCachesConvertedDotDict(self):
        """Cache the converted DotDict in the underlying dict.

        Validates that after the first attribute access converts a
        plain dict, subsequent accesses return the same instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"child": {"a": 1}})
        first = d.child
        second = d.child
        self.assertIs(first, second)

    def testGetAttrWithNonStringKey(self):
        """Return None for attribute names not present as keys.

        Validates that arbitrary attribute names that were never set
        return None gracefully.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict()
        self.assertIsNone(d.anything)

    # ------------------------------------------------ __setattr__

    def testSetAttrStoresValue(self):
        """Store a value via attribute-style assignment.

        Validates that setting an attribute stores it as a dictionary
        key-value pair.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict()
        d.name = "test"
        self.assertEqual(d["name"], "test")

    def testSetAttrConvertsDictToDotDict(self):
        """Convert plain dict to DotDict on attribute assignment.

        Validates that assigning a plain dict via attribute syntax
        automatically converts it to a DotDict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict()
        d.config = {"debug": True}
        self.assertIsInstance(d["config"], DotDict)
        self.assertTrue(d.config.debug)

    def testSetAttrPreservesDotDict(self):
        """Preserve DotDict instances on attribute assignment.

        Validates that assigning a DotDict value does not double-wrap
        it in another DotDict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        inner = DotDict({"z": 42})
        d = DotDict()
        d.inner = inner
        self.assertIs(d["inner"], inner)

    def testSetAttrOverwritesExistingKey(self):
        """Overwrite an existing key via attribute assignment.

        Validates that re-assigning an attribute replaces the
        previous value stored under the same key.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"key": "old"})
        d.key = "new"
        self.assertEqual(d.key, "new")

    def testSetAttrWithNoneValue(self):
        """Store None via attribute assignment.

        Validates that None can be stored and retrieved correctly
        through attribute-style access.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict()
        d.value = None
        self.assertIsNone(d.value)
        self.assertIn("value", d)

    # ------------------------------------------------ __delattr__

    def testDelAttrRemovesKey(self):
        """Remove an existing key via attribute deletion.

        Validates that deleting an attribute removes the key from
        the underlying dictionary.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"key": "value"})
        del d.key
        self.assertNotIn("key", d)

    def testDelAttrRaisesAttributeErrorForMissingKey(self):
        """Raise AttributeError when deleting a nonexistent attribute.

        Validates that attempting to delete a key that does not exist
        raises an AttributeError with a descriptive message.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict()
        with self.assertRaises(AttributeError) as ctx:
            del d.nonexistent
        self.assertIn("nonexistent", str(ctx.exception))

    def testDelAttrErrorMessageContainsClassName(self):
        """Include class name in the AttributeError message.

        Validates that the error message references the DotDict
        class name for clarity.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict()
        with self.assertRaises(AttributeError) as ctx:
            del d.missing
        self.assertIn("DotDict", str(ctx.exception))

    # ------------------------------------------------ get

    def testGetReturnsValueForExistingKey(self):
        """Return the value for an existing key.

        Validates that the get method retrieves the correct value
        when the key is present in the DotDict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"x": 5})
        self.assertEqual(d.get("x"), 5)

    def testGetReturnsDefaultForMissingKey(self):
        """Return the default value when the key is absent.

        Validates that get falls back to the provided default
        when the requested key is not found.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict()
        self.assertEqual(d.get("missing", 42), 42)

    def testGetReturnsNoneWhenNoDefault(self):
        """Return None when key is absent and no default is given.

        Validates that get returns None by default for missing keys
        when no explicit default is provided.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict()
        self.assertIsNone(d.get("absent"))

    def testGetConvertsNestedDictToDotDict(self):
        """Convert nested dict to DotDict on retrieval via get.

        Validates that get automatically wraps a plain dict value
        in a DotDict for consistent attribute access.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"cfg": {"level": 3}})
        result = d.get("cfg")
        self.assertIsInstance(result, DotDict)
        self.assertEqual(result.level, 3)

    def testGetCachesConvertedDotDict(self):
        """Cache converted DotDict after get call.

        Validates that the plain dict is replaced in the underlying
        storage after conversion via get.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"data": {"a": 1}})
        d.get("data")
        self.assertIsInstance(d["data"], DotDict)

    # ------------------------------------------------ export

    def testExportReturnsPlainDict(self):
        """Export DotDict as a standard dictionary.

        Validates that export returns a plain dict, not a DotDict
        instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"a": 1})
        result = d.export()
        self.assertIsInstance(result, dict)
        self.assertNotIsInstance(result, DotDict)

    def testExportConvertsNestedDotDict(self):
        """Recursively convert nested DotDict to plain dicts.

        Validates that all nested DotDict instances are converted
        to standard dictionaries during export.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"outer": DotDict({"inner": DotDict({"v": 1})})})
        result = d.export()
        self.assertNotIsInstance(result["outer"], DotDict)
        self.assertNotIsInstance(result["outer"]["inner"], DotDict)
        self.assertEqual(result["outer"]["inner"]["v"], 1)

    def testExportPreservesNonDictValues(self):
        """Preserve non-dict values unchanged during export.

        Validates that string, int, list, and other non-dict values
        are not modified by the export process.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"s": "text", "n": 42, "lst": [1, 2, 3]})
        result = d.export()
        self.assertEqual(result["s"], "text")
        self.assertEqual(result["n"], 42)
        self.assertEqual(result["lst"], [1, 2, 3])

    def testExportEmptyDotDict(self):
        """Export an empty DotDict as an empty dict.

        Validates that exporting a DotDict with no entries returns
        an empty standard dictionary.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict()
        self.assertEqual(d.export(), {})

    # ------------------------------------------------ copy

    def testCopyReturnsDotDict(self):
        """Return a DotDict instance from copy.

        Validates that the copy method produces a new DotDict
        rather than a plain dict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"a": 1})
        c = d.copy()
        self.assertIsInstance(c, DotDict)

    def testCopyIsDeepCopy(self):
        """Create a deep copy of nested structures.

        Validates that modifying the copied DotDict does not affect
        the original instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"nested": DotDict({"x": 10})})
        c = d.copy()
        c.nested.x = 99
        self.assertEqual(d.nested.x, 10)

    def testCopyIsNotSameObject(self):
        """Ensure copy returns a distinct object.

        Validates that the copied DotDict is not the same object
        as the original.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"a": 1})
        c = d.copy()
        self.assertIsNot(d, c)

    def testCopyConvertsPlainDictValues(self):
        """Convert plain dict values to DotDict during copy.

        Validates that plain dict values within the DotDict are
        converted to DotDict in the copy result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"child": {"k": "v"}})
        c = d.copy()
        self.assertIsInstance(c["child"], DotDict)
        self.assertEqual(c.child.k, "v")

    def testCopyPreservesValues(self):
        """Preserve all values in the copied DotDict.

        Validates that the copy retains the same key-value pairs
        as the original.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"a": 1, "b": "two", "c": [3]})
        c = d.copy()
        self.assertEqual(c["a"], 1)
        self.assertEqual(c["b"], "two")
        self.assertEqual(c["c"], [3])

    # ------------------------------------------------ __repr__

    def testReprReturnsString(self):
        """Return a string from repr.

        Validates that calling repr on a DotDict produces a string
        representation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"a": 1})
        self.assertIsInstance(repr(d), str)

    def testReprMatchesDictFormat(self):
        """Match standard dict repr format.

        Validates that the DotDict repr output matches the format
        produced by a plain dict with the same content.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"a": 1})
        self.assertEqual(repr(d), repr({"a": 1}))

    def testReprEmptyDotDict(self):
        """Return empty dict repr for an empty DotDict.

        Validates that an empty DotDict produces the same repr
        as an empty dict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict()
        self.assertEqual(repr(d), "{}")

    # ---------------------------------------- dict compatibility

    def testBracketAccessStillWorks(self):
        """Support standard bracket-style dictionary access.

        Validates that DotDict retains standard dict bracket
        access alongside attribute-style access.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"key": "value"})
        self.assertEqual(d["key"], "value")

    def testInOperatorWorks(self):
        """Support the `in` membership operator.

        Validates that the `in` keyword correctly checks for key
        existence in a DotDict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"present": True})
        self.assertIn("present", d)
        self.assertNotIn("absent", d)

    def testIterationOverKeys(self):
        """Iterate over DotDict keys like a standard dict.

        Validates that iterating over a DotDict yields its keys
        in the expected order.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"a": 1, "b": 2})
        keys = list(d)
        self.assertIn("a", keys)
        self.assertIn("b", keys)

    def testLenReturnsCorrectCount(self):
        """Return the correct number of entries.

        Validates that len on a DotDict returns the number of
        key-value pairs stored.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"x": 1, "y": 2, "z": 3})
        self.assertEqual(len(d), 3)

    def testEmptyDotDictHasZeroLength(self):
        """Return zero length for an empty DotDict.

        Validates that an empty DotDict correctly reports a
        length of zero.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict()
        self.assertEqual(len(d), 0)

    def testInitFromKeywordArgs(self):
        """Initialize DotDict from keyword arguments.

        Validates that DotDict can be constructed using keyword
        arguments similarly to a standard dict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict(name="test", value=42)
        self.assertEqual(d.name, "test")
        self.assertEqual(d.value, 42)

    def testUpdateMergesData(self):
        """Merge data using the update method.

        Validates that the dict update method correctly merges
        new key-value pairs into the DotDict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"a": 1})
        d.update({"b": 2})
        self.assertEqual(d.b, 2)
        self.assertEqual(d.a, 1)

    # ---------------------------------------- deep nesting

    def testDeeplyNestedAccess(self):
        """Access deeply nested values via chained attributes.

        Validates that attribute-style access works correctly
        through multiple levels of nesting.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({
            "level1": {
                "level2": {
                    "level3": "deep",
                },
            },
        })
        self.assertEqual(d.level1.level2.level3, "deep")

    def testSetDeeplyNestedValue(self):
        """Set a value in a deeply nested DotDict.

        Validates that attribute assignment works correctly
        on nested DotDict structures.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = DotDict({"a": {"b": {"c": 0}}})
        d.a.b.c = 99
        self.assertEqual(d.a.b.c, 99)
