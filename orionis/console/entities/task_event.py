from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from orionis.support.entities.base import BaseEntity
from orionis.console.enums.events import TaskEvent as TaskEventEnum

@dataclass(kw_only=True)
class TaskEvent(BaseEntity):
    """
    Represent a task execution event with scheduling and result information.

    Parameters
    ----------
    code : int
        Event status or result code.
    signature : str
        Task signature identifier.
    jobstore : str, default "memory"
        Storage backend for the job.
    scheduled_run_times : Any | None, default None
        Collection of scheduled execution times.
    scheduled_run_time : Any | None, default None
        Specific scheduled execution time.
    retval : Any | None, default None
        Return value from task execution.
    exception : Any | None, default None
        Exception raised during task execution.
    traceback : Any | None, default None
        Exception traceback information.
    """

    code: int

    description: str = field(
        default="",
    )

    signature: str

    jobstore: str = field(
        default="memory",
    )

    scheduled_run_times: Any | None = field(
        default=None,
    )

    scheduled_run_time: Any | None = field(
        default=None,
    )

    retval: Any | None = field(
        default=None,
    )

    exception: Any | None = field(
        default=None,
    )

    traceback: Any | None = field(
        default=None,
    )

    def __post_init__(self) -> None:
        """
        Initialize the TaskEvent instance after dataclass creation.

        Map the event code to a human-readable message and set it as the description.

        Parameters
        ----------
        self : TaskEvent
            The instance of TaskEvent being initialized.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Call the parent class's __post_init__ method
        super().__post_init__()

        # Map event codes to descriptive messages
        code_to_message = {
            TaskEventEnum.ADDED : "Task Added.",
            TaskEventEnum.REMOVED : "Task Removed.",
            TaskEventEnum.MODIFIED : "Task Modified.",
            TaskEventEnum.EXECUTED : "Task Executed.",
            TaskEventEnum.ERROR : "Task Error.",
            TaskEventEnum.MISSED : "Task Missed.",
            TaskEventEnum.SUBMITTED : "Task Submitted.",
            TaskEventEnum.MAX_INSTANCES : "Task Reached Max Instances.",
        }

        # Set the description attribute for the event
        description = code_to_message.get(self.code, "Unknown Task Event.")
        object.__setattr__(self, "description", description)
