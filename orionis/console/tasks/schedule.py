import asyncio
import functools
import inspect
import logging
from typing import Self, TYPE_CHECKING
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from orionis.console.contracts.schedule import ISchedule
from orionis.console.core.contracts.reactor import IReactor
from orionis.console.entities.scheduler_event import (
    SchedulerEvent as SchedulerEventEntity,
)
from orionis.console.enums.events import SchedulerEvent, TaskEvent
from orionis.console.fluent.contracts.task import ITask
from orionis.console.fluent.task import Task
from orionis.console.enums.states import ScheduleStates
from orionis.console.contracts.store import IScheduleStore
from orionis.failure.contracts.catch import ICatch
from orionis.support.facades.logger import Log
from orionis.support.facades.datetime import DateTime
from orionis.support.facades.reactor import Reactor
from orionis.console.entities.task_event import TaskEvent as TaskEventEntity

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from apscheduler.events import JobEvent as APJobEvent
    from apscheduler.events import SchedulerEvent as APSchedulerEvent
    from orionis.console.entities.task import Task as TaskEntity
    from orionis.foundation.config.scheduler.entities.scheduler import (
        Scheduler as ConfigScheduler,
    )

async def _executeScheduledCommand(
    signature: str,
    args: list[str] | None = None,
) -> int:
    """
    Execute a scheduled command signature through the Reactor facade.

    Parameters
    ----------
    signature : str
        The command signature to execute.
    args : list of str, optional
        Arguments to pass to the command. Defaults to an empty list.

    Returns
    -------
    int
        The result of the reactor call, typically an exit code or status.

    Notes
    -----
    Used as the callable registered with APScheduler jobs instead of a
    bound instance method. Persistent job stores (e.g. the "database"
    job store) serialize the job's callable as a textual reference
    (``module:function``); a bound method forces APScheduler to also
    pickle the owning instance (``self``) to restore it, which drags in
    the whole dependency graph (Reactor/Application) and fails on
    unpicklable objects such as a ``mappingproxy``. Resolving the reactor
    through the ``Reactor`` facade avoids that entirely.
    """
    # Delegate to the pinned reactor facade, resolved dynamically at call time
    return await Reactor.call(signature, args or [])

class Schedule(ISchedule):

    # ruff: noqa: BLE001, TC001

    _SCHEDULER_NOT_STARTED_ERROR = "The Orionis task scheduler has not been started."

    def __init__(
        self,
        reactor: IReactor,
        exception_handler: ICatch,
        stores: IScheduleStore,
    ) -> None:
        """
        Initialize the Schedule instance.

        Parameters
        ----------
        reactor : IReactor
            Reactor instance for command execution.
        exception_handler : ICatch
            Exception handler for managing errors.
        stores : IScheduleStore
            Schedule store for managing job stores.

        Returns
        -------
        None
            This constructor does not return a value.
        """
        self.__reactor: IReactor = reactor
        self.__exception_handler: ICatch = exception_handler
        self.__stores: IScheduleStore = stores
        self.__config: ConfigScheduler = stores.config
        self.__available_command_signatures: set[str] = set()
        self.__job_store: str = self.__config.store
        self.__scheduler: AsyncIOScheduler | None = None
        self.__scheduler_listeners: dict[SchedulerEvent, Callable] = {}
        self.__tasks_listeners: dict[str, dict[TaskEvent, Callable]] = {}
        self.__fluent_tasks: dict[str, ITask] = {}
        self.__tasks: dict[str, TaskEntity] = {}
        self.__state: ScheduleStates = ScheduleStates.STOPPED
        self.__running_tasks: set[str] = set()
        self.__paused_tasks: set[str] = set()
        self.__removed_tasks: set[str] = set()
        self.__pending_listener_tasks: set[asyncio.Task] = set()
        self.__shutdown_event = asyncio.Event()
        self.__wait_to_shutdown: float = 0.5

    async def __loadAvailableCommands(self) -> None:
        """
        Retrieve and cache available command signatures from the reactor.

        Queries the reactor for all available jobs/commands and stores their
        signatures in the internal set for quick lookup.

        Returns
        -------
        None
            This method does not return any value. It updates the internal set
            of available command signatures.
        """
        # Return early if command signatures are already cached
        if self.__available_command_signatures:
            return

        # Query the reactor for available commands and cache their signatures
        commands: list[dict] = await self.__reactor.info()
        self.__available_command_signatures.update(
            job.get("signature") for job in commands
        )

    def __suppressApschedulerLogging(self) -> None:
        """
        Disable APScheduler logging to prevent log message interference.

        Set APScheduler component loggers to CRITICAL level and disable message
        propagation to prevent internal scheduler logs from appearing in the
        application's logging output.

        Returns
        -------
        None
            Modifies APScheduler logging configuration in place.
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

    async def __validateAndLoadFluentTasks(self) -> None:
        """
        Validate and load fluent tasks from the internal registry.

        Ensures that all fluent tasks have signatures available in the reactor.
        Populates the internal tasks dictionary with validated task entities.

        Returns
        -------
        None
            This method updates the internal tasks dictionary in place.
        """
        # Cache locals to avoid repeated attribute lookups in the loop
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

    async def info(self) -> list[dict]:
        """
        Retrieve information about all loaded fluent tasks.

        Returns
        -------
        list of dict
            A list of dictionaries, each containing details about a loaded task.
        """
        # Ensure available command signatures are loaded before validating tasks
        await self.__loadAvailableCommands()

        # Validate that all fluent tasks have valid signatures and load their entities
        await self.__validateAndLoadFluentTasks()

        # Build and return via comprehension (C-level loop in CPython)
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
                    if task.start_date else None
                ),
                "end_date": (
                    task.end_date.strftime("%Y-%m-%d %H:%M:%S")
                    if task.end_date else None
                ),
                "details": task.details,
            }
            for signature, task in self.__tasks.items()
        ]

    async def _reactorCall(
        self,
        signature: str,
        args: list[str] | None = None,
    ) -> int:
        """
        Execute a reactor command asynchronously.

        Parameters
        ----------
        signature : str
            The command signature to execute.
        args : list of str, optional
            Arguments to pass to the command. Defaults to an empty list.

        Returns
        -------
        int
            The result of the reactor call, typically an exit code or status.

        Notes
        -----
        This method wraps the reactor call for task execution.
        """
        # Call the reactor asynchronously with the provided signature and arguments
        return await self.__reactor.call(signature, args or [])

    def _dispatchSchedulerEventListener(
        self,
        event: APSchedulerEvent,
    ) -> None:
        """
        Call the registered global event listener for a scheduler event.

        Parameters
        ----------
        event : APSchedulerEvent
            The scheduler event that occurred.

        Returns
        -------
        None
            This method does not return a value. It triggers the appropriate
            listener for the event.
        """
        # Cache event code to avoid repeated attribute lookup
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
                Log.error(f"Error executing listener: {e}")
                self.__createManagedTask(self.__handleListenerException(e))
            return

        # Handle asynchronous listeners using an async wrapper
        async def _asyncListenerWrapper() -> None:
            try:
                await listener(event_entity)
            except Exception as e:
                Log.error(f"Error executing listener: {e}")
                await self.__handleListenerException(e)

        # Schedule the async listener wrapper as a managed task
        self.__createManagedTask(_asyncListenerWrapper())

    def _dispatchTaskEventListener(
        self,
        event: APJobEvent,
    ) -> None:
        """
        Dispatch registered task event listener for a specific job event.

        Parameters
        ----------
        event : APJobEvent
            The job event that occurred.

        Returns
        -------
        None
            This method does not return a value. It triggers the appropriate
            listener for the event.
        """
        # Extract the job signature from the event (single attribute lookup)
        signature = getattr(event, "job_id", None)
        if not signature:
            return

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

        # Cache event code to avoid repeated attribute lookup
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
                Log.error(f"Error executing listener: {e}")
                self.__createManagedTask(self.__handleListenerException(e))
            return

        # Handle asynchronous listeners using an async wrapper
        async def _asyncListenerWrapper() -> None:
            try:
                await listener(event_entity)
            except Exception as e:
                Log.error(f"Error executing listener: {e}")
                await self.__handleListenerException(e)

        # Schedule the async listener wrapper as a managed task
        self.__createManagedTask(_asyncListenerWrapper())

    def __createManagedTask(
        self,
        coroutine: Coroutine,
    ) -> None:
        """
        Create and manage an asyncio task with automatic cleanup.

        Parameters
        ----------
        coroutine : Coroutine
            The coroutine to be executed as an async task.

        Returns
        -------
        None
            This method does not return a value. It manages the lifecycle of
            the created asyncio task.
        """
        # Create and track the async task, ensuring cleanup on completion
        # Bind discard directly — avoids lambda allocation and closure overhead
        pending = self.__pending_listener_tasks
        task = asyncio.create_task(coroutine)
        pending.add(task)
        task.add_done_callback(pending.discard)

    async def __handleListenerException(
        self,
        exception: Exception,
    ) -> None:
        """
        Handle exceptions raised in event listeners.

        Parameters
        ----------
        exception : Exception
            The exception raised by the listener.

        Returns
        -------
        None
            This method does not return any value.
        """
        try:
            # Handle the exception using the provided exception handler
            await self.__exception_handler.exception(exception)
        except Exception as handler_error:
            # Log errors that occur within the exception handler itself
            Log.error(f"Error in exception handler: {handler_error}")

    def __addConfiguredJobStore(self) -> None:
        """
        Add the database or redis jobstore matching the configured driver.

        `stores.database`/`stores.redis` default to None when not declared
        in config, so this validates explicitly instead of letting an
        AttributeError leak out of the config object when the selected
        driver's dedicated section was never configured.

        Returns
        -------
        None
            This method does not return a value. It registers the
            corresponding jobstore on the running scheduler, if applicable.

        Raises
        ------
        RuntimeError
            If the selected store is "database" or "redis" but its
            dedicated configuration section is missing.
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

    async def boot(self) -> None:
        """
        Boot the scheduler and register all configured tasks.

        Load available command signatures, validate and load fluent tasks,
        initialize the scheduler, register event listeners, and add all jobs
        to the scheduler.

        Returns
        -------
        None
            This method does not return a value but initializes the scheduler.
        """
        # Load available command signatures from the CLI reactor
        await self.__loadAvailableCommands()

        # Validate and load task entities to be registered
        await self.__validateAndLoadFluentTasks()

        # Get the current asyncio event loop for scheduling async tasks
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

        # Cache locals to avoid repeated LOAD_ATTR in the loop
        scheduler = self.__scheduler
        tasks_listeners = self.__tasks_listeners
        running_tasks = self.__running_tasks
        reactor_call = _executeScheduledCommand

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
        self,
        event: SchedulerEvent,
        listener: Callable,
    ) -> Self:
        """
        Register a listener for a scheduler event.

        Parameters
        ----------
        event : SchedulerEvent
            The scheduler event to listen for.
        listener : Callable
            The callable to invoke when the event occurs.

        Returns
        -------
        Self
            The Schedule instance for method chaining.

        Raises
        ------
        RuntimeError
            If the scheduler has already been booted.
        TypeError
            If event is not a SchedulerEvent or listener is not callable.
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

    def state(self) -> str:
        """
        Return the current scheduler state as a string.

        Returns
        -------
        str
            The current state of the scheduler, e.g., "RUNNING", "PAUSED", or "STOPPED".
        """
        # Return the value of the internal state enum
        return self.__state.value

    def isRunning(self) -> bool:
        """
        Determine if the scheduler is currently running.

        Returns
        -------
        bool
            True if the scheduler state is "RUNNING", otherwise False.
        """
        # Check if the internal state is RUNNING
        return self.__state == ScheduleStates.RUNNING

    def isPaused(self) -> bool:
        """
        Determine if the scheduler is currently paused.

        Returns
        -------
        bool
            True if the scheduler state is "PAUSED", otherwise False.
        """
        # Check if the internal state is PAUSED
        return self.__state == ScheduleStates.PAUSED

    def isStopped(self) -> bool:
        """
        Determine if the scheduler is currently stopped.

        Returns
        -------
        bool
            True if the scheduler state is "STOPPED", otherwise False.
        """
        # Check if the internal state is STOPPED
        return self.__state == ScheduleStates.STOPPED

    def command(
        self,
        signature: str,
        args: list[str] | None = None,
        purpose: str | None = None,
    ) -> ITask:
        """
        Add a command for fluent configuration.

        Parameters
        ----------
        signature : str
            Unique signature of the command to schedule.
        args : list[str] | None, optional
            Arguments for the command. Defaults to None.
        purpose : str | None, optional
            Description of the command's purpose.

        Returns
        -------
        ITask
            Task instance for further configuration.

        Raises
        ------
        RuntimeError
            If the scheduler has already been started.
        TypeError
            If the signature is not a non-empty string or arguments are invalid.
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
                error_msg = (
                    "Arguments must be provided as a list of strings or None."
                )
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
        self.__fluent_tasks[signature] = Task(
            signature,
            args or [],
            purpose=purpose,
        )
        return self.__fluent_tasks[signature]

    def pauseTask(
        self,
        signature: str,
    ) -> bool:
        """
        Pause a running task by its signature.

        Parameters
        ----------
        signature : str
            Unique identifier of the task to pause.

        Returns
        -------
        bool
            True if the task was successfully paused, otherwise raises an exception.

        Raises
        ------
        RuntimeError
            If the scheduler has not been started or the task is not running.
        ValueError
            If the specified task does not exist.

        Notes
        -----
        This method pauses a running task in the scheduler.
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
            Log.error(error_msg)
            raise RuntimeError(error_msg) from e

    def resumeTask(
        self,
        signature: str,
    ) -> bool:
        """
        Resume a paused task by its signature.

        Parameters
        ----------
        signature : str
            Unique identifier of the task to resume.

        Returns
        -------
        bool
            True if the task was successfully resumed, otherwise raises an exception.

        Raises
        ------
        RuntimeError
            If the scheduler has not been started or the task is not paused.
        ValueError
            If the specified task does not exist.

        Notes
        -----
        This method resumes a paused task in the scheduler.
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
            Log.error(error_msg)
            raise RuntimeError(error_msg) from e

    def removeTask(
        self,
        signature: str,
    ) -> bool:
        """
        Remove a task from the scheduler by its signature.

        Parameters
        ----------
        signature : str
            Unique identifier of the task to remove.

        Returns
        -------
        bool
            True if the task was successfully removed, otherwise raises an exception.

        Raises
        ------
        RuntimeError
            If the scheduler has not been started or the task is not found.
        ValueError
            If the specified task does not exist.

        Notes
        -----
        This method removes a task from the scheduler and updates internal state.
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
            Log.error(error_msg)
            raise RuntimeError(error_msg) from e

    def removeAllTasks(self) -> bool:
        """
        Remove all tasks from the scheduler.

        Returns
        -------
        bool
            True if all tasks were successfully removed, otherwise raises an exception.

        Raises
        ------
        RuntimeError
            If the scheduler has not been started or an error occurs during removal.

        Notes
        -----
        This method removes all tasks from the scheduler and updates internal state.
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
            Log.error(error_msg)
            raise RuntimeError(error_msg) from e

    def pause(self) -> bool:
        """
        Pause the scheduler if it is running.

        Parameters
        ----------
        self : Schedule
            The Schedule instance.

        Returns
        -------
        bool
            True if the scheduler was successfully paused.

        Raises
        ------
        RuntimeError
            If the scheduler is not started or not running.
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
            Log.error(error_msg)
            raise RuntimeError(error_msg) from e

    def resume(self) -> bool:
        """
        Resume the scheduler if it is paused.

        Parameters
        ----------
        self : Schedule
            The Schedule instance.

        Returns
        -------
        bool
            True if the scheduler was successfully resumed.

        Raises
        ------
        RuntimeError
            If the scheduler is not started or not paused.
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
            Log.error(error_msg)
            raise RuntimeError(error_msg) from e

    def shutdown(self, wait: int | None = None) -> None:
        """
        Shut down the task scheduler safely without waiting for running tasks.

        This method terminates the scheduler execution safely. It does not wait
        for currently executing tasks to complete, but prevents new tasks from
        starting and cleans up scheduler resources. Ideal for console
        environments where the process stops immediately after calling this
        method.

        Parameters
        ----------
        wait : int | None, optional
            Time in seconds to wait before completing shutdown. Defaults to
            None, which keeps the previously configured grace period instead
            of collapsing it to zero.

        Returns
        -------
        None
            This method does not return a value. It initiates graceful shutdown.

        Raises
        ------
        TypeError
            If `wait` is neither None nor a non-negative integer (bool is
            explicitly rejected even though it is technically an int subtype).
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

        # Create and execute the shutdown task asynchronously
        self.__createManagedTask(self.__gracefulShutdown())

    async def __gracefulShutdown(self) -> None:
        """
        Execute graceful shutdown of the scheduler without blocking.

        This method runs the scheduler shutdown in a thread executor to avoid
        blocking the event loop, then sets the shutdown event to notify any
        waiting tasks that shutdown is complete.

        Returns
        -------
        None
            This method does not return a value.
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
            await asyncio.gather(*pending, return_exceptions=True)

        # Execute scheduler shutdown without blocking the main thread
        # functools.partial avoids lambda allocation and closure overhead
        await loop.run_in_executor(
            None,
            functools.partial(self.__scheduler.shutdown, wait=True),
        )

        # Signal that shutdown is complete
        self.__shutdown_event.set()

    async def wait(self) -> None:
        """
        Wait for the scheduler shutdown to complete.

        This method blocks until the shutdown process initiated by the shutdown()
        method has finished. It provides a way to synchronize with the graceful
        shutdown process.

        Returns
        -------
        None
            This method does not return a value but blocks until shutdown
            completes.
        """
        # Wait for the shutdown event to be set by the graceful shutdown process
        await self.__shutdown_event.wait()
