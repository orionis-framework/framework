from orionis.test import TestCase
from orionis.support.types.collection import Collection

class TestCollection(TestCase):

    # ------------------------------------------------ __init__ / all

    def testInitWithNoArguments(self):
        """Initialize collection with no arguments.

        Validates that a Collection created without items
        contains an empty list.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection()
        self.assertEqual(c.all(), [])

    def testInitWithItems(self):
        """Initialize collection with a list of items.

        Validates that items passed at construction are
        stored and retrievable via all().

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        self.assertEqual(c.all(), [1, 2, 3])

    def testInitWithNoneDefaultsToEmpty(self):
        """Initialize collection with None defaults to empty.

        Validates that passing None explicitly produces an
        empty collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection(None)
        self.assertEqual(c.all(), [])

    # ------------------------------------------------ count / len

    def testCountReturnsItemCount(self):
        """Return the correct number of items.

        Validates that count returns the number of elements
        stored in the collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        self.assertEqual(c.count(), 3)

    def testCountEmptyCollection(self):
        """Return zero for an empty collection.

        Validates that count returns zero when no items
        are present.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection()
        self.assertEqual(c.count(), 0)

    def testLenMatchesCount(self):
        """Match len with count for consistency.

        Validates that the len dunder returns the same
        value as count.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2])
        self.assertEqual(len(c), c.count())

    # ------------------------------------------------ first / last

    def testFirstReturnsFirstItem(self):
        """Return the first item from the collection.

        Validates that first returns the element at index 0.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([10, 20, 30])
        self.assertEqual(c.first(), 10)

    def testFirstReturnsNoneWhenEmpty(self):
        """Return None when collection is empty.

        Validates that first returns None for an empty
        collection instead of raising.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection()
        self.assertIsNone(c.first())

    def testFirstWithCallback(self):
        """Return first item matching a callback.

        Validates that first applies the callback filter and
        returns the first matching element.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3, 4])
        result = c.first(lambda x: x > 2)
        self.assertEqual(result, 3)

    def testFirstWithCallbackNoMatch(self):
        """Return None when no item matches the callback.

        Validates that first returns None when the callback
        rejects all items.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2])
        self.assertIsNone(c.first(lambda x: x > 10))

    def testFirstWithCallbackStopsAtFirstMatch(self):
        """Stop evaluating items after the first callback match.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        visited = []
        result = Collection([1, 2, 3]).first(
            lambda item: visited.append(item) or item == 2,
        )
        self.assertEqual(result, 2)
        self.assertEqual(visited, [1, 2])

    def testLastReturnsLastItem(self):
        """Return the last item from the collection.

        Validates that last returns the final element.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([10, 20, 30])
        self.assertEqual(c.last(), 30)

    def testLastReturnsNoneWhenEmpty(self):
        """Return None when collection is empty.

        Validates that last returns None for an empty
        collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection()
        self.assertIsNone(c.last())

    def testLastWithCallback(self):
        """Return last item matching a callback.

        Validates that last applies the callback filter and
        returns the last matching element.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3, 4])
        result = c.last(lambda x: x < 4)
        self.assertEqual(result, 3)

    def testLastWithCallbackReturnsLastMatchingNone(self):
        """Return None when the last matching item is None.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Collection([None, 1, None]).last(lambda item: item is None)
        self.assertIsNone(result)

    # ------------------------------------------------ take

    def testTakePositiveNumber(self):
        """Take items from the beginning of the collection.

        Validates that a positive number takes from the start.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3, 4, 5])
        result = c.take(3)
        self.assertEqual(result.all(), [1, 2, 3])

    def testTakeNegativeNumber(self):
        """Take items from the end of the collection.

        Validates that a negative number takes from the end.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3, 4, 5])
        result = c.take(-2)
        self.assertEqual(result.all(), [4, 5])

    def testTakeZeroReturnsEmpty(self):
        """Return empty collection when taking zero items.

        Validates that taking zero items produces an empty
        collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        result = c.take(0)
        self.assertEqual(result.all(), [])

    # ------------------------------------------------ avg / sum / max / min

    def testAvgOfNumbers(self):
        """Compute the average of numeric items.

        Validates that avg returns the arithmetic mean of
        all items in the collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([2, 4, 6])
        self.assertEqual(c.avg(), 4.0)

    def testAvgOfEmptyCollectionReturnsZero(self):
        """Return zero for the average of an empty collection.

        Validates that avg returns 0 when no items are present.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection()
        self.assertEqual(c.avg(), 0)

    def testAvgWithKey(self):
        """Compute the average using a dict key.

        Validates that avg extracts values by key and computes
        their arithmetic mean.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([{"v": 10}, {"v": 20}])
        self.assertEqual(c.avg("v"), 15.0)

    def testSumOfNumbers(self):
        """Compute the sum of numeric items.

        Validates that sum returns the total of all items.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        self.assertEqual(c.sum(), 6)

    def testSumOfEmptyCollectionReturnsZero(self):
        """Return zero for the sum of an empty collection.

        Validates that sum returns 0 when no items exist.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection()
        self.assertEqual(c.sum(), 0)

    def testMaxOfNumbers(self):
        """Return the maximum value from numeric items.

        Validates that max returns the largest element.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([3, 1, 4, 1, 5])
        self.assertEqual(c.max(), 5)

    def testMaxOfEmptyReturnsZero(self):
        """Return zero for max of an empty collection.

        Validates that max returns 0 when no items exist.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection()
        self.assertEqual(c.max(), 0)

    def testMinOfNumbers(self):
        """Return the minimum value from numeric items.

        Validates that min returns the smallest element.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([3, 1, 4, 1, 5])
        self.assertEqual(c.min(), 1)

    def testMinOfEmptyReturnsZero(self):
        """Return zero for min of an empty collection.

        Validates that min returns 0 when no items exist.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection()
        self.assertEqual(c.min(), 0)

    # ------------------------------------------------ chunk

    def testChunkDividesEvenly(self):
        """Divide collection into equal-sized chunks.

        Validates that chunk splits items into collections
        of the specified size.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3, 4])
        chunks = c.chunk(2)
        self.assertEqual(chunks.count(), 2)
        self.assertEqual(chunks[0].all(), [1, 2])
        self.assertEqual(chunks[1].all(), [3, 4])

    def testChunkWithRemainder(self):
        """Handle remainder in the last chunk.

        Validates that the last chunk contains remaining
        items when the total is not evenly divisible.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3, 4, 5])
        chunks = c.chunk(2)
        self.assertEqual(chunks.count(), 3)
        self.assertEqual(chunks[2].all(), [5])

    def testChunkRaisesOnZeroSize(self):
        """Raise ValueError when chunk size is zero.

        Validates that an invalid chunk size causes
        a ValueError to be raised.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2])
        with self.assertRaises(ValueError):
            c.chunk(0)

    def testChunkRaisesOnNegativeSize(self):
        """Raise ValueError when chunk size is negative.

        Validates that a negative chunk size causes
        a ValueError to be raised.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2])
        with self.assertRaises(ValueError):
            c.chunk(-1)

    # ------------------------------------------------ collapse

    def testCollapseNestedLists(self):
        """Flatten nested lists into a single collection.

        Validates that collapse merges sub-lists into one
        flat collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([[1, 2], [3, 4]])
        result = c.collapse()
        self.assertEqual(result.all(), [1, 2, 3, 4])

    # ------------------------------------------------ contains

    def testContainsWithValue(self):
        """Check if collection contains a specific value.

        Validates that contains returns True when the item
        is present in the collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        self.assertTrue(c.contains(2))

    def testContainsMissingValue(self):
        """Return False when value is not in collection.

        Validates that contains returns False for an absent
        item.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        self.assertFalse(c.contains(99))

    def testContainsWithCallback(self):
        """Check containment using a callback.

        Validates that a callable key is used to test if
        any item matches the condition.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        self.assertTrue(c.contains(lambda x: x > 2))

    def testContainsWithKeyValue(self):
        """Check containment with a key-value pair.

        Validates that contains searches for items where
        the specified key matches the given value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([{"name": "a"}, {"name": "b"}])
        self.assertTrue(c.contains("name", "a"))
        self.assertFalse(c.contains("name", "z"))

    # ------------------------------------------------ diff

    def testDiffRemovesCommonItems(self):
        """Remove items present in the given list.

        Validates that diff produces a collection without
        elements found in the comparison list.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3, 4])
        result = c.diff([2, 4])
        self.assertEqual(result.all(), [1, 3])

    def testDiffWithCollectionArgument(self):
        """Accept a Collection as the diff argument.

        Validates that diff works when passed another
        Collection instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        other = Collection([2])
        result = c.diff(other)
        self.assertEqual(result.all(), [1, 3])

    # ------------------------------------------------ each

    def testEachAppliesCallback(self):
        """Apply callback to each item in the collection.

        Validates that each iterates over and transforms
        items using the provided callback.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        c.each(lambda x: x * 2)
        self.assertEqual(c.all(), [2, 4, 6])

    # ------------------------------------------------ every

    def testEveryReturnsTrueWhenAllMatch(self):
        """Return True when all items satisfy the callback.

        Validates that every returns True if every item
        passes the test.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([2, 4, 6])
        self.assertTrue(c.every(lambda x: x % 2 == 0))

    def testEveryReturnsFalseWhenSomeFail(self):
        """Return False when some items fail the callback.

        Validates that every returns False if at least one
        item does not pass the test.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([2, 3, 6])
        self.assertFalse(c.every(lambda x: x % 2 == 0))

    # ------------------------------------------------ filter

    def testFilterReturnsMatchingItems(self):
        """Filter items matching the callback condition.

        Validates that filter produces a collection with
        only items passing the test.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3, 4, 5])
        result = c.filter(lambda x: x > 3)
        self.assertEqual(result.all(), [4, 5])

    def testFilterEmptyResult(self):
        """Return empty collection when no items match.

        Validates that filter produces an empty collection
        when the callback rejects all items.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2])
        result = c.filter(lambda x: x > 10)
        self.assertEqual(result.all(), [])

    def testWhereInSupportsUnhashableValues(self):
        """Match nested values that cannot be stored in a set.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        collection = Collection([{"value": [1]}, {"value": [2]}])
        self.assertEqual(
            collection.whereIn("value", [[2]]).all(),
            [{"value": [2]}],
        )

    def testWhereNotInSupportsUnhashableValues(self):
        """Exclude nested values that cannot be stored in a set.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        collection = Collection([{"value": [1]}, {"value": [2]}])
        self.assertEqual(
            collection.whereNotIn("value", [[2]]).all(),
            [{"value": [1]}],
        )

    # ------------------------------------------------ flatten

    def testFlattenNestedStructures(self):
        """Flatten deeply nested structures.

        Validates that flatten recursively extracts all
        leaf values into a single-dimension collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, [2, [3, 4]], 5])
        result = c.flatten()
        self.assertEqual(result.all(), [1, 2, 3, 4, 5])

    def testFlattenDictValues(self):
        """Flatten dict values into a flat collection.

        Validates that flatten extracts values from nested
        dicts.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([{"a": 1, "b": 2}])
        result = c.flatten()
        self.assertEqual(result.all(), [1, 2])

    # ------------------------------------------------ forget

    def testForgetRemovesItemByIndex(self):
        """Remove an item by its index.

        Validates that forget deletes the item at the
        specified index.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([10, 20, 30])
        c.forget(1)
        self.assertEqual(c.all(), [10, 30])

    def testForgetMultipleIndices(self):
        """Remove multiple items by their indices.

        Validates that forget handles multiple keys and
        removes all specified items.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([10, 20, 30, 40])
        c.forget(0, 2)
        self.assertEqual(c.all(), [20, 40])

    # ------------------------------------------------ forPage

    def testForPageReturnsCorrectSlice(self):
        """Return the correct page of items.

        Validates that forPage slices the collection for
        the requested page number and size.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3, 4, 5, 6])
        page = c.forPage(2, 2)
        self.assertEqual(page.all(), [3, 4])

    def testForPageFirstPage(self):
        """Return the first page of items.

        Validates that page 1 starts from the beginning
        of the collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3, 4])
        page = c.forPage(1, 2)
        self.assertEqual(page.all(), [1, 2])

    def testForPageRaisesOnZeroPerPage(self):
        """Raise ValueError when items per page is zero.

        Validates that an invalid page size causes a
        ValueError to be raised.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2])
        with self.assertRaises(ValueError):
            c.forPage(1, 0)

    # ------------------------------------------------ get

    def testGetByIndex(self):
        """Retrieve an item by index.

        Validates that get returns the item at the given
        index position.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([10, 20, 30])
        self.assertEqual(c.get(1), 20)

    def testGetReturnsDefaultWhenMissing(self):
        """Return default when index is out of range.

        Validates that get returns the default value when
        the index does not exist.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1])
        self.assertEqual(c.get(99, "default"), "default")

    def testGetReturnsNoneByDefault(self):
        """Return None when index is missing and no default.

        Validates that get returns None when no default
        is specified for a missing index.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1])
        self.assertIsNone(c.get(99))

    # ------------------------------------------------ implode

    def testImplodeStrings(self):
        """Join string items with a glue string.

        Validates that implode concatenates all items using
        the specified separator.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection(["a", "b", "c"])
        self.assertEqual(c.implode("-"), "a-b-c")

    def testImplodeDefaultGlue(self):
        """Join items with default comma glue.

        Validates that implode uses comma as the default
        separator.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection(["x", "y"])
        self.assertEqual(c.implode(), "x,y")

    def testImplodeEmptyCollection(self):
        """Return empty string for an empty collection.

        Validates that implode returns an empty string when
        the collection has no items.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection()
        self.assertEqual(c.implode(), "")

    # ------------------------------------------------ isEmpty

    def testIsEmptyReturnsTrueWhenEmpty(self):
        """Return True for an empty collection.

        Validates that isEmpty correctly identifies a
        collection with no items.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection()
        self.assertTrue(c.isEmpty())

    def testIsEmptyReturnsFalseWhenNotEmpty(self):
        """Return False for a non-empty collection.

        Validates that isEmpty returns False when the
        collection contains items.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1])
        self.assertFalse(c.isEmpty())

    # ------------------------------------------------ map

    def testMapAppliesCallbackToAll(self):
        """Apply a callback to all items and return new collection.

        Validates that map produces a new collection with
        each item transformed by the callback.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        result = c.map(lambda x: x * 10)
        self.assertEqual(result.all(), [10, 20, 30])

    # ------------------------------------------------ merge

    def testMergeWithList(self):
        """Merge a list into the collection.

        Validates that merge appends all items from the
        given list into the collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2])
        c.merge([3, 4])
        self.assertEqual(c.all(), [1, 2, 3, 4])

    def testMergeWithCollection(self):
        """Merge another Collection into the collection.

        Validates that merge accepts a Collection instance
        and appends its items.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1])
        c.merge(Collection([2, 3]))
        self.assertEqual(c.all(), [1, 2, 3])

    def testMergeRaisesOnInvalidType(self):
        """Raise TypeError when merging incompatible types.

        Validates that merge raises TypeError when given
        a value that is not a list or Collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1])
        with self.assertRaises(TypeError):
            c.merge("invalid")

    # ------------------------------------------------ pluck

    def testPluckExtractsValues(self):
        """Extract values for a given key from all items.

        Validates that pluck collects the specified key
        from each dict item.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([{"n": "a"}, {"n": "b"}, {"n": "c"}])
        result = c.pluck("n")
        self.assertEqual(result.all(), ["a", "b", "c"])

    def testPluckWithKeyIndex(self):
        """Extract values with a custom key index.

        Validates that pluck uses the specified key as
        dictionary keys in the result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([
            {"id": 1, "name": "a"},
            {"id": 2, "name": "b"},
        ])
        result = c.pluck("name", "id")
        self.assertEqual(result.all(), {1: "a", 2: "b"})

    # ------------------------------------------------ pop / push / prepend

    def testPopRemovesLastItem(self):
        """Remove and return the last item.

        Validates that pop extracts the final element and
        reduces the collection size.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        val = c.pop()
        self.assertEqual(val, 3)
        self.assertEqual(c.all(), [1, 2])

    def testPopOnEmptyReturnsNone(self):
        """Return None when popping from empty collection.

        Validates that pop returns None instead of raising
        when the collection is empty.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection()
        self.assertIsNone(c.pop())

    def testPushAddsToEnd(self):
        """Add an item to the end of the collection.

        Validates that push appends the value at the tail.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2])
        c.push(3)
        self.assertEqual(c.all(), [1, 2, 3])

    def testPrependAddsToBeginning(self):
        """Add an item to the beginning of the collection.

        Validates that prepend inserts the value at index 0.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([2, 3])
        c.prepend(1)
        self.assertEqual(c.all(), [1, 2, 3])

    # ------------------------------------------------ pull / put

    def testPullRemovesAndReturns(self):
        """Remove and return an item by key.

        Validates that pull extracts the item at the given
        index and removes it from the collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([10, 20, 30])
        val = c.pull(1)
        self.assertEqual(val, 20)
        self.assertEqual(c.count(), 2)

    def testPutSetsValueAtIndex(self):
        """Set a value at the specified index.

        Validates that put replaces the existing value at
        the given index.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        c.put(1, 99)
        self.assertEqual(c.all(), [1, 99, 3])

    # ------------------------------------------------ random

    def testRandomReturnsSingleItem(self):
        """Return a single random item.

        Validates that random without count returns one
        element from the collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3, 4, 5])
        result = c.random()
        self.assertIn(result, [1, 2, 3, 4, 5])

    def testRandomWithCount(self):
        """Return specified number of random items.

        Validates that random with a count returns a
        collection of that many items.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3, 4, 5])
        result = c.random(3)
        self.assertEqual(result.count(), 3)

    def testRandomOnEmptyReturnsNone(self):
        """Return None for random on empty collection.

        Validates that random returns None when there are
        no items to choose from.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection()
        self.assertIsNone(c.random())

    def testRandomRaisesOnExcessiveCount(self):
        """Raise ValueError when count exceeds collection size.

        Validates that requesting more random items than
        available raises a ValueError.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2])
        with self.assertRaises(ValueError):
            c.random(5)

    # ------------------------------------------------ reduce

    def testReduceAccumulatesValues(self):
        """Reduce collection to a single accumulated value.

        Validates that reduce applies the callback
        cumulatively to produce a single result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        result = c.reduce(lambda acc, x: acc + x, 0)
        self.assertEqual(result, 6)

    # ------------------------------------------------ reject

    def testRejectRemovesMatchingItems(self):
        """Reject items that match the callback.

        Validates that reject removes items for which the
        callback returns True.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3, 4])
        c.reject(lambda x: x > 2)
        self.assertEqual(c.all(), [1, 2])

    # ------------------------------------------------ reverse

    def testReverseOrder(self):
        """Reverse the order of items.

        Validates that reverse flips the item order in
        the collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        c.reverse()
        self.assertEqual(c.all(), [3, 2, 1])

    # ------------------------------------------------ shift

    def testShiftRemovesFirstItem(self):
        """Remove and return the first item.

        Validates that shift extracts the element at
        index 0 from the collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([10, 20, 30])
        val = c.shift()
        self.assertEqual(val, 10)
        self.assertEqual(c.all(), [20, 30])

    # ------------------------------------------------ sort

    def testSortOrdersItemsAscending(self):
        """Sort items in ascending order.

        Validates that sort arranges items from smallest
        to largest.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([3, 1, 2])
        c.sort()
        self.assertEqual(c.all(), [1, 2, 3])

    def testSortByKey(self):
        """Sort items by a specified dict key.

        Validates that sort arranges dict items by the
        given key in ascending order.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([{"v": 3}, {"v": 1}, {"v": 2}])
        c.sort("v")
        self.assertEqual(
            c.all(),
            [{"v": 1}, {"v": 2}, {"v": 3}],
        )

    # ------------------------------------------------ unique

    def testUniqueRemovesDuplicates(self):
        """Remove duplicate items from the collection.

        Validates that unique returns only distinct items.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 2, 3, 3, 3])
        result = c.unique()
        self.assertEqual(sorted(result.all()), [1, 2, 3])

    def testUniqueByKey(self):
        """Remove duplicates based on a dict key.

        Validates that unique with a key returns items with
        distinct values for that key.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([
            {"id": 1, "v": "a"},
            {"id": 2, "v": "b"},
            {"id": 1, "v": "c"},
        ])
        result = c.unique("id")
        self.assertEqual(result.count(), 2)

    # ------------------------------------------------ where / whereIn / whereNotIn

    def testWhereFiltersEqual(self):
        """Filter items by key-value equality.

        Validates that where returns items matching the
        specified key-value condition.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([
            {"status": "active"},
            {"status": "inactive"},
            {"status": "active"},
        ])
        result = c.where("status", "active")
        self.assertEqual(result.count(), 2)

    def testWhereWithOperator(self):
        """Filter items using a comparison operator.

        Validates that where supports operators like > and
        returns matching items.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([{"v": 1}, {"v": 5}, {"v": 10}])
        result = c.where("v", ">", 3)
        self.assertEqual(result.count(), 2)

    def testWhereRaisesWithNoArgs(self):
        """Raise ValueError when no arguments are provided.

        Validates that where raises when called with only
        the key and no value or operator.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([{"v": 1}])
        with self.assertRaises(ValueError):
            c.where("v")

    def testWhereInFiltersValues(self):
        """Filter items where key value is in a list.

        Validates that whereIn returns items whose key
        value matches any in the provided list.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([
            {"id": 1}, {"id": 2}, {"id": 3},
        ])
        result = c.whereIn("id", [1, 3])
        self.assertEqual(result.count(), 2)

    def testWhereNotInExcludesValues(self):
        """Exclude items where key value is in a list.

        Validates that whereNotIn returns items whose key
        value does not match any in the provided list.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([
            {"id": 1}, {"id": 2}, {"id": 3},
        ])
        result = c.whereNotIn("id", [2])
        self.assertEqual(result.count(), 2)

    # ------------------------------------------------ zip

    def testZipPairsItems(self):
        """Pair items from two collections by index.

        Validates that zip produces pairs from both
        collections aligned by position.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        result = c.zip([4, 5, 6])
        self.assertEqual(result.all(), [[1, 4], [2, 5], [3, 6]])

    def testZipRaisesOnInvalidType(self):
        """Raise TypeError when zipping with invalid type.

        Validates that zip raises TypeError when given
        a value that is not a list or Collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1])
        with self.assertRaises(TypeError):
            c.zip("invalid")

    # ------------------------------------------------ toJson / serialize

    def testToJsonReturnsString(self):
        """Return a JSON string representation.

        Validates that toJson produces a valid JSON string
        from the collection items.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        result = c.toJson()
        self.assertEqual(result, "[1, 2, 3]")

    def testSerializeReturnsList(self):
        """Serialize collection items as a list.

        Validates that serialize returns a plain list of
        the collection items.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, "a", None])
        result = c.serialize()
        self.assertEqual(result, [1, "a", None])

    # ------------------------------------------------ transform

    def testTransformModifiesInPlace(self):
        """Transform items in-place using a callback.

        Validates that transform replaces each item with
        the callback result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        c.transform(lambda x: x * 2)
        self.assertEqual(c.all(), [2, 4, 6])

    # ------------------------------------------------ groupBy

    def testGroupByKey(self):
        """Group items by a specified key.

        Validates that groupBy produces a dict mapping
        unique key values to their item lists.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([
            {"type": "a", "v": 1},
            {"type": "b", "v": 2},
            {"type": "a", "v": 3},
        ])
        result = c.groupBy("type")
        data = result.all()
        self.assertIn("a", data)
        self.assertIn("b", data)

    # ---------------------------------------- comparison operators

    def testEqualityWithSameItems(self):
        """Compare equal collections as equal.

        Validates that two collections with identical items
        are considered equal.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        a = Collection([1, 2, 3])
        b = Collection([1, 2, 3])
        self.assertEqual(a, b)

    def testInequalityWithDifferentItems(self):
        """Compare different collections as not equal.

        Validates that collections with different items
        are not considered equal.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        a = Collection([1, 2])
        b = Collection([3, 4])
        self.assertNotEqual(a, b)

    def testLessThanComparison(self):
        """Compare collections with less-than operator.

        Validates that the < operator uses list comparison
        semantics on the underlying items.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        a = Collection([1, 2])
        b = Collection([1, 3])
        self.assertTrue(a < b)

    def testGreaterThanComparison(self):
        """Compare collections with greater-than operator.

        Validates that the > operator uses list comparison
        semantics on the underlying items.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        a = Collection([1, 3])
        b = Collection([1, 2])
        self.assertTrue(a > b)

    # ------------------------------------------------ iteration

    def testIterationYieldsItems(self):
        """Iterate over all items in the collection.

        Validates that iterating produces each item in
        the expected order.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([10, 20, 30])
        result = list(c)
        self.assertEqual(result, [10, 20, 30])

    # ------------------------------------------------ getitem / setitem

    def testGetItemByIndex(self):
        """Retrieve item using bracket notation.

        Validates that bracket access returns the item
        at the specified index.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([10, 20, 30])
        self.assertEqual(c[1], 20)

    def testGetItemBySlice(self):
        """Retrieve a slice as a new Collection.

        Validates that slicing returns a new Collection
        with the specified range.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3, 4])
        result = c[1:3]
        self.assertIsInstance(result, Collection)
        self.assertEqual(result.all(), [2, 3])

    def testSetItemByIndex(self):
        """Set item using bracket notation.

        Validates that bracket assignment replaces the
        value at the given index.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        c[1] = 99
        self.assertEqual(c[1], 99)

    # ------------------------------------------------ hash

    def testHashIsConsistent(self):
        """Return consistent hash for same items.

        Validates that collections with identical items
        produce the same hash value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        a = Collection([1, 2, 3])
        b = Collection([1, 2, 3])
        self.assertEqual(hash(a), hash(b))

    # ---------------------------------------- mapInto

    def testMapIntoCreatesInstances(self):
        """Map items into instances of a class.

        Validates that mapInto produces a collection of
        class instances initialized from the items.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2, 3])
        result = c.mapInto(str)
        self.assertEqual(result.all(), ["1", "2", "3"])

    def testMapIntoRaisesOnNonType(self):
        """Raise TypeError when cls is not a type.

        Validates that mapInto raises when given a non-type
        argument for the class parameter.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1])
        with self.assertRaises(TypeError):
            c.mapInto("not_a_type")

    # ---------------------------------------- setAppends

    def testSetAppendsStoresAttributes(self):
        """Store attributes to append to the collection.

        Validates that setAppends saves the attribute names
        for later use in serialization.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        c = Collection([1, 2])
        c.setAppends(["extra"])
        self.assertIn("extra", c.__appends__)
