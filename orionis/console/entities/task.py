"""Represent a scheduled event and configure its execution and timing."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypedDict
from orionis.support.entities.base import BaseEntity

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime
    from orionis.console.entities.task_event import TaskEvent as TaskEventEntity
    from orionis.console.enums.events import TaskEvent
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.interval import IntervalTrigger


class ScheduledTaskInfo(TypedDict):
    """Metadata returned by the scheduler for one task."""

    signature: str
    """Command signature registered with the scheduler."""
    args: list[str] | None
    """Positional arguments passed to the scheduled command."""
    kwargs: dict | None
    """Keyword arguments passed to the scheduled command."""
    purpose: str | None
    """Description of the task's purpose."""
    random_delay: int | None
    """Maximum random delay, in seconds, added before execution."""
    coalesce: bool | None
    """Whether multiple missed runs are combined into one execution."""
    max_instances: int | None
    """Maximum number of concurrent runs of this task."""
    misfire_grace_time: int | None
    """Number of seconds a late run remains eligible for execution."""
    start_date: str | None
    """Formatted date and time when the task becomes eligible to run."""
    end_date: str | None
    """Formatted date and time after which the task stops running."""
    details: str | None
    """Human-readable description of the configured schedule."""


@dataclass(kw_only=True)
class Task(BaseEntity):
    """
    Represent a scheduled event and configure its execution and timing.

    Attributes
    ----------
    signature : str
        Unique identifier for the event.
    args : list[str] | None, optional
        Arguments to be passed to the event. Defaults to empty list.
    kwargs : dict | None, optional
        Keyword arguments to be passed to the event. Defaults to empty dict.
    purpose : str | None, optional
        Description of the event's purpose.
    random_delay : int | None, optional
        Random delay in seconds before triggering.
    start_date : datetime.datetime | None, optional
        Date and time when the event becomes active.
    end_date : datetime.datetime | None, optional
        Date and time when the event becomes inactive.
    trigger
        Trigger mechanism for event execution.
    details : str | None, optional
        Additional metadata about the event.
    max_instances : int, optional
        Maximum concurrent instances allowed. Defaults to 1.
    misfire_grace_time : int | None, optional
        Grace period in seconds for misfired events.
    coalesce : bool, optional
        Whether to coalesce missed runs into a single run. Defaults to True.
    listeners : list[collections.abc.Callable[``...``, None]], optional
        Listeners for event-specific logic. Defaults to empty list.

    Returns
    -------
    orionis.console.entities.Task
        Instance of Task with specified configuration.
    """

    # Unique identifier for the event
    signature: str

    # List of arguments for the event, defaults to empty list if not provided
    args: list[str] | None = field(
        default_factory=list,
    )

    # Keyword arguments for the event, defaults to empty dict if not provided
    kwargs: dict | None = field(
        default_factory=dict,
    )

    # Description of the event's purpose
    purpose: str | None = None

    # Optional random delay (in seconds) before the event is triggered
    random_delay: int | None = None

    # Start date and time for the event
    start_date: datetime | None = None

    # End date and time for the event
    end_date: datetime | None = None

    # Trigger mechanism for the event (cron, date, or interval)
    trigger: CronTrigger | DateTrigger | IntervalTrigger | None = None

    # Optional details about the event
    details: str | None = None

    # Maximum number of concurrent instances allowed for the event
    max_instances: int | None = 1

    # Grace time in seconds for misfired events
    misfire_grace_time: int | None = None

    # Whether to coalesce missed runs into a single run
    coalesce: bool | None = True

    # Optional listeners for event-specific logic, not included in equality checks
    listeners: list[tuple[TaskEvent, Callable[[TaskEventEntity], object]]] = field(
        default_factory=list,
    )
