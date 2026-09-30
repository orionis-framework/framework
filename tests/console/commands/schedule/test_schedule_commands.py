import asyncio
from io import StringIO
from unittest.mock import patch
from rich.console import Console
from orionis.console.commands.schedule.list import ScheduleListCommand
from orionis.console.commands.schedule.work import ScheduleWorkCommand
from orionis.console.contracts.schedule import ISchedule
from orionis.console.enums.events import SchedulerEvent
from orionis.database.exceptions import MissingDatabaseDependencyException
from orionis.test import TestCase

class _ScheduleService:
    """Provide schedule information and lifecycle operations for command tests."""

    __slots__ = (
        "bootError",
        "booted",
        "cancelFirstWait",
        "infoRows",
        "listeners",
        "shutdownCalls",
        "tasksRegistered",
        "waitCalls",
        "waitError",
    )

    def __init__(
        self,
        info_rows: list[dict[str, object]] | None = None,
        *,
        boot_error: Exception | None = None,
        cancel_first_wait: bool = False,
        wait_error: Exception | None = None,
    ) -> None:
        """Initialize the fake schedule service.

        Parameters
        ----------
        info_rows : list[dict[str, object]] | None, optional
            Task information returned by ``info``.
        boot_error : Exception | None, optional
            Error raised while starting the scheduler.
        cancel_first_wait : bool, optional
            Whether the first ``wait`` call raises cancellation.
        wait_error : Exception | None, optional
            Error raised by the first ``wait`` call, when provided.

        Returns
        -------
        None
            Initialize the test service state.
        """
        self.bootError = boot_error
        self.booted = False
        self.cancelFirstWait = cancel_first_wait
        self.infoRows = info_rows or []
        self.listeners: dict[SchedulerEvent, object] = {}
        self.shutdownCalls = 0
        self.tasksRegistered = False
        self.waitCalls = 0
        self.waitError = wait_error

    async def info(self) -> list[dict[str, object]]:
        """Return the configured task information.

        Returns
        -------
        list[dict[str, object]]
            Scheduled task rows used by the list command.
        """
        return self.infoRows

    def on(self, event: SchedulerEvent, listener: object) -> None:
        """Record a scheduler event listener.

        Parameters
        ----------
        event : SchedulerEvent
            Lifecycle event associated with the listener.
        listener : object
            Callback registered for the event.

        Returns
        -------
        None
            Store the event callback for assertions.
        """
        self.listeners[event] = listener

    async def boot(self) -> None:
        """Start the fake scheduler or raise its configured startup error.

        Returns
        -------
        None
            Update the boot state.
        """
        if self.bootError is not None:
            raise self.bootError
        self.booted = True

    async def wait(self) -> None:
        """Simulate waiting for shutdown or a worker failure.

        Returns
        -------
        None
            Finish the wait unless the configured first-call outcome is raised.

        Raises
        ------
        asyncio.CancelledError
            If cancellation is configured for the first wait.
        Exception
            If a first-call worker error is configured.
        """
        self.waitCalls += 1
        if self.waitCalls == 1 and self.cancelFirstWait:
            raise asyncio.CancelledError
        if self.waitCalls == 1 and self.waitError is not None:
            error = self.waitError
            self.waitError = None
            raise error

    def shutdown(self) -> None:
        """Record a graceful shutdown request.

        Returns
        -------
        None
            Increment the shutdown request count.
        """
        self.shutdownCalls += 1

class _Scheduler:
    """Expose the task registrar and one optional lifecycle callback."""

    __slots__ = ("tasksCalled",)

    def __init__(self) -> None:
        """Initialize scheduler call tracking.

        Returns
        -------
        None
            Create an uncalled scheduler fake.
        """
        self.tasksCalled = False

    async def tasks(self, schedule: _ScheduleService) -> None:
        """Record task registration with the schedule service.

        Parameters
        ----------
        schedule : _ScheduleService
            Service receiving the registered task declarations.

        Returns
        -------
        None
            Mark task registration on both test fakes.
        """
        self.tasksCalled = True
        schedule.tasksRegistered = True

    async def onStarted(self, event: object) -> None:
        """Provide a scheduler start callback for listener registration.

        Parameters
        ----------
        event : object
            Scheduler start event supplied by the scheduler service.

        Returns
        -------
        None
            This callback has no test-side effect.
        """

class _Application:
    """Provide scheduler services required by the commands under test."""

    __slots__ = ("debug", "madeType", "schedule", "scheduler")

    def __init__(
        self,
        scheduler: object,
        schedule: _ScheduleService,
        *,
        debug: bool = False,
    ) -> None:
        """Store scheduler dependencies and application mode.

        Parameters
        ----------
        scheduler : object
            Scheduler instance returned by ``getScheduler``.
        schedule : _ScheduleService
            Schedule service returned by ``make``.
        debug : bool, optional
            Whether debug-only startup output is enabled.

        Returns
        -------
        None
            Store the configured command dependencies.
        """
        self.debug = debug
        self.madeType: type | None = None
        self.schedule = schedule
        self.scheduler = scheduler

    async def getScheduler(self) -> object:
        """Return the configured scheduler instance.

        Returns
        -------
        object
            Scheduler used to register application tasks.
        """
        return self.scheduler

    async def make(self, service_type: type) -> _ScheduleService:
        """Return the schedule service requested by a command.

        Parameters
        ----------
        service_type : type
            Service contract requested by the command.

        Returns
        -------
        _ScheduleService
            Configured fake schedule service.
        """
        self.madeType = service_type
        return self.schedule

    async def call(
        self,
        instance: object,
        method_name: str,
        **kwargs: object,
    ) -> object:
        """Invoke a scheduler method with the application's call arguments.

        Parameters
        ----------
        instance : object
            Target object that owns the method.
        method_name : str
            Name of the method to invoke.
        **kwargs : object
            Keyword arguments passed to the target method.

        Returns
        -------
        object
            Result returned by the scheduler method.
        """
        method = getattr(instance, method_name)
        return await method(**kwargs)

    def isDebug(self) -> bool:
        """Return whether the application is running in debug mode.

        Returns
        -------
        bool
            Configured debug mode.
        """
        return self.debug

class _SchedulerWithoutTasks:
    """Represent an invalid scheduler with no task registration method."""

class TestScheduleListCommand(TestCase):
    """Verify schedule:list output for empty and configured task sets."""

    async def testScheduleListDisplaysEmptyState(self) -> None:
        """Render a clear message when no scheduled tasks are registered.

        Returns
        -------
        None
            Assertions verify registration and empty-state output.
        """
        scheduler = _Scheduler()
        schedule = _ScheduleService()
        application = _Application(scheduler, schedule)
        output = StringIO()
        console = Console(file=output, width=160, color_system=None)

        await ScheduleListCommand().handle(application, console)

        self.assertTrue(scheduler.tasksCalled)
        self.assertTrue(schedule.tasksRegistered)
        self.assertIn("No scheduled tasks found.", output.getvalue())

    async def testScheduleListDisplaysArgumentsAndFullTaskDetails(self) -> None:
        """Show keyword arguments, full purpose, and missing values clearly.

        Returns
        -------
        None
            Assertions verify schedule columns and untruncated task details.
        """
        purpose = "Send the complete daily billing summary to customers"
        schedule = _ScheduleService([
            {
                "signature": "billing:send",
                "args": ["--region", "west"],
                "kwargs": {"limit": 20, "locale": "es"},
                "purpose": purpose,
                "random_delay": None,
                "coalesce": False,
                "max_instances": 3,
                "misfire_grace_time": None,
                "start_date": None,
                "end_date": "2030-01-01 00:00:00",
                "details": "Every day at 08:30",
            },
        ])
        application = _Application(_Scheduler(), schedule)
        output = StringIO()
        console = Console(file=output, width=220, color_system=None)

        await ScheduleListCommand().handle(application, console)

        rendered = output.getvalue()
        self.assertIn("Keyword Arguments", rendered)
        self.assertIn("billing:send", rendered)
        self.assertIn("limit", rendered)
        self.assertIn("billing summary to", rendered)
        self.assertIn("customers", rendered)
        self.assertIn("False", rendered)
        self.assertIn("Every day at 08:30", rendered)
        self.assertIn("-", rendered)

class TestScheduleWorkCommand(TestCase):
    """Verify schedule:work registration and graceful shutdown behavior."""

    async def testScheduleWorkReportsMissingDatabaseDriver(self) -> None:
        """Report a missing scheduler driver without starting the worker.

        Returns
        -------
        None
            Assertions verify the exit code and installation guidance.
        """
        error = MissingDatabaseDependencyException(
            "The 'pgsql' connection requires 'psycopg2'. "
            "Install it with: pip install orionis[pgsql]",
        )
        schedule = _ScheduleService(boot_error=error)
        application = _Application(_Scheduler(), schedule)
        output = StringIO()
        console = Console(file=output, width=160, color_system=None)

        result = await ScheduleWorkCommand().handle(application, console)

        self.assertEqual(result, 1)
        self.assertIn("Scheduler backend error:", output.getvalue())
        self.assertIn("orionis[pgsql]", output.getvalue())
        self.assertFalse(schedule.booted)
        self.assertEqual(schedule.shutdownCalls, 0)
        self.assertEqual(schedule.waitCalls, 0)

    async def testScheduleWorkReportsBackendErrorsAfterStartup(self) -> None:
        """Stop the scheduler and report an operational worker failure.

        Returns
        -------
        None
            Assertions verify cleanup and a failing exit code.
        """
        schedule = _ScheduleService(wait_error=ConnectionRefusedError("offline"))
        application = _Application(_Scheduler(), schedule)
        output = StringIO()
        console = Console(file=output, width=160, color_system=None)

        result = await ScheduleWorkCommand().handle(application, console)

        self.assertEqual(result, 1)
        self.assertIn("Scheduler backend error: offline", output.getvalue())
        self.assertEqual(schedule.shutdownCalls, 1)
        self.assertEqual(schedule.waitCalls, 2)

    async def testScheduleWorkPropagatesUnexpectedStartupErrors(self) -> None:
        """Expose unexpected startup errors to the application's handler.

        Returns
        -------
        None
            Assertions verify that unexpected errors are not converted to output.
        """
        schedule = _ScheduleService(boot_error=RuntimeError("invalid scheduler"))
        application = _Application(_Scheduler(), schedule)
        output = StringIO()
        console = Console(file=output, width=160, color_system=None)

        with self.assertRaisesRegex(RuntimeError, "invalid scheduler"):
            await ScheduleWorkCommand().handle(application, console)

        self.assertEqual(output.getvalue(), "")
        self.assertEqual(schedule.shutdownCalls, 0)

    async def testScheduleWorkRegistersTasksAndOptionalListeners(self) -> None:
        """Register declared tasks and callbacks before waiting for shutdown.

        Returns
        -------
        None
            Assertions verify task registration, listeners, boot, and output.
        """
        scheduler = _Scheduler()
        schedule = _ScheduleService()
        application = _Application(scheduler, schedule, debug=True)
        command = ScheduleWorkCommand()
        console = Console(file=StringIO(), width=160, color_system=None)

        with patch.object(
            command,
            "_ScheduleWorkCommand__startPanel",
        ) as start_panel:
            await command.handle(application, console)

        self.assertIs(application.madeType, ISchedule)
        self.assertTrue(scheduler.tasksCalled)
        self.assertTrue(schedule.tasksRegistered)
        self.assertIn(SchedulerEvent.STARTED, schedule.listeners)
        self.assertTrue(schedule.booted)
        self.assertEqual(schedule.waitCalls, 1)
        self.assertEqual(schedule.shutdownCalls, 0)
        start_panel.assert_called_once_with(console)

    async def testScheduleWorkRejectsSchedulersWithoutTaskRegistration(self) -> None:
        """Raise an actionable error when the scheduler has no tasks method.

        Returns
        -------
        None
            Assertions verify invalid schedulers fail before service resolution.
        """
        schedule = _ScheduleService()
        application = _Application(_SchedulerWithoutTasks(), schedule)
        command = ScheduleWorkCommand()
        console = Console(file=StringIO(), color_system=None)

        with self.assertRaisesRegex(TypeError, "callable 'tasks"):
            await command.handle(application, console)

        self.assertIsNone(application.madeType)

    async def testScheduleWorkShutsDownAfterCancellation(self) -> None:
        """Finish graceful scheduler shutdown after worker cancellation.

        Returns
        -------
        None
            Assertions verify shutdown and a second wait for completion.
        """
        schedule = _ScheduleService(cancel_first_wait=True)
        application = _Application(_Scheduler(), schedule)
        command = ScheduleWorkCommand()
        console = Console(file=StringIO(), color_system=None)

        await command.handle(application, console)

        self.assertEqual(schedule.shutdownCalls, 1)
        self.assertEqual(schedule.waitCalls, 2)

    async def testScheduleWorkShutsDownAndReraisesWorkerErrors(self) -> None:
        """Shut down the scheduler before propagating worker failures.

        Returns
        -------
        None
            Assertions verify cleanup occurs and the original error propagates.
        """
        error = RuntimeError("scheduler wait failed")
        schedule = _ScheduleService(wait_error=error)
        application = _Application(_Scheduler(), schedule)
        command = ScheduleWorkCommand()
        console = Console(file=StringIO(), color_system=None)

        with self.assertRaisesRegex(RuntimeError, "scheduler wait failed"):
            await command.handle(application, console)

        self.assertEqual(schedule.shutdownCalls, 1)
        self.assertEqual(schedule.waitCalls, 2)
