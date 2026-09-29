from enum import Enum

class SQLiteSynchronous(Enum):
    """
    Represent SQLite synchronous settings for transaction durability.

    Attributes
    ----------
    FULL : str
        Provides maximum data integrity and durability, but is the slowest option.
    NORMAL : str
        Offers a balance between data safety and performance.
    EXTRA : str
        Adds a directory sync in DELETE journal mode for extra durability.
    OFF : str
        Maximizes speed, but data may be lost in the event of a crash.

    Returns
    -------
    SQLiteSynchronous
        Enum member representing the synchronous setting.
    """

    FULL = "FULL"      # Greater safety, slower
    NORMAL = "NORMAL"  # Balance between safety and performance
    EXTRA = "EXTRA"  # Extra durability for rollback-journal commits
    OFF = "OFF"        # Greater speed, less safe in case of failures
