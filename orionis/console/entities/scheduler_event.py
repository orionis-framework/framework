from __future__ import annotations
from dataclasses import dataclass, field
from orionis.console.enums.events import SchedulerEvent as SchedulerEventEnum
from orionis.support.entities.base import BaseEntity

@dataclass(kw_only=True)
class SchedulerEvent(BaseEntity):
    """
    Represent a scheduler event entity.

    Parameters
    ----------
    code : int
        Unique identifier code for the scheduler event.
    description : str, optional
        Description of the scheduler event. Defaults to an empty string.
    jobstore : str, optional
        Storage backend for the scheduler job. Defaults to "memory".
    """

    code: int
    description: str = field(default="")
    jobstore: str = field(default="memory")

    def __post_init__(self) -> None:
        """
        Initialize the SchedulerEvent instance after dataclass construction.

        Maps the event code to a descriptive message and sets the description
        attribute accordingly. Calls the parent class's __post_init__ method.

        Returns
        -------
        None
            This method modifies the instance in place and returns None.
        """
        # Call the parent class's __post_init__ method to ensure proper setup
        super().__post_init__()

        # Map event codes to descriptive messages
        code_to_message = {
            SchedulerEventEnum.STARTED: "Scheduler started.",
            SchedulerEventEnum.SHUTDOWN: "Scheduler shutdown.",
            SchedulerEventEnum.RESUMED: "Scheduler resumed.",
            SchedulerEventEnum.PAUSED: "Scheduler paused.",
        }

        # Set the description attribute for the event
        description = code_to_message.get(self.code, "Unknown Task Event.")
        object.__setattr__(self, "description", description)
