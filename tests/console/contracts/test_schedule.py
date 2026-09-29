from __future__ import annotations
import inspect
from unittest.mock import AsyncMock, MagicMock
from orionis.console.contracts.schedule import ISchedule
from orionis.console.tasks.schedule import Schedule
from orionis.test import TestCase

class TestIScheduleContract(TestCase):

    @staticmethod
    def _makeStores() -> MagicMock:
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
    #  Abstract class characteristics                                    #
    # ------------------------------------------------------------------ #

    def testIsAbstractClass(self) -> None:
        """Verify that ISchedule is recognised as an abstract class.

        Ensures the interface declares at least one abstract method so
        Python prevents direct instantiation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.isabstract(ISchedule))

    def testCannotBeInstantiatedDirectly(self) -> None:
        """Verify that ISchedule cannot be instantiated directly.

        Ensures that attempting to create an instance raises TypeError
        due to unimplemented abstract methods.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            ISchedule()  # type: ignore[abstract]

    def testHasSixteenAbstractMethods(self) -> None:
        """Verify that ISchedule declares exactly sixteen abstract methods.

        Ensures the interface surface area is stable and that no methods
        have been silently added or removed without updating consumers.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(len(ISchedule.__abstractmethods__), 16)

    # ------------------------------------------------------------------ #
    #  Abstract method presence                                          #
    # ------------------------------------------------------------------ #

    def testInfoIsAbstract(self) -> None:
        """Verify that 'info' is listed in ISchedule.__abstractmethods__.

        Ensures every concrete subclass is forced to implement the task
        information retrieval method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("info", ISchedule.__abstractmethods__)

    def testBootIsAbstract(self) -> None:
        """Verify that 'boot' is listed in ISchedule.__abstractmethods__.

        Ensures every concrete subclass is forced to implement the scheduler
        initialisation method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("boot", ISchedule.__abstractmethods__)

    def testOnIsAbstract(self) -> None:
        """Verify that 'on' is listed in ISchedule.__abstractmethods__.

        Ensures every concrete subclass is forced to implement the event
        listener registration method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("on", ISchedule.__abstractmethods__)

    def testStateIsAbstract(self) -> None:
        """Verify that 'state' is listed in ISchedule.__abstractmethods__.

        Ensures every concrete subclass is forced to implement the state
        string accessor method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("state", ISchedule.__abstractmethods__)

    def testIsRunningIsAbstract(self) -> None:
        """Verify that 'isRunning' is listed in ISchedule.__abstractmethods__.

        Ensures every concrete subclass is forced to implement the running
        state predicate.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("isRunning", ISchedule.__abstractmethods__)

    def testIsPausedIsAbstract(self) -> None:
        """Verify that 'isPaused' is listed in ISchedule.__abstractmethods__.

        Ensures every concrete subclass is forced to implement the paused
        state predicate.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("isPaused", ISchedule.__abstractmethods__)

    def testIsStoppedIsAbstract(self) -> None:
        """Verify that 'isStopped' is listed in ISchedule.__abstractmethods__.

        Ensures every concrete subclass is forced to implement the stopped
        state predicate.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("isStopped", ISchedule.__abstractmethods__)

    def testCommandIsAbstract(self) -> None:
        """Verify that 'command' is listed in ISchedule.__abstractmethods__.

        Ensures every concrete subclass is forced to implement the fluent
        task registration method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("command", ISchedule.__abstractmethods__)

    def testPauseTaskIsAbstract(self) -> None:
        """Verify that 'pauseTask' is listed in ISchedule.__abstractmethods__.

        Ensures every concrete subclass is forced to implement the per-task
        pause method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("pauseTask", ISchedule.__abstractmethods__)

    def testResumeTaskIsAbstract(self) -> None:
        """Verify that 'resumeTask' is listed in ISchedule.__abstractmethods__.

        Ensures every concrete subclass is forced to implement the per-task
        resume method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("resumeTask", ISchedule.__abstractmethods__)

    def testRemoveTaskIsAbstract(self) -> None:
        """Verify that 'removeTask' is listed in ISchedule.__abstractmethods__.

        Ensures every concrete subclass is forced to implement the per-task
        removal method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("removeTask", ISchedule.__abstractmethods__)

    def testRemoveAllTasksIsAbstract(self) -> None:
        """Verify that 'removeAllTasks' is listed in ISchedule.__abstractmethods__.

        Ensures every concrete subclass is forced to implement the bulk
        task removal method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("removeAllTasks", ISchedule.__abstractmethods__)

    def testPauseIsAbstract(self) -> None:
        """Verify that 'pause' is listed in ISchedule.__abstractmethods__.

        Ensures every concrete subclass is forced to implement the
        scheduler-global pause method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("pause", ISchedule.__abstractmethods__)

    def testResumeIsAbstract(self) -> None:
        """Verify that 'resume' is listed in ISchedule.__abstractmethods__.

        Ensures every concrete subclass is forced to implement the
        scheduler-global resume method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("resume", ISchedule.__abstractmethods__)

    def testShutdownIsAbstract(self) -> None:
        """Verify that 'shutdown' is listed in ISchedule.__abstractmethods__.

        Ensures every concrete subclass is forced to implement the graceful
        shutdown initiation method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("shutdown", ISchedule.__abstractmethods__)

    def testWaitIsAbstract(self) -> None:
        """Verify that 'wait' is listed in ISchedule.__abstractmethods__.

        Ensures every concrete subclass is forced to implement the async
        shutdown completion wait method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("wait", ISchedule.__abstractmethods__)

    # ------------------------------------------------------------------ #
    #  Async method detection                                            #
    # ------------------------------------------------------------------ #

    def testInfoIsAsync(self) -> None:
        """Verify that 'info' is declared as a coroutine function in ISchedule.

        Ensures callers know to await the method rather than call it
        synchronously, preventing silent no-op usage.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.iscoroutinefunction(ISchedule.info))

    def testBootIsAsync(self) -> None:
        """Verify that 'boot' is declared as a coroutine function in ISchedule.

        Ensures callers know to await the scheduler initialisation method,
        which performs I/O operations to load commands.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.iscoroutinefunction(ISchedule.boot))

    def testWaitIsAsync(self) -> None:
        """Verify that 'wait' is declared as a coroutine function in ISchedule.

        Ensures callers must await the shutdown synchronisation method,
        which blocks until the graceful shutdown event is set.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.iscoroutinefunction(ISchedule.wait))

    # ------------------------------------------------------------------ #
    #  Signature verification                                            #
    # ------------------------------------------------------------------ #

    def testCommandSignatureHasSignatureParam(self) -> None:
        """Verify that 'command' declares a 'signature' parameter.

        Ensures the parameter name is stable so callers always use the
        correct keyword when invoking the method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(ISchedule.command)
        self.assertIn("signature", sig.parameters)

    def testCommandSignatureHasArgsParamWithNoneDefault(self) -> None:
        """Verify that 'command' has an 'args' parameter defaulting to None.

        Ensures callers can omit args and receive the documented default
        of None which is then treated as an empty list.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(ISchedule.command)
        params = sig.parameters
        self.assertIn("args", params)
        self.assertIsNone(params["args"].default)

    def testCommandSignatureHasPurposeParamWithNoneDefault(self) -> None:
        """Verify that 'command' has a 'purpose' parameter defaulting to None.

        Ensures the optional description parameter has the correct default
        so callers can omit it without specifying an explicit None.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(ISchedule.command)
        params = sig.parameters
        self.assertIn("purpose", params)
        self.assertIsNone(params["purpose"].default)

    def testOnSignatureHasEventParam(self) -> None:
        """Verify that 'on' declares an 'event' parameter.

        Ensures the parameter name matches the documented interface so
        callers are not surprised by unexpected keyword names.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(ISchedule.on)
        self.assertIn("event", sig.parameters)

    def testOnSignatureHasListenerParam(self) -> None:
        """Verify that 'on' declares a 'listener' parameter.

        Ensures the parameter name matches the documented interface so
        callers know exactly which keyword to use.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(ISchedule.on)
        self.assertIn("listener", sig.parameters)

    def testShutdownSignatureHasWaitParamWithNoneDefault(self) -> None:
        """Verify that 'shutdown' has a 'wait' parameter defaulting to None.

        Ensures callers can trigger an immediate shutdown without specifying
        a wait duration, as documented.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(ISchedule.shutdown)
        params = sig.parameters
        self.assertIn("wait", params)
        self.assertIsNone(params["wait"].default)

    def testPauseTaskSignatureHasSignatureParam(self) -> None:
        """Verify that 'pauseTask' declares a 'signature' parameter.

        Ensures callers identify the target task by signature string,
        consistent with how tasks are registered via command().

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(ISchedule.pauseTask)
        self.assertIn("signature", sig.parameters)

    def testResumeTaskSignatureHasSignatureParam(self) -> None:
        """Verify that 'resumeTask' declares a 'signature' parameter.

        Ensures callers identify the target task by signature string,
        consistent with how tasks are registered via command().

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(ISchedule.resumeTask)
        self.assertIn("signature", sig.parameters)

    def testRemoveTaskSignatureHasSignatureParam(self) -> None:
        """Verify that 'removeTask' declares a 'signature' parameter.

        Ensures callers identify the target task by signature string,
        consistent with how tasks are registered via command().

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(ISchedule.removeTask)
        self.assertIn("signature", sig.parameters)

    # ------------------------------------------------------------------ #
    #  Schedule conformance                                              #
    # ------------------------------------------------------------------ #

    def testScheduleIsSubclassOfISchedule(self) -> None:
        """Verify that Schedule is a subclass of ISchedule.

        Ensures the concrete class satisfies the abstract interface so it
        can be used anywhere ISchedule is expected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(Schedule, ISchedule))

    def testScheduleCanBeInstantiated(self) -> None:
        """Verify that Schedule can be instantiated without raising errors.

        Ensures the concrete class provides implementations for all abstract
        members declared by ISchedule.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        reactor = MagicMock()
        reactor.info = AsyncMock(return_value=[])
        reactor.call = AsyncMock(return_value=0)
        handler = MagicMock()
        schedule = Schedule(
            reactor=reactor,
            exception_handler=handler,
            stores=self._makeStores(),
        )
        self.assertIsInstance(schedule, Schedule)

    def testScheduleIsInstanceOfISchedule(self) -> None:
        """Verify that a Schedule instance passes isinstance(obj, ISchedule).

        Ensures polymorphic usage is valid so any code accepting an
        ISchedule can transparently receive a Schedule.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        reactor = MagicMock()
        reactor.info = AsyncMock(return_value=[])
        reactor.call = AsyncMock(return_value=0)
        handler = MagicMock()
        schedule = Schedule(
            reactor=reactor,
            exception_handler=handler,
            stores=self._makeStores(),
        )
        self.assertIsInstance(schedule, ISchedule)

    def testScheduleImplementsAllAbstractMethods(self) -> None:
        """Verify that Schedule provides a concrete implementation for every abstract.

        method declared in ISchedule.

        Ensures no method was accidentally left unimplemented in the concrete
        class so Python would not raise TypeError at instantiation time.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for name in ISchedule.__abstractmethods__:
            member = getattr(Schedule, name, None)
            self.assertIsNotNone(
                member,
                msg=f"Schedule is missing implementation for '{name}'",
            )
            is_concrete = (
                inspect.isfunction(member) or inspect.iscoroutinefunction(member)
            )
            self.assertTrue(
                is_concrete,
                msg=f"Schedule.{name} is not a concrete implementation",
            )
