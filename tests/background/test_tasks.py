from orionis.background.contracts.task import IBackgroundTask
from orionis.background.task import BackgroundTask
from orionis.background.tasks import BackgroundTasks
from orionis.test import TestCase

def noop() -> None:
    """
    Do nothing.

    Returns
    -------
    None
        This function does not return a value.
    """

class TestBackgroundTasksInitialization(TestCase):
    """Validate how a collection stores the tasks it is seeded with."""

    def testStartsEmptyWhenNoSequenceIsProvided(self) -> None:
        """Start with an empty collection by default.

        Validates that a collection built without arguments exposes an
        empty task list ready to be filled.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(BackgroundTasks().tasks, [])

    def testTreatsNoneAsAnEmptySequence(self) -> None:
        """Accept None as the absence of initial tasks.

        Validates that an explicit None behaves exactly like omitting the
        argument altogether.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(BackgroundTasks(None).tasks, [])

    def testTreatsAnEmptySequenceAsNoTasks(self) -> None:
        """Accept an empty sequence as the absence of initial tasks.

        Validates that a falsy sequence takes the same branch as None and
        yields an independent empty list.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(BackgroundTasks([]).tasks, [])

    def testStoresTheProvidedTasksInOrder(self) -> None:
        """Keep the seeded tasks and their order.

        Validates that every task supplied at construction is stored
        verbatim, without wrapping or reordering.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        first = BackgroundTask(noop)
        second = BackgroundTask(noop)

        collection = BackgroundTasks([first, second])
        self.assertEqual(collection.tasks, [first, second])

    def testConvertsAnyProvidedSequenceIntoAList(self) -> None:
        """Normalise the seeded sequence into a mutable list.

        Validates that immutable inputs such as tuples are converted so
        further tasks can still be appended.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        collection = BackgroundTasks((BackgroundTask(noop),))

        self.assertIsInstance(collection.tasks, list)

    def testDoesNotAliasTheProvidedSequence(self) -> None:
        """Copy the seeded sequence instead of referencing it.

        Validates that mutating the original container after construction
        cannot alter the collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        provided = [BackgroundTask(noop)]

        collection = BackgroundTasks(provided)
        provided.clear()
        self.assertEqual(len(collection.tasks), 1)

    def testDoesNotInitialiseTheSingleTaskState(self) -> None:
        """Skip the single-task state inherited from the parent class.

        Validates that a collection never populates the callable and
        argument slots used by an individual task.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        collection = BackgroundTasks()

        self.assertFalse(hasattr(collection, "_BackgroundTask__func"))
        self.assertFalse(hasattr(collection, "_BackgroundTask__is_async"))

    def testDeclaresSlotsInsteadOfAnInstanceDictionary(self) -> None:
        """Store the collection state in slots.

        Validates that extending the task class does not reintroduce an
        instance dictionary.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(hasattr(BackgroundTasks(), "__dict__"))

class TestBackgroundTasksAddTask(TestCase):
    """Validate the incremental registration of callables."""

    def testAppendsOneTaskPerCall(self) -> None:
        """Append exactly one task on every call.

        Validates that the collection grows by a single entry each time a
        callable is registered.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        collection = BackgroundTasks()

        collection.addTask(noop)
        collection.addTask(noop)
        self.assertEqual(len(collection.tasks), 2)

    def testWrapsTheCallableInABackgroundTask(self) -> None:
        """Wrap the registered callable in a background task.

        Validates that callers may register raw callables and still obtain
        a uniform collection of task objects.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        collection = BackgroundTasks()

        collection.addTask(noop)
        self.assertIsInstance(collection.tasks[0], BackgroundTask)

    def testReportsNoValue(self) -> None:
        """Report no value when registering a callable.

        Validates that registration is a pure side effect on the internal
        list, matching the declared None return type.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        collection = BackgroundTasks()

        self.assertIsNone(collection.addTask(noop))

    async def testForwardsPositionalArguments(self) -> None:
        """Forward positional arguments to the registered callable.

        Validates that arguments captured during registration reach the
        callable when the collection runs.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        received: list[tuple[int, int]] = []

        def capture(first: int, second: int) -> None:
            """Record the supplied call arguments.

            Parameters
            ----------
            first : int
                Value supplied for ``first``.
            second : int
                Value supplied for ``second``.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            received.append((first, second))

        collection = BackgroundTasks()
        collection.addTask(capture, 3, 7)
        await collection()
        self.assertEqual(received, [(3, 7)])

    async def testForwardsKeywordArguments(self) -> None:
        """Forward keyword arguments to the registered callable.

        Validates that keyword arguments captured during registration are
        applied when the collection runs.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        received: list[tuple[str, int]] = []

        def capture(name: str, value: int) -> None:
            """Record the supplied call arguments.

            Parameters
            ----------
            name : str
                Value supplied for ``name``.
            value : int
                Value supplied for ``value``.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            received.append((name, value))

        collection = BackgroundTasks()
        collection.addTask(capture, name="report", value=42)
        await collection()
        self.assertEqual(received, [("report", 42)])

    async def testAcceptsCoroutineFunctions(self) -> None:
        """Register coroutine functions alongside plain callables.

        Validates that asynchronous callables are wrapped with the same
        API and awaited when the collection runs.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        calls: list[int] = []

        async def async_func() -> None:
            """Run an asynchronous test callable.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            calls.append(1)

        collection = BackgroundTasks()
        collection.addTask(async_func)
        await collection()
        self.assertEqual(calls, [1])

class TestBackgroundTasksExecution(TestCase):
    """Validate the sequential execution of a task collection."""

    async def testRunsEveryTaskInInsertionOrder(self) -> None:
        """Execute the registered tasks in insertion order.

        Validates that the collection preserves the order callers relied
        on when registering their side effects.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        results: list[int] = []

        def first() -> None:
            """Record the first task marker.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            results.append(1)

        def second() -> None:
            """Record the second task marker.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            results.append(2)

        def third() -> None:
            """Record the third task marker.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            results.append(3)

        collection = BackgroundTasks()
        collection.addTask(first)
        collection.addTask(second)
        collection.addTask(third)
        await collection.run()
        self.assertEqual(results, [1, 2, 3])

    async def testCallAndRunBehaveIdentically(self) -> None:
        """Produce the same effect from both invocation paths.

        Validates that invoking the collection directly and calling its
        run method execute the very same work.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        results: list[str] = []

        def append_entry() -> None:
            """Append a marker to the execution log.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            results.append("entry")

        collection = BackgroundTasks()
        collection.addTask(append_entry)
        await collection()
        await collection.run()
        self.assertEqual(results, ["entry", "entry"])

    async def testCompletesWithoutErrorWhenEmpty(self) -> None:
        """Complete silently when no task is registered.

        Validates that an empty collection is a harmless no-op rather than
        an error condition.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsNone(await BackgroundTasks().run())

    async def testRunsTasksProvidedAtConstruction(self) -> None:
        """Execute tasks supplied at construction time.

        Validates that seeded tasks are treated exactly like tasks added
        afterwards.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        results: list[int] = []

        def append_entry() -> None:
            """Append a marker to the execution log.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            results.append(1)

        await BackgroundTasks([BackgroundTask(append_entry)]).run()
        self.assertEqual(results, [1])

    async def testRunsSynchronousAndAsynchronousTasksAlike(self) -> None:
        """Execute mixed callables within a single collection.

        Validates that synchronous and asynchronous callables can be
        combined while keeping the declared order.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        results: list[str] = []

        def sync_func() -> None:
            """Run a synchronous test callable.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            results.append("sync")

        async def async_func() -> None:
            """Run an asynchronous test callable.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            results.append("async")

        collection = BackgroundTasks()
        collection.addTask(sync_func)
        collection.addTask(async_func)
        await collection.run()
        self.assertEqual(results, ["sync", "async"])

    async def testRunsNestedCollections(self) -> None:
        """Execute collections nested inside another collection.

        Validates that a collection is itself a valid task, so groups of
        side effects can be composed.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        results: list[str] = []

        def inner_func() -> None:
            """Record the inner task execution.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            results.append("inner")

        def outer_func() -> None:
            """Record the outer task execution.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            results.append("outer")

        inner = BackgroundTasks()
        inner.addTask(inner_func)
        outer = BackgroundTasks([inner, BackgroundTask(outer_func)])
        await outer.run()
        self.assertEqual(results, ["inner", "outer"])

    async def testRunsNestedCollectionsRegisteredWithAddTask(self) -> None:
        """Execute a collection registered as a regular callable.

        Validates that nesting through the registration API awaits the
        inner collection instead of dropping its coroutine in a thread.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        results: list[str] = []

        def inner_func() -> None:
            """Record the inner task execution.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            results.append("inner")

        inner = BackgroundTasks()
        inner.addTask(inner_func)
        outer = BackgroundTasks()
        outer.addTask(inner)
        await outer.run()
        self.assertEqual(results, ["inner"])

    async def testStopsAtTheFirstFailingTask(self) -> None:
        """Abort the sequence when a task raises.

        Validates that the failure is propagated and that tasks queued
        after the failing one are never executed.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        results: list[int] = []

        def first() -> None:
            """Record the first task marker.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            results.append(1)

        def failing() -> None:
            """Raise an error during task execution.

            Returns
            -------
            None
                Initializes or completes the operation described above.

            Raises
            ------
            RuntimeError
                Raised by this helper to exercise the error path.
            """
            error_msg = "task failure"
            raise RuntimeError(error_msg)

        def third() -> None:
            """Record the third task marker.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            results.append(3)

        collection = BackgroundTasks()
        collection.addTask(first)
        collection.addTask(failing)
        collection.addTask(third)

        with self.assertRaises(RuntimeError):
            await collection.run()

        self.assertEqual(results, [1])

    async def testCanBeExecutedRepeatedly(self) -> None:
        """Allow a collection to be executed more than once.

        Validates that running the collection does not consume or clear
        the registered tasks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        calls: list[int] = []

        def append_entry() -> None:
            """Append a marker to the execution log.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            calls.append(1)

        collection = BackgroundTasks()
        collection.addTask(append_entry)
        await collection.run()
        await collection.run()
        self.assertEqual(len(calls), 2)

    async def testPicksUpTasksAddedAfterAPreviousRun(self) -> None:
        """Execute tasks registered after an earlier run.

        Validates that the collection reads its task list on every
        invocation instead of caching it.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        results: list[str] = []

        def first() -> None:
            """Record the first task marker.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            results.append("first")

        def second() -> None:
            """Record the second task marker.

            Returns
            -------
            None
                Initializes or completes the operation described above.
            """
            results.append("second")

        collection = BackgroundTasks()
        collection.addTask(first)
        await collection.run()
        collection.addTask(second)
        await collection.run()
        self.assertEqual(results, ["first", "first", "second"])

class TestBackgroundTasksSubstitutability(TestCase):
    """Validate that a collection can replace a single task."""

    def testExtendsTheSingleTaskImplementation(self) -> None:
        """Derive the collection from the single task class.

        Validates that isinstance checks expecting a single task, such as
        the one guarding HTTP responses, also accept a collection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(BackgroundTasks, BackgroundTask))
        self.assertIsInstance(BackgroundTasks(), BackgroundTask)

    def testImplementsTheBackgroundTaskContract(self) -> None:
        """Satisfy the background task interface.

        Validates that a collection is usable wherever the abstract
        contract is required.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(BackgroundTasks(), IBackgroundTask)

    def testInheritsTheRunEntryPoint(self) -> None:
        """Reuse the run entry point defined by the parent class.

        Validates that the collection does not duplicate the delegation
        already implemented for a single task.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIs(BackgroundTasks.run, BackgroundTask.run)
