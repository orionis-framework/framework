from __future__ import annotations
import secrets
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Self
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from orionis.console.base.listener import BaseTaskListener
from orionis.console.entities.task import Task as TaskEntity
from orionis.console.enums.events import TaskEvent
from orionis.console.fluent.contracts.task import ITask
from orionis.support.facades.datetime import DateTime

if TYPE_CHECKING:
    from collections.abc import Callable

class Task(ITask):

    # ruff: noqa: PLR2004, PLR0913

    _ERROR_MSG_INVALID_INTERVAL = "Interval value must be a positive integer."
    _ERROR_MSG_INVALID_MINUTE = "Minute must be between 0 and 59."
    _ERROR_MSG_INVALID_SECOND = "Second must be between 0 and 59."
    _ERROR_MSG_INVALID_HOUR = "Hour must be between 0 and 23."

    # Built once at import time; avoids dict allocation on each registerListener call
    _LISTENER_METHODS_MAP: ClassVar[dict[str, TaskEvent]] = {
        "onTaskAdded": TaskEvent.ADDED,
        "onTaskRemoved": TaskEvent.REMOVED,
        "onTaskExecuted": TaskEvent.EXECUTED,
        "onTaskError": TaskEvent.ERROR,
        "onTaskMissed": TaskEvent.MISSED,
        "onTaskSubmitted": TaskEvent.SUBMITTED,
        "onTaskMaxInstances": TaskEvent.MAX_INSTANCES,
    }

    def __init__(
        self,
        signature: str,
        args: list[str] | None,
        kwargs: dict | None = None,
        purpose: str | None = None,
    ) -> None:
        """
        Initialize the Task instance.

        Set up the initial state of the Task, including its signature, arguments,
        purpose, and optional attributes such as random delay, start and end dates,
        trigger, details, listener, maximum instances, misfire grace time, and
        coalesce flag.

        Parameters
        ----------
        signature : str
            Unique identifier for the task. Must be a non-empty string.
        args : list of str or None
            List of arguments for the task. Defaults to an empty list if None.
        purpose : str or None, optional
            Human-readable description or purpose of the task.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Initialize the default timezone for the event using DateTime utility.
        self.__default_tz = DateTime.getZoneInfo()

        # Store the task's unique signature
        self.__signature: str = signature

        # Store the task's arguments, defaulting to an empty list if None is provided
        self.__args: list[str] | None = args if args is not None else []

        # Store the task's keyword arguments,
        # defaulting to an empty dict if None is provided
        self.__kwargs: dict | None = kwargs if kwargs is not None else {}

        # Store the task's purpose or description
        self.__purpose: str | None = purpose

        # Initialize the random delay attribute (in seconds) as None
        self.__random_delay: int | None = None

        # Initialize the start date for the task as None
        self.__start_date: datetime | None = None

        # Initialize the end date for the task as None
        self.__end_date: datetime | None = None

        # Initialize the trigger for the task as None
        self.__trigger: CronTrigger | DateTrigger | IntervalTrigger | None = None

        # Initialize the details for the task as None
        self.__details: str | None = None

        # Initialize list to hold task event listeners
        self.__listeners: list[Callable] = []

        # Initialize the maximum instances attribute as 1
        self.__max_instances: int | None = None

        # Initialize the misfire grace time attribute as None
        self.__misfire_grace_time: int | None = None

        # Initialize the coalesce attribute as None
        self.__coalesce: bool | None = None

    def __datetime(
        self,
        year: int,
        month: int,
        day: int,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
    ) -> datetime:
        """
        Create a datetime instance from individual date and time components.

        Validates all input parameters and constructs a datetime object using
        the provided year, month, day, hour, minute, and second values.

        Parameters
        ----------
        year : int
            The year component.
        month : int
            The month component (1-12).
        day : int
            The day component (1-31).
        hour : int, optional
            The hour component (0-23). Default is 0.
        minute : int, optional
            The minute component (0-59). Default is 0.
        second : int, optional
            The second component (0-59). Default is 0.

        Returns
        -------
        datetime
            A datetime instance constructed from the provided components.

        Raises
        ------
        TypeError
            If year, month, day, hour, minute, or second are not integers.
        ValueError
            If hour, minute, or second are outside their valid ranges.
        """
        # Validate that year, month, and day are integers.
        if (
            not isinstance(year, int)
            or not isinstance(month, int)
            or not isinstance(day, int)
        ):
            error_msg = "Year, month and day must be integers."
            raise TypeError(error_msg)

        # Validate that hour, minute, and second are integers.
        if (
            not isinstance(hour, int)
            or not isinstance(minute, int)
            or not isinstance(second, int)
        ):
            error_msg = "Hour, minute and second must be integers."
            raise TypeError(error_msg)

        # Validate hour is within valid range [0, 23].
        if not (0 <= hour <= 23):
            error_msg = self._ERROR_MSG_INVALID_HOUR
            raise ValueError(error_msg)

        # Validate minute is within valid range [0, 59].
        if not (0 <= minute <= 59):
            error_msg = self._ERROR_MSG_INVALID_MINUTE
            raise ValueError(error_msg)

        # Validate second is within valid range [0, 59].
        if not (0 <= second <= 59):
            error_msg = self._ERROR_MSG_INVALID_SECOND
            raise ValueError(error_msg)

        # Construct and return a datetime instance.
        return datetime(
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            second=second,
            tzinfo=self.__default_tz,
        )

    def entity(
        self,
        random_delay: int | None = 0,
        max_instances: int | None = 1,
        misfire_grace_time: int | None = 0,
        *,
        coalesce: bool | None = True,
    ) -> TaskEntity:
        """
        Create and return a TaskEntity instance from the current Task.

        Collect all relevant attributes of the Task and encapsulate them in a
        TaskEntity object.

        Parameters
        ----------
        random_delay : int | None, optional
            Random delay in seconds before triggering. Defaults to 0.
        max_instances : int | None, optional
            Maximum concurrent instances allowed. Defaults to 1.
        misfire_grace_time : int | None, optional
            Grace period in seconds for misfired events. Defaults to 0.
        coalesce : bool | None, optional
            Whether to coalesce missed runs into a single run. Defaults to True.

        Returns
        -------
        TaskEntity
            The TaskEntity instance containing the task's data.

        Raises
        ------
        ValueError
            If signature or trigger is not set.

        Notes
        -----
        A per-task value explicitly configured through the fluent API
        (``.maxInstances()``, ``.coalesce()``, ``.misfireGraceTime()``,
        ``.randomDelay()``) always takes precedence over the scheduler-level
        default received here. Using ``or`` instead of an explicit ``is not
        None`` check would silently discard the task override whenever the
        scheduler-level default is truthy (which it is for every field by
        default: ``coalesce=True``, ``max_instances=1``,
        ``misfire_grace_time=30``), so that comparison must not be
        reintroduced.
        """
        # Ensure both signature and trigger are set before creating the entity.
        if not (self.__signature and self.__trigger):
            error_msg = (
                "Both signature and trigger must be set to create a TaskEntity."
            )
            raise ValueError(error_msg)

        # Construct and return a TaskEntity with the current task's attributes.
        # The task-level value (self.__xxx) wins whenever it was explicitly
        # set; only an unset (None) attribute falls back to the scheduler's
        # default, passed in via the corresponding parameter.
        return TaskEntity(
            signature=self.__signature,
            args=self.__args,
            kwargs=self.__kwargs,
            purpose=self.__purpose,
            random_delay=(
                self.__random_delay
                if self.__random_delay is not None
                else random_delay
            ),
            start_date=self.__start_date,
            end_date=self.__end_date,
            trigger=self.__trigger,
            details=self.__details,
            max_instances=(
                self.__max_instances
                if self.__max_instances is not None
                else max_instances
            ),
            misfire_grace_time=(
                self.__misfire_grace_time
                if self.__misfire_grace_time is not None
                else misfire_grace_time
            ),
            coalesce=(
                self.__coalesce if self.__coalesce is not None else coalesce
            ),
            listeners=self.__listeners,
        )

    def coalesce(
        self,
        *,
        coalesce: bool = True,
    ) -> Self:
        """
        Set the coalesce behavior for missed task executions.

        Parameters
        ----------
        coalesce : bool, optional
            If True, only the most recent missed execution is run. If False, all
            missed executions are run in sequence. Default is True.

        Returns
        -------
        Task
            The current Task instance for method chaining.
        """
        # Set the internal coalesce attribute to control missed execution behavior.
        self.__coalesce = coalesce

        # Return self to support method chaining.
        return self

    def misfireGraceTime(
        self,
        seconds: int = 60,
    ) -> Self:
        """
        Set the misfire grace time in seconds.

        Parameters
        ----------
        seconds : int, optional
            Number of seconds for the misfire grace period. Must be a positive
            integer greater than zero. Default is 60.

        Returns
        -------
        Task
            This instance for method chaining.

        Raises
        ------
        ValueError
            If `seconds` is not a positive integer.
        """
        # Validate that the seconds parameter is a positive integer.
        if not isinstance(seconds, int) or seconds <= 0:
            error_msg = "Misfire grace time must be a positive integer."
            raise ValueError(error_msg)

        # Set the internal misfire grace time attribute.
        self.__misfire_grace_time = seconds

        # Return self to support method chaining.
        return self

    def purpose(
        self,
        purpose: str,
    ) -> Self:
        """
        Set the purpose or description for the scheduled command.

        Parameters
        ----------
        purpose : str
            Purpose or description to associate with the scheduled command. Must be a
            non-empty string.

        Returns
        -------
        Task
            The current instance for method chaining.

        Raises
        ------
        ValueError
            If the purpose is not a non-empty string.
        """
        # Validate that the purpose is a non-empty string.
        if not isinstance(purpose, str) or not purpose.strip():
            error_msg = "The purpose must be a non-empty string."
            raise ValueError(error_msg)

        # Set the internal purpose attribute.
        self.__purpose = purpose.strip()

        # Return self to support method chaining.
        return self

    def startDate(
        self,
        year: int,
        month: int,
        day: int,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
    ) -> Self:
        """
        Set the start date for task execution.

        Parameters
        ----------
        year : int
            The year component.
        month : int
            The month component (1-12).
        day : int
            The day component (1-31).
        hour : int, optional
            The hour component (0-23). Default is 0.
        minute : int, optional
            The minute component (0-59). Default is 0.
        second : int, optional
            The second component (0-59). Default is 0.

        Returns
        -------
        Self
            The current Task instance for method chaining.

        Raises
        ------
        TypeError
            If any date component is not an integer.
        ValueError
            If hour, minute, or second are outside their valid ranges.
        """
        # Assign the start date to the internal attribute.
        self.__start_date = self.__datetime(
            year, month, day, hour, minute, second,
        )

        # Return self to allow method chaining.
        return self

    def endDate(
        self,
        year: int,
        month: int,
        day: int,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
    ) -> Self:
        """
        Set the end date for task execution.

        Parameters
        ----------
        year : int
            The year component.
        month : int
            The month component (1-12).
        day : int
            The day component (1-31).
        hour : int, optional
            The hour component (0-23). Default is 0.
        minute : int, optional
            The minute component (0-59). Default is 0.
        second : int, optional
            The second component (0-59). Default is 0.

        Returns
        -------
        Self
            The current Task instance for method chaining.

        Raises
        ------
        TypeError
            If any date component is not an integer.
        ValueError
            If hour, minute, or second are outside their valid ranges.
        """
        # Assign the end date to the internal attribute.
        self.__end_date = self.__datetime(year, month, day, hour, minute, second)

        # Return self to allow method chaining.
        return self

    def randomDelay(
        self,
        max_seconds: int = 10,
    ) -> Self:
        """
        Configure a random delay before task execution.

        Parameters
        ----------
        max_seconds : int, optional
            Maximum delay in seconds before execution. Must be between 0 and 120.
            Default is 10.

        Returns
        -------
        Task
            The current Task instance for method chaining.

        Raises
        ------
        ValueError
            If max_seconds is not an integer in [0, 120].
        """
        # Validate that max_seconds is an integer within the allowed range.
        if not isinstance(max_seconds, int) or max_seconds < 0 or max_seconds > 120:
            error_msg = (
                "Max seconds must be a positive integer between 0 and 120."
            )
            raise ValueError(error_msg)

        # Set a random delay between 0 and max_seconds using a cryptographically secure
        # generator, or 0 if max_seconds is 0.
        self.__random_delay = (
            secrets.randbelow(max_seconds + 1) if max_seconds > 0 else 0
        )

        # If a trigger was already configured before this call (e.g. the fluent
        # chain calls .everyMinutes() before .randomDelay()), the trigger was
        # built with the jitter known at that time. Patch it in place so the
        # random delay is never silently dropped due to call order.
        if self.__trigger is not None and hasattr(self.__trigger, "jitter"):
            self.__trigger.jitter = self.__random_delay

        # Return self to allow method chaining.
        return self

    def maxInstances(
        self,
        max_instances: int,
    ) -> Self:
        """
        Set the maximum number of concurrent task instances.

        Parameters
        ----------
        max_instances : int
            Maximum number of concurrent instances. Must be a positive integer.

        Returns
        -------
        Task
            This instance for method chaining.
        """
        # Validate that max_instances is a positive integer.
        if not isinstance(max_instances, int) or max_instances <= 0:
            error_msg = "Max instances must be a positive integer."
            raise ValueError(error_msg)

        # Set the internal max instances attribute.
        self.__max_instances = max_instances

        # Return self to support method chaining.
        return self

    def on(
        self,
        event: TaskEvent,
        callback: Callable,
    ) -> Self:
        """
        Register a callback for a specific task event.

        Parameters
        ----------
        event : TaskEvent
            The event type to listen for.
        callback : Callable
            The function to call when the event occurs.

        Returns
        -------
        Task
            The current Task instance for method chaining.

        Raises
        ------
        ValueError
            If `event` is not a TaskEvent or `callback` is not callable.
        """
        # Validate that the event is a valid TaskEvent enum member.
        if not isinstance(event, TaskEvent):
            error_msg = "Event must be an instance of TaskEvent."
            raise TypeError(error_msg)

        # Validate that the callback is a callable function.
        if not callable(callback):
            error_msg = "Callback must be a callable function."
            raise TypeError(error_msg)

        # Append the event and callback as a tuple to the listeners list
        self.__listeners.append((event, callback))

        # Return self to allow method chaining.
        return self

    def registerListener(
        self,
        listener: BaseTaskListener,
    ) -> Self:
        """
        Register a task listener for task events.

        Parameters
        ----------
        listener : BaseTaskListener
            Listener instance implementing the BaseTaskListener interface.

        Returns
        -------
        Self
            The current Task instance for method chaining.

        Raises
        ------
        TypeError
            If the listener does not implement BaseTaskListener.
        """
        # Ensure the listener implements the BaseTaskListener interface.
        if not isinstance(listener, BaseTaskListener):
            error_msg = (
                "Listener instance must implement BaseTaskListener interface."
            )
            raise TypeError(error_msg)
        listener_instance = listener

        # Automatically register listener methods for supported events
        # based on the _LISTENER_METHODS_MAP
        for method_name, event in self._LISTENER_METHODS_MAP.items():
            method = getattr(listener_instance, method_name, None)
            if callable(method):
                self.on(event, method)

        # Return self to support method chaining.
        return self

    def onceAt(
        self,
        year: int,
        month: int,
        day: int,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
    ) -> bool:
        """
        Schedule the task to execute once at a specific date and time.

        Configure the task to run a single time at the specified date and time
        using the provided year, month, day, hour, minute, and second values.
        This sets both start and end dates to the specified datetime and uses
        a DateTrigger for one-time execution.

        Parameters
        ----------
        year : int
            The year component.
        month : int
            The month component (1-12).
        day : int
            The day component (1-31).
        hour : int, optional
            The hour component (0-23). Default is 0.
        minute : int, optional
            The minute component (0-59). Default is 0.
        second : int, optional
            The second component (0-59). Default is 0.

        Returns
        -------
        bool
            True if the scheduling was configured successfully.

        Raises
        ------
        ValueError
            If random delay is set or if date components are invalid.
        TypeError
            If any date component is not an integer.
        """
        # Construct a datetime instance from the provided components.
        date = self.__datetime(year, month, day, hour, minute, second)

        # Ensure random delay is not set for one-time execution. `__random_delay`
        # defaults to None (randomDelay() was never called), so it must be
        # guarded before the numeric comparison to avoid a TypeError.
        if self.__random_delay and self.__random_delay > 0:
            error_msg = (
                "Random delay cannot be applied to a one-time execution."
            )
            raise ValueError(error_msg)

        # Set both start and end dates to the specified date.
        self.__start_date = date
        self.__end_date = date
        self.__max_instances = 1

        # Configure the trigger for one-time execution at the specified date.
        self.__trigger = DateTrigger(
            run_date=date,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the scheduled execution.
        self.__details = f"Once At: {date.strftime('%Y-%m-%d %H:%M:%S')}"

        # Indicate that scheduling was configured successfully.
        return True

    def everySeconds(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule the task to run at fixed intervals in seconds.

        Validate that `seconds` is a positive integer. Set an IntervalTrigger to run
        at the specified interval. If a random delay is set, raise an error. Return
        True if scheduling is configured.

        Parameters
        ----------
        seconds : int
            Interval in seconds. Must be a positive integer.

        Returns
        -------
        bool
            True if scheduling was configured successfully.

        Raises
        ------
        ValueError
            If `seconds` is not a positive integer or if random delay is set.
        """
        # Validate that the seconds parameter is a positive integer.
        if not isinstance(seconds, int) or seconds <= 0:
            error_msg = self._ERROR_MSG_INVALID_INTERVAL
            raise ValueError(error_msg)

        # Ensure that random delay is not set for second-based intervals.
        if self.__random_delay and self.__random_delay > 0:
            error_msg = (
                "Random delay (jitter) cannot be applied to second-based intervals."
            )
            raise ValueError(error_msg)

        # Configure the trigger to execute the event at the specified interval,
        # using any previously set start_date and end_date.
        self.__trigger = IntervalTrigger(
            seconds=seconds,
            start_date=self.__start_date,
            end_date=self.__end_date,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule.
        if seconds == 1:
            self.__details = "Every second"
        else:
            self.__details = f"Every {seconds} seconds"

        # Indicate that the scheduling was successful.
        return True

    def everyFiveSeconds(
        self,
    ) -> bool:
        """
        Schedule the task to run every five seconds.

        This method sets up the event to execute at a fixed interval of five seconds
        using an `IntervalTrigger`. The scheduling window can be limited by the
        `start_date` and `end_date` attributes if they are set. If a random delay
        (jitter) is configured, it will be applied to the trigger.

        Returns
        -------
        bool
            Always returns True after configuring the interval trigger.
        """
        # Delegate scheduling to the everySeconds method with an interval of 5 seconds.
        return self.everySeconds(5)

    def everyTenSeconds(
        self,
    ) -> bool:
        """
        Schedule the task to run every ten seconds.

        Configure the event to execute at a fixed interval of ten seconds using an
        IntervalTrigger. The schedule can be limited by `start_date` and `end_date`.
        If a random delay (jitter) is set, it is not applied.

        Returns
        -------
        bool
            Always returns True after configuring the interval trigger.
        """
        # Delegate scheduling to the everySeconds method with an interval of 10 seconds.
        return self.everySeconds(10)

    def everyFifteenSeconds(
        self,
    ) -> bool:
        """
        Schedule the task to run every fifteen seconds.

        Configure the event to execute at a fixed interval of fifteen seconds using an
        IntervalTrigger. The schedule can be restricted by `start_date` and `end_date`.
        If a random delay (jitter) is set, it is not applied.

        Returns
        -------
        bool
            Always returns True after configuring the interval trigger.
        """
        # Delegate scheduling to the everySeconds method with an interval of 15 seconds.
        return self.everySeconds(15)

    def everyTwentySeconds(
        self,
    ) -> bool:
        """
        Schedule the task to run every twenty seconds.

        Configures the event to execute at a fixed interval of twenty seconds using an
        IntervalTrigger. The schedule can be restricted by `start_date` and `end_date`.
        If a random delay (jitter) is set, it is not applied.

        Returns
        -------
        bool
            Always returns True after configuring the interval trigger.
        """
        # Delegate scheduling to the everySeconds method with an interval of 20 seconds.
        return self.everySeconds(20)

    def everyTwentyFiveSeconds(
        self,
    ) -> bool:
        """
        Schedule the task to run every twenty-five seconds.

        Configure the event to execute at a fixed interval of twenty-five seconds using
        an IntervalTrigger. The schedule can be restricted by `start_date` and
        `end_date`. If a random delay (jitter) is set, it is not applied.

        Returns
        -------
        bool
            Always returns True after configuring the interval trigger.
        """
        # Delegate scheduling to the everySeconds method with an interval of 25 seconds.
        return self.everySeconds(25)

    def everyThirtySeconds(
        self,
    ) -> bool:
        """
        Schedule the task to run every thirty seconds.

        Configures the event to execute at a fixed interval of thirty seconds using an
        IntervalTrigger. The schedule can be limited by `start_date` and `end_date`.
        If a random delay (jitter) is set, it is not applied.

        Returns
        -------
        bool
            Always returns True after configuring the interval trigger.
        """
        # Delegate scheduling to the everySeconds method with an interval of 30 seconds.
        return self.everySeconds(30)

    def everyThirtyFiveSeconds(
        self,
    ) -> bool:
        """
        Schedule the task to run every thirty-five seconds.

        Configures the event to execute at a fixed interval of thirty-five seconds
        using an IntervalTrigger. The schedule can be restricted by `start_date`
        and `end_date`. If a random delay (jitter) is set, it is not applied.

        Returns
        -------
        bool
            Returns True after configuring the interval trigger for execution every
            thirty-five seconds.
        """
        # Delegate scheduling to the everySeconds method with an interval of 35 seconds.
        return self.everySeconds(35)

    def everyFortySeconds(
        self,
    ) -> bool:
        """
        Schedule the task to run every forty seconds.

        Configure the event to execute at a fixed interval of forty seconds using an
        IntervalTrigger. The schedule can be restricted by `start_date` and `end_date`.
        If a random delay (jitter) is set, it is not applied.

        Returns
        -------
        bool
            Always returns True after configuring the interval trigger.
        """
        # Delegate scheduling to the everySeconds method with an interval of 40 seconds.
        return self.everySeconds(40)

    def everyFortyFiveSeconds(
        self,
    ) -> bool:
        """
        Schedule the task to run every forty-five seconds.

        Configures the event to execute at a fixed interval of forty-five seconds using
        an IntervalTrigger. The schedule can be limited by `start_date` and `end_date`.
        If a random delay (jitter) is set, it is not applied.

        Returns
        -------
        bool
            Always returns True after configuring the interval trigger.
        """
        # Delegate scheduling to the everySeconds method with an interval of 45 seconds.
        return self.everySeconds(45)

    def everyFiftySeconds(
        self,
    ) -> bool:
        """
        Schedule the task to run every fifty seconds.

        Configure the event to execute at a fixed interval of fifty seconds using an
        IntervalTrigger. The scheduling window can be restricted by `start_date` and
        `end_date`. If a random delay (jitter) is set, it is not applied.

        Returns
        -------
        bool
            Always returns True after configuring the interval trigger.
        """
        # Delegate scheduling to the everySeconds method with an interval of 50 seconds.
        return self.everySeconds(50)

    def everyFiftyFiveSeconds(
        self,
    ) -> bool:
        """
        Schedule the task to run every fifty-five seconds.

        Configure the event to execute at a fixed interval of fifty-five seconds using
        an IntervalTrigger. The scheduling window can be restricted by `start_date`
        and `end_date`. If a random delay (jitter) is set, it is not applied.

        Returns
        -------
        bool
            Always returns True after configuring the interval trigger.
        """
        # Delegate scheduling to the everySeconds method with an interval of 55 seconds.
        return self.everySeconds(55)

    def everyMinutes(
        self,
        minutes: int,
    ) -> bool:
        """
        Schedule the task to run at fixed intervals in minutes.

        Validates that `minutes` is a positive integer. Sets an IntervalTrigger with
        the specified interval, using any configured `start_date`, `end_date`, and
        random delay (jitter) if set.

        Parameters
        ----------
        minutes : int
            Interval in minutes. Must be a positive integer.

        Returns
        -------
        bool
            Always returns True after configuring the interval trigger.
        """
        # Validate that the minutes parameter is a positive integer.
        if not isinstance(minutes, int) or minutes <= 0:
            error_msg = self._ERROR_MSG_INVALID_INTERVAL
            raise ValueError(error_msg)

        # Configure the trigger to execute the event at the specified interval,
        # using any previously set start_date, end_date, and random_delay (jitter).
        self.__trigger = IntervalTrigger(
            minutes=minutes,
            start_date=self.__start_date,
            end_date=self.__end_date,
            jitter=self.__random_delay,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule.
        self.__details = f"Every {minutes} minutes"

        # Indicate that the scheduling was successful.
        return True

    def everyMinuteAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule the task to run every minute at a specific second.

        Validate that `seconds` is an integer in [0, 59]. Set a CronTrigger to execute
        at the specified second of every minute. Ignore any previously set jitter.

        Parameters
        ----------
        seconds : int
            The second (0-59) of each minute to execute the event.

        Returns
        -------
        bool
            True if scheduling was configured successfully.

        Notes
        -----
        The event will be triggered at the specified second of every minute.
        """
        # Validate that 'seconds' is an integer between 0 and 59.
        if not isinstance(seconds, int) or not (0 <= seconds <= 59):
            error_msg = "Seconds must be an integer between 0 and 59."
            raise ValueError(error_msg)

        # Set the trigger to execute the event every minute at the specified second.
        # Jitter is not applied for this schedule.
        self.__trigger = CronTrigger(
            minute="*",
            second=seconds,
            start_date=self.__start_date,
            end_date=self.__end_date,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule.
        self.__details = f"Every minute at {seconds} seconds"

        # Indicate that the scheduling was successful.
        return True

    def everyMinutesAt(
        self,
        minutes: int,
        seconds: int,
    ) -> bool:
        """
        Schedule to run at a specific second of every N-minute interval.

        Validates input for minutes and seconds. Sets a CronTrigger to execute at the
        specified second of every N-minute interval. Returns True if scheduling is set.

        Parameters
        ----------
        minutes : int
            Interval in minutes. Must be a positive integer.
        seconds : int
            Second of the minute (0-59).

        Returns
        -------
        bool
            True if scheduling was configured successfully.

        Raises
        ------
        ValueError
            If minutes is not a positive integer or seconds is not in [0, 59].
        """
        # Validate that 'minutes' is a positive integer.
        if not isinstance(minutes, int) or minutes <= 0:
            error_msg = "Minutes must be a positive integer."
            raise ValueError(error_msg)

        # Validate that 'seconds' is an integer between 0 and 59.
        if not isinstance(seconds, int) or not (0 <= seconds <= 59):
            error_msg = "Seconds must be an integer between 0 and 59."
            raise ValueError(error_msg)

        # Set the trigger to execute at the specified second of every N-minute interval.
        self.__trigger = CronTrigger(
            minute=f"*/{minutes}",
            second=seconds,
            start_date=self.__start_date,
            end_date=self.__end_date,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule.
        self.__details = f"Every {minutes} minutes at {seconds} seconds"

        # Indicate that the scheduling was successful.
        return True

    def everyFiveMinutes(
        self,
    ) -> bool:
        """
        Schedule the task to run every five minutes.

        Configures the event to execute at a fixed interval of five minutes using an
        IntervalTrigger. The scheduling window can be restricted by `start_date` and
        `end_date`. Applies random delay (jitter) if set.

        Returns
        -------
        bool
            Always returns True after configuring the interval trigger.
        """
        # Delegate scheduling to the everyMinutes method with an interval of 5 minutes.
        return self.everyMinutes(5)

    def everyFiveMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule the task to run every five minutes at a specific second.

        Set the event to execute at the specified second (0-59) of every five-minute
        interval. The scheduling window can be restricted by `start_date` and
        `end_date`. Random delay (jitter) is not applied to this schedule,
        since it targets an exact second.

        Parameters
        ----------
        seconds : int
            Second (0-59) of each five-minute interval.

        Returns
        -------
        bool
            True if scheduling is configured successfully.
        """
        # Delegate scheduling to the everyMinutesAt method with an interval of 5 minutes
        # and the specified second.
        return self.everyMinutesAt(5, seconds)

    def everyTenMinutes(
        self,
    ) -> bool:
        """
        Schedule to run every ten minutes.

        Configures the event to execute at a fixed interval of ten minutes using an
        IntervalTrigger. The scheduling window can be restricted by `start_date` and
        `end_date`. If a random delay (jitter) is set, it is applied to the trigger.

        Returns
        -------
        bool
            Always returns True after configuring the interval trigger.
        """
        # Delegate scheduling to the everyMinutes method with an interval of 10 minutes.
        return self.everyMinutes(10)

    def everyTenMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule to run every ten minutes at a specific second.

        Configures the event to execute at the specified second (0-59) of every
        ten-minute interval. Ignores any previously set random delay (jitter).
        The scheduling window can be restricted by `start_date` and `end_date`.

        Parameters
        ----------
        seconds : int
            The second (0-59) of each ten-minute interval to execute the event.

        Returns
        -------
        bool
            Returns True if scheduling is configured successfully.
        """
        # Delegate scheduling to everyMinutesAt with an interval of 10 minutes and the
        # specified second.
        return self.everyMinutesAt(10, seconds)

    def everyFifteenMinutes(
        self,
    ) -> bool:
        """
        Schedule the task to run every fifteen minutes.

        Set up an interval trigger for execution every fifteen minutes. The schedule
        can be limited by `start_date` and `end_date`. If a random delay (jitter) is
        set, it is applied to the trigger.

        Returns
        -------
        bool
            Always returns True after configuring the interval trigger.
        """
        # Delegate scheduling to the everyMinutes method with an interval of 15 minutes.
        return self.everyMinutes(15)

    def everyFifteenMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule to run every fifteen minutes at a specific second.

        This method sets the event to execute at the given second (0-59) of every
        fifteen-minute interval. The schedule can be limited by `start_date` and
        `end_date`. Random delay (jitter) is not applied to this schedule, since
        it targets an exact second.

        Parameters
        ----------
        seconds : int
            Second (0-59) of each fifteen-minute interval.

        Returns
        -------
        bool
            Returns True if scheduling is configured successfully.
        """
        # Delegate scheduling to everyMinutesAt with an interval of 15 minutes and the
        # specified second.
        return self.everyMinutesAt(15, seconds)

    def everyTwentyMinutes(
        self,
    ) -> bool:
        """
        Schedule to run every twenty minutes.

        This method sets the event to execute at a fixed interval of twenty minutes
        using an IntervalTrigger. The schedule can be limited by `start_date` and
        `end_date`. If a random delay (jitter) is set, it is applied to the trigger.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyMinute`.
        """
        # Delegate scheduling to the everyMinute method with an interval of 20 minutes.
        # This ensures consistent handling of start_date, end_date, and random_delay.
        return self.everyMinutes(20)

    def everyTwentyMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule to run every twenty minutes at a specific second.

        Configures the event to execute at the specified second (0-59) of every
        twenty-minute interval. The schedule can be restricted by `start_date`
        and `end_date`. Random delay (jitter) is not applied to this schedule,
        since it targets an exact second.

        Parameters
        ----------
        seconds : int
            Second (0-59) of each twenty-minute interval.

        Returns
        -------
        bool
            Returns True if scheduling is configured successfully.
        """
        # Delegate scheduling to everyMinutesAt with an interval of 20 minutes and the
        # specified second.
        return self.everyMinutesAt(20, seconds)

    def everyTwentyFiveMinutes(
        self,
    ) -> bool:
        """
        Schedule the task to run every twenty-five minutes.

        Configures the event to execute at a fixed interval of twenty-five minutes
        using an IntervalTrigger. The scheduling window can be restricted by
        `start_date` and `end_date`. If a random delay (jitter) is set, it is
        applied to the trigger.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyMinute`.
        """
        # Delegate scheduling to the everyMinute method with an interval of 25 minutes.
        # This ensures consistent handling of start_date, end_date, and random_delay.
        return self.everyMinutes(25)

    def everyTwentyFiveMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule to run every twenty-five minutes at a specific second.

        Set up the event to execute at the given second (0-59) of every twenty-five-
        minute interval. The schedule can be limited by `start_date` and `end_date`.

        Parameters
        ----------
        seconds : int
            Second (0-59) of each twenty-five-minute interval.

        Returns
        -------
        bool
            Returns True if scheduling is configured successfully.
        """
        # Delegate scheduling to everyMinutesAt with an interval of 25 minutes and the
        # specified second.
        return self.everyMinutesAt(25, seconds)

    def everyThirtyMinutes(
        self,
    ) -> bool:
        """
        Schedule the task to run every thirty minutes.

        Configures the event to execute at a fixed interval of thirty minutes using an
        IntervalTrigger. The schedule can be restricted by `start_date` and `end_date`.
        If a random delay (jitter) is set, it is applied to the trigger.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyMinute`.
        """
        # Delegate scheduling to the everyMinute method with an interval of 30 minutes.
        # This ensures consistent handling of start_date, end_date, and random_delay.
        return self.everyMinutes(30)

    def everyThirtyMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule to run every thirty minutes at a specific second.

        Configures the event to execute at the given second (0-59) of every
        thirty-minute interval.
        The schedule can be restricted by `start_date` and `end_date`. Random
        delay (jitter) is not applied to this schedule, since it targets an
        exact second.

        Parameters
        ----------
        seconds : int
            Second of each thirty-minute interval to execute the event.

        Returns
        -------
        bool
            Returns True if scheduling is configured successfully.
        """
        # Delegate scheduling to everyMinutesAt with an interval of 30 minutes and the
        # specified second.
        return self.everyMinutesAt(30, seconds)

    def everyThirtyFiveMinutes(
        self,
    ) -> bool:
        """
        Schedule to run every thirty-five minutes.

        This method sets the event to execute at a fixed interval of thirty-five minutes
        using an `IntervalTrigger`. The schedule can be limited by `start_date` and
        `end_date`. If a random delay (jitter) is set, it is applied to the trigger.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyMinute`.
        """
        # Delegate scheduling to the everyMinute method with an interval of 35 minutes.
        # This ensures consistent handling of start_date, end_date, and random_delay.
        return self.everyMinutes(35)

    def everyThirtyFiveMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule to run every 35 minutes at a specific second.

        Parameters
        ----------
        seconds : int
            Second (0-59) of each 35-minute interval to execute the event.

        Returns
        -------
        bool
            Return True if scheduling is configured successfully.

        Raises
        ------
        ValueError
            If `seconds` is not an integer between 0 and 59 (inclusive).

        Notes
        -----
        The event is triggered at the specified second of every 35-minute interval.
        """
        # Delegate scheduling to everyMinutesAt with an interval of 35 minutes and the
        # specified second.
        return self.everyMinutesAt(35, seconds)

    def everyFortyMinutes(
        self,
    ) -> bool:
        """
        Schedule the task to run every forty minutes.

        Configures the event to execute at a fixed interval of forty minutes using an
        IntervalTrigger. The schedule can be restricted by `start_date` and `end_date`.
        If a random delay (jitter) is set, it is applied to the trigger.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyMinute`.
        """
        # Delegate scheduling to the everyMinute method with an interval of 40 minutes.
        # This ensures consistent handling of start_date, end_date, and random_delay.
        return self.everyMinutes(40)

    def everyFortyMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule to run every forty minutes at a specific second.

        Configures the event to execute at the specified second (0-59) of every
        forty-minute interval. The scheduling window can be restricted by `start_date`
        and `end_date`. Random delay (jitter) is not applied to this schedule,
        since it targets an exact second.

        Parameters
        ----------
        seconds : int
            The specific second (0-59) of each forty-minute interval.

        Returns
        -------
        bool
            Returns True if scheduling is configured successfully.
        """
        # Delegate scheduling to the everyMinutesAt method with an interval
        # of 40 minutes and the specified second.
        return self.everyMinutesAt(40, seconds)

    def everyFortyFiveMinutes(
        self,
    ) -> bool:
        """
        Schedule the task to run every forty-five minutes.

        Configure the event to execute at a fixed interval of forty-five minutes using
        an IntervalTrigger. The schedule can be restricted by `start_date` and
        `end_date`. If a random delay (jitter) is set, it is applied to the trigger.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyMinute`.
        """
        # Delegate scheduling to the everyMinute method with an interval of 45 minutes.
        # This ensures consistent handling of start_date, end_date, and random_delay.
        return self.everyMinutes(45)

    def everyFortyFiveMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule the task to run every forty-five minutes at a specific second.

        Set up the event to execute at the given second (0-59) of every forty-five-
        minute interval. The schedule can be limited by `start_date` and `end_date`.
        Random delay (jitter) is not applied to this schedule, since it targets
        an exact second.

        Parameters
        ----------
        seconds : int
            The second (0-59) of each forty-five-minute interval to execute the event.

        Returns
        -------
        bool
            Returns True if the scheduling is configured successfully.
        """
        # Delegate scheduling to the everyMinutesAt method with an interval
        # of 45 minutes and the specified second.
        # This ensures consistent handling of start_date,
        # end_date, and random_delay (jitter).
        return self.everyMinutesAt(45, seconds)

    def everyFiftyMinutes(
        self,
    ) -> bool:
        """
        Schedule to run every fifty minutes.

        Configures the event to execute at a fixed interval of fifty minutes using an
        IntervalTrigger. The schedule can be restricted by `start_date` and `end_date`.
        If a random delay (jitter) is set, it is applied to the trigger.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyMinute`.
        """
        # Delegate scheduling to the everyMinute method with an interval of 50 minutes.
        # This ensures consistent handling of start_date, end_date, and random_delay.
        return self.everyMinutes(50)

    def everyFiftyMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule to run every fifty minutes at a specific second.

        Configures the event to execute at the specified second (0-59) of every
        fifty-minute interval. The scheduling window can be restricted by `start_date`
        and `end_date`. Random delay (jitter) is not applied to this schedule,
        since it targets an exact second.

        Parameters
        ----------
        seconds : int
            Specific second (0-59) of each fifty-minute interval.

        Returns
        -------
        bool
            Returns True if scheduling is configured successfully.
        """
        # Delegate scheduling to everyMinutesAt with an interval of 50 minutes and the
        # specified second. This ensures consistent handling of start_date, end_date,
        # and random_delay (jitter).
        return self.everyMinutesAt(50, seconds)

    def everyFiftyFiveMinutes(
        self,
    ) -> bool:
        """
        Schedule the task to run every fifty-five minutes.

        Configure the event to execute at a fixed interval of fifty-five minutes using
        an IntervalTrigger. The schedule can be restricted by `start_date` and
        `end_date`. If a random delay (jitter) is set, it is applied to the trigger.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyMinute`.
        """
        # Delegate scheduling to the everyMinute method with an interval of 55 minutes.
        # This ensures consistent handling of start_date, end_date, and random_delay.
        return self.everyMinutes(55)

    def everyFiftyFiveMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule the task to run every fifty-five minutes at a specific second.

        Parameters
        ----------
        seconds : int
            The specific second (0-59) of each fifty-five-minute interval at which the
            event should be executed.

        Returns
        -------
        bool
            Return True if the scheduling was successfully configured.

        Notes
        -----
        This method delegates scheduling to `everyMinutesAt` with an interval of
        55 minutes and the specified second.
        """
        # Delegate scheduling to the everyMinutesAt method with an
        # interval of 55 minutes and the specified second.
        return self.everyMinutesAt(55, seconds)

    def hourly(
        self,
    ) -> bool:
        """
        Schedule the task to run every hour.

        Configure the event to execute once every hour. The schedule starts from
        `start_date` and ends at `end_date` if set. If a random delay (jitter) is
        configured, it is applied to the trigger. The event is triggered at regular
        hourly intervals.

        Returns
        -------
        bool
            Always returns True after configuring the interval trigger.
        """
        # Configure the trigger to execute the event every hour.
        self.__trigger = IntervalTrigger(
            hours=1,
            start_date=self.__start_date,
            end_date=self.__end_date,
            jitter=self.__random_delay,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule.
        self.__details = "Every hour"

        # Indicate that the scheduling was successfully configured.
        return True

    def hourlyAt(
        self,
        minute: int,
        second: int = 0,
    ) -> bool:
        """
        Schedule the task to run every hour at a specific minute and second.

        Validate that `minute` and `second` are integers within valid ranges. Set up
        an IntervalTrigger to execute the event every hour at the specified minute and
        second. Store a human-readable description of the schedule.

        Parameters
        ----------
        minute : int
            Minute of the hour in the range [0, 59].
        second : int, optional
            Second of the minute in the range [0, 59]. Default is 0.

        Returns
        -------
        bool
            True if the scheduling was successfully configured.

        Raises
        ------
        ValueError
            If `minute` or `second` are not integers in valid ranges.
        """
        # Validate that minute and second are integers.
        if not isinstance(minute, int) or not isinstance(second, int):
            error_msg = "Minute and second must be integers."
            raise TypeError(error_msg)

        # Validate that minute is within the range [0, 59].
        if not (0 <= minute < 60):
            error_msg = self._ERROR_MSG_INVALID_MINUTE
            raise ValueError(error_msg)

        # Validate that second is within the range [0, 59].
        if not (0 <= second < 60):
            error_msg = self._ERROR_MSG_INVALID_SECOND
            raise ValueError(error_msg)

        # Set up the trigger to execute the event every hour at the specified minute
        # and second. CronTrigger is used because IntervalTrigger does not accept
        # minute/second positioning parameters.
        self.__trigger = CronTrigger(
            minute=minute,
            second=second,
            start_date=self.__start_date,
            end_date=self.__end_date,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule for reference or logging.
        self.__details = f"Every hour at {minute:02d}:{second:02d}"

        # Indicate that the scheduling was successfully configured.
        return True

    def everyOddHours(
        self,
    ) -> bool:
        """
        Schedule the task to run at every odd hour of the day.

        Configure the event to execute at every odd-numbered hour using a CronTrigger.
        The schedule can be restricted by `start_date` and `end_date`. If a random delay
        (jitter) is set, it is applied to the trigger.

        Returns
        -------
        bool
            True if the scheduling was successfully configured.
        """
        # Configure the trigger to execute the event at every odd hour (1, 3, ..., 23)
        # using a CronTrigger. The `hour='1-23/2'` specifies odd hours in the range.
        self.__trigger = CronTrigger(
            hour="1-23/2",                # Schedule the task for odd hours.
            start_date=self.__start_date, # Restrict the schedule start if set.
            end_date=self.__end_date,     # Restrict the schedule end if set.
            jitter=self.__random_delay,   # Apply random delay (jitter) if configured.
            timezone=self.__default_tz,   # Use the default timezone for scheduling.
        )

        # Store a human-readable description of the schedule for reference or logging.
        self.__details = "Every odd hour (1, 3, 5, ..., 23)"

        # Indicate that the scheduling was successfully configured.
        return True

    def everyEvenHours(
        self,
    ) -> bool:
        """
        Schedule the task to run at every even hour of the day.

        Configure the event to execute at every even-numbered hour using a CronTrigger.
        The schedule can be restricted by `start_date` and `end_date`. If a random delay
        (jitter) is set, it is applied to the trigger.

        Returns
        -------
        bool
            True if the scheduling was successfully configured.
        """
        # Configure the trigger to execute the event at every even hour (0, 2, ..., 22)
        # using a CronTrigger. The `hour='0-22/2'` specifies even hours in the range.
        self.__trigger = CronTrigger(
            hour="0-22/2",                # Schedule the task for even hours.
            start_date=self.__start_date, # Restrict the schedule start if set.
            end_date=self.__end_date,     # Restrict the schedule end if set.
            jitter=self.__random_delay,   # Apply random delay (jitter) if configured.
            timezone=self.__default_tz,   # Use the default timezone for scheduling.
        )

        # Store a human-readable description of the schedule for reference or logging.
        self.__details = "Every even hour (0, 2, 4, ..., 22)"

        # Indicate that the scheduling was successfully configured.
        return True

    def everyHours(
        self,
        hours: int,
    ) -> bool:
        """
        Schedule the task to run at fixed intervals in hours.

        Validate that `hours` is a positive integer. Set up an IntervalTrigger with the
        specified interval in hours, using any configured start and end dates,
        and random delay (jitter) if set.

        Returns
        -------
        bool
            True if the scheduling was configured successfully.
        """
        # Validate that the `hours` parameter is a positive integer.
        if not isinstance(hours, int) or hours <= 0:

            # Assign error message before raising exception.
            error_msg = self._ERROR_MSG_INVALID_INTERVAL
            raise ValueError(error_msg)

        # Configure the trigger to execute the event at the specified interval.
        # The `start_date` and `end_date` define the optional scheduling window.
        # The `jitter` adds a random delay if configured.
        self.__trigger = IntervalTrigger(
            hours=hours,
            start_date=self.__start_date,
            end_date=self.__end_date,
            jitter=self.__random_delay,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule for reference or logging.
        self.__details = f"Every {hours} hours"

        # Indicate that the scheduling was successfully configured.
        return True

    def everyHoursAt(
        self,
        hours: int,
        minute: int,
        second: int = 0,
    ) -> bool:
        """
        Schedule the task to run every N hours at a specific minute and second.

        Validates input for hours, minute, and second. Sets up an IntervalTrigger
        with the specified interval and time.

        Parameters
        ----------
        hours : int
            Interval in hours. Must be a positive integer.
        minute : int
            Minute of the hour in [0, 59].
        second : int, optional
            Second of the minute in [0, 59]. Default is 0.

        Returns
        -------
        bool
            True if scheduling was configured successfully.

        Raises
        ------
        ValueError
            If any parameter is out of valid range or not an integer.
        """
        # Validate that the `hours` parameter is a positive integer.
        if not isinstance(hours, int) or hours <= 0:

            # Assign error message before raising exception.
            error_msg = self._ERROR_MSG_INVALID_INTERVAL
            raise ValueError(error_msg)

        # Validate that minute and second are integers.
        if not isinstance(minute, int) or not isinstance(second, int):

            # Assign error message before raising exception.
            error_msg = "Minute and second must be integers."
            raise TypeError(error_msg)

        # Validate that minute is within the range [0, 59].
        if not (0 <= minute < 60):

            # Assign error message before raising exception.
            error_msg = self._ERROR_MSG_INVALID_MINUTE
            raise ValueError(error_msg)

        # Validate that second is within the range [0, 59].
        if not (0 <= second < 60):

            # Assign error message before raising exception.
            error_msg = self._ERROR_MSG_INVALID_SECOND
            raise ValueError(error_msg)

        # Configure the trigger to execute the event every N hours at the specified
        # minute and second. CronTrigger is used because IntervalTrigger does not
        # accept minute/second positioning parameters.
        self.__trigger = CronTrigger(
            hour=f"*/{hours}",
            minute=minute,
            second=second,
            start_date=self.__start_date,
            end_date=self.__end_date,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule.
        self.__details = f"Every {hours} hour(s) at {minute:02d}:{second:02d}"

        # Indicate that the scheduling was successfully configured.
        return True

    def everyTwoHours(
        self,
    ) -> bool:
        """
        Schedule the task to run every two hours.

        Use the `everyHours` method with an interval of two hours. The schedule can be
        restricted by `start_date` and `end_date`. If a random delay (jitter) is set,
        it will be applied to the trigger.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyHours`.
        """
        # Delegate scheduling to the everyHours method with an interval of 2 hours.
        return self.everyHours(2)

    def everyTwoHoursAt(
        self,
        minute: int,
        second: int = 0,
    ) -> bool:
        """
        Schedule to run every two hours at a specific minute and second.

        Validate input ranges for minute and second. Delegate scheduling to
        `everyHoursAt` with an interval of two hours and the specified time.

        Parameters
        ----------
        minute : int
            Minute of the hour in range [0, 59].
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            True if scheduling was configured successfully.
        """
        # Delegate scheduling to everyHoursAt with interval of two hours
        # and the specified minute and second.
        return self.everyHoursAt(2, minute, second)

    def everyThreeHours(
        self,
    ) -> bool:
        """
        Schedule the task to run every three hours.

        Use the `everyHours` method with an interval of three hours. The schedule can be
        restricted by `start_date` and `end_date`. If a random delay (jitter) is set, it
        will be applied to the trigger.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyHours`.
        """
        # Delegate scheduling to the everyHours method with an interval of 3 hours.
        return self.everyHours(3)

    def everyThreeHoursAt(
        self,
        minute: int,
        second: int = 0,
    ) -> bool:
        """
        Schedule to run every three hours at a specific minute and second.

        Set up the event to execute every three hours at the given minute and second.
        The schedule can be limited by `start_date` and `end_date`. Jitter is not used.

        Parameters
        ----------
        minute : int
            Minute of the hour in [0, 59].
        second : int, optional
            Second of the minute in [0, 59]. Default is 0.

        Returns
        -------
        bool
            True if scheduling is configured successfully.
        """
        # Delegate scheduling to everyHoursAt with interval of
        # three hours and given time.
        return self.everyHoursAt(3, minute, second)

    def everyFourHours(
        self,
    ) -> bool:
        """
        Schedule the task to run every four hours.

        Use the `everyHours` method with an interval of four hours. The schedule can be
        restricted by `start_date` and `end_date`. If a random delay (jitter) is set, it
        will be applied to the trigger.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyHours`.
        """
        # Delegate scheduling to the everyHours method with an interval of 4 hours.
        return self.everyHours(4)

    def everyFourHoursAt(
        self,
        minute: int,
        second: int = 0,
    ) -> bool:
        """
        Schedule to run every four hours at a specific minute and second.

        Validate input ranges for minute and second. Delegate scheduling to
        `everyHoursAt` with an interval of four hours and the specified time.

        Parameters
        ----------
        minute : int
            Minute of the hour in range [0, 59].
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            Returns True if scheduling was configured successfully.
        """
        # Delegate scheduling to everyHoursAt with interval of four hours
        # and the specified minute and second.
        return self.everyHoursAt(4, minute, second)

    def everyFiveHours(
        self,
    ) -> bool:
        """
        Schedule the task to run every five hours.

        Use the `everyHours` method with an interval of five hours. The schedule can be
        restricted by `start_date` and `end_date`. If a random delay (jitter) is set, it
        will be applied to the trigger.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyHours`.
        """
        # Delegate scheduling to the everyHours method with an interval of 5 hours.
        return self.everyHours(5)

    def everyFiveHoursAt(
        self,
        minute: int,
        second: int = 0,
    ) -> bool:
        """
        Schedule to run every five hours at a specific minute and second.

        Validates input ranges for minute and second. Delegates scheduling to
        `everyHoursAt` with an interval of five hours and the specified time.

        Parameters
        ----------
        minute : int
            Minute of the hour in range [0, 59].
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            Returns True if scheduling was configured successfully.
        """
        # Delegate scheduling to everyHoursAt with interval of five hours
        # and the specified minute and second.
        return self.everyHoursAt(5, minute, second)

    def everySixHours(
        self,
    ) -> bool:
        """
        Schedule to run every six hours.

        Delegates scheduling to `everyHours` with an interval of six hours.
        Returns True if scheduling was configured.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyHours`.
        """
        # Delegate scheduling to the everyHours method with an interval of 6 hours.
        return self.everyHours(6)

    def everySixHoursAt(
        self,
        minute: int,
        second: int = 0,
    ) -> bool:
        """
        Schedule to run every six hours at a specific minute and second.

        Validate input ranges for minute and second. Delegate scheduling to
        `everyHoursAt` with an interval of six hours and the specified time.

        Parameters
        ----------
        minute : int
            Minute of the hour in range [0, 59].
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            Returns True if scheduling was configured successfully.
        """
        # Delegate scheduling to everyHoursAt with interval of six hours
        # and the specified minute and second.
        return self.everyHoursAt(6, minute, second)

    def everySevenHours(
        self,
    ) -> bool:
        """
        Schedule to run every seven hours.

        Use `everyHours` with an interval of seven hours. Restrict schedule with
        `start_date` and `end_date` if set. Apply random delay (jitter) if configured.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyHours`.
        """
        # Delegate scheduling to the everyHours method with an interval of 7 hours.
        return self.everyHours(7)

    def everySevenHoursAt(
        self,
        minute: int,
        second: int = 0,
    ) -> bool:
        """
        Schedule to run every seven hours at a specific minute and second.

        Validate input ranges for minute and second. Delegate scheduling to
        `everyHoursAt` with an interval of seven hours and the specified time.

        Parameters
        ----------
        minute : int
            Minute of the hour in range [0, 59].
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            Returns True if scheduling was configured successfully.
        """
        # Delegate scheduling to everyHoursAt with interval of seven hours
        # and the specified minute and second.
        return self.everyHoursAt(7, minute, second)

    def everyEightHours(
        self,
    ) -> bool:
        """
        Schedule to run every eight hours.

        Delegate scheduling to `everyHours` with an interval of eight hours.
        Return True if scheduling was configured.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyHours`.
        """
        # Delegate scheduling to the everyHours method with an interval of 8 hours.
        return self.everyHours(8)

    def everyEightHoursAt(
        self,
        minute: int,
        second: int = 0,
    ) -> bool:
        """
        Schedule to run every eight hours at a specific minute and second.

        Validate input ranges for minute and second. Delegate scheduling to
        `everyHoursAt` with an interval of eight hours and the specified time.

        Parameters
        ----------
        minute : int
            Minute of the hour in range [0, 59].
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            Returns True if scheduling was configured successfully.
        """
        # Delegate scheduling to everyHoursAt with interval of eight hours
        # and the specified minute and second.
        return self.everyHoursAt(8, minute, second)

    def everyNineHours(
        self,
    ) -> bool:
        """
        Schedule to run every nine hours.

        Delegates scheduling to `everyHours` with an interval of nine hours.
        Returns True if scheduling was configured.

        Returns
        -------
        bool
            True if scheduling was configured.
        """
        # Delegate scheduling to the everyHours method with an interval of 9 hours.
        return self.everyHours(9)

    def everyNineHoursAt(
        self,
        minute: int,
        second: int = 0,
    ) -> bool:
        """
        Schedule to run every nine hours at a specific minute and second.

        Validate input ranges for minute and second. Delegate scheduling to
        `everyHoursAt` with an interval of nine hours and the specified time.

        Parameters
        ----------
        minute : int
            Minute of the hour in range [0, 59].
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            Returns True if scheduling was configured successfully.
        """
        # Delegate scheduling to everyHoursAt with interval of nine hours
        # and the specified minute and second.
        return self.everyHoursAt(9, minute, second)

    def everyTenHours(
        self,
    ) -> bool:
        """
        Schedule to run every ten hours.

        Delegate scheduling to `everyHours` with an interval of ten hours.
        The scheduling window can be restricted by `start_date` and `end_date`.
        Applies random delay (jitter) if configured.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyHours`.
        """
        # Delegate scheduling to the everyHours method with an interval of 10 hours.
        return self.everyHours(10)

    def everyTenHoursAt(
        self,
        minute: int,
        second: int = 0,
    ) -> bool:
        """
        Schedule to run every ten hours at a specific minute and second.

        Validate input ranges for minute and second. Delegate scheduling to
        `everyHoursAt` with an interval of ten hours and the specified time.

        Parameters
        ----------
        minute : int
            Minute of the hour in range [0, 59].
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            Returns True if scheduling was configured successfully.
        """
        # Delegate scheduling to everyHoursAt with interval of ten hours
        # and the specified minute and second.
        return self.everyHoursAt(10, minute, second)

    def everyElevenHours(
        self,
    ) -> bool:
        """
        Schedule to run every eleven hours.

        Delegates scheduling to `everyHours` with an interval of 11 hours.
        Returns True if scheduling was configured.

        Returns
        -------
        bool
            True if scheduling was configured.
        """
        # Delegate scheduling to the everyHours method with an interval of 11 hours.
        return self.everyHours(11)

    def everyElevenHoursAt(
        self,
        minute: int,
        second: int = 0,
    ) -> bool:
        """
        Schedule to run every eleven hours at a specific minute and second.

        Validate input ranges for minute and second. Delegate scheduling to
        `everyHoursAt` with an interval of 11 hours and the specified time.

        Parameters
        ----------
        minute : int
            Minute of the hour in range [0, 59].
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            Returns True if scheduling was configured successfully.
        """
        # Delegate scheduling to everyHoursAt with interval of
        # 11 hours and specified time.
        return self.everyHoursAt(11, minute, second)

    def everyTwelveHours(
        self,
    ) -> bool:
        """
        Schedule to run every twelve hours.

        Delegates scheduling to `everyHours` with an interval of 12 hours.
        The scheduling window can be restricted by `start_date` and `end_date`.
        Applies random delay (jitter) if configured.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyHours`.
        """
        # Delegate scheduling to the everyHours method with an interval of 12 hours.
        return self.everyHours(12)

    def everyTwelveHoursAt(
        self,
        minute: int,
        second: int = 0,
    ) -> bool:
        """
        Schedule to run every twelve hours at a specific minute and second.

        Validate input ranges for minute and second. Delegate scheduling to
        `everyHoursAt` with an interval of 12 hours and the specified time.

        Parameters
        ----------
        minute : int
            Minute of the hour in range [0, 59].
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            Returns True if scheduling was configured successfully.
        """
        # Delegate scheduling to everyHoursAt with interval of
        # 12 hours and specified time.
        return self.everyHoursAt(12, minute, second)

    def daily(
        self,
    ) -> bool:
        """
        Schedule the task to run once per day.

        Configure the event to execute daily at midnight using a CronTrigger.
        Restrict the schedule with `start_date` and `end_date` if set.
        Apply random delay (jitter) if configured.

        Returns
        -------
        bool
            Always returns True after configuring the daily schedule.
        """
        # Set up the trigger to execute the event every day at 00:00:00.
        self.__trigger = CronTrigger(
            hour=0,
            minute=0,
            second=0,
            start_date=self.__start_date,  # Restrict the schedule start if set.
            end_date=self.__end_date,      # Restrict the schedule end if set.
            jitter=self.__random_delay,    # Apply random delay if configured.
            timezone=self.__default_tz,    # Use the default timezone for scheduling.
        )

        # Store a human-readable description of the schedule.
        self.__details = "Every day at 00:00:00"

        # Indicate that the scheduling was successful.
        return True

    def dailyAt(
        self,
        hour: int,
        minute: int = 0,
        second: int = 0,
    ) -> bool:
        """
        Schedule the task to run daily at a specific hour, minute, and second.

        Validate input ranges for hour, minute, and second. Set up a CronTrigger for
        daily execution at the specified time. Store a description of the schedule.

        Parameters
        ----------
        hour : int
            Hour of the day in range [0, 23].
        minute : int, optional
            Minute of the hour in range [0, 59]. Default is 0.
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            True if the scheduling was successfully configured.
        """
        # Validate that hour, minute, and second are integers.
        if (
            not isinstance(hour, int) or
            not isinstance(minute, int) or
            not isinstance(second, int)
        ):
            error_msg = "Hour, minute, and second must be integers."
            raise TypeError(error_msg)

        # Validate that hour is within valid range.
        if not (0 <= hour < 24):
            error_msg = self._ERROR_MSG_INVALID_HOUR
            raise ValueError(error_msg)

        # Validate that minute and second are within valid ranges.
        if not (0 <= minute < 60):
            error_msg = self._ERROR_MSG_INVALID_MINUTE
            raise ValueError(error_msg)
        if not (0 <= second < 60):
            error_msg = self._ERROR_MSG_INVALID_SECOND
            raise ValueError(error_msg)

        # Set up the trigger to execute the event daily at the
        # specified time using CronTrigger.
        self.__trigger = CronTrigger(
            hour=hour,
            minute=minute,
            second=second,
            start_date=self.__start_date,
            end_date=self.__end_date,
            jitter=self.__random_delay,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule.
        self.__details = f"Every day at {hour:02d}:{minute:02d}:{second:02d}"

        # Indicate that the scheduling was successfully configured.
        return True

    def everyDays(
        self,
        days: int,
    ) -> bool:
        """
        Schedule to run at fixed intervals measured in days.

        Validates that `days` is a positive integer. Sets up an IntervalTrigger with
        the specified interval in days, using any configured start and end dates, and
        random delay (jitter) if set.

        Returns
        -------
        bool
            True if scheduling was configured successfully.
        """
        # Validate that the days parameter is a positive integer.
        if not isinstance(days, int) or days <= 0:
            error_msg = self._ERROR_MSG_INVALID_INTERVAL
            raise ValueError(error_msg)

        # Configure the trigger to execute the event at the specified interval,
        # using any previously set start_date, end_date, and random_delay (jitter).
        self.__trigger = IntervalTrigger(
            days=days,
            start_date=self.__start_date,
            end_date=self.__end_date,
            jitter=self.__random_delay,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule.
        self.__details = f"Every {days} days"

        # Indicate that the scheduling was successful.
        return True

    def everyDaysAt(
        self,
        days: int,
        hour: int,
        minute: int = 0,
        second: int = 0,
    ) -> bool:
        """
        Schedule to run every N days at a specific hour, minute, and second.

        Validates input ranges for days, hour, minute, and second. Sets up a CronTrigger
        for the specified interval and time. Returns True if scheduling was configured.

        Parameters
        ----------
        days : int
            Interval in days. Must be a positive integer.
        hour : int
            Hour of the day in range [0, 23].
        minute : int, optional
            Minute of the hour in range [0, 59]. Default is 0.
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            True if scheduling was configured successfully.
        """
        # Validate that the days parameter is a positive integer.
        if not isinstance(days, int) or days <= 0:
            error_msg = "Days must be a positive integer."
            raise ValueError(error_msg)

        # Validate that hour, minute, and second are integers.
        if (
            not isinstance(hour, int)
            or not isinstance(minute, int)
            or not isinstance(second, int)
        ):
            error_msg = "Hour, minute, and second must be integers."
            raise TypeError(error_msg)

        # Validate that hour is within the valid range [0, 23].
        if not (0 <= hour < 24):
            error_msg = self._ERROR_MSG_INVALID_HOUR
            raise ValueError(error_msg)

        # Validate that minute and second are within the valid range [0, 59].
        if not (0 <= minute < 60):
            error_msg = self._ERROR_MSG_INVALID_MINUTE
            raise ValueError(error_msg)
        if not (0 <= second < 60):
            error_msg = self._ERROR_MSG_INVALID_SECOND
            raise ValueError(error_msg)

        # Set up the trigger to execute the event every N days at the specified time.
        self.__trigger = CronTrigger(
            day=f"*/{days}",
            hour=hour,
            minute=minute,
            second=second,
            start_date=self.__start_date,
            end_date=self.__end_date,
            jitter=self.__random_delay,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule.
        self.__details = f"Every {days} days at {hour:02d}:{minute:02d}:{second:02d}"

        # Indicate that the scheduling was successful.
        return True

    def everyTwoDays(
        self,
    ) -> bool:
        """
        Schedule to run every two days.

        Delegates scheduling to `everyDays` with an interval of 2 days.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyDays`.
        """
        # Delegate scheduling to the everyDays method with an interval of 2 days.
        return self.everyDays(2)

    def everyTwoDaysAt(
        self,
        hour: int,
        minute: int = 0,
        second: int = 0,
    ) -> bool:
        """
        Schedule to run every two days at a specific hour, minute, and second.

        Validate input ranges for hour, minute, and second. Delegate scheduling to
        `everyDaysAt` with an interval of 2 days and the specified time.

        Parameters
        ----------
        hour : int
            Hour of the day in range [0, 23].
        minute : int, optional
            Minute of the hour in range [0, 59]. Default is 0.
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            Returns True if scheduling was configured successfully.
        """
        # Delegate scheduling to everyDaysAt with interval of 2 days and specified time.
        return self.everyDaysAt(2, hour, minute, second)

    def everyThreeDays(
        self,
    ) -> bool:
        """
        Schedule to run every three days.

        Delegates scheduling to `everyDays` with an interval of 3 days. Returns True.

        Returns
        -------
        bool
            True if scheduling was configured successfully.
        """
        # Delegate scheduling to the everyDays method with an interval of 3 days.
        return self.everyDays(3)

    def everyThreeDaysAt(
        self,
        hour: int,
        minute: int = 0,
        second: int = 0,
    ) -> bool:
        """
        Schedule to run every three days at a specific hour, minute, and second.

        Validates input ranges for hour, minute, and second. Delegates scheduling to
        `everyDaysAt` with an interval of 3 days and the specified time.

        Parameters
        ----------
        hour : int
            Hour of the day in range [0, 23].
        minute : int, optional
            Minute of the hour in range [0, 59]. Default is 0.
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            Returns True if scheduling was configured successfully.
        """
        # Delegate scheduling to everyDaysAt with interval of 3 days and specified time.
        return self.everyDaysAt(3, hour, minute, second)

    def everyFourDays(
        self,
    ) -> bool:
        """
        Schedule to run every four days.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyDays`.
        """
        # Delegate scheduling to the everyDays method with an interval of 4 days.
        return self.everyDays(4)

    def everyFourDaysAt(
        self,
        hour: int,
        minute: int = 0,
        second: int = 0,
    ) -> bool:
        """
        Schedule to run every four days at a specific hour, minute, and second.

        Parameters
        ----------
        hour : int
            Hour of the day in range [0, 23].
        minute : int, optional
            Minute of the hour in range [0, 59]. Default is 0.
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            Returns True if scheduling was configured successfully.
        """
        # Delegate scheduling to everyDaysAt with interval of 4 days and specified time.
        return self.everyDaysAt(4, hour, minute, second)

    def everyFiveDays(
        self,
    ) -> bool:
        """
        Schedule to run every five days.

        Use the `everyDays` method with an interval of five days. The scheduling
        window can be restricted by `start_date` and `end_date`. If a random delay
        (jitter) is configured, it is applied to the trigger.

        Returns
        -------
        bool
            Always returns True after delegating scheduling to `everyDays`.
        """
        # Delegate scheduling to the everyDays method with an interval of 5 days.
        return self.everyDays(5)

    def everyFiveDaysAt(
        self,
        hour: int,
        minute: int = 0,
        second: int = 0,
    ) -> bool:
        """
        Schedule event to run every five days at a specific hour, minute, and second.

        Validate input ranges for hour, minute, and second. Delegate scheduling to
        `everyDaysAt` with an interval of 5 days and the specified time.

        Parameters
        ----------
        hour : int
            Hour of the day in range [0, 23].
        minute : int, optional
            Minute of the hour in range [0, 59]. Default is 0.
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            Returns True if scheduling was configured successfully.
        """
        # Delegate scheduling to everyDaysAt with interval of 5 days and specified time.
        return self.everyDaysAt(5, hour, minute, second)

    def everySixDays(
        self,
    ) -> bool:
        """
        Schedule the task to run every six days.

        Use the `everyDays` method with an interval of six days. The scheduling window
        can be restricted by `start_date` and `end_date`. If a random delay (jitter) is
        configured, it is applied to the trigger.

        Returns
        -------
        bool
            Returns True if the scheduling was successfully configured.
        """
        # Delegate scheduling to the everyDays method with an interval of 6 days.
        return self.everyDays(6)

    def everySixDaysAt(
        self,
        hour: int,
        minute: int = 0,
        second: int = 0,
    ) -> bool:
        """
        Schedule event to run every six days at a specific hour, minute, and second.

        Validate input ranges for hour, minute, and second. Delegate scheduling to
        `everyDaysAt` with an interval of 6 days and the specified time.

        Parameters
        ----------
        hour : int
            Hour of the day in range [0, 23].
        minute : int, optional
            Minute of the hour in range [0, 59]. Default is 0.
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            Returns True if scheduling was configured successfully.
        """
        # Delegate scheduling to everyDaysAt with interval of 6 days and specified time.
        return self.everyDaysAt(6, hour, minute, second)

    def everySevenDays(
        self,
    ) -> bool:
        """
        Schedule the task to run every seven days.

        Use the `everyDays` method with an interval of seven days. The scheduling
        window can be restricted by `start_date` and `end_date`. If a random delay
        (jitter) is configured, it is applied to the trigger.

        Returns
        -------
        bool
            True if the scheduling was successfully configured.
        """
        # Delegate scheduling to the everyDays method with an interval of 7 days.
        return self.everyDays(7)

    def everySevenDaysAt(
        self,
        hour: int,
        minute: int = 0,
        second: int = 0,
    ) -> bool:
        """
        Schedule event to run every seven days at a specific hour, minute, and second.

        Validate input ranges for hour, minute, and second. Delegate scheduling to
        `everyDaysAt` with an interval of 7 days and the specified time.

        Parameters
        ----------
        hour : int
            Hour of the day in range [0, 23].
        minute : int, optional
            Minute of the hour in range [0, 59]. Default is 0.
        second : int, optional
            Second of the minute in range [0, 59]. Default is 0.

        Returns
        -------
        bool
            True if scheduling was configured successfully.
        """
        # Delegate scheduling to everyDaysAt with interval of 7 days and specified time.
        return self.everyDaysAt(7, hour, minute, second)

    def everyMondayAt(
        self,
        hour: int,
        minute: int = 0,
        second: int = 0,
    ) -> bool:
        """
        Schedule event to run every Monday at a specific hour, minute, and second.

        Validates input ranges for hour, minute, and second. Sets up a CronTrigger for
        Mondays at the specified time. Stores a description of the schedule.

        Returns
        -------
        bool
            Returns True if the scheduling was successfully configured.

        Raises
        ------
        ValueError
            If `hour`, `minute`, or `second` are not integers within their valid ranges.
        """
        # Validate that the hour is within the valid range [0, 23].
        if not (0 <= hour < 24):
            error_msg = self._ERROR_MSG_INVALID_HOUR
            raise ValueError(error_msg)

        # Validate that the minute is within the valid range [0, 59].
        if not (0 <= minute < 60):
            error_msg = self._ERROR_MSG_INVALID_MINUTE
            raise ValueError(error_msg)

        # Validate that the second is within the valid range [0, 59].
        if not (0 <= second < 60):
            error_msg = self._ERROR_MSG_INVALID_SECOND
            raise ValueError(error_msg)

        # Configure the trigger to execute the event every Monday at the specified time.
        self.__trigger = CronTrigger(
            day_of_week="mon",
            hour=hour,
            minute=minute,
            second=second,
            start_date=self.__start_date,
            end_date=self.__end_date,
            jitter=self.__random_delay,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule.
        self.__details = f"Every Monday at {hour:02d}:{minute:02d}:{second:02d}"

        # Indicate that the scheduling was successfully configured.
        return True

    def everyTuesdayAt(
        self,
        hour: int,
        minute: int = 0,
        second: int = 0,
    ) -> bool:
        """
        Schedule event to run every Tuesday at a specific hour, minute, and second.

        Validates input ranges for hour, minute, and second. Sets up a CronTrigger for
        Tuesdays at the specified time. Stores a description of the schedule.

        Parameters
        ----------
        hour : int
            Hour of the day (0-23).
        minute : int, optional
            Minute of the hour (0-59). Default is 0.
        second : int, optional
            Second of the minute (0-59). Default is 0.

        Returns
        -------
        bool
            True if the scheduling was successfully configured.
        """
        # Validate that the hour is within the valid range [0, 23].
        if not (0 <= hour < 24):
            error_msg = self._ERROR_MSG_INVALID_HOUR
            raise ValueError(error_msg)

        # Validate that the minute is within the valid range [0, 59].
        if not (0 <= minute < 60):
            error_msg = self._ERROR_MSG_INVALID_MINUTE
            raise ValueError(error_msg)

        # Validate that the second is within the valid range [0, 59].
        if not (0 <= second < 60):
            error_msg = self._ERROR_MSG_INVALID_SECOND
            raise ValueError(error_msg)

        # Configure the trigger to execute the event every
        # Tuesday at the specified time.
        self.__trigger = CronTrigger(
            day_of_week="tue",
            hour=hour,
            minute=minute,
            second=second,
            start_date=self.__start_date,
            end_date=self.__end_date,
            jitter=self.__random_delay,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule.
        self.__details = f"Every Tuesday at {hour:02d}:{minute:02d}:{second:02d}"

        # Indicate that the scheduling was successfully configured.
        return True

    def everyWednesdayAt(
        self,
        hour: int,
        minute: int = 0,
        second: int = 0,
    ) -> bool:
        """
        Schedule event to run every Wednesday at a specific hour, minute, and second.

        Validates input ranges for hour, minute, and second. Sets up a CronTrigger for
        Wednesdays at the specified time. Stores a description of the schedule.

        Parameters
        ----------
        hour : int
            Hour of the day (0-23).
        minute : int, optional
            Minute of the hour (0-59). Default is 0.
        second : int, optional
            Second of the minute (0-59). Default is 0.

        Returns
        -------
        bool
            True if the scheduling was successfully configured.
        """
        # Validate that the hour is within the valid range [0, 23].
        if not (0 <= hour < 24):
            error_msg = self._ERROR_MSG_INVALID_HOUR
            raise ValueError(error_msg)

        # Validate that the minute is within the valid range [0, 59].
        if not (0 <= minute < 60):
            error_msg = self._ERROR_MSG_INVALID_MINUTE
            raise ValueError(error_msg)

        # Validate that the second is within the valid range [0, 59].
        if not (0 <= second < 60):
            error_msg = self._ERROR_MSG_INVALID_SECOND
            raise ValueError(error_msg)

        # Configure the trigger to execute the event every
        # Wednesday at the specified time.
        self.__trigger = CronTrigger(
            day_of_week="wed",
            hour=hour,
            minute=minute,
            second=second,
            start_date=self.__start_date,
            end_date=self.__end_date,
            jitter=self.__random_delay,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule.
        self.__details = f"Every Wednesday at {hour:02d}:{minute:02d}:{second:02d}"

        # Indicate that the scheduling was successfully configured.
        return True

    def everyThursdayAt(
        self,
        hour: int,
        minute: int = 0,
        second: int = 0,
    ) -> bool:
        """
        Schedule event to run every Thursday at a specific hour, minute, and second.

        Validates input ranges for hour, minute, and second. Sets up a CronTrigger for
        Thursdays at the specified time. Stores a description of the schedule.

        Parameters
        ----------
        hour : int
            Hour of the day (0-23).
        minute : int, optional
            Minute of the hour (0-59). Default is 0.
        second : int, optional
            Second of the minute (0-59). Default is 0.

        Returns
        -------
        bool
            True if the scheduling was successfully configured.
        """
        # Validate that the hour is within the valid range [0, 23].
        if not (0 <= hour < 24):
            error_msg = self._ERROR_MSG_INVALID_HOUR
            raise ValueError(error_msg)

        # Validate that the minute is within the valid range [0, 59].
        if not (0 <= minute < 60):
            error_msg = self._ERROR_MSG_INVALID_MINUTE
            raise ValueError(error_msg)

        # Validate that the second is within the valid range [0, 59].
        if not (0 <= second < 60):
            error_msg = self._ERROR_MSG_INVALID_SECOND
            raise ValueError(error_msg)

        # Configure the trigger to execute the event every
        # Thursday at the specified time.
        self.__trigger = CronTrigger(
            day_of_week="thu",
            hour=hour,
            minute=minute,
            second=second,
            start_date=self.__start_date,
            end_date=self.__end_date,
            jitter=self.__random_delay,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule.
        self.__details = f"Every Thursday at {hour:02d}:{minute:02d}:{second:02d}"

        # Indicate that the scheduling was successfully configured.
        return True

    def everyFridayAt(
        self,
        hour: int,
        minute: int = 0,
        second: int = 0,
    ) -> bool:
        """
        Schedule the task to run every Friday at a specific hour, minute, and second.

        Validates input ranges for hour, minute, and second. Sets up a CronTrigger for
        Fridays at the specified time. Stores a description of the schedule.

        Parameters
        ----------
        hour : int
            Hour of the day (0-23).
        minute : int, optional
            Minute of the hour (0-59). Default is 0.
        second : int, optional
            Second of the minute (0-59). Default is 0.

        Returns
        -------
        bool
            True if the scheduling was successfully configured.
        """
        # Validate that the hour is within the valid range [0, 23].
        if not (0 <= hour < 24):
            error_msg = self._ERROR_MSG_INVALID_HOUR
            raise ValueError(error_msg)

        # Validate that the minute is within the valid range [0, 59].
        if not (0 <= minute < 60):
            error_msg = self._ERROR_MSG_INVALID_MINUTE
            raise ValueError(error_msg)

        # Validate that the second is within the valid range [0, 59].
        if not (0 <= second < 60):
            error_msg = self._ERROR_MSG_INVALID_SECOND
            raise ValueError(error_msg)

        # Configure the trigger to execute the event every Friday at the specified time.
        self.__trigger = CronTrigger(
            day_of_week="fri",
            hour=hour,
            minute=minute,
            second=second,
            start_date=self.__start_date,
            end_date=self.__end_date,
            jitter=self.__random_delay,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule.
        self.__details = f"Every Friday at {hour:02d}:{minute:02d}:{second:02d}"

        # Indicate that the scheduling was successfully configured.
        return True

    def everySaturdayAt(
        self,
        hour: int,
        minute: int = 0,
        second: int = 0,
    ) -> bool:
        """
        Schedule the task to run every Saturday at a specific hour, minute, and second.

        Validate the input ranges for hour, minute, and second. Set up a CronTrigger for
        Saturdays at the specified time. Store a description of the schedule.

        Parameters
        ----------
        hour : int
            Hour of the day (0-23).
        minute : int, optional
            Minute of the hour (0-59). Default is 0.
        second : int, optional
            Second of the minute (0-59). Default is 0.

        Returns
        -------
        bool
            True if the scheduling was successfully configured.
        """
        # Validate that the hour is within the valid range [0, 23].
        if not (0 <= hour < 24):
            error_msg = self._ERROR_MSG_INVALID_HOUR
            raise ValueError(error_msg)

        # Validate that the minute is within the valid range [0, 59].
        if not (0 <= minute < 60):
            error_msg = self._ERROR_MSG_INVALID_MINUTE
            raise ValueError(error_msg)

        # Validate that the second is within the valid range [0, 59].
        if not (0 <= second < 60):
            error_msg = self._ERROR_MSG_INVALID_SECOND
            raise ValueError(error_msg)

        # Configure the trigger to execute the event every Saturday
        # at the specified time.
        self.__trigger = CronTrigger(
            day_of_week="sat",
            hour=hour,
            minute=minute,
            second=second,
            start_date=self.__start_date,
            end_date=self.__end_date,
            jitter=self.__random_delay,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule.
        self.__details = f"Every Saturday at {hour:02d}:{minute:02d}:{second:02d}"

        # Indicate that the scheduling was successfully configured.
        return True

    def everySundayAt(
        self,
        hour: int,
        minute: int = 0,
        second: int = 0,
    ) -> bool:
        """
        Schedule the task to run every Sunday at a specific hour, minute, and second.

        Validate input ranges for hour, minute, and second. Set up a CronTrigger for
        Sundays at the specified time. Store a description of the schedule.

        Parameters
        ----------
        hour : int
            Hour of the day (0-23).
        minute : int, optional
            Minute of the hour (0-59). Default is 0.
        second : int, optional
            Second of the minute (0-59). Default is 0.

        Returns
        -------
        bool
            True if the scheduling was successfully configured.
        """
        # Validate that the hour is within the valid range [0, 23].
        if not (0 <= hour < 24):
            error_msg = self._ERROR_MSG_INVALID_HOUR
            raise ValueError(error_msg)

        # Validate that the minute is within the valid range [0, 59].
        if not (0 <= minute < 60):
            error_msg = self._ERROR_MSG_INVALID_MINUTE
            raise ValueError(error_msg)

        # Validate that the second is within the valid range [0, 59].
        if not (0 <= second < 60):
            error_msg = self._ERROR_MSG_INVALID_SECOND
            raise ValueError(error_msg)

        # Configure the trigger to execute the event every Sunday at the specified time.
        self.__trigger = CronTrigger(
            day_of_week="sun",
            hour=hour,
            minute=minute,
            second=second,
            start_date=self.__start_date,
            end_date=self.__end_date,
            jitter=self.__random_delay,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule.
        self.__details = f"Every Sunday at {hour:02d}:{minute:02d}:{second:02d}"

        # Indicate that the scheduling was successfully configured.
        return True

    def weekly(
        self,
    ) -> bool:
        """
        Schedule the task to run every week.

        Configure the event to execute once per week on Sunday at 00:00:00. The schedule
        can be restricted by `start_date` and `end_date`. If a random delay (jitter) is
        configured, it is applied to the trigger.

        Returns
        -------
        bool
            True if the scheduling was successfully configured.
        """
        # Configure the trigger to execute the event every week on Sunday at 00:00:00.
        self.__trigger = CronTrigger(
            day_of_week="sun",
            hour=0,
            minute=0,
            second=0,
            start_date=self.__start_date,
            end_date=self.__end_date,
            jitter=self.__random_delay,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule for reference or logging.
        self.__details = "Every week on Sunday at 00:00:00"

        # Indicate that the scheduling was successfully configured.
        return True

    def everyWeeks(
        self,
        weeks: int,
    ) -> bool:
        """
        Configure the task to run at fixed intervals measured in weeks.

        Validates that the `weeks` parameter is a positive integer. Sets up an
        IntervalTrigger with the specified interval in weeks. Returns True if
        the scheduling was successfully configured.

        Parameters
        ----------
        weeks : int
            Number of weeks between executions. Must be a positive integer.

        Returns
        -------
        bool
            True if the scheduling was successfully configured.

        Raises
        ------
        ValueError
            If `weeks` is not a positive integer.
        """
        # Validate that the `weeks` parameter is a positive integer.
        if not isinstance(weeks, int) or weeks <= 0:
            error_msg = self._ERROR_MSG_INVALID_INTERVAL
            raise ValueError(error_msg)

        # Configure the trigger to execute the event at the specified interval.
        self.__trigger = IntervalTrigger(
            weeks=weeks,
            start_date=self.__start_date,
            end_date=self.__end_date,
            jitter=self.__random_delay,
            timezone=self.__default_tz,
        )

        # Store a human-readable description of the schedule.
        self.__details = f"Every {weeks} week(s)"

        # Indicate that the scheduling was successfully configured.
        return True

    def every(
        self,
        weeks: int = 0,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
    ) -> bool:
        """
        Configure the task to run at a custom interval.

        Validates that all interval parameters are non-negative integers
        and that at least one is greater than zero.
        Sets up an IntervalTrigger with the specified intervals.

        Parameters
        ----------
        weeks : int, optional
            Number of weeks between executions. Must be non-negative. Default is 0.
        days : int, optional
            Number of days between executions. Must be non-negative. Default is 0.
        hours : int, optional
            Number of hours between executions. Must be non-negative. Default is 0.
        minutes : int, optional
            Number of minutes between executions. Must be non-negative. Default is 0.
        seconds : int, optional
            Number of seconds between executions. Must be non-negative. Default is 0.

        Returns
        -------
        bool
            True if the scheduling was successfully configured.

        Raises
        ------
        ValueError
            If any parameter is not a non-negative integer or if all are zero.
        """
        # Validate that all parameters are integers and non-negative.
        for param_name, param_value in {
            "weeks": weeks,
            "days": days,
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
        }.items():
            if not isinstance(param_value, int) or param_value < 0:
                error_msg = (
                    f"{param_name.capitalize()} must be a non-negative integer."
                )
                raise ValueError(error_msg)

        # Ensure that at least one parameter is greater than zero.
        intervals = [weeks, days, hours, minutes, seconds]
        if all(param == 0 for param in intervals):
            error_msg = (
                "At least one interval parameter must be greater than zero."
            )
            raise ValueError(error_msg)

        # Configure the trigger to execute the event at the specified interval.
        self.__trigger = IntervalTrigger(
            weeks=weeks,
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            start_date=self.__start_date,
            end_date=self.__end_date,
            jitter=self.__random_delay,
            timezone=self.__default_tz,
        )

        # Build a human-readable description of the schedule.
        interval_parts = []
        if weeks > 0:
            interval_parts.append(f"{weeks} week(s)")
        if days > 0:
            interval_parts.append(f"{days} day(s)")
        if hours > 0:
            interval_parts.append(f"{hours} hour(s)")
        if minutes > 0:
            interval_parts.append(f"{minutes} minute(s)")
        if seconds > 0:
            interval_parts.append(f"{seconds} second(s)")
        self.__details = "Every " + ", ".join(interval_parts)

        # Indicate that the scheduling was successfully configured.
        return True

    def cron(
        self,
        year: str | None = None,
        month: str | None = None,
        day: str | None = None,
        week: str | None = None,
        day_of_week: str | None = None,
        hour: str | None = None,
        minute: str | None = None,
        second: str | None = None,
    ) -> bool:
        """
        Configure the task using a CRON-like expression.

        Parameters
        ----------
        year : str or None, optional
            Year field for the cron expression.
        month : str or None, optional
            Month field for the cron expression.
        day : str or None, optional
            Day field for the cron expression.
        week : str or None, optional
            Week field for the cron expression.
        day_of_week : str or None, optional
            Day of week field for the cron expression.
        hour : str or None, optional
            Hour field for the cron expression.
        minute : str or None, optional
            Minute field for the cron expression.
        second : str or None, optional
            Second field for the cron expression.

        Returns
        -------
        bool
            Return True if the cron scheduling was successfully configured.

        Raises
        ------
        ValueError
            If all CRON parameters are None.
        """
        # Validate that at least one CRON field is provided
        fields = [year, month, day, week, day_of_week, hour, minute, second]
        if all(v is None for v in fields):
            error_msg = "Specify at least one CRON field."
            raise ValueError(error_msg)

        # Configure the trigger using the provided CRON fields
        self.__trigger = CronTrigger(
            year=year,
            month=month,
            day=day,
            week=week,
            day_of_week=day_of_week,
            hour=hour,
            minute=minute,
            second=second,
            start_date=self.__start_date,
            end_date=self.__end_date,
            jitter=self.__random_delay,
            timezone=self.__default_tz,
        )

        # Build a human-readable description using all possible arguments
        cron_parts = []
        if year is not None:
            cron_parts.append(f"year={year}")
        if month is not None:
            cron_parts.append(f"month={month}")
        if day is not None:
            cron_parts.append(f"day={day}")
        if week is not None:
            cron_parts.append(f"week={week}")
        if day_of_week is not None:
            cron_parts.append(f"day_of_week={day_of_week}")
        if hour is not None:
            cron_parts.append(f"hour={hour}")
        if minute is not None:
            cron_parts.append(f"minute={minute}")
        if second is not None:
            cron_parts.append(f"second={second}")

        # Create a descriptive string for the cron schedule
        parts_str = ", ".join(cron_parts) if cron_parts else "Custom CRON schedule"
        self.__details = f"Cron schedule: {parts_str}"

        # Return True to indicate successful configuration
        return True
