from enum import IntEnum

class TaskEvent(IntEnum):
    """
    Define task-related event types for the scheduler.

    Attributes
    ----------
    ADDED : int
        Event type for when a task is added.
    REMOVED : int
        Event type for when a task is removed.
    MODIFIED : int
        Event type for when a task is modified.
    EXECUTED : int
        Event type for when a task is executed.
    ERROR : int
        Event type for when a task encounters an error.
    MISSED : int
        Event type for when a task is missed.
    SUBMITTED : int
        Event type for when a task is submitted.
    MAX_INSTANCES : int
        Event type for when a task reaches max instances.

    Returns
    -------
    None
        This class does not return a value.
    """

    ADDED = 2**9
    REMOVED = 2**10
    MODIFIED = 2**11
    EXECUTED = 2**12
    ERROR = 2**13
    MISSED = 2**14
    SUBMITTED = 2**15
    MAX_INSTANCES = 2**16

class SchedulerEvent(IntEnum):
    """
    Define scheduler-related event types.

    Attributes
    ----------
    STARTED : int
        Event type for when the scheduler starts.
    SHUTDOWN : int
        Event type for when the scheduler shuts down.
    PAUSED : int
        Event type for when the scheduler is paused.
    RESUMED : int
        Event type for when the scheduler resumes.

    Returns
    -------
    None
        This class does not return a value.
    """

    STARTED = 2**0
    SHUTDOWN = 2**1
    PAUSED = 2**2
    RESUMED = 2**3
