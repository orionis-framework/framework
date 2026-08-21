import functools
import threading

from orionis.background.contracts.task import IBackgroundTask
from orionis.background.task import BackgroundTask, is_async_callable
from orionis.test import TestCase

class _SyncCallable:
    """Callable object used to prove non-function callables are supported."""

    __slots__ = ("calls",)

    def __init__(self) -> None:
        """
        Initialise the invocation log.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.calls: list[tuple[object, ...]] = []

    def __call__(self, *args: object) -> None:
        """
        Record a single invocation of the callable.

        Parameters
        ----------
        *args : object
            Positional arguments received by the callable.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.calls.append(args)

class _AsyncCallable:
    """Callable object whose invocation returns a coroutine."""

    __slots__ = ("calls",)

    def __init__(self) -> None:
        """
        Initialise the invocation log.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.calls: list[tuple[object, ...]] = []

    async def __call__(self, *args: object) -> None:
        """
        Record a single invocation of the callable.

        Parameters
        ----------
        *args : object
            Positional arguments received by the callable.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.calls.append(args)

class TestIsAsyncCallable(TestCase):
    """Validate the detection of callables that return an awaitable."""

    def testDetectsCoroutineFunctions(self) -> None:
        """
        Detect coroutine functions as awaitable callables.

        Validates the most common case, where the target is declared with
        the async keyword.
        """

        async def async_func() -> None:
            pass

        self.assertTrue(is_async_callable(async_func))

    def testDetectsCallableInstancesWithACoroutineCall(self) -> None:
        """
        Detect instances whose call method is a coroutine.

        Validates that objects behaving like coroutine functions are not
        mistaken for blocking callables.
        """
        self.assertTrue(is_async_callable(_AsyncCallable()))

    def testUnwrapsPartialsBeforeInspectingTheTarget(self) -> None:
        """
        Look through partials to reach the real target.

        Validates that pre-binding arguments never hides the awaitable
        nature of the wrapped callable.
        """

        async def async_func(value: int) -> None:
            pass

        self.assertTrue(is_async_callable(functools.partial(async_func, 1)))
        self.assertTrue(is_async_callable(functools.partial(_AsyncCallable())))

    def testRejectsPlainCallables(self) -> None:
        """
        Reject callables that return a regular value.

        Validates that blocking functions and objects keep being routed to
        the executor.
        """

        def sync_func() -> None:
            pass

        self.assertFalse(is_async_callable(sync_func))
        self.assertFalse(is_async_callable(_SyncCallable()))
        self.assertFalse(is_async_callable(functools.partial(sync_func)))

    def testRejectsObjectsThatAreNotCallable(self) -> None:
        """
        Reject targets that cannot be called at all.

        Validates that the inspection is safe for values lacking a call
        implementation instead of raising.
        """
        self.assertFalse(is_async_callable(42))

class TestBackgroundTaskConstruction(TestCase):
    """Validate how a task captures its callable and its arguments."""

    def testDeclaresSlotsInsteadOfAnInstanceDictionary(self) -> None:
        """
        Store the task state in slots.

        Validates that tasks stay lightweight, which matters because one
        instance may be created per HTTP response.
        """

        def sync_func() -> None:
            pass

        self.assertFalse(hasattr(BackgroundTask(sync_func), "__dict__"))

    def testDoesNotInvokeTheCallableEagerly(self) -> None:
        """
        Defer the callable until the task is awaited.

        Validates that building a task only records the callable and
        produces none of its side effects.
        """
        calls: list[int] = []

        def sync_func() -> None:
            calls.append(1)

        BackgroundTask(sync_func)
        self.assertEqual(calls, [])

    def testStoresPositionalAndKeywordArguments(self) -> None:
        """
        Capture the arguments supplied at construction time.

        Validates that positional arguments are kept as a tuple and
        keyword arguments as a mapping, ready for a later invocation.
        """

        def sync_func(*args: int, **kwargs: int) -> None:
            pass

        task = BackgroundTask(sync_func, 1, 2, offset=3)
        self.assertEqual(task._BackgroundTask__args, (1, 2))
        self.assertEqual(task._BackgroundTask__kwargs, {"offset": 3})

    def testFlagsCoroutineFunctionsAsAsynchronous(self) -> None:
        """
        Classify coroutine functions as asynchronous once.

        Validates that the sync/async decision is resolved during
        construction rather than on every invocation.
        """

        async def async_func() -> None:
            pass

        self.assertTrue(BackgroundTask(async_func)._BackgroundTask__is_async)

    def testFlagsPlainCallablesAsSynchronous(self) -> None:
        """
        Classify regular callables as synchronous.

        Validates that functions and callable objects alike are routed to
        the executor branch instead of being awaited directly.
        """

        def sync_func() -> None:
            pass

        self.assertFalse(BackgroundTask(sync_func)._BackgroundTask__is_async)
        self.assertFalse(BackgroundTask(_SyncCallable())._BackgroundTask__is_async)

    def testFlagsCallableInstancesWithACoroutineCallAsAsynchronous(self) -> None:
        """
        Classify awaitable callable objects as asynchronous.

        Validates that an object implementing an async call method is
        awaited instead of being run in a thread and silently dropped.
        """
        self.assertTrue(BackgroundTask(_AsyncCallable())._BackgroundTask__is_async)

    def testUnwrapsPartialsWhenDetectingCoroutineFunctions(self) -> None:
        """
        Detect coroutine functions hidden behind a partial.

        Validates that a partially applied coroutine function is still
        recognised as asynchronous instead of being sent to a thread.
        """

        async def async_func(value: int) -> None:
            pass

        task = BackgroundTask(functools.partial(async_func, 1))
        self.assertTrue(task._BackgroundTask__is_async)

    def testImplementsTheBackgroundTaskContract(self) -> None:
        """
        Satisfy the background task interface.

        Validates that a task can be consumed by any collaborator that
        depends only on the abstract contract.
        """

        def sync_func() -> None:
            pass

        self.assertIsInstance(BackgroundTask(sync_func), IBackgroundTask)

class TestBackgroundTaskSynchronousExecution(TestCase):
    """Validate the executor branch used for synchronous callables."""

    async def testExecutesTheWrappedCallable(self) -> None:
        """
        Execute a synchronous callable when the task is awaited.

        Validates that awaiting the task runs the wrapped function body
        exactly once.
        """
        calls: list[int] = []

        def sync_func() -> None:
            calls.append(1)

        await BackgroundTask(sync_func)()
        self.assertEqual(calls, [1])

    async def testForwardsPositionalArguments(self) -> None:
        """
        Forward positional arguments to a synchronous callable.

        Validates that arguments captured at construction reach the
        wrapped function unchanged.
        """
        received: list[tuple[int, int]] = []

        def sync_func(first: int, second: int) -> None:
            received.append((first, second))

        await BackgroundTask(sync_func, 1, 2)()
        self.assertEqual(received, [(1, 2)])

    async def testForwardsKeywordArguments(self) -> None:
        """
        Forward keyword arguments to a synchronous callable.

        Validates that keyword arguments survive the partial binding used
        by the executor branch.
        """
        received: list[tuple[str, str]] = []

        def sync_func(left: str, right: str) -> None:
            received.append((left, right))

        await BackgroundTask(sync_func, left="hello", right="world")()
        self.assertEqual(received, [("hello", "world")])

    async def testForwardsMixedArguments(self) -> None:
        """
        Forward positional and keyword arguments together.

        Validates that a mixed call signature is reconstructed exactly as
        the caller declared it.
        """
        received: list[tuple[int, int, str]] = []

        def sync_func(first: int, second: int, label: str = "default") -> None:
            received.append((first, second, label))

        await BackgroundTask(sync_func, 10, 20, label="custom")()
        self.assertEqual(received, [(10, 20, "custom")])

    async def testRunsOutsideTheEventLoopThread(self) -> None:
        """
        Offload synchronous callables to a worker thread.

        Validates that blocking code never runs on the thread owning the
        event loop, which is what keeps the loop responsive.
        """
        observed: list[int] = []

        def sync_func() -> None:
            observed.append(threading.get_ident())

        await BackgroundTask(sync_func)()
        self.assertNotEqual(observed[0], threading.get_ident())

    async def testSupportsCallableObjects(self) -> None:
        """
        Execute callables that are not plain functions.

        Validates that any object implementing ``__call__`` can be wrapped
        and invoked with its arguments.
        """
        target = _SyncCallable()

        await BackgroundTask(target, "payload")()
        self.assertEqual(target.calls, [("payload",)])

    async def testDiscardsTheReturnValue(self) -> None:
        """
        Return nothing regardless of the callable result.

        Validates that a task is a fire-and-forget unit of work and never
        surfaces the value produced by the wrapped callable.
        """

        def sync_func() -> str:
            return "ignored"

        self.assertIsNone(await BackgroundTask(sync_func)())

    async def testCanBeAwaitedRepeatedly(self) -> None:
        """
        Allow a task instance to be reused.

        Validates that each await performs a new invocation instead of
        caching the first result.
        """
        calls: list[int] = []

        def sync_func() -> None:
            calls.append(1)

        task = BackgroundTask(sync_func)
        await task()
        await task()
        self.assertEqual(len(calls), 2)

    async def testPropagatesExceptions(self) -> None:
        """
        Surface failures raised inside the worker thread.

        Validates that an exception thrown by a synchronous callable is
        re-raised to whoever awaited the task.
        """

        def sync_func() -> None:
            error_msg = "synchronous failure"
            raise RuntimeError(error_msg)

        with self.assertRaises(RuntimeError):
            await BackgroundTask(sync_func)()

    async def testRejectsNonCallableTargetsWhenExecuted(self) -> None:
        """
        Fail on execution when the target cannot be called.

        Validates that the constructor performs no validation, so the
        resulting TypeError only appears once the task is awaited.
        """
        task = BackgroundTask(42)  # type: ignore[arg-type]

        with self.assertRaises(TypeError):
            await task()

class TestBackgroundTaskAsynchronousExecution(TestCase):
    """Validate the direct-await branch used for coroutine functions."""

    async def testAwaitsTheWrappedCoroutineFunction(self) -> None:
        """
        Await a coroutine function when the task is awaited.

        Validates that the coroutine is driven to completion and its side
        effects are observable.
        """
        calls: list[int] = []

        async def async_func() -> None:
            calls.append(1)

        await BackgroundTask(async_func)()
        self.assertEqual(calls, [1])

    async def testForwardsPositionalArguments(self) -> None:
        """
        Forward positional arguments to a coroutine function.

        Validates that arguments captured at construction reach the
        coroutine unchanged.
        """
        received: list[tuple[int, int]] = []

        async def async_func(first: int, second: int) -> None:
            received.append((first, second))

        await BackgroundTask(async_func, 1, 2)()
        self.assertEqual(received, [(1, 2)])

    async def testForwardsKeywordArguments(self) -> None:
        """
        Forward keyword arguments to a coroutine function.

        Validates that keyword arguments are applied when the coroutine is
        created.
        """
        received: list[tuple[str, str]] = []

        async def async_func(left: str, right: str) -> None:
            received.append((left, right))

        await BackgroundTask(async_func, left="alpha", right="beta")()
        self.assertEqual(received, [("alpha", "beta")])

    async def testRunsInsideTheEventLoopThread(self) -> None:
        """
        Keep coroutine execution on the running event loop.

        Validates that asynchronous callables are awaited directly instead
        of being offloaded to the default executor.
        """
        observed: list[int] = []

        async def async_func() -> None:
            observed.append(threading.get_ident())

        await BackgroundTask(async_func)()
        self.assertEqual(observed[0], threading.get_ident())

    async def testAwaitsCoroutineFunctionsWrappedInPartial(self) -> None:
        """
        Await a partially applied coroutine function.

        Validates that pre-bound arguments are honoured and the coroutine
        is awaited rather than scheduled in a thread.
        """
        received: list[tuple[int, int]] = []

        async def async_func(first: int, second: int) -> None:
            received.append((first, second))

        await BackgroundTask(functools.partial(async_func, 1), 2)()
        self.assertEqual(received, [(1, 2)])

    async def testAwaitsCallableObjectsWithACoroutineCall(self) -> None:
        """
        Await callable objects that return a coroutine.

        Validates that the coroutine is driven to completion; had it been
        offloaded to a thread it would have been created and discarded,
        leaving no trace of the invocation.
        """
        target = _AsyncCallable()

        await BackgroundTask(target, "payload")()
        self.assertEqual(target.calls, [("payload",)])

    async def testDiscardsTheReturnValue(self) -> None:
        """
        Return nothing regardless of the coroutine result.

        Validates that the value produced by the coroutine is dropped, as
        background work reports no result to its caller.
        """

        async def async_func() -> str:
            return "ignored"

        self.assertIsNone(await BackgroundTask(async_func)())

    async def testCanBeAwaitedRepeatedly(self) -> None:
        """
        Allow an asynchronous task instance to be reused.

        Validates that a fresh coroutine is created on every invocation,
        which is what makes the task re-entrant.
        """
        calls: list[int] = []

        async def async_func() -> None:
            calls.append(1)

        task = BackgroundTask(async_func)
        await task()
        await task()
        self.assertEqual(len(calls), 2)

    async def testPropagatesExceptions(self) -> None:
        """
        Surface failures raised inside the coroutine.

        Validates that an exception thrown by an asynchronous callable is
        re-raised to whoever awaited the task.
        """

        async def async_func() -> None:
            error_msg = "asynchronous failure"
            raise ValueError(error_msg)

        with self.assertRaises(ValueError):
            await BackgroundTask(async_func)()

class TestBackgroundTaskRunMethod(TestCase):
    """Validate the explicit run entry point of a single task."""

    async def testRunExecutesSynchronousCallables(self) -> None:
        """
        Execute a synchronous callable through the run method.

        Validates that the contract method produces the same effect as
        invoking the task directly.
        """
        calls: list[int] = []

        def sync_func() -> None:
            calls.append(1)

        await BackgroundTask(sync_func).run()
        self.assertEqual(calls, [1])

    async def testRunExecutesCoroutineFunctions(self) -> None:
        """
        Execute a coroutine function through the run method.

        Validates that the contract method awaits asynchronous callables
        exactly like the direct invocation path.
        """
        calls: list[int] = []

        async def async_func() -> None:
            calls.append(1)

        await BackgroundTask(async_func).run()
        self.assertEqual(calls, [1])

    async def testRunForwardsArgumentsLikeDirectInvocation(self) -> None:
        """
        Forward captured arguments when running the task.

        Validates that the run method delegates to the same invocation
        logic and therefore honours the stored arguments.
        """
        received: list[tuple[int, str]] = []

        def sync_func(value: int, label: str) -> None:
            received.append((value, label))

        await BackgroundTask(sync_func, 5, label="unit").run()
        self.assertEqual(received, [(5, "unit")])

    async def testRunPropagatesExceptions(self) -> None:
        """
        Surface failures raised while running the task.

        Validates that the run method does not swallow errors thrown by
        the wrapped callable.
        """

        def sync_func() -> None:
            error_msg = "run failure"
            raise RuntimeError(error_msg)

        with self.assertRaises(RuntimeError):
            await BackgroundTask(sync_func).run()

    async def testRunReturnsNone(self) -> None:
        """
        Report no value from the run coroutine.

        Validates that the run method matches the None return type
        declared by the contract.
        """

        def sync_func() -> str:
            return "ignored"

        self.assertIsNone(await BackgroundTask(sync_func).run())
