from enum import Enum

class MySQLEngine(Enum):
    """
    Enumerate supported MySQL storage engines.

    This enum is used to specify the storage engine for MySQL database tables.

    Attributes
    ----------
    INNODB : str
        Default transactional storage engine, supports ACID compliance and
        foreign keys.

    Returns
    -------
    MySQLEngine
        An enumeration member representing a MySQL storage engine.
    """

    INNODB = "InnoDB"  # Guaranteed default storage engine.
