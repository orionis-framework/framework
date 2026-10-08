from __future__ import annotations
from asyncio import create_task, ensure_future
import re
from typing import TYPE_CHECKING, Any, Protocol
from sqlalchemy import URL, event
from sqlalchemy.dialects import registry
from sqlalchemy.pool import AsyncAdaptedQueuePool, QueuePool
from orionis.database.exceptions import (
    MissingDatabaseDependencyException,
    UnsupportedDriverException,
)
from orionis.database.threaded.worker import _wait_for_completion

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from sqlalchemy.engine import Connection as SqlConnection
    from sqlalchemy.engine.interfaces import Dialect
    from sqlalchemy.exc import NoSuchModuleError
    from sqlalchemy.ext.asyncio import AsyncEngine
    from orionis.database.threaded.engine import ThreadedEngine

# Map of Orionis driver names to SQLAlchemy async dialect names.
_ASYNC_DIALECTS: dict[str, str] = {
    "sqlite": "sqlite+aiosqlite",
    "mysql": "mysql+aiomysql",
    "pgsql": "postgresql+asyncpg",
    "oracle": "oracle+oracledb_async",
    "sqlserver": "mssql+aioodbc",
    "redshift": "redshift+redshift_connector",
}

# Map of Orionis driver names to (driver package, install extra) hints.
_ASYNC_DRIVER_PACKAGES: dict[str, tuple[str, str]] = {
    "sqlite": ("aiosqlite", "orionis"),
    "mysql": ("aiomysql", "orionis[mysql]"),
    "pgsql": ("asyncpg", "orionis[pgsql]"),
    "oracle": ("oracledb", "orionis[oracle]"),
    "sqlserver": ("aioodbc", "orionis[sqlserver]"),
    "redshift": ("redshift_connector", "orionis[redshift]"),
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
    "redshift": "redshift+redshift_connector",
}

# Map of Orionis driver names to (driver package, install extra) hints for the
# synchronous DBAPI drivers above. SQLite needs nothing extra (stdlib
# sqlite3); Oracle reuses the async package, which also works synchronously.
# The other extras install both the async and sync driver together.
_SYNC_DRIVER_PACKAGES: dict[str, tuple[str, str]] = {
    "sqlite": ("sqlite3", "the Python standard library"),
    "mysql": ("pymysql", "orionis[mysql]"),
    "pgsql": ("psycopg2", "orionis[pgsql]"),
    "oracle": ("oracledb", "orionis[oracle]"),
    "sqlserver": ("pyodbc", "orionis[sqlserver]"),
    "redshift": ("redshift_connector", "orionis[redshift]"),
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

_REDSHIFT_CONNECT_OPTIONS: tuple[str, ...] = (
    "ssl", "sslmode", "timeout", "iam", "region", "cluster_identifier",
    "db_user", "profile", "is_serverless", "serverless_work_group",
    "serverless_acct_id",
)

class _MySQLParameterEscaper:
    """Escape binary parameters independently of aiomysql's removed converter."""

    __slots__ = ("_original",)

    def __init__(self, original: Callable[[object], object]) -> None:
        """
        Retain the connection's existing nonbinary parameter conversion.

        Parameters
        ----------
        original : Callable
            Original escape method owned by this connection.

        Returns
        -------
        None
            Initialize a connection-local converter without global mutations.
        """
        self._original = original

    def __call__(self, value: object) -> object:
        """
        Convert binary values to charset-independent MySQL hex literals.

        Parameters
        ----------
        value : object
            One bound DBAPI parameter.

        Returns
        -------
        object
            Binary hex literal or the original nonbinary conversion result.
        """
        if isinstance(value, (bytes, bytearray, memoryview)):
            return "_binary X'" + bytes(value).hex() + "'"
        return self._original(value)


def _configure_mysql_binary_parameters(dbapi_connection: object) -> None:
    """
    Install safe binary conversion on one adapted aiomysql connection.

    PyMySQL 1.2.3 keeps ``escape_bytes_prefixed`` as a noncallable import alias;
    aiomysql 0.3.2 calls that alias for every bytes parameter. Hex literals keep
    binary storage working without downgrading PyMySQL or patching its modules.

    Parameters
    ----------
    dbapi_connection : object
        SQLAlchemy DBAPI adapter exposing its underlying driver connection.

    Returns
    -------
    None
        Replace only this connection's binary escape path when available.
    """
    connection = getattr(dbapi_connection, "driver_connection", None)
    if connection is None:
        return
    original = getattr(connection, "escape", None)
    if callable(original) and not isinstance(original, _MySQLParameterEscaper):
        connection.escape = _MySQLParameterEscaper(original)

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
    cause: ImportError | NoSuchModuleError,
    *,
    sync: bool = False,
) -> MissingDatabaseDependencyException:
    """
    Build the exception raised when a DB driver package is absent.

    Parameters
    ----------
    driver : str
        Orionis driver name whose package is missing.
    cause : ImportError | NoSuchModuleError
        Original missing driver or dialect error raised by the engine.
    sync : bool, optional
        Whether the missing package is the blocking (synchronous) driver
        instead of the default async one.

    Returns
    -------
    MissingDatabaseDependencyException
        Exception with an actionable uv installation hint.
    """
    packages: dict[str, tuple[str, str]] = (
        _SYNC_DRIVER_PACKAGES if sync else _ASYNC_DRIVER_PACKAGES
    )
    package, extra = packages.get(driver, (driver, "orionis"))
    error_msg = (
        f"The '{driver}' connection requires the '{package}' package "
        f"({cause}). Install it with: uv add '{extra}'"
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
    if driver == "redshift":
        registry.register(
            "redshift.redshift_connector", "orionis.database.redshift",
            "RedshiftDialect",
        )
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
    options: dict[str, Any] = {
        "echo": False, "future": True, "hide_parameters": True,
    }

    if driver == "sqlite":
        # In-memory databases retain one connection with exclusive checkout.
        if _is_sqlite_memory(config):
            options["poolclass"] = QueuePool if sync else AsyncAdaptedQueuePool
            options["pool_size"] = 1
            options["max_overflow"] = 0
            options["connect_args"] = {"check_same_thread": False}
        return options

    if driver == "redshift":
        connect_args = {"ssl": True, "sslmode": "verify-full", "timeout": 30}
        connect_args.update({
            name: config[name] for name in _REDSHIFT_CONNECT_OPTIONS if name in config
        })
        connect_args["sslmode"] = _enum_value(connect_args["sslmode"])
        options["connect_args"] = connect_args
        return options

    if driver == "pgsql":
        connect_args = _pgsql_connect_args(config, sync=sync)
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

def _pgsql_connect_args( # NOSONAR
    config: dict[str, Any], *, sync: bool = False,
) -> dict[str, Any]:
    """
    Build asyncpg or libpq connect arguments for PostgreSQL.

    Maps ``sslmode`` to the driver ``ssl`` argument and forwards the
    configured ``search_path`` and ``charset`` as server settings.

    Parameters
    ----------
    config : dict
        PostgreSQL connection configuration.
    sync : bool, optional
        Whether to build the blocking libpq options instead of asyncpg settings.

    Returns
    -------
    dict
        Driver connect arguments; empty when nothing is configured.
    """
    connect_args: dict[str, Any] = {}
    if sync:
        for key, source in (("sslmode", "sslmode"), ("client_encoding", "charset")):
            value = _config_text(config, source)
            if value:
                connect_args[key] = value
        search_path = _config_text(config, "search_path")
        if search_path:
            escaped = "".join(
                "\\" + character if character == "\\" or character.isspace()
                else character for character in search_path
            )
            connect_args["options"] = "-csearch_path=" + escaped
        return connect_args

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

def configure_engine(
    engine: AsyncEngine | ThreadedEngine, config: dict[str, Any],
) -> None:
    """
    Apply driver-specific session settings to a freshly built engine.

    For SQLite this installs a connect hook applying the configured
    PRAGMA settings; for MySQL it applies the connection charset,
    collation, and strict mode on every new pooled connection.

    Parameters
    ----------
    engine : AsyncEngine | ThreadedEngine
        Engine to configure.
    config : dict
        Connection configuration.

    Returns
    -------
    None
        This function does not return a value.
    """
    statements = _session_statements(config)
    driver = resolve_driver(config)
    if (driver, engine.sync_engine.dialect.driver) in {
        ("sqlserver", "aioodbc"), ("oracle", "oracledb"),
    }:
        _configure_async_native_creation(engine, driver)
    sqlite = driver == "sqlite"
    mysql_async = driver == "mysql" and engine.sync_engine.dialect.driver == "aiomysql"
    if not statements and not sqlite and not mysql_async:
        return

    if sqlite:
        @event.listens_for(engine.sync_engine, "begin")
        def _begin_sqlite_transaction(connection: SqlConnection) -> None:
            """
            Start a database transaction before statements or savepoints.

            Parameters
            ----------
            connection : SqlConnection
                Value supplied for ``connection``.

            Returns
            -------
            None
                Complete the documented operation without returning a value.
            """
            connection.exec_driver_sql("BEGIN")

    # Register a Core pool event on the underlying sync engine; the async
    # adapters expose a synchronous cursor facade suitable for session setup.
    @event.listens_for(engine.sync_engine, "connect")
    def _apply_session_statements(
        dbapi_connection: object,
        _record: object,
    ) -> None:
        """
        Apply configured session settings to a new pooled connection.

        Parameters
        ----------
        dbapi_connection : object
            Synchronous DBAPI connection receiving the session settings.
        _record : object
            Pool record associated with the new connection; unused.

        Returns
        -------
        None
            This callback does not return a value.
        """
        if sqlite:
            dbapi_connection.isolation_level = None
        if mysql_async:
            _configure_mysql_binary_parameters(dbapi_connection)
        if not statements:
            return
        cursor = dbapi_connection.cursor()
        try:
            for statement in statements:
                cursor.execute(statement)
        finally:
            cursor.close()


class _AsyncDBAPIClient(Protocol):
    """Native async client whose close operation must settle after cancellation."""

    async def close(self) -> None:
        """
        Release the underlying native database handle.

        Returns
        -------
        None
            Close the client and release its database resources.
        """
        ...


class _AsyncNativeCreator:
    """Collect a late native client before propagating caller cancellation."""

    __slots__ = ("_creator",)

    def __init__(
        self, creator: Callable[..., Awaitable[_AsyncDBAPIClient]],
    ) -> None:
        """
        Store the native database client factory.

        Parameters
        ----------
        creator : Callable
            Factory that asynchronously creates a native database client.

        Returns
        -------
        None
            Retain the factory for later connection attempts.
        """
        self._creator = creator

    async def __call__(
        self, *args: object, **kwargs: object,
    ) -> _AsyncDBAPIClient:
        """
        Create a native client and collect it if cancellation arrives late.

        Parameters
        ----------
        *args : object
            Positional arguments passed to the native creator.
        **kwargs : object
            Keyword arguments passed to the native creator.

        Returns
        -------
        _AsyncDBAPIClient
            Created native database client.
        """
        async def close_late(client: _AsyncDBAPIClient) -> None:
            """
            Close a client created after its caller was cancelled.

            Parameters
            ----------
            client : _AsyncDBAPIClient
                Late result from the native creator.

            Returns
            -------
            None
                Release the late client's database handle.
            """
            await _wait_for_completion(create_task(client.close()))

        return await _wait_for_completion(
            ensure_future(self._creator(*args, **kwargs)),
            on_cancel=close_late,
        )


def _configure_async_native_creation(engine: AsyncEngine, driver: str) -> None:
    """
    Protect native client creation while keeping pool waiters cancellable.

    Parameters
    ----------
    engine : AsyncEngine
        Engine whose native creator will be wrapped.
    driver : str
        Orionis driver name used to select the native creator.

    Returns
    -------
    None
        Register the native connection creation event listener.
    """
    @event.listens_for(engine.sync_engine, "do_connect")
    def protect_native_creator(
        dialect: Dialect,
        _record: object,
        _args: list[Any],
        parameters: dict[str, Any],
    ) -> None:
        """
        Wrap the dialect's native creator for cancellation-safe cleanup.

        Parameters
        ----------
        dialect : Dialect
            SQLAlchemy dialect creating the native connection.
        _record : object
            Pool record supplied by SQLAlchemy; unused.
        _args : list of Any
            Positional arguments supplied by the dialect; unused.
        parameters : dict of str to Any
            Connection parameters containing the native creator.

        Returns
        -------
        None
            Replace the creator with its cancellation-safe wrapper.
        """
        creator = parameters.get("async_creator_fn")
        if not isinstance(creator, _AsyncNativeCreator):
            if creator is None:
                creator = (
                    dialect.loaded_dbapi.aioodbc.connect
                    if driver == "sqlserver"
                    else dialect.loaded_dbapi.oracledb.connect_async
                )
            parameters["async_creator_fn"] = _AsyncNativeCreator(creator)

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
        password=(
            config.get("password")
            if driver == "redshift"
            else _config_text(config, "password")
        ),
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
