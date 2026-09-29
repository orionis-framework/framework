from enum import Enum


class Strategy(Enum):
    """
    Represent different queue strategies supported by the system.

    Attributes
    ----------
    FIFO : str
        First-In, First-Out. Elements are processed in the order they arrive.
    LIFO : str
        Last-In, First-Out. The most recent elements are processed first.
    PRIORITY : str
        Elements are processed according to their assigned priority.

    Returns
    -------
    Strategy
        An enumeration member representing the queue strategy.
    """

    FIFO = "fifo"
    LIFO = "lifo"
    PRIORITY = "priority"
