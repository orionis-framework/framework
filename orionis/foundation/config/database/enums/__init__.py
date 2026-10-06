from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from .connection_name import ConnectionName
    from .mysql_charsets import MySQLCharset
    from .mysql_collations import MySQLCollation
    from .mysql_engine import MySQLEngine
    from .oracle_encoding import OracleEncoding
    from .oracle_nencoding import OracleNencoding
    from .pgsql_charsets import PGSQLCharset
    from .pgsql_collations import PGSQLCollation
    from .pgsql_mode import PGSQLSSLMode
    from .redshift_mode import RedshiftSSLMode
    from .sqlite_foreign_key import SQLiteForeignKey
    from .sqlite_journal import SQLiteJournalMode
    from .sqlite_synchronous import SQLiteSynchronous
    from .sqlserver_charset import SQLServerCharset

__all__ = [
    "ConnectionName",
    "MySQLCharset",
    "MySQLCollation",
    "MySQLEngine",
    "OracleEncoding",
    "OracleNencoding",
    "PGSQLCharset",
    "PGSQLCollation",
    "PGSQLSSLMode",
    "RedshiftSSLMode",
    "SQLServerCharset",
    "SQLiteForeignKey",
    "SQLiteJournalMode",
    "SQLiteSynchronous",
]

_EXPORTS = {
    "ConnectionName": (
        "orionis.foundation.config.database.enums.connection_name", "ConnectionName",
    ),
    "MySQLCharset": (
        "orionis.foundation.config.database.enums.mysql_charsets", "MySQLCharset",
    ),
    "MySQLCollation": (
        "orionis.foundation.config.database.enums.mysql_collations", "MySQLCollation",
    ),
    "MySQLEngine": (
        "orionis.foundation.config.database.enums.mysql_engine", "MySQLEngine",
    ),
    "OracleEncoding": (
        "orionis.foundation.config.database.enums.oracle_encoding", "OracleEncoding",
    ),
    "OracleNencoding": (
        "orionis.foundation.config.database.enums.oracle_nencoding", "OracleNencoding",
    ),
    "PGSQLCharset": (
        "orionis.foundation.config.database.enums.pgsql_charsets", "PGSQLCharset",
    ),
    "PGSQLCollation": (
        "orionis.foundation.config.database.enums.pgsql_collations", "PGSQLCollation",
    ),
    "PGSQLSSLMode": (
        "orionis.foundation.config.database.enums.pgsql_mode", "PGSQLSSLMode",
    ),
    "RedshiftSSLMode": (
        "orionis.foundation.config.database.enums.redshift_mode", "RedshiftSSLMode",
    ),
    "SQLServerCharset": (
        "orionis.foundation.config.database.enums.sqlserver_charset",
        "SQLServerCharset",
    ),
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
    """Resolve and cache a public database enum.

    Parameters
    ----------
    name : str
        Public enum requested from this package.

    Returns
    -------
    object
        Enum class from its defining module.

    Raises
    ------
    AttributeError
        If the requested enum is not exported.
    """
    return _resolve_export(globals(), _EXPORTS, name)

def __dir__() -> list[str]:
    """List loaded attributes and declared enum exports.

    Returns
    -------
    list[str]
        Sorted names without importing unrelated driver catalogs.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
