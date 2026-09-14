from __future__ import annotations
import asyncio
from orionis.test import TestCase
from orionis.container.context.manager import ScopeManager
from orionis.container.context.scope import ScopedContext

class TestScopeManager(TestCase):

    def setUp(self) -> None:
        """Reset the active scope before each test to guarantee isolation."""
        ScopedContext.setCurrentScope(None)

    def tearDown(self) -> None:
        """Reset the active scope after each test to avoid state leakage."""
        ScopedContext.setCurrentScope(None)

    # ------------------------------------------------------------------
    # __init__
    # ------------------------------------------------------------------

    def testInitCreatesEmptyInstancesDict(self) -> None:
        """
        Test that a newly created ScopeManager contains no stored instances.

        Verifies that after construction the internal storage is empty and
        that arbitrary key lookups return None.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        self.assertNotIn("any_key", sm)
        self.assertIsNone(sm["any_key"])

    # ------------------------------------------------------------------
    # __getitem__
    # ------------------------------------------------------------------

    def testGetitemReturnNoneForMissingKey(self) -> None:
        """
        Test that __getitem__ returns None when the key does not exist.

        Ensures graceful handling of missing keys rather than raising
        a KeyError.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        self.assertIsNone(sm["missing"])
        self.assertIsNone(sm[0])
        self.assertIsNone(sm[None])

    def testGetitemReturnsStoredValue(self) -> None:
        """
        Test that __getitem__ retrieves the exact value previously stored.

        Verifies identity preservation for the retrieved object.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        obj = object()
        sm["k"] = obj
        self.assertIs(sm["k"], obj)

    # ------------------------------------------------------------------
    # __setitem__
    # ------------------------------------------------------------------

    def testSetitemStoresValue(self) -> None:
        """
        Test that __setitem__ stores a value that is later retrievable.

        Covers multiple types: string, integer, list, and dict.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        sm["str_key"] = "hello"
        sm["int_key"] = 99
        sm["list_key"] = [1, 2, 3]
        sm["dict_key"] = {"a": 1}

        self.assertEqual(sm["str_key"], "hello")
        self.assertEqual(sm["int_key"], 99)
        self.assertEqual(sm["list_key"], [1, 2, 3])
        self.assertEqual(sm["dict_key"], {"a": 1})

    def testSetitemOverwritesExistingValue(self) -> None:
        """
        Test that assigning to an existing key replaces its previous value.

        Confirms that the overwrite is reflected immediately on the next
        __getitem__ call.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        sm["k"] = "original"
        sm["k"] = "updated" # NOSONAR
        self.assertEqual(sm["k"], "updated")

    def testSetitemWithNoneValue(self) -> None:
        """
        Test that None can be stored as a value and is distinguishable from absence.

        After storing None under a key, __contains__ must confirm the key exists
        even though __getitem__ returns None.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        sm["k"] = None
        self.assertIn("k", sm)
        self.assertIsNone(sm["k"])

    # ------------------------------------------------------------------
    # __contains__
    # ------------------------------------------------------------------

    def testContainsReturnsTrueForExistingKey(self) -> None:
        """
        Test that the 'in' operator returns True after a key is stored.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        sm["present"] = "value"
        self.assertIn("present", sm)

    def testContainsReturnsFalseForMissingKey(self) -> None:
        """
        Test that the 'in' operator returns False for a key that was never stored.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        self.assertNotIn("absent", sm)

    def testContainsReturnsFalseAfterClear(self) -> None:
        """
        Test that 'in' returns False for a previously stored key after clear().

        Ensures that clear() removes all key-presence information from the
        internal dictionary.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        sm["k"] = "v"
        sm.clear()
        self.assertNotIn("k", sm)

    # ------------------------------------------------------------------
    # clear
    # ------------------------------------------------------------------

    def testClearRemovesAllInstances(self) -> None:
        """
        Test that clear() empties all stored instances from the scope.

        Populates the scope with several keys and verifies none remain
        after calling clear().

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        sm["a"] = 1
        sm["b"] = 2
        sm["c"] = 3
        sm.clear()

        self.assertNotIn("a", sm)
        self.assertNotIn("b", sm)
        self.assertNotIn("c", sm)

    def testClearOnEmptyScopeIsNoop(self) -> None:
        """
        Test that calling clear() on an already-empty scope raises no errors.

        Verifies that the scope remains functional after clearing an empty state.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        sm.clear()  # Should not raise
        sm["new_key"] = "new_value"
        self.assertEqual(sm["new_key"], "new_value")

    # ------------------------------------------------------------------
    # set (public sync method)
    # ------------------------------------------------------------------

    def testSetMethodStoresValue(self) -> None:
        """
        Test that the set() method stores a value retrievable via __getitem__.

        Confirms that set() is an equivalent alternative to __setitem__ for
        storing instances.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        sm.set("key", "value")
        self.assertEqual(sm["key"], "value")
        self.assertIn("key", sm)

    def testSetMethodOverwritesExistingValue(self) -> None:
        """
        Test that set() overwrites an existing value stored under the same key.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        sm.set("key", "first")
        sm.set("key", "second")
        self.assertEqual(sm["key"], "second")

    # ------------------------------------------------------------------
    # Special key types
    # ------------------------------------------------------------------

    def testSpecialHashableKeyTypes(self) -> None:
        """
        Store and retrieve values using various hashable key types.

        Verifies that integer, tuple, and class-type keys are all valid.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()

        sm[42] = "int_key_value"
        sm[("a", "b")] = "tuple_key_value"

        class _Dummy:
            pass

        sm[_Dummy] = "class_key_value"

        self.assertEqual(sm[42], "int_key_value")
        self.assertEqual(sm[("a", "b")], "tuple_key_value")
        self.assertEqual(sm[_Dummy], "class_key_value")

    # ------------------------------------------------------------------
    # Multiple independent instances
    # ------------------------------------------------------------------

    def testMultipleScopeManagerInstancesAreIndependent(self) -> None:
        """
        Test that two ScopeManager instances maintain separate storage.

        Ensures that data written to one instance is invisible to another
        and that clearing one does not affect the other.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm1 = ScopeManager()
        sm2 = ScopeManager()

        sm1["shared"] = "from_sm1"
        sm2["shared"] = "from_sm2"

        self.assertEqual(sm1["shared"], "from_sm1")
        self.assertEqual(sm2["shared"], "from_sm2")

        sm1.clear()
        self.assertNotIn("shared", sm1)
        self.assertIn("shared", sm2)

    # ------------------------------------------------------------------
    # async __aenter__ / __aexit__
    # ------------------------------------------------------------------

    async def testAsyncAenterSetsScopeAndReturnsSelf(self) -> None:
        """
        Test that async __aenter__ registers self as the active scope and returns self.

        Verifies that after entering the async context the ScopedContext
        reports the manager as the current scope.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        result = await sm.__aenter__()
        try:
            self.assertIs(result, sm)
            self.assertIs(ScopedContext.getCurrentScope(), sm)
        finally:
            await sm.__aexit__(None, None, None)

    async def testAsyncAexitClearsInstancesAndResetsScope(self) -> None:
        """
        Remove all stored instances and deactivate the scope on async __aexit__.

        Populates the scope, enters the context, then calls __aexit__ and
        confirms both the instance dictionary and the ScopedContext are cleared.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        sm["key"] = "value"
        await sm.__aenter__()

        self.assertIs(ScopedContext.getCurrentScope(), sm)
        self.assertIn("key", sm)

        await sm.__aexit__(None, None, None)

        self.assertIsNone(ScopedContext.getCurrentScope())
        self.assertNotIn("key", sm)

    async def testAsyncContextManagerWithStatement(self) -> None:
        """
        Test the full async context manager workflow using 'async with'.

        Verifies that the scope is active inside the block, instances are
        accessible, and everything is cleaned up after the block exits.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIsNone(ScopedContext.getCurrentScope())

        async with ScopeManager() as scope:
            self.assertIs(ScopedContext.getCurrentScope(), scope)
            scope["service"] = "instance"
            self.assertIn("service", scope)
            self.assertEqual(scope["service"], "instance")

        self.assertIsNone(ScopedContext.getCurrentScope())

    async def testAsyncContextManagerCleansUpOnException(self) -> None:
        """
        Clean up correctly even when an exception is raised inside async context.

        Confirms that instances and the active scope are cleared regardless of
        whether an exception propagates out of the 'async with' block.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        raised: bool = False

        try:
            async with sm as scope:
                scope["k"] = "v"
                err_msg = "deliberate error"
                raise RuntimeError(err_msg)
        except RuntimeError:
            raised = True

        self.assertTrue(raised)
        self.assertIsNone(ScopedContext.getCurrentScope())
        self.assertNotIn("k", sm)

    # ------------------------------------------------------------------
    # async get
    # ------------------------------------------------------------------

    async def testAsyncGetReturnsSyncValue(self) -> None:
        """
        Test that get() returns a plain (non-coroutine) stored value directly.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        sm["k"] = "direct_value"
        result = await sm.get("k")
        self.assertEqual(result, "direct_value")

    async def testAsyncGetReturnsNoneForMissingKey(self) -> None:
        """
        Test that get() returns None when the requested key is not present.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        result = await sm.get("missing")
        self.assertIsNone(result)

    async def testAsyncGetResolvesAndCachesCoroutine(self) -> None:
        """
        Test that get() awaits a stored coroutine and caches the resolved value.

        After the first get() call the coroutine result should be stored in
        place of the original coroutine, so subsequent calls return the cached
        value without re-executing the coroutine.

        Returns
        -------
        None
            This method does not return a value.
        """
        async def _make_value() -> str: # NOSONAR
            return "coroutine_result"

        sm = ScopeManager()
        sm["k"] = _make_value()  # Store unawaited coroutine

        result = await sm.get("k")
        self.assertEqual(result, "coroutine_result")

        # Second call should return the cached string, not a coroutine.
        result_again = await sm.get("k")
        self.assertEqual(result_again, "coroutine_result")

    async def testAsyncGetResolvesAndCachesTask(self) -> None:
        """
        Test that get() awaits an asyncio.Task and caches the resolved result.

        Verifies that after resolution the Task is replaced in storage with
        its concrete return value.

        Returns
        -------
        None
            This method does not return a value.
        """
        async def _worker() -> int: # NOSONAR
            return 42

        sm = ScopeManager()
        task = asyncio.create_task(_worker())
        sm["k"] = task

        result = await sm.get("k")
        self.assertEqual(result, 42)

        # Cached value should now be the integer, not the Task.
        cached = await sm.get("k")
        self.assertEqual(cached, 42)

    # ------------------------------------------------------------------
    # async resolve
    # ------------------------------------------------------------------

    async def testAsyncResolveReturnsExistingValue(self) -> None:
        """
        Test that resolve() returns the value associated with a stored key.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        sm["k"] = "resolved_value"
        result = await sm.resolve("k")
        self.assertEqual(result, "resolved_value")

    async def testAsyncResolveRaisesKeyErrorForMissingKey(self) -> None:
        """
        Test that resolve() raises KeyError when the key does not exist.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        with self.assertRaises(KeyError):
            await sm.resolve("nonexistent")

    async def testAsyncResolveRaisesKeyErrorWhenValueIsNone(self) -> None:
        """
        Test that resolve() raises KeyError when the stored value resolves to None.

        Edge case: if None is explicitly stored under a key, resolve() cannot
        distinguish it from a missing key and raises KeyError.

        Returns
        -------
        None
            This method does not return a value.
        """
        sm = ScopeManager()
        sm["k"] = None
        with self.assertRaises(KeyError):
            await sm.resolve("k")

    async def testAsyncResolveCoroutineValue(self) -> None:
        """
        Test that resolve() correctly awaits and returns a stored coroutine's result.

        Combines the coroutine-resolution logic of get() with the KeyError guard
        of resolve().

        Returns
        -------
        None
            This method does not return a value.
        """
        async def _produce() -> str: # NOSONAR
            return "produced"

        sm = ScopeManager()
        sm["k"] = _produce()

        result = await sm.resolve("k")
        self.assertEqual(result, "produced")

    async def testClosedScopeCannotBeReenteredOrRepopulated(self) -> None:
        """Keep inherited references from reviving a completed request scope."""
        async with ScopeManager() as scope:
            self.assertTrue(scope.isActive)
        self.assertFalse(scope.isActive)
        with self.assertRaises(RuntimeError):
            scope["identity"] = object()
        with self.assertRaises(RuntimeError):
            await scope.__aenter__()

    async def testInFlightResolutionCannotPublishAfterScopeExit(self) -> None:
        """Reject a late service result even when its task inherited the scope."""
        entered = asyncio.Event()
        finished = asyncio.Event()

        async def build_late() -> object:
            entered.set()
            await finished.wait()
            return object()

        async with ScopeManager() as scope:
            scope["late"] = build_late()
            pending = asyncio.create_task(scope.get("late"))
            await entered.wait()
        finished.set()
        with self.assertRaises(RuntimeError):
            await pending
        self.assertNotIn("late", scope)
