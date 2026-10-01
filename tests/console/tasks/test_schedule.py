from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
from orionis.console.contracts.schedule import ISchedule
from orionis.console.enums.events import SchedulerEvent
from orionis.console.enums.states import ScheduleStates
from orionis.console.fluent.contracts.task import ITask
from orionis.console.tasks.schedule import Schedule
from orionis.test import TestCase

class TestSchedule(TestCase):

    # ------------------------------------------------------------------ #
    #  Helpers                                                           #
    # ------------------------------------------------------------------ #

    def _make(self) -> Schedule:
        """
        Create a Schedule instance with fully mocked dependencies.

        Returns
        -------
        Schedule
            A Schedule with a mocked IReactor and ICatch so no real
            subprocess or network calls are made during tests.
        """
        reactor = MagicMock()
        reactor.info = AsyncMock(return_value=[])
        reactor.call = AsyncMock(return_value=0)
        handler = MagicMock()
        stores = self._makeStores()
        return Schedule(
            reactor=reactor,
            exception_handler=handler,
            stores=stores,
        )

    def _makeStores(self) -> MagicMock:
        """
        Create a mocked ScheduleStore exposing a realistic config entity.

        Returns
        -------
        MagicMock
            A mock with ``store``/``config`` attributes matching the real
            ``ScheduleStore`` API used by ``Schedule``.
        """
        stores = MagicMock()
        stores.store = "memory"
        config = MagicMock()
        config.store = "memory"
        config.jitter = 0
        config.max_instances = 1
        config.misfire_grace_time = 30
        config.coalesce = True
        config.replace_existing = True
        stores.config = config
        return stores

    # ------------------------------------------------------------------ #
    #  Instantiation & interface                                         #
    # ------------------------------------------------------------------ #

    def testInstantiation(self) -> None:
        """Verify that Schedule can be instantiated with valid dependencies.

        Ensures the constructor completes without raising any exception
        when provided with mocked IReactor and ICatch instances.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        self.assertIsInstance(schedule, Schedule)

    def testIsSubclassOfISchedule(self) -> None:
        """Verify that Schedule is a subclass of ISchedule.

        Ensures the concrete implementation satisfies the abstract interface
        so it can be used polymorphically wherever ISchedule is expected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(Schedule, ISchedule))

    def testInstanceIsISchedule(self) -> None:
        """Verify that a Schedule instance satisfies isinstance(obj, ISchedule).

        Ensures polymorphic usage is valid and the object passes type checks
        against the abstract interface.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        self.assertIsInstance(schedule, ISchedule)

    # ------------------------------------------------------------------ #
    #  Initial state                                                     #
    # ------------------------------------------------------------------ #

    def testInitialStateIsStopped(self) -> None:
        """Verify that the scheduler state is 'STOPPED' immediately after construction.

        Ensures the scheduler does not auto-start and that callers can rely
        on the STOPPED state before calling boot().

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        self.assertEqual(schedule.state(), "STOPPED")

    def testIsStoppedReturnsTrueInitially(self) -> None:
        """Verify that isStopped() returns True before boot() is called.

        Ensures the initial stopped flag is consistent with the state string
        so callers can use either API interchangeably.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        self.assertTrue(schedule.isStopped())

    def testIsRunningReturnsFalseInitially(self) -> None:
        """Verify that isRunning() returns False before boot() is called.

        Ensures the scheduler does not report itself as running before it
        has been explicitly started.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        self.assertFalse(schedule.isRunning())

    def testIsPausedReturnsFalseInitially(self) -> None:
        """Verify that isPaused() returns False before boot() is called.

        Ensures the scheduler does not report itself as paused when it has
        never been started.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        self.assertFalse(schedule.isPaused())

    # ------------------------------------------------------------------ #
    #  state() after manual state mutation                               #
    # ------------------------------------------------------------------ #

    def testStateReturnsRunningWhenStateIsRunning(self) -> None:
        """Verify that state() returns 'RUNNING' when internal state is RUNNING.

        Ensures the state property correctly reflects an externally set
        running state for test isolation purposes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        schedule._Schedule__state = ScheduleStates.RUNNING
        self.assertEqual(schedule.state(), "RUNNING")

    def testStateReturnsPausedWhenStateIsPaused(self) -> None:
        """Verify that state() returns 'PAUSED' when internal state is PAUSED.

        Ensures the state property correctly reflects an externally set
        paused state so test scenarios can verify all three values.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        schedule._Schedule__state = ScheduleStates.PAUSED
        self.assertEqual(schedule.state(), "PAUSED")

    def testIsRunningReturnsTrueWhenStateIsRunning(self) -> None:
        """Verify that isRunning() returns True when internal state is RUNNING.

        Ensures the predicate method is consistent with the state string
        so callers never need to compare strings directly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        schedule._Schedule__state = ScheduleStates.RUNNING
        self.assertTrue(schedule.isRunning())

    def testIsPausedReturnsTrueWhenStateIsPaused(self) -> None:
        """Verify that isPaused() returns True when internal state is PAUSED.

        Ensures the predicate method is consistent with the state string
        for all supported state values.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        schedule._Schedule__state = ScheduleStates.PAUSED
        self.assertTrue(schedule.isPaused())

    def testIsStoppedReturnsFalseWhenRunning(self) -> None:
        """Verify that isStopped() returns False when the state is RUNNING.

        Ensures the stopped predicate is mutually exclusive with the
        running predicate at any given time.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        schedule._Schedule__state = ScheduleStates.RUNNING
        self.assertFalse(schedule.isStopped())

    # ------------------------------------------------------------------ #
    # Tests for command() method and its argument validation             #
    # ------------------------------------------------------------------ #

    def testCommandReturnsITaskForValidSignature(self) -> None:
        """Verify that command() returns an ITask instance for a valid signature.

        Ensures the fluent task builder is returned so callers can chain
        scheduling configuration methods onto it.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        task = schedule.command("inspire:quote")
        self.assertIsInstance(task, ITask)

    def testCommandWithValidArgsReturnsITask(self) -> None:
        """Verify that command() accepts string arguments with a task signature.

        Ensures the method stores the argument list and returns the ITask
        without raising any exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        task = schedule.command("db:seed", args=["--class", "UserSeeder"])
        self.assertIsInstance(task, ITask)

    def testCommandWithNoneArgsReturnsITask(self) -> None:
        """Verify that command() accepts None as the args argument.

        Ensures the default None value is treated as an empty argument list
        without raising any exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        task = schedule.command("migrate:fresh", args=None)
        self.assertIsInstance(task, ITask)

    def testCommandWithPurposeReturnsITask(self) -> None:
        """Verify that command() stores an optional purpose description.

        Ensures the method accepts and stores the descriptive purpose string
        without raising any exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        task = schedule.command("queue:work", purpose="Process queued jobs")
        self.assertIsInstance(task, ITask)

    def testCommandRaisesTypeErrorForEmptySignature(self) -> None:
        """Verify that command() raises TypeError when given an empty string signature.

        Ensures blank signatures are rejected before they can be registered
        in the internal task map, preventing silent misconfiguration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        with self.assertRaises(TypeError):
            schedule.command("")

    def testCommandRaisesTypeErrorForWhitespaceOnlySignature(self) -> None:
        """Verify that command() raises TypeError for whitespace-only signatures.

        Ensures that signatures containing only spaces or tabs are treated
        as empty and rejected consistently with empty string handling.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        with self.assertRaises(TypeError):
            schedule.command("   ")

    def testCommandRaisesTypeErrorForNonStringSignature(self) -> None:
        """Verify that command() raises TypeError when signature is not a string.

        Ensures numeric and other non-string values are rejected so the
        task map always contains homogeneous string keys.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        with self.assertRaises(TypeError):
            schedule.command(123)  # type: ignore[arg-type]

    def testCommandRaisesTypeErrorForNonListArgs(self) -> None:
        """Verify that command() raises TypeError when args is not a list.

        Ensures that passing a tuple or string instead of a list is rejected
        with a clear error rather than silently accepted.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        with self.assertRaises(TypeError):
            schedule.command("db:seed", args="--force")  # type: ignore[arg-type]

    def testCommandRaisesTypeErrorForArgsWithNonStringElements(self) -> None:
        """Verify that command() raises TypeError when a list element is not a string.

        Ensures that mixed-type argument lists are rejected because the
        scheduler passes these args directly to the CLI which expects strings.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        with self.assertRaises(TypeError):
            schedule.command("db:seed", args=[1, 2, 3])  # type: ignore[arg-type]

    def testCommandRaisesRuntimeErrorWhenNotStopped(self) -> None:
        """Verify that command() raises RuntimeError when the scheduler is running.

        Ensures that new commands cannot be added after boot() so the job
        set remains stable during execution.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        schedule._Schedule__state = ScheduleStates.RUNNING
        with self.assertRaises(RuntimeError):
            schedule.command("migrate:fresh")

    def testCommandRaisesRuntimeErrorWhenPaused(self) -> None:
        """Verify that command() raises RuntimeError when the scheduler is paused.

        Ensures the restriction applies to both the RUNNING and PAUSED states
        so commands can only be added in the STOPPED state.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        schedule._Schedule__state = ScheduleStates.PAUSED
        with self.assertRaises(RuntimeError):
            schedule.command("migrate:fresh")

    def testCommandRegistersSignatureInFluentTasks(self) -> None:
        """Verify that command() stores the signature in the internal fluent tasks map.

        Ensures the command is available for validation and loading when
        boot() is later called.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        schedule.command("cache:clear")
        self.assertIn("cache:clear", schedule._Schedule__fluent_tasks)

    # ------------------------------------------------------------------ #
    # Tests for on() method and its argument validation                  #
    # ------------------------------------------------------------------ #

    def testOnRegistersListenerWhenStopped(self) -> None:
        """Verify that on() registers the listener in the internal listeners map.

        Ensures the listener is stored against the given event code so it
        will be dispatched by the scheduler once boot() is called.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        listener = lambda _: None  # noqa: E731
        schedule.on(SchedulerEvent.STARTED, listener)
        self.assertIn(SchedulerEvent.STARTED, schedule._Schedule__scheduler_listeners)

    def testOnReturnsSelf(self) -> None:
        """Verify that on() returns the Schedule instance for method chaining.

        Ensures the fluent registration interface allows callers to chain
        multiple on() calls without capturing intermediate results.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        result = schedule.on(SchedulerEvent.STARTED, lambda _: None)
        self.assertIs(result, schedule)

    def testOnRaisesTypeErrorForInvalidEvent(self) -> None:
        """Verify that on() raises TypeError when the event is not a SchedulerEvent.

        Ensures string literals and integers cannot be used as event keys so
        listeners are always bound to a well-typed event.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        with self.assertRaises(TypeError):
            schedule.on("started", lambda _: None)  # type: ignore[arg-type]

    def testOnRaisesTypeErrorForNonCallableListener(self) -> None:
        """Verify that on() raises TypeError when the listener is not callable.

        Ensures non-callable values like strings or None are rejected early
        so the scheduler never tries to invoke an invalid listener.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        with self.assertRaises(TypeError):
            schedule.on(SchedulerEvent.STARTED, "not_a_callable")

    def testOnRaisesRuntimeErrorWhenRunning(self) -> None:
        """Verify that on() raises RuntimeError when the scheduler is already running.

        Ensures scheduler event listeners cannot be registered after boot()
        has been called, enforcing a clear configuration lifecycle.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        schedule._Schedule__state = ScheduleStates.RUNNING
        with self.assertRaises(RuntimeError):
            schedule.on(SchedulerEvent.STARTED, lambda _: None)

    def testOnRaisesRuntimeErrorWhenPaused(self) -> None:
        """Verify that on() raises RuntimeError when the scheduler is paused.

        Ensures that the PAUSED state is also treated as a post-boot state
        that prevents listener registration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        schedule._Schedule__state = ScheduleStates.PAUSED
        with self.assertRaises(RuntimeError):
            schedule.on(SchedulerEvent.STARTED, lambda _: None)

    def testOnAcceptsAllSchedulerEventValues(self) -> None:
        """Verify that on() accepts every value defined in the SchedulerEvent enum.

        Ensures all documented event types can be registered without raising
        any exception, providing full event coverage.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        for event in SchedulerEvent:
            result = schedule.on(event, lambda _: None)
            self.assertIs(result, schedule)

    # ------------------------------------------------------------------ #
    #  pauseTask() — scheduler not started                               #
    # ------------------------------------------------------------------ #

    def testPauseTaskRaisesRuntimeErrorWhenSchedulerNotStarted(self) -> None:
        """Verify that pauseTask() raises RuntimeError when the scheduler is None.

        Ensures the guard against an uninitialised scheduler prevents
        calling APScheduler methods that would fail with AttributeError.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        with self.assertRaises(RuntimeError):
            schedule.pauseTask("some:task")

    def testPauseTaskErrorMessageMentionsScheduler(self) -> None:
        """Verify that the RuntimeError from pauseTask() contains a meaningful message.

        Ensures the error message helps callers understand that the scheduler
        must be booted before task-level operations can be performed.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        with self.assertRaises(RuntimeError) as ctx:
            schedule.pauseTask("some:task")
        self.assertIn("scheduler", str(ctx.exception).lower())

    # ------------------------------------------------------------------ #
    #  resumeTask() — scheduler not started                              #
    # ------------------------------------------------------------------ #

    def testResumeTaskRaisesRuntimeErrorWhenSchedulerNotStarted(self) -> None:
        """Verify that resumeTask() raises RuntimeError when the scheduler is None.

        Ensures the guard prevents callers from attempting to resume a task
        when the scheduler infrastructure is not yet initialised.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        with self.assertRaises(RuntimeError):
            schedule.resumeTask("some:task")

    # ------------------------------------------------------------------ #
    #  removeTask() — scheduler not started                              #
    # ------------------------------------------------------------------ #

    def testRemoveTaskRaisesRuntimeErrorWhenSchedulerNotStarted(self) -> None:
        """Verify that removeTask() raises RuntimeError when the scheduler is None.

        Ensures the guard prevents callers from trying to remove a job that
        was never registered with an uninitialised APScheduler instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        with self.assertRaises(RuntimeError):
            schedule.removeTask("some:task")

    # ------------------------------------------------------------------ #
    #  removeAllTasks() — scheduler not started                          #
    # ------------------------------------------------------------------ #

    def testRemoveAllTasksRaisesRuntimeErrorWhenSchedulerNotStarted(self) -> None:
        """Verify that removeAllTasks() raises RuntimeError when the scheduler is None.

        Ensures the guard covers the bulk-removal code path with the same
        safety check that individual task methods enforce.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        with self.assertRaises(RuntimeError):
            schedule.removeAllTasks()

    # ------------------------------------------------------------------ #
    #  pause() — scheduler not started                                   #
    # ------------------------------------------------------------------ #

    def testPauseRaisesRuntimeErrorWhenSchedulerNotStarted(self) -> None:
        """Verify that pause() raises RuntimeError when the scheduler is None.

        Ensures the scheduler-global pause operation cannot be invoked
        before boot() has initialised the APScheduler instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        with self.assertRaises(RuntimeError):
            schedule.pause()

    # ------------------------------------------------------------------ #
    #  resume() — scheduler not started                                  #
    # ------------------------------------------------------------------ #

    def testResumeRaisesRuntimeErrorWhenSchedulerNotStarted(self) -> None:
        """Verify that resume() raises RuntimeError when the scheduler is None.

        Ensures the scheduler-global resume operation cannot be invoked
        before boot() has initialised the APScheduler instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        with self.assertRaises(RuntimeError):
            schedule.resume()

    # ------------------------------------------------------------------ #
    #  pause() / resume() state checks with mocked scheduler            #
    # ------------------------------------------------------------------ #

    def testPauseRaisesRuntimeErrorWhenNotRunning(self) -> None:
        """Verify that pause() raises RuntimeError when the scheduler is stopped.

        Ensures a second guard prevents pausing a scheduler that is already
        in the STOPPED state, providing a clear and actionable error.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        schedule._Schedule__scheduler = MagicMock()
        # state is STOPPED by default, not RUNNING
        with self.assertRaises(RuntimeError):
            schedule.pause()

    def testResumeRaisesRuntimeErrorWhenNotPaused(self) -> None:
        """Verify that resume() raises RuntimeError when the scheduler is not paused.

        Ensures a second guard prevents resuming a scheduler in the STOPPED
        or RUNNING state, providing a clear and actionable error.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        schedule._Schedule__scheduler = MagicMock()
        schedule._Schedule__state = ScheduleStates.RUNNING
        with self.assertRaises(RuntimeError):
            schedule.resume()

    # ------------------------------------------------------------------ #
    #  pauseTask() / resumeTask() with mocked scheduler                  #
    # ------------------------------------------------------------------ #

    def testPauseTaskRaisesRuntimeErrorWhenTaskNotRunning(self) -> None:
        """Verify that pauseTask() raises RuntimeError when the task is not running.

        Ensures that tasks must first be registered and running before they
        can be paused, preventing silent no-ops.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        schedule._Schedule__scheduler = MagicMock()
        with self.assertRaises(RuntimeError):
            schedule.pauseTask("non:existent")

    def testResumeTaskRaisesRuntimeErrorWhenTaskNotPaused(self) -> None:
        """Verify that resumeTask() raises RuntimeError when the task is not paused.

        Ensures that tasks must be paused before they can be resumed,
        preventing accidental double-resume calls.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        schedule._Schedule__scheduler = MagicMock()
        with self.assertRaises(RuntimeError):
            schedule.resumeTask("non:existent")

    def testRemoveTaskRaisesRuntimeErrorWhenTaskNotFound(self) -> None:
        """Verify that removeTask() raises RuntimeError when the task is not found.

        Ensures the method rejects removal of unknown tasks before attempting
        any APScheduler operations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        schedule._Schedule__scheduler = MagicMock()
        with self.assertRaises(RuntimeError):
            schedule.removeTask("non:existent")

    def testPauseTaskSucceedsWithMockedJob(self) -> None:
        """Verify that pauseTask() returns True when the scheduler and job exist.

        Ensures the happy-path completes, moves the task from running to
        paused, and returns the documented boolean result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        mock_scheduler = MagicMock()
        mock_scheduler.get_job.return_value = MagicMock()
        schedule._Schedule__scheduler = mock_scheduler
        schedule._Schedule__running_tasks = {"my:task"}
        result = schedule.pauseTask("my:task")
        self.assertTrue(result)
        self.assertIn("my:task", schedule._Schedule__paused_tasks)
        self.assertNotIn("my:task", schedule._Schedule__running_tasks)

    def testResumeTaskSucceedsWithMockedJob(self) -> None:
        """Verify that resumeTask() returns True when the job is in the paused set.

        Ensures the happy-path completes, moves the task from paused to
        running, and returns the documented boolean result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        mock_scheduler = MagicMock()
        mock_scheduler.get_job.return_value = MagicMock()
        schedule._Schedule__scheduler = mock_scheduler
        schedule._Schedule__paused_tasks = {"my:task"}
        result = schedule.resumeTask("my:task")
        self.assertTrue(result)
        self.assertIn("my:task", schedule._Schedule__running_tasks)
        self.assertNotIn("my:task", schedule._Schedule__paused_tasks)

    def testRemoveTaskSucceedsWithMockedJob(self) -> None:
        """Verify that removeTask() returns True when the job is in the running set.

        Ensures the happy-path removes the task from internal sets and
        returns the documented boolean result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        mock_scheduler = MagicMock()
        mock_scheduler.get_job.return_value = MagicMock()
        schedule._Schedule__scheduler = mock_scheduler
        schedule._Schedule__running_tasks = {"my:task"}
        result = schedule.removeTask("my:task")
        self.assertTrue(result)
        self.assertNotIn("my:task", schedule._Schedule__running_tasks)
        self.assertIn("my:task", schedule._Schedule__removed_tasks)

    def testRemoveAllTasksSucceedsWithMockedScheduler(self) -> None:
        """Verify that removeAllTasks() returns True when the scheduler is initialised.

        Ensures all internal task tracking sets are cleared and the method
        returns True as documented.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        mock_scheduler = MagicMock()
        schedule._Schedule__scheduler = mock_scheduler
        schedule._Schedule__running_tasks = {"t1", "t2"}
        result = schedule.removeAllTasks()
        self.assertTrue(result)
        self.assertEqual(len(schedule._Schedule__running_tasks), 0)

    def testPauseSucceedsWithMockedRunningScheduler(self) -> None:
        """Verify that pause() returns True when the scheduler is in RUNNING state.

        Ensures the state transitions from RUNNING to PAUSED after a
        successful pause call.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        mock_scheduler = MagicMock()
        schedule._Schedule__scheduler = mock_scheduler
        schedule._Schedule__state = ScheduleStates.RUNNING
        result = schedule.pause()
        self.assertTrue(result)
        self.assertEqual(schedule.state(), "PAUSED")

    def testResumeSucceedsWithMockedPausedScheduler(self) -> None:
        """Verify that resume() returns True when the scheduler is in PAUSED state.

        Ensures the state transitions from PAUSED to RUNNING after a
        successful resume call.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()
        mock_scheduler = MagicMock()
        schedule._Schedule__scheduler = mock_scheduler
        schedule._Schedule__state = ScheduleStates.PAUSED
        result = schedule.resume()
        self.assertTrue(result)
        self.assertEqual(schedule.state(), "RUNNING")

    # ------------------------------------------------------------------ #
    #  _reactorCall (async)                                              #
    # ------------------------------------------------------------------ #

    async def testReactorCallDelegatesToReactor(self) -> None:
        """Verify that _reactorCall() awaits the reactor call and returns its result.

        Ensures the thin async wrapper delegates correctly to the underlying
        reactor without altering the return value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        reactor = MagicMock()
        reactor.call = AsyncMock(return_value=0)
        handler = MagicMock()
        schedule = Schedule(
            reactor=reactor,
            exception_handler=handler,
            stores=self._makeStores(),
        )
        result = await schedule._reactorCall("inspire:quote", ["--lang", "en"])
        reactor.call.assert_called_once_with("inspire:quote", ["--lang", "en"])
        self.assertEqual(result, 0)

    async def testReactorCallUsesEmptyListWhenArgsIsNone(self) -> None:
        """Verify that _reactorCall() passes an empty list when args is None.

        Ensures the None default is converted to [] before being forwarded
        to the reactor so the reactor never receives None as its args.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        reactor = MagicMock()
        reactor.call = AsyncMock(return_value=0)
        handler = MagicMock()
        schedule = Schedule(
            reactor=reactor,
            exception_handler=handler,
            stores=self._makeStores(),
        )
        await schedule._reactorCall("db:seed")
        reactor.call.assert_called_once_with("db:seed", [])

    # ------------------------------------------------------------------ #
    #  shutdown() wait parameter                                         #
    # ------------------------------------------------------------------ #

    async def testShutdownKeepsDefaultWaitForNone(self) -> None:
        """Verify that shutdown(None) keeps the configured default wait time.

        Ensures passing None as the wait argument preserves the grace
        period configured in __init__ (0.5s) instead of collapsing it to
        zero, so pending cleanup still gets a chance to run by default.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()

        def _close(coro):
            """Close the supplied coroutine.

            Parameters
            ----------
            coro : object
                Value supplied for ``coro``.

            Returns
            -------
            None
                Completes the operation described above.
            """
            coro.close()

        with patch.object(schedule, "_Schedule__createManagedTask", side_effect=_close):
            schedule.shutdown(None)
        self.assertEqual(schedule._Schedule__wait_to_shutdown, 0.5)

    async def testShutdownSetsWaitForValidInteger(self) -> None:
        """Verify that shutdown(5) stores 5 as the internal wait-before-shutdown delay.

        Ensures integer wait values are stored verbatim so the graceful
        shutdown coroutine sleeps for the correct duration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()

        def _close(coro):
            """Close the supplied coroutine.

            Parameters
            ----------
            coro : object
                Value supplied for ``coro``.

            Returns
            -------
            None
                Completes the operation described above.
            """
            coro.close()

        with patch.object(schedule, "_Schedule__createManagedTask", side_effect=_close):
            schedule.shutdown(5)
        self.assertEqual(schedule._Schedule__wait_to_shutdown, 5)

    async def testShutdownRaisesTypeErrorForNegativeInt(self) -> None:
        """Verify that shutdown(-1) raises TypeError instead of silently clamping.

        Ensures negative integers are rejected outright rather than being
        silently normalised to zero, which would mask a caller bug.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()

        def _close(coro):
            """Close the supplied coroutine.

            Parameters
            ----------
            coro : object
                Value supplied for ``coro``.

            Returns
            -------
            None
                Completes the operation described above.
            """
            coro.close()

        with (
            patch.object(schedule, "_Schedule__createManagedTask", side_effect=_close),
            self.assertRaises(TypeError),
        ):
            schedule.shutdown(-1)

    async def testShutdownRaisesTypeErrorForBool(self) -> None:
        """Verify that shutdown(True) raises TypeError instead of being accepted.

        Ensures bool (a subtype of int) is explicitly rejected so a caller
        mistake is not silently coerced into a 0/1 second wait.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        schedule = self._make()

        def _close(coro):
            """Close the supplied coroutine.

            Parameters
            ----------
            coro : object
                Value supplied for ``coro``.

            Returns
            -------
            None
                Completes the operation described above.
            """
            coro.close()

        with (
            patch.object(schedule, "_Schedule__createManagedTask", side_effect=_close),
            self.assertRaises(TypeError),
        ):
            schedule.shutdown(True)
