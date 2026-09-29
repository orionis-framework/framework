from __future__ import annotations
import asyncio
import gc
import threading
import time
import weakref
from orionis.test import TestCase
from orionis.support.patterns.singleton.meta import Singleton

# ---------------------------------------------------------------------------
# Fixture helpers - each test that needs a *fresh* singleton must define its
# own class so there is no shared state between tests.
# ---------------------------------------------------------------------------

class _SimpleSingleton(metaclass=Singleton):
    """Minimal singleton for basic identity tests."""

    def __init__(self) -> None:
        """Initialize the support test double.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.created = True

class _ArgedSingleton(metaclass=Singleton):
    """Singleton whose constructor accepts arguments."""

    def __init__(self, name: str = "default") -> None:
        """Initialize the support test double.

        Parameters
        ----------
        name : str
            Value supplied for ``name``.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.name = name

# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestSingletonMeta(TestCase):

    # ------------------------------------------------ basic identity (sync)

    def testCallReturnsSameInstance(self) -> None:
        """Return the identical instance on repeated calls.

        Validates that the hot-path identity check of Singleton.__call__
        returns the exact same object every time the class is called.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        a = _SimpleSingleton()
        b = _SimpleSingleton()
        self.assertIs(a, b)

    def testSingletonInstanceIsInitialised(self) -> None:
        """Confirm the singleton instance was initialised by __init__.

        Validates that the instance returned by the first call to the
        singleton class has been properly constructed.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        obj = _SimpleSingleton()
        self.assertTrue(obj.created)

    def testCallReturnsSameInstanceAfterManyAccesses(self) -> None:
        """Return the same instance across many sequential calls.

        Validates that the singleton guarantee holds for an arbitrary
        number of repeated accesses.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        instances = [_SimpleSingleton() for _ in range(20)]
        first = instances[0]
        for inst in instances[1:]:
            self.assertIs(inst, first)

    def testFirstCallArgumentsCapturedByConstructor(self) -> None:
        """Capture constructor arguments only on the first call.

        Validates that the instance is initialised with the arguments
        supplied during the very first call and that subsequent calls
        with different arguments still return the original instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        first = _ArgedSingleton("alpha")
        second = _ArgedSingleton("beta")
        self.assertIs(first, second)
        self.assertEqual(first.name, "alpha")

    def testSingletonIsThreadSafe(self) -> None:
        """Return the same instance from multiple concurrent threads.

        Validates that the double-checked locking in Singleton.__call__
        produces a single instance even when many threads race to create
        the singleton simultaneously.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        class _ThreadedSingleton(metaclass=Singleton):
            pass

        instances: list[object] = []
        lock = threading.Lock()

        def _create() -> None:
            """Create and record one singleton instance.

            Returns
            -------
            None
                Completes the operation described above.
            """
            obj = _ThreadedSingleton()
            with lock:
                instances.append(obj)

        threads = [threading.Thread(target=_create) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        first = instances[0]
        for inst in instances[1:]:
            self.assertIs(inst, first)

    # ------------------------------------------------ async path (__acall__)

    async def testAcallReturnsSameInstance(self) -> None:
        """Return the same instance from the async creation path.

        Validates that ``__acall__`` enforces the singleton guarantee
        when the class is created through the async interface.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        class _AsyncSingleton(metaclass=Singleton):
            pass

        a = await _AsyncSingleton.__acall__()
        b = await _AsyncSingleton.__acall__()
        self.assertIs(a, b)

    async def testAcallReturnsSameInstanceAsSync(self) -> None:
        """Return the same instance regardless of sync or async creation.

        Validates that an instance first created by ``__call__`` is
        returned unchanged by a subsequent ``__acall__`` invocation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        class _MixedSingleton(metaclass=Singleton):
            pass

        sync_instance = _MixedSingleton()
        async_instance = await _MixedSingleton.__acall__()
        self.assertIs(sync_instance, async_instance)

    async def testAcallReturnsSameInstanceWhenAsyncFirst(self) -> None:
        """Return the same instance when async path is used first.

        Validates that an instance first created by ``__acall__`` is
        returned unchanged by a subsequent ``__call__`` invocation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        class _AsyncFirstSingleton(metaclass=Singleton):
            pass

        async_instance = await _AsyncFirstSingleton.__acall__()
        sync_instance = _AsyncFirstSingleton()
        self.assertIs(async_instance, sync_instance)

    async def testAcallIsConcurrentlySafe(self) -> None:
        """Return the same instance from concurrent async tasks.

        Validates that the async lock inside ``__acall__`` prevents
        duplicate instance creation when many coroutines race.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        class _ConcurrentSingleton(metaclass=Singleton):
            pass

        async def _create() -> object:
            """Create and record one singleton instance.

            Returns
            -------
            object
                Value produced by the helper.
            """
            return await _ConcurrentSingleton.__acall__()

        results = await asyncio.gather(*[_create() for _ in range(30)])
        first = results[0]
        for inst in results[1:]:
            self.assertIs(inst, first)

    def testSyncAndAsyncCreationShareOneInstance(self) -> None:
        """Share singleton state when synchronous and async calls race.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        start = threading.Barrier(2)
        instances: list[object] = []
        construction_count = 0

        class _MixedConcurrentSingleton(metaclass=Singleton):
            def __init__(self) -> None:
                """Initialize the support test double.

                Returns
                -------
                None
                    Completes the operation described above.
                """
                nonlocal construction_count
                construction_count += 1
                time.sleep(0.02)

        def _create_async() -> None:
            """Create the singleton through the async entry point.

            Returns
            -------
            None
                Completes the operation described above.
            """
            async def _resolve() -> object:
                """Wait for the concurrent singleton construction to finish.

                Returns
                -------
                object
                    Value produced by the helper.
                """
                start.wait()
                return await _MixedConcurrentSingleton.__acall__()

            instances.append(asyncio.run(_resolve()))

        async_thread = threading.Thread(target=_create_async)
        async_thread.start()
        start.wait()
        instances.append(_MixedConcurrentSingleton())
        async_thread.join()

        self.assertEqual(construction_count, 1)
        self.assertIs(instances[0], instances[1])

    # ------------------------------------------------ per-class isolation

    def testTwoSingletonClassesHaveIndependentInstances(self) -> None:
        """Maintain independent instances for distinct singleton classes.

        Validates that the Singleton metaclass correctly scopes its
        instance cache per class so that two distinct singleton classes
        do not share the same instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        class _SingletonX(metaclass=Singleton):
            pass

        class _SingletonY(metaclass=Singleton):
            pass

        x = _SingletonX()
        y = _SingletonY()
        self.assertIsNot(x, y)
        self.assertIsInstance(x, _SingletonX)
        self.assertIsInstance(y, _SingletonY)

    def testSingletonInstanceBelongsToItsClass(self) -> None:
        """Verify the singleton instance is an instance of its own class.

        Validates that isinstance and type checks correctly identify
        the singleton as belonging to its defining class.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        obj = _SimpleSingleton()
        self.assertIsInstance(obj, _SimpleSingleton)
        self.assertIs(type(obj), _SimpleSingleton)

    # ------------------------------------------------ metaclass identity

    def testMetaclassIsSingleton(self) -> None:
        """Confirm the metaclass of a singleton class is Singleton.

        Validates that ``type(_SimpleSingleton)`` is exactly ``Singleton``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIs(type(_SimpleSingleton), Singleton)

    def testSingletonInstanceAttributePresentOnClass(self) -> None:
        """Expose _singleton_instance after the first call.

        Validates that after the first instantiation the class-level
        ``_singleton_instance`` attribute holds a non-sentinel value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        # Trigger creation so the attribute is populated
        obj = _SimpleSingleton()
        stored = type.__getattribute__(_SimpleSingleton, "_singleton_instance")
        self.assertIs(stored, obj)

    # ------------------------------------------------ subclassing a singleton

    def testSingletonSubclassHasOwnInstance(self) -> None:
        """Give each subclass its own singleton instance.

        Validates that subclassing a singleton class produces an independent
        singleton rather than sharing the parent's instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        class _Parent(metaclass=Singleton):
            pass

        class _Child(_Parent):
            pass

        parent = _Parent()
        child = _Child()
        self.assertIsNot(parent, child)
        self.assertIsInstance(child, _Child)
        self.assertIsInstance(child, _Parent)

    def testUnusedSingletonClassCanBeCollected(self) -> None:
        """Release dynamically created singleton classes after their use.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        singleton_class = Singleton("_TemporarySingleton", (), {})
        class_ref = weakref.ref(singleton_class)

        del singleton_class
        gc.collect()

        self.assertIsNone(class_ref())
