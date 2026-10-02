from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.foundation.config.database.entities.connections import Connections
    from orionis.foundation.config.database.entities.database import Database
    from orionis.foundation.config.database.entities.mysql import MySQL
    from orionis.foundation.config.database.entities.oracle import Oracle
    from orionis.foundation.config.database.entities.pgsql import PGSQL
    from orionis.foundation.config.database.entities.sqlite import SQLite
    from orionis.foundation.config.database.entities.sqlserver import SQLServer
    from orionis.foundation.config.database.enums.connection_name import ConnectionName
    from orionis.foundation.config.database.enums.mysql_charsets import MySQLCharset
    from orionis.foundation.config.database.enums.mysql_collations import MySQLCollation
    from orionis.foundation.config.database.enums.mysql_engine import MySQLEngine
    from orionis.foundation.config.database.enums.oracle_encoding import OracleEncoding
    from orionis.foundation.config.database.enums.oracle_nencoding import (
        OracleNencoding,
    )
    from orionis.foundation.config.database.enums.pgsql_charsets import PGSQLCharset
    from orionis.foundation.config.database.enums.pgsql_collations import PGSQLCollation
    from orionis.foundation.config.database.enums.pgsql_mode import PGSQLSSLMode
    from orionis.foundation.config.database.enums.sqlite_foreign_key import (
        SQLiteForeignKey,
    )
    from orionis.foundation.config.database.enums.sqlite_journal import (
        SQLiteJournalMode,
    )
    from orionis.foundation.config.database.enums.sqlite_synchronous import (
        SQLiteSynchronous,
    )
    from orionis.foundation.config.database.enums.sqlserver_charset import (
        SQLServerCharset,
    )

__all__ = [
    "PGSQL",
    "ConnectionName",
    "Connections",
    "Database",
    "MySQL",
    "MySQLCharset",
    "MySQLCollation",
    "MySQLEngine",
    "Oracle",
    "OracleEncoding",
    "OracleNencoding",
    "PGSQLCharset",
    "PGSQLCollation",
    "PGSQLSSLMode",
    "SQLServer",
    "SQLServerCharset",
    "SQLite",
    "SQLiteForeignKey",
    "SQLiteJournalMode",
    "SQLiteSynchronous",
]

_EXPORTS = {
    "ConnectionName": (
        "orionis.foundation.config.database.enums.connection_name", "ConnectionName",
    ),
    "Connections": (
        "orionis.foundation.config.database.entities.connections", "Connections",
    ),
    "Database": ("orionis.foundation.config.database.entities.database", "Database"),
    "MySQL": ("orionis.foundation.config.database.entities.mysql", "MySQL"),
    "MySQLCharset": (
        "orionis.foundation.config.database.enums.mysql_charsets", "MySQLCharset",
    ),
    "MySQLCollation": (
        "orionis.foundation.config.database.enums.mysql_collations", "MySQLCollation",
    ),
    "MySQLEngine": (
        "orionis.foundation.config.database.enums.mysql_engine", "MySQLEngine",
    ),
    "Oracle": ("orionis.foundation.config.database.entities.oracle", "Oracle"),
    "OracleEncoding": (
        "orionis.foundation.config.database.enums.oracle_encoding", "OracleEncoding",
    ),
    "OracleNencoding": (
        "orionis.foundation.config.database.enums.oracle_nencoding", "OracleNencoding",
    ),
    "PGSQL": ("orionis.foundation.config.database.entities.pgsql", "PGSQL"),
    "PGSQLCharset": (
        "orionis.foundation.config.database.enums.pgsql_charsets", "PGSQLCharset",
    ),
    "PGSQLCollation": (
        "orionis.foundation.config.database.enums.pgsql_collations", "PGSQLCollation",
    ),
    "PGSQLSSLMode": (
        "orionis.foundation.config.database.enums.pgsql_mode", "PGSQLSSLMode",
    ),
    "SQLServer": (
        "orionis.foundation.config.database.entities.sqlserver", "SQLServer",
    ),
    "SQLServerCharset": (
        "orionis.foundation.config.database.enums.sqlserver_charset",
        "SQLServerCharset",
    ),
    "SQLite": ("orionis.foundation.config.database.entities.sqlite", "SQLite"),
    "SQLiteForeignKey": (
        "orionis.foundation.config.database.enums.sqlite_foreign_key",
        "SQLiteForeignKey",
    ),
    "SQLiteJournalMode": (
        "orionis.foundation.config.database.enums.sqlite_journal", "SQLiteJournalMode",
    ),
    "SQLiteSynchronous": (
        "orionis.foundation.config.database.enums.sqlite_synchronous",
        "SQLiteSynchronous",
    ),
}

def __getattr__(name: str) -> object:
    """Resolve and cache a public database configuration export.

    Parameters
    ----------
    name : str
        Public attribute requested from this package.

    Returns
    -------
    object
        Exported entity or enum from its defining module.

    Raises
    ------
    AttributeError
        If the requested attribute is not exported.
    """
    return _resolve_export(globals(), _EXPORTS, name)

def __dir__() -> list[str]:
    """List loaded attributes and declared database configuration exports.

    Returns
    -------
    list[str]
        Sorted names without importing the declared entities or enums.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
