from enum import Enum

class SQLiteForeignKey(Enum):
    """
    Represent the state of foreign key constraints in SQLite.

    Attributes
    ----------
    ON : str
        Enables foreign key constraint enforcement.
    OFF : str
        Disables foreign key constraint enforcement.

    Returns
    -------
    SQLiteForeignKey
        The enumeration member representing the foreign key state.
    """

    ON = "ON"       # Enables foreign key constraint enforcement
    OFF = "OFF"     # Disables foreign key constraint enforcement
