from enum import Enum

class PGSQLCollation(Enum):
    """
    Enumerate common PostgreSQL collations.

    This enumeration provides a set of commonly used collations in PostgreSQL.
    Collations determine how string comparison is performed in the database.

    Attributes
    ----------
    C : str
        Binary collation, fast, based on byte order.
    POSIX : str
        Similar to 'C', binary order.

    Returns
    -------
    PGSQLCollation
        The enumeration member representing a PostgreSQL collation.
    """

    C = "C"
    POSIX = "POSIX"
