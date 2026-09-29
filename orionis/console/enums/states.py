from enum import Enum

class ScheduleStates(Enum):
    """
    Represent the possible states of a schedule.

    Attributes
    ----------
    STOPPED : str
        Indicates the schedule is stopped.
    RUNNING : str
        Indicates the schedule is running.
    PAUSED : str
        Indicates the schedule is paused.
    """

    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
