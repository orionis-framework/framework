from enum import StrEnum

class Drivers(StrEnum):
    """
    Enumerate supported scheduler job store drivers.

    Attributes
    ----------
    MEMORY : str
        Represents an in-memory job store driver.
    REDIS : str
        Represents a Redis job store driver.
    DATABASE : str
        Represents a database job store driver.

    Returns
    -------
    Drivers
        An enumeration member representing a scheduler job store driver.
    """

    MEMORY = "memory"
    REDIS = "redis"
    DATABASE = "database"
