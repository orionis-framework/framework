from __future__ import annotations
import re
from typing import TYPE_CHECKING, Any
from sqlalchemy import URL, event
from sqlalchemy.pool import StaticPool
from orionis.database.exceptions import (
    MissingDatabaseDependencyException,
    UnsupportedDriverException,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

# Map of Orionis driver names to SQLAlchemy async dialect names.
_ASYNC_DIALECTS: dict[str, str] = {
    "sqlite": "sqlite+aiosqlite",
    "mysql": "mysql+aiomysql",
    "pgsql": "postgresql+asyncpg",
    "oracle": "oracle+oracledb_async",
    "sqlserver": "mssql+aioodbc",
}

# Map of Orionis driver names to (pip package, install extra) hints.
_ASYNC_DRIVER_PACKAGES: dict[str, tuple[str, str]] = {
    "sqlite": ("aiosqlite", "orionis"),
    "mysql": ("aiomysql", "orionis[mysql]"),
    "pgsql": ("asyncpg", "orionis[pgsql]"),
    "oracle": ("oracledb", "orionis[oracle]"),
    "sqlserver": ("aioodbc", "orionis[sqlserver]"),
}

# Map of Orionis driver names to SQLAlchemy dialects backed by a blocking
# (synchronous) DBAPI driver. Used to build engines for consumers that
# cannot use the async engine, such as APScheduler's scheduleTaskStore.
_SYNC_DIALECTS: dict[str, str] = {
    "sqlite": "sqlite",
    "mysql": "mysql+pymysql",
    "pgsql": "postgresql+psycopg2",
    "oracle": "oracle+oracledb",
    "sqlserver": "mssql+pyodbc",
}

# Map of Orionis driver names to (pip package, install extra) hints for the
# synchronous DBAPI drivers above. SQLite needs nothing extra (stdlib
# sqlite3); Oracle reuses the async package, which also works synchronously.
# The other extras install both the async and sync driver together.
_SYNC_DRIVER_PACKAGES: dict[str, tuple[str, str]] = {
    "sqlite": ("sqlite3", "the Python standard library"),
    "mysql": ("pymysql", "orionis[mysql]"),
    "pgsql": ("psycopg2", "orionis[pgsql]"),
    "oracle": ("oracledb", "orionis[oracle]"),
    "sqlserver": ("pyodbc", "orionis[sqlserver]"),
}

# Default ODBC driver used for SQL Server connections.
_DEFAULT_ODBC_DRIVER: str = "ODBC Driver 18 for SQL Server"

# Charset and collation identifiers accepted in session commands.
_IDENTIFIER_PATTERN: re.Pattern[str] = re.compile(r"^\w+$", re.ASCII)

# MySQL strict sql_mode flags.
_MYSQL_STRICT_MODE: str = (
    "ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,"
    "NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION"
)

# MySQL relaxed sql_mode applied when strict mode is disabled.
_MYSQL_RELAXED_MODE: str = "NO_ENGINE_SUBSTITUTION"

# SQLite database markers that identify an in-memory database.
_SQLITE_MEMORY_MARKERS: frozenset[str] = frozenset({":memory:", ""})

def resolve_driver(config: dict[str, Any]) -> str:
    """
    Extract and validate the driver name from a connection configuration.

    Parameters
    ----------
    config : dict
        Connection configuration containing a ``driver`` key.

    Returns
    -------
    str
        Normalized driver name.

    Raises
    ------
    UnsupportedDriverException
        If the driver is missing or has no registered dialect.
    """
    driver = str(config.get("driver", "")).strip().lower()
    if driver not in _ASYNC_DIALECTS:
        supported = ", ".join(sorted(_ASYNC_DIALECTS))
        error_msg = (
            f"Unsupported database driver '{driver}'. "
            f"Supported drivers: {supported}."
        )
        raise UnsupportedDriverException(error_msg)
    return driver

def missing_dependency_error(
    driver: str,
    cause: ModuleNotFoundError,
    *,
    sync: bool = False,
) -> MissingDatabaseDependencyException:
    """
    Build the exception raised when a DB driver package is absent.

    Parameters
    ----------
    driver : str
        Orionis driver name whose package is missing.
    cause : ModuleNotFoundError
        Original import error raised by the engine.
    sync : bool, optional
        Whether the missing package is the blocking (synchronous) driver
        instead of the default async one.

    Returns
    -------
    MissingDatabaseDependencyException
        Exception with an actionable installation hint.
    """
    packages: dict[str, tuple[str, str]] = (
        _SYNC_DRIVER_PACKAGES if sync else _ASYNC_DRIVER_PACKAGES
    )
    package, extra = packages.get(driver, (driver, "orionis"))
    error_msg = (
        f"The '{driver}' connection requires the '{package}' package "
        f"({cause}). Install it with: pip install {extra}"
    )
    return MissingDatabaseDependencyException(error_msg)

def build_engine_url(
    config: dict[str, Any],
    *,
    sync: bool = False,
) -> URL:
    """
    Build the engine URL for a connection configuration.

    Parameters
    ----------
    config : dict
        Connection configuration produced by the database config entities.
    sync : bool, optional
        Whether to select the blocking DBAPI dialect instead of the async
        one.

    Returns
    -------
    URL
        Engine URL for the configured driver.

    Raises
    ------
    UnsupportedDriverException
        If the driver has no registered dialect.
    """
    driver = resolve_driver(config)
    dialects = _SYNC_DIALECTS if sync else _ASYNC_DIALECTS
    dialect = dialects[driver]
    if driver == "sqlite":
        return _sqlite_url(config, dialect)
    if driver == "oracle":
        return _oracle_url(config, dialect)
    return _server_url(driver, config, dialect)

def engine_options(
    config: dict[str, Any],
    *,
    sync: bool = False,
) -> dict[str, Any]:
    """
    Build keyword options for an engine factory.

    Parameters
    ----------
    config : dict
        Connection configuration.
    sync : bool, optional
        Whether to select the blocking DBAPI driver options instead of
        the async ones.

    Returns
    -------
    dict
        Options such as pool class and driver connect arguments.
    """
    driver = resolve_driver(config)
    options: dict[str, Any] = {"echo": False, "future": True}

    if driver == "sqlite":
        # A shared in-memory database requires a single pooled connection.
        if _is_sqlite_memory(config):
            options["poolclass"] = StaticPool
            options["connect_args"] = {"check_same_thread": False}
        return options

    if not sync and driver == "pgsql":
        connect_args = _pgsql_connect_args(config)
        if connect_args:
            options["connect_args"] = connect_args
        return options

    if driver == "oracle":
        # A full DSN bypasses the host/port URL components entirely.
        dsn = config.get("dsn") or config.get("tns_name")
        if dsn:
            options["connect_args"] = {"dsn": str(dsn)}
        return options

    return options

def _pgsql_connect_args(config: dict[str, Any]) -> dict[str, Any]:
    """
    Build the asyncpg connect arguments for a PostgreSQL connection.

    Maps ``sslmode`` to the driver ``ssl`` argument and forwards the
    configured ``search_path`` and ``charset`` as server settings.

    Parameters
    ----------
    config : dict
        PostgreSQL connection configuration.

    Returns
    -------
    dict
        Driver connect arguments; empty when nothing is configured.
    """
    connect_args: dict[str, Any] = {}

    # asyncpg accepts libpq-style ssl mode strings directly.
    sslmode = _config_text(config, "sslmode")
    if sslmode:
        connect_args["ssl"] = sslmode

    server_settings: dict[str, str] = {}
    search_path = _config_text(config, "search_path")
    if search_path:
        server_settings["search_path"] = search_path
    charset = _config_text(config, "charset")
    if charset:
        server_settings["client_encoding"] = charset
    if server_settings:
        connect_args["server_settings"] = server_settings

    return connect_args

def configure_engine(engine: AsyncEngine, config: dict[str, Any]) -> None:
    """
    Apply driver-specific session settings to a freshly built engine.

    For SQLite this installs a connect hook applying the configured
    PRAGMA settings; for MySQL it applies the connection charset,
    collation, and strict mode on every new pooled connection.

    Parameters
    ----------
    engine : AsyncEngine
        Engine to configure.
    config : dict
        Connection configuration.

    Returns
    -------
    None
        This function does not return a value.
    """
    statements = _session_statements(config)
    if not statements:
        return

    # Register a Core pool event on the underlying sync engine; the async
    # adapters expose a synchronous cursor facade suitable for session setup.
    @event.listens_for(engine.sync_engine, "connect")
    def _apply_session_statements(
        dbapi_connection: object,
        _record: object,
    ) -> None:
        cursor = dbapi_connection.cursor()
        for statement in statements:
            cursor.execute(statement)
        cursor.close()

def _session_statements(config: dict[str, Any]) -> tuple[str, ...]:
    """
    Build the per-connection session statements for a configuration.

    Parameters
    ----------
    config : dict
        Connection configuration.

    Returns
    -------
    tuple of str
        Statements to run on each new pooled connection.
    """
    driver = resolve_driver(config)
    if driver == "sqlite":
        return _sqlite_pragmas(config)
    if driver == "mysql":
        return _mysql_session_commands(config)
    return ()

def _mysql_session_commands(config: dict[str, Any]) -> tuple[str, ...]:
    """
    Build the MySQL session commands for a configuration.

    Applies the connection charset and collation through ``SET NAMES``
    and the strict (or relaxed) ``sql_mode`` preset, mirroring the
    behavior of mainstream frameworks.

    Parameters
    ----------
    config : dict
        MySQL connection configuration.

    Returns
    -------
    tuple of str
        Session commands to run on each new pooled connection.
    """
    commands: list[str] = []

    # Charset and collation are validated as identifiers before being
    # embedded; both originate from trusted configuration entities.
    charset = _config_text(config, "charset")
    if charset and _IDENTIFIER_PATTERN.fullmatch(charset):
        command = f"SET NAMES {charset}"
        collation = _config_text(config, "collation")
        if collation and _IDENTIFIER_PATTERN.fullmatch(collation):
            command += f" COLLATE {collation}"
        commands.append(command)

    strict = config.get("strict")
    if strict is not None:
        mode = _MYSQL_STRICT_MODE if _yes_no(strict) == "yes" else _MYSQL_RELAXED_MODE
        commands.append(f"SET SESSION sql_mode='{mode}'")

    return tuple(commands)

def _sqlite_url(config: dict[str, Any], dialect: str) -> URL:
    """
    Build the engine URL for a SQLite connection.

    The engine URL is always derived from the ``database`` path; the
    informational ``url`` key (sync-style DSN) is intentionally ignored.

    Parameters
    ----------
    config : dict
        SQLite connection configuration.
    dialect : str
        SQLAlchemy dialect name to build the URL for.

    Returns
    -------
    URL
        SQLite engine URL.
    """
    database = str(config.get("database", "") or "")
    if database in _SQLITE_MEMORY_MARKERS:
        database = ":memory:"
    return URL.create(dialect, database=database)

def _config_text(config: dict[str, Any], key: str) -> str | None:
    """
    Extract a trimmed text value from a configuration mapping.

    Parameters
    ----------
    config : dict
        Connection configuration.
    key : str
        Configuration key to read.

    Returns
    -------
    str or None
        Trimmed value, or ``None`` when empty or absent.
    """
    value = str(config.get(key, "") or "").strip()
    return value or None

def _server_url(driver: str, config: dict[str, Any], dialect: str) -> URL:
    """
    Build the engine URL for host-based drivers.

    Covers MySQL, PostgreSQL, and SQL Server connections addressed by
    host, port, and database name.

    Parameters
    ----------
    driver : str
        Normalized driver name.
    config : dict
        Connection configuration.
    dialect : str
        SQLAlchemy dialect name to build the URL for.

    Returns
    -------
    URL
        Engine URL with credentials, host, port, and database.
    """
    return URL.create(
        dialect,
        username=_config_text(config, "username"),
        password=_config_text(config, "password"),
        host=_config_text(config, "host"),
        port=int(config["port"]) if config.get("port") else None,
        database=_config_text(config, "database"),
        query=_server_query(driver, config),
    )

def _server_query(driver: str, config: dict[str, Any]) -> dict[str, str]:
    """
    Build the URL query parameters for host-based drivers.

    Parameters
    ----------
    driver : str
        Normalized driver name.
    config : dict
        Connection configuration.

    Returns
    -------
    dict of str to str
        Query parameters for the engine URL.
    """
    query: dict[str, str] = {}

    if driver == "mysql":
        charset = _config_text(config, "charset")
        if charset:
            query["charset"] = charset
        unix_socket = _config_text(config, "unix_socket")
        if unix_socket:
            query["unix_socket"] = unix_socket

    if driver == "sqlserver":
        query["driver"] = _config_text(config, "odbc_driver") or _DEFAULT_ODBC_DRIVER
        if config.get("encrypt") is not None:
            query["Encrypt"] = _yes_no(config["encrypt"])
        if config.get("trust_server_certificate") is not None:
            query["TrustServerCertificate"] = _yes_no(
                config["trust_server_certificate"],
            )

    return query

def _oracle_url(config: dict[str, Any], dialect: str) -> URL:
    """
    Build the engine URL for an Oracle connection.

    Parameters
    ----------
    config : dict
        Oracle connection configuration.
    dialect : str
        SQLAlchemy dialect name to build the URL for.

    Returns
    -------
    URL
        Oracle engine URL using service name or SID addressing.
    """
    # When a DSN or TNS alias is present, addressing happens via
    # connect_args and the URL only carries the credentials.
    if config.get("dsn") or config.get("tns_name"):
        return URL.create(
            dialect,
            username=_config_text(config, "username"),
            password=_config_text(config, "password"),
        )

    sid = _config_text(config, "sid")
    return URL.create(
        dialect,
        username=_config_text(config, "username"),
        password=_config_text(config, "password"),
        host=_config_text(config, "host"),
        port=int(config["port"]) if config.get("port") else None,
        database=sid,
        query=_oracle_query(config, sid),
    )

def _oracle_query(config: dict[str, Any], sid: str | None) -> dict[str, str]:
    """
    Build the URL query parameters for an Oracle connection.

    Parameters
    ----------
    config : dict
        Oracle connection configuration.
    sid : str or None
        Resolved SID; service-name addressing applies only without it.

    Returns
    -------
    dict of str to str
        Query parameters for the engine URL.
    """
    service_name = _config_text(config, "service_name")
    if service_name and not sid:
        return {"service_name": service_name}
    return {}

def _is_sqlite_memory(config: dict[str, Any]) -> bool:
    """
    Report whether a SQLite configuration targets an in-memory database.

    Parameters
    ----------
    config : dict
        SQLite connection configuration.

    Returns
    -------
    bool
        ``True`` for in-memory databases.
    """
    database = str(config.get("database", "") or "")
    return database in _SQLITE_MEMORY_MARKERS

def _sqlite_pragmas(config: dict[str, Any]) -> tuple[str, ...]:
    """
    Build the PRAGMA statements for a SQLite configuration.

    Parameters
    ----------
    config : dict
        SQLite connection configuration.

    Returns
    -------
    tuple of str
        PRAGMA statements to run on each new connection.
    """
    pragmas: list[str] = []

    foreign_keys = config.get("foreign_key_constraints")
    if foreign_keys is not None:
        state = _normalize_switch(foreign_keys)
        pragmas.append(f"PRAGMA foreign_keys={state}")

    busy_timeout = config.get("busy_timeout")
    if isinstance(busy_timeout, int) and busy_timeout > 0:
        pragmas.append(f"PRAGMA busy_timeout={busy_timeout}")

    journal_mode = _enum_value(config.get("journal_mode"))
    if journal_mode:
        pragmas.append(f"PRAGMA journal_mode={journal_mode}")

    synchronous = _enum_value(config.get("synchronous"))
    if synchronous:
        pragmas.append(f"PRAGMA synchronous={synchronous}")

    return tuple(pragmas)

def _normalize_switch(value: Any) -> str:  # noqa: ANN401
    """
    Normalize a boolean-like configuration value to ``ON`` or ``OFF``.

    Parameters
    ----------
    value : Any
        Boolean, string, or enum member describing the switch state.

    Returns
    -------
    str
        ``"ON"`` or ``"OFF"``.
    """
    raw = _enum_value(value)
    if isinstance(value, bool):
        return "ON" if value else "OFF"
    return "ON" if str(raw).strip().upper() in {"ON", "TRUE", "1"} else "OFF"

def _yes_no(value: Any) -> str:  # noqa: ANN401
    """
    Normalize a boolean-like configuration value to ``yes`` or ``no``.

    Parameters
    ----------
    value : Any
        Boolean, string, or enum member describing the switch state.

    Returns
    -------
    str
        ``"yes"`` or ``"no"``.
    """
    if isinstance(value, bool):
        return "yes" if value else "no"
    raw = str(_enum_value(value)).strip().upper()
    return "yes" if raw in {"YES", "ON", "TRUE", "1"} else "no"

def _enum_value(value: Any) -> str:  # noqa: ANN401
    """
    Extract the primitive value from a possible enum member.

    Parameters
    ----------
    value : Any
        Enum member, string, or ``None``.

    Returns
    -------
    str
        String form of the value; empty when the input is ``None``.
    """
    if value is None:
        return ""
    inner = getattr(value, "value", value)
    return str(inner)
