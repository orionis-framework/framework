from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.database import (
    PGSQL, ConnectionName, Connections, Database, MySQL, MySQLCharset,
    MySQLCollation, MySQLEngine, Oracle, OracleEncoding, OracleNencoding,
    PGSQLCharset, PGSQLSSLMode, SQLite, SQLiteForeignKey, SQLiteJournalMode,
    SQLiteSynchronous, SQLServer, SQLServerCharset,
)

@dataclass(frozen=True, kw_only=True)
class BootstrapDatabase(Database):
    # ----------------------------------------------------------------------------------
    # default : ConnectionName | str, optional
    # --- The default database connection name. Uses the 'DB_CONNECTION' environment
    # --- variable or defaults to 'ConnectionName.SQLITE' if not set.
    # ----------------------------------------------------------------------------------
    default: ConnectionName | str = field(
        default_factory=lambda: Env.get("DB_CONNECTION", ConnectionName.SQLITE),
    )

    # ----------------------------------------------------------------------------------
    # connections : Connections | dict, optional
    # --- Configure each connection's environment keys and fallback values here.
    # --- DB_CHARSET is shared and applies only to the active driver.
    # ----------------------------------------------------------------------------------
    connections: Connections | dict = field(
        default_factory=lambda: Connections(
            # --------------------------------------------------------------------------
            # sqlite : SQLite, optional
            # --- SQLite connection settings. A missing URL is derived from the database
            # --- path.
            # --------------------------------------------------------------------------
            sqlite=SQLite(
                url=Env.get("DB_URL", None),
                database=Env.get("DB_DATABASE", "database/database.sqlite"),
                prefix=Env.get("DB_PREFIX", ""),
                foreign_key_constraints=Env.get( "DB_FOREIGN_KEYS", SQLiteForeignKey.OFF),
                busy_timeout=Env.get("DB_BUSY_TIMEOUT", 5000),
                journal_mode=Env.get("DB_JOURNAL_MODE", SQLiteJournalMode.DELETE),
                synchronous=Env.get("DB_SYNCHRONOUS", SQLiteSynchronous.NORMAL),
            ),
            # --------------------------------------------------------------------------
            # mysql : MySQL, optional
            # --- MySQL connection settings, including socket, charset, and storage
            # --- engine.
            # --------------------------------------------------------------------------
            mysql=MySQL(
                host=Env.get("DB_HOST", "127.0.0.1"),
                port=Env.get("DB_PORT", 3306),
                database=Env.get("DB_DATABASE", "orionis"),
                username=Env.get("DB_USERNAME", "root"),
                password=Env.get("DB_PASSWORD", ""),
                unix_socket=Env.get("DB_SOCKET", ""),
                charset=(
                    Env.get("DB_CHARSET", MySQLCharset.UTF8MB4)
                    if str(Env.get("DB_CONNECTION")).strip().lower() == "mysql"
                    else MySQLCharset.UTF8MB4.value
                ),
                collation=Env.get("DB_COLLATION", MySQLCollation.UTF8MB4_UNICODE_CI),
                prefix=Env.get("DB_PREFIX", ""),
                prefix_indexes=Env.get("DB_PREFIX_INDEXES", True),
                strict=Env.get("DB_STRICT", True),
                engine=Env.get("DB_ENGINE", MySQLEngine.INNODB),
            ),
            # --------------------------------------------------------------------------
            # pgsql : PGSQL, optional
            # --- PostgreSQL connection settings, including search path and SSL mode.
            # --------------------------------------------------------------------------
            pgsql=PGSQL(
                host=Env.get("DB_HOST", "127.0.0.1"),
                port=Env.get("DB_PORT", 5432),
                database=Env.get("DB_DATABASE", "orionis"),
                username=Env.get("DB_USERNAME", "postgres"),
                password=Env.get("DB_PASSWORD", ""),
                charset=(
                    Env.get("DB_CHARSET", PGSQLCharset.UTF8)
                    if str(Env.get("DB_CONNECTION")).strip().lower() == "pgsql"
                    else PGSQLCharset.UTF8
                ),
                prefix=Env.get("DB_PREFIX", ""),
                prefix_indexes=Env.get("DB_PREFIX_INDEXES", True),
                search_path=Env.get("DB_SEARCH_PATH", "public"),
                sslmode=Env.get("DB_SSLMODE", PGSQLSSLMode.PREFER),
            ),
            # --------------------------------------------------------------------------
            # oracle : Oracle, optional
            # --- Oracle connection settings with service name, SID, DSN, or TNS
            # --- options.
            # --------------------------------------------------------------------------
            oracle=Oracle(
                username=Env.get("DB_USERNAME", "sys"),
                password=Env.get("DB_PASSWORD", ""),
                host=Env.get("DB_HOST", "localhost"),
                port=Env.get("DB_PORT", 1521),
                service_name=Env.get("DB_SERVICE_NAME", "ORCL"),
                sid=Env.get("DB_SID", None),
                dsn=Env.get("DB_DSN", None),
                tns_name=Env.get("DB_TNS", None),
                encoding=Env.get("DB_ENCODING", OracleEncoding.AL32UTF8),
                nencoding=Env.get("DB_NENCODING", OracleNencoding.AL16UTF16),
            ),
            # --------------------------------------------------------------------------
            # sqlserver : SQLServer, optional
            # --- SQL Server connection settings, including ODBC and TLS options.
            # --------------------------------------------------------------------------
            sqlserver=SQLServer(
                host=Env.get("DB_HOST", "127.0.0.1"),
                port=Env.get("DB_PORT", 1433),
                database=Env.get("DB_DATABASE", "orionis"),
                username=Env.get("DB_USERNAME", "sa"),
                password=Env.get("DB_PASSWORD", ""),
                charset=(
                    Env.get("DB_CHARSET", SQLServerCharset.UTF8)
                    if str(Env.get("DB_CONNECTION")).strip().lower() == "sqlserver"
                    else SQLServerCharset.UTF8
                ),
                prefix=Env.get("DB_PREFIX", ""),
                prefix_indexes=Env.get("DB_PREFIX_INDEXES", True),
                encrypt=Env.get("DB_ENCRYPT", "yes"),
                trust_server_certificate=Env.get("DB_TRUST_SERVER_CERTIFICATE", True),
                odbc_driver=Env.get("DB_ODBC_DRIVER", "ODBC Driver 18 for SQL Server"),
            ),
        ),
    )
