from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from orionis.support.entities.base import BaseEntity

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.interval import IntervalTrigger

@dataclass(kw_only=True)
class Task(BaseEntity):
    """
    Represent a scheduled event and configure its execution and timing.

    Parameters
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
    start_date : datetime | None, optional
        Date and time when the event becomes active.
    end_date : datetime | None, optional
        Date and time when the event becomes inactive.
    trigger : CronTrigger | DateTrigger | IntervalTrigger | None, optional
        Trigger mechanism for event execution.
    details : str | None, optional
        Additional metadata about the event.
    max_instances : int, optional
        Maximum concurrent instances allowed. Defaults to 1.
    misfire_grace_time : int | None, optional
        Grace period in seconds for misfired events.
    coalesce : bool, optional
        Whether to coalesce missed runs into a single run. Defaults to True.
    listeners : list[Callable[..., None]], optional
        Listeners for event-specific logic. Defaults to empty list.

    Returns
    -------
    Task
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
    listeners: list[Callable[..., None]] = field(
        default_factory=list,
    )
