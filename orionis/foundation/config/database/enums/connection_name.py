from enum import StrEnum

class ConnectionName(StrEnum):
    """
    Enumerate the built-in database connection names supported by Orionis.

    Attributes
    ----------
    SQLITE : str
        Represents the SQLite database connection.
    MYSQL : str
        Represents the MySQL database connection.
    PGSQL : str
        Represents the PostgreSQL database connection.
    ORACLE : str
        Represents the Oracle database connection.
    SQLSERVER : str
        Represents the Microsoft SQL Server database connection.

    Returns
    -------
    ConnectionName
        An enumeration member representing a database connection name.
    """

    SQLITE = "sqlite"          # SQLite database connection
    MYSQL = "mysql"            # MySQL database connection
    PGSQL = "pgsql"            # PostgreSQL database connection
    ORACLE = "oracle"          # Oracle database connection
    SQLSERVER = "sqlserver"    # Microsoft SQL Server database connection
