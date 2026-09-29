from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from orionis.console.base.contracts.listener import IBaseTaskListener
    from orionis.console.entities.task import Task as TaskEntity
    from orionis.console.enums.events import TaskEvent as TaskEventListener

class ITask(ABC):

    @abstractmethod
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
        """

    @abstractmethod
    def coalesce(
        self,
        *,
        coalesce: bool = True,
    ) -> ITask:
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

    @abstractmethod
    def misfireGraceTime(
        self,
        seconds: int = 60,
    ) -> ITask:
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

    @abstractmethod
    def purpose(
        self,
        purpose: str,
    ) -> ITask:
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

    @abstractmethod
    def startDate(
        self,
        year: int,
        month: int,
        day: int,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
    ) -> ITask:
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

    @abstractmethod
    def endDate(
        self,
        year: int,
        month: int,
        day: int,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
    ) -> ITask:
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

    @abstractmethod
    def randomDelay(
        self,
        max_seconds: int = 10,
    ) -> ITask:
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

    @abstractmethod
    def maxInstances(
        self,
        max_instances: int,
    ) -> ITask:
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

    @abstractmethod
    def on(
        self,
        event: TaskEventListener,
        callback: Callable,
    ) -> ITask:
        """
        Register a callback for a specific task event.

        Parameters
        ----------
        event : TaskEventListener
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
            If `event` is not a TaskEventListener or `callback` is not callable.
        """

    @abstractmethod
    def registerListener(
        self,
        listener: IBaseTaskListener,
    ) -> ITask:
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def everyFiveMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule the task to run every five minutes at a specific second.

        Set the event to execute at the specified second (0-59) of every five-minute
        interval. The scheduling window can be restricted by `start_date` and
        `end_date`. If a random delay (jitter) is configured, it will be applied.

        Parameters
        ----------
        seconds : int
            Second (0-59) of each five-minute interval.

        Returns
        -------
        bool
            True if scheduling is configured successfully.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def everyFifteenMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule to run every fifteen minutes at a specific second.

        This method sets the event to execute at the given second (0-59) of every
        fifteen-minute interval. The schedule can be limited by `start_date` and
        `end_date`. If a random delay (jitter) is set, it is applied to the trigger.

        Parameters
        ----------
        seconds : int
            Second (0-59) of each fifteen-minute interval.

        Returns
        -------
        bool
            Returns True if scheduling is configured successfully.
        """

    @abstractmethod
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

    @abstractmethod
    def everyTwentyMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule to run every twenty minutes at a specific second.

        Configures the event to execute at the specified second (0-59) of every
        twenty-minute interval. The schedule can be restricted by `start_date`
        and `end_date`. If a random delay (jitter) is set, it is applied to the
        trigger.

        Parameters
        ----------
        seconds : int
            Second (0-59) of each twenty-minute interval.

        Returns
        -------
        bool
            Returns True if scheduling is configured successfully.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def everyThirtyMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule to run every thirty minutes at a specific second.

        Configures the event to execute at the given second (0-59) of every
        thirty-minute interval. The schedule can be restricted by `start_date`
        and `end_date`. If a random delay (jitter) is set, it is applied to the trigger.

        Parameters
        ----------
        seconds : int
            Second of each thirty-minute interval to execute the event.

        Returns
        -------
        bool
            Returns True if scheduling is configured successfully.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def everyFortyMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule to run every forty minutes at a specific second.

        Configures the event to execute at the specified second (0-59) of every
        forty-minute interval. The scheduling window can be restricted by `start_date`
        and `end_date`. If a random delay (jitter) is set, it is applied to the trigger.

        Parameters
        ----------
        seconds : int
            The specific second (0-59) of each forty-minute interval.

        Returns
        -------
        bool
            Returns True if scheduling is configured successfully.
        """

    @abstractmethod
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

    @abstractmethod
    def everyFortyFiveMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule the task to run every forty-five minutes at a specific second.

        Set up the event to execute at the given second (0-59) of every forty-five-
        minute interval. The schedule can be limited by `start_date` and `end_date`.
        If a random delay (jitter) is set, it is applied to the trigger.

        Parameters
        ----------
        seconds : int
            The second (0-59) of each forty-five-minute interval to execute the event.

        Returns
        -------
        bool
            Returns True if the scheduling is configured successfully.
        """

    @abstractmethod
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

    @abstractmethod
    def everyFiftyMinutesAt(
        self,
        seconds: int,
    ) -> bool:
        """
        Schedule to run every fifty minutes at a specific second.

        Configures the event to execute at the specified second (0-59) of every
        fifty-minute interval. The scheduling window can be restricted by `start_date`
        and `end_date`. If a random delay (jitter) is set, it is applied to the trigger.

        Parameters
        ----------
        seconds : int
            Specific second (0-59) of each fifty-minute interval.

        Returns
        -------
        bool
            Returns True if scheduling is configured successfully.

        Raises
        ------
        ValueError
            If `seconds` is not an integer between 0 and 59 (inclusive).
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

        Raises
        ------
        ValueError
            If `minute` or `second` are not integers in valid ranges.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def everyWeeks(
        self,
        weeks: int,
    ) -> bool:
        """
        Configure the event to run at fixed intervals measured in weeks.

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

    @abstractmethod
    def every(
        self,
        weeks: int = 0,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
    ) -> bool:
        """
        Configure the event to run at a custom interval.

        Validates that all interval parameters are non-negative integers and that
        at least one is greater than zero. Sets up an
        IntervalTrigger with the specified intervals.

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

    # ruff: noqa: PLR0913
    @abstractmethod
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
        Schedule the task using a CRON-like expression.

        This method configures the event to execute according to cron rules,
        allowing highly customizable schedules (e.g., every Monday at 8am).

        Parameters
        ----------
        year, month, day, week, day_of_week, hour, minute, second : str | None
            Cron-like expressions defining when the job should run.
            Examples: "*/5" (every 5 units), "1-5" (range), "0,15,30,45" (list).

        Returns
        -------
        bool
            True if the cron scheduling was successfully configured.
        """
