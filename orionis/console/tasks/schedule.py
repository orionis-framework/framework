"""Register scheduled tasks and coordinate their scheduler integration."""

import asyncio
import functools
import inspect
import logging
from contextlib import suppress
from typing import TYPE_CHECKING, Self
from orionis.console.contracts.schedule import ISchedule
from orionis.console.contracts.store import IScheduleStore
from orionis.console.core.contracts.reactor import IReactor
from orionis.console.entities.scheduler_event import (
    SchedulerEvent as SchedulerEventEntity,
)
from orionis.console.entities.task_event import TaskEvent as TaskEventEntity
from orionis.console.enums.events import SchedulerEvent, TaskEvent
from orionis.console.enums.states import ScheduleStates
from orionis.console.fluent.contracts.task import ITask
from orionis.failure.contracts.catch import ICatch
from orionis.failure.runtime import capture, capture_nowait, get_runtime, operation
from orionis.support.facades.datetime import DateTime
from orionis.support.facades.logger import Log
from orionis.support.facades.reactor import Reactor

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from apscheduler.events import JobEvent as APJobEvent
    from apscheduler.events import SchedulerEvent as APSchedulerEvent
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from orionis.console.entities.task import Task as TaskEntity
    from orionis.foundation.config.scheduler.entities.scheduler import (
        Scheduler as ConfigScheduler,
    )

async def _execute_scheduled_command(
    signature: str,
    args: list[str] | None = None,
) -> int:
    """
    Execute a scheduled command through the Reactor facade.

    Parameters
    ----------
    signature : str
        Registered command signature to execute.
    args : list[str] or None, optional
        Command-line tokens; use an empty list when ``None``.

    Returns
    -------
    int
        Exit code returned by the command dispatcher.

    Notes
    -----
    Use a module-level callable so persistent job stores can serialize its
    import path without pickling the scheduler or application dependencies.
    """
    return await Reactor.call(signature, args or [])

# Preserve the callable path stored by earlier persistent scheduler entries.
globals()["_executeScheduledCommand"] = _execute_scheduled_command

class Schedule(ISchedule):
    # ruff: noqa: BLE001, PLC0415, TC001
    """Register scheduled tasks and coordinate their scheduler integration."""

    _SCHEDULER_NOT_STARTED_ERROR = "The Orionis task scheduler has not been started."
    """
    Error text for scheduler not started error: ``The Orionis task scheduler has not
    been started.``.
    """

    def __init__(
        self: Self,
        reactor: IReactor,
        exception_handler: ICatch,
        stores: IScheduleStore,
    ) -> None:
        """
        Initialize scheduler dependencies, task registries, and shutdown state.

        Parameters
        ----------
        reactor : orionis.console.core.contracts.reactor.IReactor
            Command dispatcher used to discover available signatures.
        exception_handler : orionis.failure.contracts.catch.ICatch
            Fallback handler for event-listener failures.
        stores : orionis.console.contracts.store.IScheduleStore
            Job-store factory providing the scheduler configuration.

        Returns
        -------
        None
            Store dependencies and prepare a stopped scheduler.
        """
        self.__reactor: IReactor = reactor
        """Reactor instance for command execution."""
        self.__exception_handler: ICatch = exception_handler
        """Exception handler for managing errors."""
        self.__stores: IScheduleStore = stores
        """Schedule store for managing job stores."""
        self.__config: ConfigScheduler = stores.config
        """Validated configuration used to construct and operate the service."""
        self.__available_command_signatures: set[str] = set()
        """Available command signatures produced by ``set``."""
        self.__job_store: str = self.__config.store
        """Job store obtained from ``self.__config.store``."""
        self.__scheduler: AsyncIOScheduler | None = None
        """Scheduler instance responsible for registering and running tasks."""
        self.__scheduler_listeners: dict[SchedulerEvent, Callable] = {}
        """Callbacks subscribed to scheduler lifecycle events."""
        self.__tasks_listeners: dict[str, dict[TaskEvent, Callable]] = {}
        """Callbacks subscribed to scheduled-task events."""
        self.__fluent_tasks: dict[str, ITask] = {}
        """Task declarations awaiting conversion to scheduler jobs."""
        self.__tasks: dict[str, TaskEntity] = {}
        """Tasks registered for scheduling or lifecycle management."""
        self.__state: ScheduleStates = ScheduleStates.STOPPED
        """State selected by the maintenance-mode command."""
        self.__running_tasks: set[str] = set()
        """Running tasks produced by ``set``."""
        self.__paused_tasks: set[str] = set()
        """Paused tasks produced by ``set``."""
        self.__removed_tasks: set[str] = set()
        """Removed tasks produced by ``set``."""
        self.__pending_listener_tasks: set[asyncio.Task] = set()
        """Pending listener tasks produced by ``set``."""
        self.__shutdown_event = asyncio.Event()
        """Notify callers when scheduler shutdown settles."""
        self.__shutdown_error: BaseException | None = None
        """Failure retained for the caller awaiting shutdown completion."""
        self.__shutdown_task: asyncio.Task | None = None
        """Single shutdown operation owned by the current scheduler cycle."""
        self.__failure_runtime = None
        """Application runtime retained for callbacks outside the starting context."""
        self.__wait_to_shutdown: float = 0.5
        """Wait to shutdown value used by ``Schedule``."""

    async def __loadAvailableCommands(self: Self) -> None:
        """
        Cache command signatures exposed by the reactor.

        Skip discovery when the signature cache is already populated.

        Returns
        -------
        None
            Update the internal set of available command signatures.
        """
        # Return early if command signatures are already cached
        if self.__available_command_signatures:
            return

        # Query the reactor for available commands and cache their signatures
        commands: list[dict] = await self.__reactor.info()
        self.__available_command_signatures.update(
            job.get("signature") for job in commands
        )

    def __suppressApschedulerLogging(self: Self) -> None:
        """
        Disable APScheduler loggers and their message propagation.

        Returns
        -------
        None
            Set scheduler component loggers to ``CRITICAL`` and disable them.
        """
        for logger_name in (
            "apscheduler",
            "apscheduler.executors",
            "apscheduler.scheduler",
        ):
            apscheduler_logger = logging.getLogger(logger_name)
            apscheduler_logger.setLevel(logging.CRITICAL)
            apscheduler_logger.disabled = True
            apscheduler_logger.propagate = False

    async def __validateAndLoadFluentTasks(self: Self) -> None:
        """
        Validate fluent task signatures and build their task entities.

        Returns
        -------
        None
            Populate the task registry using configured scheduling defaults.

        Raises
        ------
        ValueError
            If a task signature is unavailable in the reactor.
        """
        # Read defaults shared by every fluent task.
        available = self.__available_command_signatures
        tasks = self.__tasks
        default_random_delay = self.__config.jitter
        default_max_instances = self.__config.max_instances
        default_misfire_grace_time = self.__config.misfire_grace_time
        default_coalesce = self.__config.coalesce

        # Validate and load each fluent task
        for signature, task in self.__fluent_tasks.items():
            if signature not in available:
                error_msg = (
                    f"Task signature '{signature}' is not available in the reactor."
                )
                raise ValueError(error_msg)
            tasks[signature] = task.entity(
                random_delay=default_random_delay,
                max_instances=default_max_instances,
                misfire_grace_time=default_misfire_grace_time,
                coalesce=default_coalesce,
            )

    async def info(self: Self) -> list[dict]:
        """
        Return scheduling metadata for all validated tasks.

        Returns
        -------
        list[dict]
            Task metadata with ``start_date`` and ``end_date`` formatted as
            ``YYYY-MM-DD HH:MM:SS``, or ``None`` when unset.

        Raises
        ------
        ValueError
            If a task signature is unavailable in the reactor.
        """
        # Ensure available command signatures are loaded before validating tasks
        await self.__loadAvailableCommands()

        # Validate that all fluent tasks have valid signatures and load their entities
        await self.__validateAndLoadFluentTasks()

        return [
            {
                "signature": signature,
                "args": task.args,
                "kwargs": task.kwargs,
                "purpose": task.purpose,
                "random_delay": task.random_delay,
                "coalesce": task.coalesce,
                "max_instances": task.max_instances,
                "misfire_grace_time": task.misfire_grace_time,
                "start_date": (
                    task.start_date.strftime("%Y-%m-%d %H:%M:%S")
                    if task.start_date
                    else None
                ),
                "end_date": (
                    task.end_date.strftime("%Y-%m-%d %H:%M:%S")
                    if task.end_date
                    else None
                ),
                "details": task.details,
            }
            for signature, task in self.__tasks.items()
        ]

    def _dispatchSchedulerEventListener(
        self: Self,
        event: APSchedulerEvent,
    ) -> None:
        """
        Dispatch a scheduler event to its registered listener.

        Parameters
        ----------
        event : ``apscheduler.events.SchedulerEvent``
            Lifecycle event to wrap for the listener.

        Returns
        -------
        None
            Invoke a synchronous listener or supervise an asynchronous listener,
            reporting failures. Do nothing when no listener is registered.
        """
        # Select the listener registered for this event code.
        code = event.code
        listener = self.__scheduler_listeners.get(code)
        if listener is None:
            return

        # Wrap the event in a SchedulerEventEntity for listener consumption
        event_entity = SchedulerEventEntity(
            code=code,
            jobstore=getattr(event, "alias", None),
        )

        # Handle synchronous listeners directly
        if not inspect.iscoroutinefunction(listener):
            try:
                listener(event_entity)
            except Exception as e:
                self.__createManagedTask(self.__handleListenerException(e))
            return

        # Handle asynchronous listeners using an async wrapper
        async def _async_listener_wrapper() -> None:
            """
            Invoke the asynchronous scheduler listener and report failures.

            Returns
            -------
            None
                Await the listener and route exceptions through error handling.
            """
            try:
                await listener(event_entity)
            except Exception as e:
                await self.__handleListenerException(e)

        # Schedule the async listener wrapper as a managed task
        self.__createManagedTask(_async_listener_wrapper())

    def _dispatchTaskEventListener(
        self: Self,
        event: APJobEvent,
    ) -> None:
        """
        Observe task failures and dispatch the matching event listener.

        Parameters
        ----------
        event : ``apscheduler.events.JobEvent``
            Job event containing a task signature and execution metadata.

        Returns
        -------
        None
            Update removal bookkeeping, report execution failures, and invoke
            the registered listener when present.
        """
        # Read the job signature from the event.
        signature = getattr(event, "job_id", None)
        if not signature:
            return

        # Infrastructure failures must be observed even without user listeners.
        error = getattr(event, "exception", None)
        if isinstance(error, BaseException):
            self.__createManagedTask(self.__handleTaskException(error, signature))

        # Keep internal bookkeeping in sync with jobs that APScheduler itself
        # removes (e.g. a one-shot DateTrigger job that already fired, or a
        # job whose end_date was reached) and not only with removals made
        # through removeTask()/removeAllTasks(). Without this, __running_tasks
        # keeps a permanently stale signature after the job is gone.
        if event.code == TaskEvent.REMOVED:
            self.__running_tasks.discard(signature)
            self.__paused_tasks.discard(signature)
            self.__removed_tasks.add(signature)

        # Retrieve listeners for this specific task signature
        listener_for_signature = self.__tasks_listeners.get(signature)
        if listener_for_signature is None:
            return

        # Select the listener registered for this event code.
        code = event.code
        listener = listener_for_signature.get(code)
        if listener is None:
            return

        # Wrap the event in a TaskEventEntity for listener consumption
        event_entity = TaskEventEntity(
            code=code,
            signature=signature,
            jobstore=getattr(event, "jobstore", self.__job_store),
            scheduled_run_times=getattr(event, "scheduled_run_times", None),
            scheduled_run_time=getattr(event, "scheduled_run_time", None),
            retval=getattr(event, "retval", None),
            exception=getattr(event, "exception", None),
            traceback=getattr(event, "traceback", None),
        )

        # Handle synchronous listeners directly
        if not inspect.iscoroutinefunction(listener):
            try:
                listener(event_entity)
            except Exception as e:
                self.__createManagedTask(self.__handleListenerException(e))
            return

        # Handle asynchronous listeners using an async wrapper
        async def _async_listener_wrapper() -> None:
            """
            Invoke the asynchronous task listener and report failures.

            Returns
            -------
            None
                Await the listener and route exceptions through error handling.
            """
            try:
                await listener(event_entity)
            except Exception as e:
                await self.__handleListenerException(e)

        # Schedule the async listener wrapper as a managed task
        self.__createManagedTask(_async_listener_wrapper())

    def __createManagedTask(
        self: Self,
        coroutine: Coroutine,
    ) -> asyncio.Task:
        """
        Create a supervised asyncio task and retain it until completion.

        Parameters
        ----------
        coroutine : collections.abc.Coroutine
            Coroutine to execute and close if its supervisor never starts.

        Returns
        -------
        asyncio.Task
            Task supervised for failures and removed from the pending set when
            complete.
        """
        started = False

        async def supervise() -> None:
            """
            Run the managed coroutine within a scheduler failure context.

            Returns
            -------
            None
                Await the coroutine and report ordinary execution errors.

            Raises
            ------
            asyncio.CancelledError
                If execution is cancelled.
            """
            nonlocal started
            started = True
            with operation(runtime=self.__failure_runtime, flow="scheduler"):
                try:
                    await coroutine
                except Exception as error:
                    await self.__handleListenerException(error, legacy=False)

        def completed(task: asyncio.Task) -> None:
            """
            Release the managed task and collect supervisor failures.

            Parameters
            ----------
            task : asyncio.Task
                Completed supervisor task whose outcome must be collected.

            Returns
            -------
            None
                Remove the task from the pending set, close an unstarted
                coroutine, and report any exceptional supervisor exit.
            """
            pending.discard(task)
            if not started:
                coroutine.close()
            if not task.cancelled():
                error = task.exception()
                if error is not None:
                    capture_nowait(
                        error,
                        runtime=self.__failure_runtime,
                        flow="scheduler",
                        phase="supervisor",
                    )

        pending = self.__pending_listener_tasks
        task = asyncio.create_task(supervise())
        pending.add(task)
        task.add_done_callback(completed)
        return task

    async def __handleTaskException(
        self: Self, exception: BaseException, signature: str,
    ) -> None:
        """
        Report a task execution failure independently of event listeners.

        Parameters
        ----------
        exception : BaseException
            Execution error reported by the scheduler.
        signature : str
            Command signature associated with the failed job.

        Returns
        -------
        None
            Capture the error and use fallback reporting for ordinary exceptions
            when runtime reporting is unavailable.
        """
        runtime = self.__failure_runtime or get_runtime()
        app = runtime.app if runtime is not None else None
        with operation(app, flow="scheduler", operation=signature, isolated=True):
            receipt = await capture(
                exception,
                runtime=runtime,
                flow="scheduler",
                phase="job",
                operation=signature,
            )
            if receipt is None and isinstance(exception, Exception):
                await self.__handleListenerException(exception, legacy=False)

    async def __handleListenerException(
        self: Self,
        exception: Exception,
        *,
        legacy: bool = True,
    ) -> None:
        """
        Report a scheduler failure through runtime or legacy handling.

        Parameters
        ----------
        exception : Exception
            Exception raised by a scheduled operation or event listener.
        legacy : bool, default True
            Allow the configured exception handler as a fallback; log instead
            when ``False``.

        Returns
        -------
        None
            Capture the failure or apply the selected fallback reporting path.
        """
        with operation(runtime=self.__failure_runtime, flow="scheduler", isolated=True):
            receipt = await capture(
                exception,
                runtime=self.__failure_runtime,
                flow="scheduler",
                phase="listener",
            )
        if receipt is not None:
            return
        if not legacy:
            # New observers never resolve the app handler before activation.
            with suppress(Exception):
                Log.error(f"Scheduler operation failed: {exception}")
            return
        try:
            await self.__exception_handler.exception(exception)
        except Exception as handler_error:
            # Legacy logging cannot interrupt listener cleanup or recurse.
            with suppress(Exception):
                Log.error(f"Error in exception handler: {handler_error}")

    def __controlFailure(self, message: str, action: str) -> RuntimeError:
        """
        Report a scheduler control failure and return its error.

        Parameters
        ----------
        message : str
            Message describing the failed scheduler operation.
        action : str
            Control-method name attached to the failure report.

        Returns
        -------
        RuntimeError
            New error carrying the supplied message.
        """
        error = RuntimeError(message)
        receipt = capture_nowait(
            error,
            runtime=self.__failure_runtime,
            flow="scheduler",
            phase="control",
            operation=action,
        )
        if receipt is None:
            with suppress(Exception):
                Log.error(message)
        return error

    def __addConfiguredJobStore(self: Self) -> None:
        """
        Register the configured database or Redis job store.

        Leave the in-memory store unchanged when no persistent driver is selected.

        Returns
        -------
        None
            Add the selected persistent store to the scheduler.

        Raises
        ------
        RuntimeError
            If persistent-store configuration is missing or its backend is
            unsupported.
        """
        if self.__stores.store == "database":
            self.__scheduler.add_jobstore(
                jobstore=self.__stores.database(),
                alias="database",
            )

        if self.__stores.store == "redis":
            redis_store = self.__stores.redis()
            self.__scheduler.add_jobstore(
                jobstore=redis_store,
                alias="redis",
            )

    async def boot(self: Self) -> None:
        """
        Initialize and start the scheduler with configured tasks and listeners.

        Returns
        -------
        None
            Register job stores, jobs, and event dispatchers, then start scheduling.

        Raises
        ------
        ValueError
            If a task signature is unavailable in the reactor.
        RuntimeError
            If a selected job store lacks required configuration or a supported
            backend.
        """
        self.__failure_runtime = get_runtime()
        self.__shutdown_error = None
        self.__shutdown_task = None
        self.__shutdown_event.clear()
        # Load available command signatures from the CLI reactor
        await self.__loadAvailableCommands()

        # Validate and load task entities to be registered
        await self.__validateAndLoadFluentTasks()

        # Get the current asyncio event loop for scheduling async tasks
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        loop = asyncio.get_running_loop()
        self.__scheduler = AsyncIOScheduler(
            event_loop=loop,
            timezone=DateTime.getZoneInfo(),
        )

        # Add an in-memory jobstore for scheduled tasks
        self.__scheduler.add_jobstore(
            jobstore="memory",
            alias="memory",
        )

        # Add the database/redis jobstore matching the configured driver, if
        # any. Extracted to keep boot()'s cognitive complexity in check.
        self.__addConfiguredJobStore()

        # Register a global event listener to dispatch scheduler events
        self.__scheduler.add_listener(
            self._dispatchSchedulerEventListener,
            (
                SchedulerEvent.STARTED
                | SchedulerEvent.SHUTDOWN
                | SchedulerEvent.PAUSED
                | SchedulerEvent.RESUMED
            ),
        )

        # Register a global event listener to dispatch task events for all jobs
        self.__scheduler.add_listener(
            self._dispatchTaskEventListener,
            (
                TaskEvent.ADDED
                | TaskEvent.REMOVED
                | TaskEvent.MODIFIED
                | TaskEvent.EXECUTED
                | TaskEvent.ERROR
                | TaskEvent.MISSED
                | TaskEvent.SUBMITTED
                | TaskEvent.MAX_INSTANCES
            ),
        )

        # Read dependencies shared by every scheduled job.
        scheduler = self.__scheduler
        tasks_listeners = self.__tasks_listeners
        running_tasks = self.__running_tasks
        reactor_call = _execute_scheduled_command

        # Register all jobs from the loaded task entities
        for task_entity in self.__tasks.values():
            sig = task_entity.signature

            # Register task-specific event listeners if any are defined.
            # Multiple .on()/.registerListener() calls for the same event on
            # the same task would otherwise silently overwrite one another
            # (dict assignment keeps only the last registration); warn so the
            # collision is visible instead of a silent behavior change.
            if task_entity.listeners:
                listener_map = tasks_listeners.setdefault(sig, {})
                for event_code, func in task_entity.listeners:
                    if event_code in listener_map:
                        Log.warning(
                            f"Task '{sig}' already has a listener registered "
                            f"for event '{event_code.name}'; the previous "
                            "listener is being replaced.",
                        )
                    listener_map[event_code] = func

            # Add the job to the scheduler with all configured parameters.
            # `replace_existing` comes from config (scheduler.replace_existing,
            # defaults to True) and reconciles the declarative task list with
            # a persistent job store (e.g. "database"/"redis"), where a job
            # with the same id may already exist from a previous run and
            # would otherwise raise ConflictingIdError. Because the scheduler
            # has not been started yet (see below), APScheduler only queues
            # these calls internally; nothing actually hits the jobstore or
            # starts firing until start() runs.
            scheduler.add_job(
                reactor_call,
                trigger=task_entity.trigger,
                args=[sig, task_entity.args],
                id=sig,
                name=task_entity.purpose,
                max_instances=task_entity.max_instances,
                coalesce=task_entity.coalesce,
                misfire_grace_time=task_entity.misfire_grace_time,
                start_date=task_entity.start_date,
                end_date=task_entity.end_date,
                jobstore=self.__job_store,
                replace_existing=self.__config.replace_existing,
            )
            running_tasks.add(sig)

        # Suppress internal APScheduler logging to avoid duplicate logs
        self.__suppressApschedulerLogging()

        # Start the scheduler only after every job has been successfully
        # registered. Starting it earlier (before this loop) meant that, if
        # add_job() raised for one job (e.g. ConflictingIdError against a
        # persistent jobstore), jobs added earlier in the same iteration were
        # already firing; the unhandled exception then tore down the whole
        # command/event loop and abruptly cancelled those in-flight runs.
        # APScheduler defers add_job() calls made before start() internally,
        # so no job store I/O or execution happens until start() runs below.
        self.__state = ScheduleStates.RUNNING
        self.__scheduler.start()

    def on(
        self: Self,
        event: SchedulerEvent,
        listener: Callable,
    ) -> Self:
        """
        Register or replace a listener for a scheduler lifecycle event.

        Parameters
        ----------
        event : orionis.console.enums.events.SchedulerEvent
            Scheduler lifecycle event to observe.
        listener : collections.abc.Callable
            Synchronous or asynchronous callback receiving a scheduler event entity.

        Returns
        -------
        typing.Self
            This scheduler for chained configuration.

        Raises
        ------
        RuntimeError
            If the scheduler is not stopped.
        TypeError
            If ``event`` is not a scheduler event or ``listener`` is not callable.
        """
        # Prevent listener registration after scheduler boot
        if not self.isStopped():
            error_msg = (
                "The scheduler has already been booted, cannot register new listeners."
            )
            raise RuntimeError(error_msg)

        # Validate event type
        if not isinstance(event, SchedulerEvent):
            error_msg = "The event must be an instance of SchedulerEvent."
            raise TypeError(error_msg)

        # Validate listener is callable
        if not callable(listener):
            error_msg = "The listener must be a callable."
            raise TypeError(error_msg)

        # Register the event-listener pair for later subscription
        self.__scheduler_listeners[event] = listener
        return self

    def state(self: Self) -> str:
        """
        Return the current scheduler state value.

        Returns
        -------
        str
            ``RUNNING``, ``PAUSED``, or ``STOPPED``.
        """
        # Return the value of the internal state enum
        return self.__state.value

    def isRunning(self: Self) -> bool:
        """
        Check whether the scheduler is running.

        Returns
        -------
        bool
            ``True`` when the scheduler state is ``RUNNING``, otherwise ``False``.
        """
        # Check if the internal state is RUNNING
        return self.__state == ScheduleStates.RUNNING

    def isPaused(self: Self) -> bool:
        """
        Check whether the scheduler is paused.

        Returns
        -------
        bool
            ``True`` when the scheduler state is ``PAUSED``, otherwise ``False``.
        """
        # Check if the internal state is PAUSED
        return self.__state == ScheduleStates.PAUSED

    def isStopped(self: Self) -> bool:
        """
        Check whether the scheduler is stopped.

        Returns
        -------
        bool
            ``True`` when the scheduler state is ``STOPPED``, otherwise ``False``.
        """
        # Check if the internal state is STOPPED
        return self.__state == ScheduleStates.STOPPED

    def command(
        self: Self,
        signature: str,
        args: list[str] | None = None,
        purpose: str | None = None,
    ) -> ITask:
        """
        Declare a command for fluent scheduling configuration.

        Replace any existing fluent declaration with the same signature.

        Parameters
        ----------
        signature : str
            Non-empty command signature to schedule.
        args : list[str] or None, optional
            Command-line tokens; use an empty list when ``None``.
        purpose : str or None, optional
            Human-readable description of the scheduled command.

        Returns
        -------
        orionis.console.fluent.contracts.task.ITask
            Fluent task definition for configuring timing and listeners.

        Raises
        ------
        RuntimeError
            If the scheduler is not stopped.
        TypeError
            If the signature is blank or not a string, or arguments are not
            a list of strings or ``None``.
        """
        # Prevent adding new commands after the scheduler has started
        if not self.isStopped():
            error_msg = (
                "The Orionis task scheduler has already been started; "
                "new commands cannot be added."
            )
            raise RuntimeError(error_msg)

        # Validate that the command signature is a non-empty string
        if not isinstance(signature, str) or not signature.strip():
            error_msg = "The command signature must be a non-empty string."
            raise TypeError(error_msg)

        # Ensure arguments are a list of strings or None
        if args is not None:
            if not isinstance(args, list):
                error_msg = "Arguments must be provided as a list of strings or None."
                raise TypeError(error_msg)
            for arg in args:
                if not isinstance(arg, str):
                    error_msg = "Each argument must be a string."
                    raise TypeError(error_msg)

        # Store the Task instance for fluent configuration. `purpose` must be
        # passed by keyword: Task.__init__ signature is
        # (signature, args, kwargs=None, purpose=None) — passing `purpose`
        # positionally silently binds it to `kwargs` instead, corrupting the
        # kwargs field and always dropping the task's purpose.
        from orionis.console.fluent import Task

        self.__fluent_tasks[signature] = Task(
            signature,
            args or [],
            purpose=purpose,
        )
        return self.__fluent_tasks[signature]

    def pauseTask(
        self: Self,
        signature: str,
    ) -> bool:
        """
        Pause a running task by its signature.

        Parameters
        ----------
        signature : str
            Signature of the running task to pause.

        Returns
        -------
        bool
            ``True`` after pausing the job and updating task bookkeeping.

        Raises
        ------
        RuntimeError
            If the scheduler is uninitialized, the task is not running, or the
            pause operation fails.
        ValueError
            If the scheduler cannot find the tracked job.
        """
        # Ensure the scheduler is initialized before pausing a task
        scheduler = self.__scheduler
        if not scheduler:
            error_msg = self._SCHEDULER_NOT_STARTED_ERROR
            raise RuntimeError(error_msg)

        # Check if the task is currently running
        running_tasks = self.__running_tasks
        if signature not in running_tasks:
            error_msg = (
                f"Task '{signature}' is not currently running and cannot be paused."
            )
            raise RuntimeError(error_msg)

        # Retrieve the job from the scheduler and pause it
        job = scheduler.get_job(signature)
        if job is None:
            error_msg = f"Task '{signature}' does not exist."
            raise ValueError(error_msg)

        # Pause the job and update internal state
        try:
            scheduler.pause_job(signature)
            running_tasks.discard(signature)
            self.__paused_tasks.add(signature)
            Log.info(f"Task '{signature}' paused.")
            return True
        except Exception as e:
            error_msg = f"Failed to pause task '{signature}': {e!s}"
            raise self.__controlFailure(error_msg, "pauseTask") from e

    def resumeTask(
        self: Self,
        signature: str,
    ) -> bool:
        """
        Resume a paused task by its signature.

        Parameters
        ----------
        signature : str
            Signature of the paused task to resume.

        Returns
        -------
        bool
            ``True`` after resuming the job and updating task bookkeeping.

        Raises
        ------
        RuntimeError
            If the scheduler is uninitialized, the task is not paused, or the
            resume operation fails.
        ValueError
            If the scheduler cannot find the tracked job.
        """
        # Ensure the scheduler is initialized before resuming a task
        scheduler = self.__scheduler
        if not scheduler:
            error_msg = self._SCHEDULER_NOT_STARTED_ERROR
            raise RuntimeError(error_msg)

        # Check if the task is currently paused
        paused_tasks = self.__paused_tasks
        if signature not in paused_tasks:
            error_msg = (
                f"Task '{signature}' is not currently paused and cannot be resumed."
            )
            raise RuntimeError(error_msg)

        # Retrieve the job from the scheduler and resume it
        job = scheduler.get_job(signature)
        if job is None:
            error_msg = f"Task '{signature}' does not exist."
            raise ValueError(error_msg)

        # Resume the job and update internal state
        try:
            scheduler.resume_job(signature)
            paused_tasks.discard(signature)
            self.__running_tasks.add(signature)
            Log.info(f"Task '{signature}' resumed.")
            return True
        except Exception as e:
            error_msg = f"Failed to resume task '{signature}': {e!s}"
            raise self.__controlFailure(error_msg, "resumeTask") from e

    def removeTask(
        self: Self,
        signature: str,
    ) -> bool:
        """
        Remove a tracked task from the scheduler.

        Parameters
        ----------
        signature : str
            Signature of the running or paused task to remove.

        Returns
        -------
        bool
            ``True`` after removing the job and updating task bookkeeping.

        Raises
        ------
        RuntimeError
            If the scheduler is uninitialized, the task is not tracked as running
            or paused, or the removal operation fails.
        ValueError
            If the scheduler cannot find the tracked job.
        """
        # Ensure the scheduler is initialized before removing a task
        scheduler = self.__scheduler
        if not scheduler:
            error_msg = self._SCHEDULER_NOT_STARTED_ERROR
            raise RuntimeError(error_msg)

        # Check if the task exists in either running or paused state
        running_tasks = self.__running_tasks
        paused_tasks = self.__paused_tasks
        if signature not in running_tasks and signature not in paused_tasks:
            error_msg = f"Task '{signature}' does not exist and cannot be removed."
            raise RuntimeError(error_msg)

        # Retrieve the job from the scheduler and remove it
        job = scheduler.get_job(signature)
        if job is None:
            error_msg = f"Task '{signature}' does not exist."
            raise ValueError(error_msg)

        try:
            scheduler.remove_job(signature)
            running_tasks.discard(signature)
            paused_tasks.discard(signature)
            self.__removed_tasks.add(signature)
            Log.info(f"Task '{signature}' removed.")
            return True
        except Exception as e:
            error_msg = f"Failed to remove task '{signature}': {e!s}"
            raise self.__controlFailure(error_msg, "removeTask") from e

    def removeAllTasks(self: Self) -> bool:
        """
        Remove all tasks from the scheduler.

        Returns
        -------
        bool
            ``True`` after removing all jobs and clearing active task bookkeeping.

        Raises
        ------
        RuntimeError
            If the scheduler is uninitialized or the removal operation fails.
        """
        # Ensure the scheduler is initialized before removing tasks
        scheduler = self.__scheduler
        if not scheduler:
            error_msg = self._SCHEDULER_NOT_STARTED_ERROR
            raise RuntimeError(error_msg)

        try:
            scheduler.remove_all_jobs()
            self.__running_tasks.clear()
            self.__paused_tasks.clear()
            self.__removed_tasks.update(self.__tasks.keys())
            Log.info("All tasks removed from the scheduler.")
            return True
        except Exception as e:
            error_msg = f"Failed to remove all tasks: {e!s}"
            raise self.__controlFailure(error_msg, "removeAllTasks") from e

    def pause(self: Self) -> bool:
        """
        Pause scheduling when the scheduler is running.

        Returns
        -------
        bool
            ``True`` after pausing the scheduler and updating its state.

        Raises
        ------
        RuntimeError
            If the scheduler is uninitialized, is not running, or cannot be paused.
        """
        # Ensure the scheduler is initialized before pausing
        scheduler = self.__scheduler
        if not scheduler:
            error_msg = self._SCHEDULER_NOT_STARTED_ERROR
            raise RuntimeError(error_msg)

        # Ensure the scheduler is running before attempting to pause
        if not self.isRunning():
            error_msg = "The task scheduler is not running and cannot be paused."
            raise RuntimeError(error_msg)

        try:
            scheduler.pause()
            self.__state = ScheduleStates.PAUSED
            Log.info("Scheduler paused.")
            return True
        except Exception as e:
            error_msg = f"Failed to pause the scheduler: {e!s}"
            raise self.__controlFailure(error_msg, "pause") from e

    def resume(self: Self) -> bool:
        """
        Resume scheduling when the scheduler is paused.

        Returns
        -------
        bool
            ``True`` after resuming the scheduler and updating its state.

        Raises
        ------
        RuntimeError
            If the scheduler is uninitialized, is not paused, or cannot be resumed.
        """
        # Ensure the scheduler is initialized before resuming
        scheduler = self.__scheduler
        if not scheduler:
            error_msg = self._SCHEDULER_NOT_STARTED_ERROR
            raise RuntimeError(error_msg)

        # Ensure the scheduler is paused before attempting to resume
        if not self.isPaused():
            error_msg = "The task scheduler is not paused and cannot be resumed."
            raise RuntimeError(error_msg)

        try:
            scheduler.resume()
            self.__state = ScheduleStates.RUNNING
            Log.info("Scheduler resumed.")
            return True
        except Exception as e:
            error_msg = f"Failed to resume the scheduler: {e!s}"
            raise self.__controlFailure(error_msg, "resume") from e

    def shutdown(self: Self, wait: int | None = None) -> None:
        """
        Schedule graceful shutdown without blocking the caller.

        Start at most one shutdown task per scheduler boot cycle. The task observes
        a grace period, drains managed listeners, and requests scheduler shutdown.

        Parameters
        ----------
        wait : int or None, optional
            Non-negative grace period in seconds. Keep the current period when
            ``None``; the initial default is ``0.5`` seconds.

        Returns
        -------
        None
            Start or reuse the managed shutdown task without waiting for completion.

        Raises
        ------
        TypeError
            If ``wait`` is negative, a boolean, or neither an integer nor ``None``.
        """
        # Only override the configured grace period (defaults to 0.5s, see
        # __init__) when an explicit, valid value is provided. Unconditionally
        # falling back to 0 whenever `wait` is None silently defeats the
        # default grace period on every no-argument call, e.g. shutdown()
        # from schedule:work on Ctrl+C.
        if wait is not None:
            if isinstance(wait, bool) or not isinstance(wait, int) or wait < 0:
                error_msg = (
                    "The 'wait' parameter must be a non-negative integer or None."
                )
                raise TypeError(error_msg)
            self.__wait_to_shutdown = wait

        if self.__shutdown_task is not None:
            return
        self.__shutdown_task = self.__createManagedTask(self.__gracefulShutdown())
        self.__shutdown_task.add_done_callback(self.__shutdownCompleted)

    def __shutdownCompleted(self, task: asyncio.Task) -> None:
        """
        Notify shutdown waiters if the managed shutdown task was cancelled.

        Parameters
        ----------
        task : asyncio.Task
            Completed shutdown supervisor task.

        Returns
        -------
        None
            Record cancellation and signal completion if shutdown has not done so.
        """
        if task.cancelled() and not self.__shutdown_event.is_set():
            self.__shutdown_error = asyncio.CancelledError()
            self.__shutdown_event.set()

    async def __gracefulShutdown(self: Self) -> None:
        """
        Finalize shutdown and preserve failures for waiting callers.

        Returns
        -------
        None
            Run shutdown, retain any failure, and always notify shutdown waiters.

        Raises
        ------
        BaseException
            If shutdown is cancelled or raises another non-``Exception`` error.
        """
        try:
            await self.__finishShutdown()
        except BaseException as error:
            self.__shutdown_error = error
            receipt = await capture(
                error,
                runtime=self.__failure_runtime,
                flow="scheduler",
                phase="shutdown",
            )
            if receipt is None and isinstance(error, Exception):
                await self.__handleListenerException(error, legacy=False)
            if not isinstance(error, Exception):
                raise
        finally:
            self.__shutdown_event.set()

    async def __finishShutdown(self: Self) -> None:
        """
        Drain listeners and request scheduler shutdown off the event loop.

        Wait for the configured grace period before draining pending listeners.
        Submit the shutdown request with ``wait=True`` to an executor.

        Returns
        -------
        None
            Complete listener cleanup and the scheduler shutdown request.
        """
        # Get the current event loop for executing shutdown in a separate thread
        loop = asyncio.get_running_loop()

        # Sleep briefly to allow any pending tasks to complete cleanup
        # before signaling shutdown completion
        await asyncio.sleep(self.__wait_to_shutdown)

        # Give any in-flight listener tasks (scheduler/task event callbacks)
        # a chance to finish before the scheduler and event loop are torn
        # down, instead of abandoning them mid-execution. The currently
        # running task (this very shutdown coroutine) is excluded to avoid
        # awaiting on itself.
        current_task = asyncio.current_task()
        pending = tuple(
            task
            for task in self.__pending_listener_tasks
            if not task.done() and task is not current_task
        )
        if pending:
            outcomes = await asyncio.gather(*pending, return_exceptions=True)
            for error in outcomes:
                if isinstance(error, BaseException):
                    await capture(
                        error,
                        runtime=self.__failure_runtime,
                        flow="scheduler",
                        phase="drain",
                    )

        # Execute scheduler shutdown without blocking the main thread
        from orionis.support.concurrency import complete_on_cancel

        await complete_on_cancel(
            loop.run_in_executor(
                None,
                functools.partial(self.__scheduler.shutdown, wait=True),
            ),
        )

    async def wait(self: Self) -> None:
        """
        Wait for shutdown completion and re-raise any retained failure.

        Returns
        -------
        None
            Return once shutdown completes successfully.

        Raises
        ------
        BaseException
            If shutdown failed or its task was cancelled.
        """
        # Wait for the shutdown event to be set by the graceful shutdown process
        await self.__shutdown_event.wait()
        if self.__shutdown_error is not None:
            raise self.__shutdown_error
