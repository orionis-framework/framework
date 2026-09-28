from __future__ import annotations
from orionis.database.dialect import (
    _mysql_session_commands,
    build_engine_url,
    engine_options,
    missing_dependency_error,
    resolve_driver,
)
from orionis.database.exceptions import (
    MissingDatabaseDependencyException,
    UnsupportedDriverException,
)
from orionis.test import TestCase

class TestDialect(TestCase):

    # ── Driver resolution ─────────────────────────────────────────────────────

    def testResolveDriverAcceptsSupportedDrivers(self) -> None:
        """
        Resolve every supported driver name.

        Validates the normalization and acceptance of the five
        first-party drivers.
        """
        for driver in ("sqlite", "mysql", "pgsql", "oracle", "sqlserver"):
            self.assertEqual(resolve_driver({"driver": driver}), driver)

    def testResolveDriverRejectsUnknownDriver(self) -> None:
        """
        Raise UnsupportedDriverException for unknown drivers.

        Validates the fail-fast contract for misconfigured connections.
        """
        with self.assertRaises(UnsupportedDriverException):
            resolve_driver({"driver": "mssql"})

    def testResolveDriverRejectsMissingDriver(self) -> None:
        """
        Raise UnsupportedDriverException when the driver key is absent.

        Validates that empty configurations are rejected.
        """
        with self.assertRaises(UnsupportedDriverException):
            resolve_driver({})

    # ── URL building ──────────────────────────────────────────────────────────

    def testSqliteUrlUsesAiosqliteDialect(self) -> None:
        """
        Build the SQLite URL with the aiosqlite async dialect.

        Validates dialect selection and database path propagation.
        """
        url = build_engine_url({"driver": "sqlite", "database": "db.sqlite"})
        self.assertEqual(url.drivername, "sqlite+aiosqlite")
        self.assertEqual(url.database, "db.sqlite")

    def testSqliteEmptyDatabaseBecomesMemory(self) -> None:
        """
        Map empty database names to the in-memory marker.

        Validates the in-memory normalization rule.
        """
        url = build_engine_url({"driver": "sqlite", "database": ""})
        self.assertEqual(url.database, ":memory:")

    def testMysqlUrlCarriesCredentialsAndCharset(self) -> None:
        """
        Build the MySQL URL with credentials, host, port, and charset.

        Validates the server-style URL construction for MySQL.
        """
        url = build_engine_url({
            "driver": "mysql",
            "host": "127.0.0.1",
            "port": 3306,
            "database": "orionis",
            "username": "root",
            "password": "secret",
            "charset": "utf8mb4",
        })
        self.assertEqual(url.drivername, "mysql+aiomysql")
        self.assertEqual(url.host, "127.0.0.1")
        self.assertEqual(url.port, 3306)
        self.assertEqual(url.database, "orionis")
        self.assertEqual(url.username, "root")
        self.assertEqual(url.query.get("charset"), "utf8mb4")

    def testMysqlUnixSocketTravelsInQuery(self) -> None:
        """
        Forward the unix socket path through the URL query.

        Validates the socket addressing mode for MySQL.
        """
        url = build_engine_url({
            "driver": "mysql",
            "host": "localhost",
            "database": "orionis",
            "unix_socket": "/var/run/mysqld/mysqld.sock",
        })
        self.assertEqual(
            url.query.get("unix_socket"),
            "/var/run/mysqld/mysqld.sock",
        )

    def testPgsqlUrlUsesAsyncpgDialect(self) -> None:
        """
        Build the PostgreSQL URL with the asyncpg async dialect.

        Validates dialect selection for PostgreSQL.
        """
        url = build_engine_url({
            "driver": "pgsql",
            "host": "localhost",
            "port": 5432,
            "database": "orionis",
            "username": "postgres",
            "password": "",
        })
        self.assertEqual(url.drivername, "postgresql+asyncpg")
        self.assertEqual(url.port, 5432)

    def testOracleUrlUsesServiceName(self) -> None:
        """
        Build the Oracle URL carrying the service name in the query.

        Validates the service-name addressing mode.
        """
        url = build_engine_url({
            "driver": "oracle",
            "host": "localhost",
            "port": 1521,
            "username": "sys",
            "password": "",
            "service_name": "ORCL",
        })
        self.assertEqual(url.drivername, "oracle+oracledb_async")
        self.assertEqual(url.query.get("service_name"), "ORCL")

    def testOracleUrlWithSidUsesDatabaseSlot(self) -> None:
        """
        Route SID addressing through the database URL component.

        Validates the SID addressing mode for Oracle.
        """
        url = build_engine_url({
            "driver": "oracle",
            "host": "localhost",
            "port": 1521,
            "username": "sys",
            "password": "",
            "service_name": "ORCL",
            "sid": "XE",
        })
        self.assertEqual(url.database, "XE")
        self.assertNotIn("service_name", url.query)

    def testOracleUrlWithDsnOmitsHost(self) -> None:
        """
        Route DSN-based Oracle connections through connect args.

        Validates that the URL only carries credentials while the DSN
        travels via engine options.
        """
        config = {
            "driver": "oracle",
            "username": "sys",
            "password": "x",
            "dsn": "mydsn",
        }
        url = build_engine_url(config)
        self.assertIsNone(url.host)
        options = engine_options(config)
        self.assertEqual(options["connect_args"]["dsn"], "mydsn")

    # ── Engine options ────────────────────────────────────────────────────────

    def testSqliteMemoryUsesSingleConnectionPool(self) -> None:
        """
        Configure a single-connection pool for in-memory SQLite databases.

        Validates that the single shared connection semantics of the
        in-memory database are preserved.
        """
        options = engine_options({"driver": "sqlite", "database": ":memory:"})
        self.assertIn("poolclass", options)

    def testPgsqlSslModeTravelsAsConnectArg(self) -> None:
        """
        Forward the ssl mode to asyncpg through connect args.

        Validates the ssl translation rule for PostgreSQL.
        """
        options = engine_options({
            "driver": "pgsql",
            "sslmode": "require",
        })
        self.assertEqual(options["connect_args"]["ssl"], "require")

    def testPgsqlCharsetAndSearchPathTravelAsServerSettings(self) -> None:
        """
        Forward charset and search_path as asyncpg server settings.

        Validates the PostgreSQL session configuration mapping.
        """
        options = engine_options({
            "driver": "pgsql",
            "charset": "UTF8",
            "search_path": "public",
        })
        settings = options["connect_args"]["server_settings"]
        self.assertEqual(settings["client_encoding"], "UTF8")
        self.assertEqual(settings["search_path"], "public")

    def testPgsqlWithoutSessionOptionsHasNoConnectArgs(self) -> None:
        """
        Omit connect args when no session options are configured.

        Validates the empty configuration path for PostgreSQL.
        """
        options = engine_options({"driver": "pgsql"})
        self.assertNotIn("connect_args", options)

    # ── MySQL session commands ────────────────────────────────────────────────

    def testMysqlSessionAppliesCharsetCollationAndStrictMode(self) -> None:
        """
        Build SET NAMES and strict sql_mode session commands.

        Validates the MySQL session configuration mapping.
        """
        commands = _mysql_session_commands({
            "driver": "mysql",
            "charset": "utf8mb4",
            "collation": "utf8mb4_unicode_ci",
            "strict": True,
        })
        self.assertIn("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci", commands)
        self.assertTrue(
            any("STRICT_TRANS_TABLES" in command for command in commands),
        )

    def testMysqlRelaxedModeWhenStrictDisabled(self) -> None:
        """
        Apply the relaxed sql_mode preset when strict is disabled.

        Validates the strict switch translation.
        """
        commands = _mysql_session_commands({
            "driver": "mysql",
            "strict": False,
        })
        self.assertIn("SET SESSION sql_mode='NO_ENGINE_SUBSTITUTION'", commands)

    def testMysqlSessionRejectsMalformedIdentifiers(self) -> None:
        """
        Skip charset/collation values that are not plain identifiers.

        Validates the session command injection guard.
        """
        commands = _mysql_session_commands({
            "driver": "mysql",
            "charset": "utf8; DROP TABLE users",
        })
        self.assertFalse(any("SET NAMES" in command for command in commands))

    # ── SQL Server ─────────────────────────────────────────────────────────────────

    def testSqlServerUrlUsesAioodbcDialect(self) -> None:
        """
        Build the SQL Server URL with the aioodbc async dialect.

        Validates dialect selection and endpoint propagation.
        """
        url = build_engine_url({
            "driver": "sqlserver",
            "host": "127.0.0.1",
            "port": 1433,
            "database": "orionis",
            "username": "sa",
            "password": "secret",
        })
        self.assertEqual(url.drivername, "mssql+aioodbc")
        self.assertEqual(url.port, 1433)
        self.assertEqual(url.database, "orionis")

    def testSqlServerUrlCarriesOdbcDriver(self) -> None:
        """
        Forward the ODBC driver name through the URL query.

        Validates the default and explicit ODBC driver selection.
        """
        default_url = build_engine_url({
            "driver": "sqlserver",
            "host": "h",
            "database": "d",
        })
        self.assertEqual(
            default_url.query.get("driver"),
            "ODBC Driver 18 for SQL Server",
        )

        explicit_url = build_engine_url({
            "driver": "sqlserver",
            "host": "h",
            "database": "d",
            "odbc_driver": "ODBC Driver 17 for SQL Server",
        })
        self.assertEqual(
            explicit_url.query.get("driver"),
            "ODBC Driver 17 for SQL Server",
        )

    def testSqlServerEncryptionFlagsAreNormalized(self) -> None:
        """
        Normalize encryption switches to the yes/no ODBC convention.

        Validates boolean and textual switch normalization.
        """
        url = build_engine_url({
            "driver": "sqlserver",
            "host": "h",
            "database": "d",
            "encrypt": True,
            "trust_server_certificate": False,
        })
        self.assertEqual(url.query.get("Encrypt"), "yes")
        self.assertEqual(url.query.get("TrustServerCertificate"), "no")

        textual = build_engine_url({
            "driver": "sqlserver",
            "host": "h",
            "database": "d",
            "encrypt": "no",
            "trust_server_certificate": "YES",
        })
        self.assertEqual(textual.query.get("Encrypt"), "no")
        self.assertEqual(textual.query.get("TrustServerCertificate"), "yes")

    # ── Dependency hints ─────────────────────────────────────────────────────────

    def testMissingDependencyErrorCarriesInstallHint(self) -> None:
        """
        Build actionable errors for missing async driver packages.

        Validates the package name and install extra in the message.
        """
        cause = ModuleNotFoundError("No module named 'aioodbc'")
        error = missing_dependency_error("sqlserver", cause)
        self.assertIsInstance(error, MissingDatabaseDependencyException)
        self.assertIn("aioodbc", str(error))
        self.assertIn("orionis[sqlserver]", str(error))

    def testMissingDependencyErrorForEveryDriver(self) -> None:
        """
        Provide hints for every supported driver.

        Validates the hint registry completeness.
        """
        cause = ModuleNotFoundError("boom")
        for driver, package in (
            ("sqlite", "aiosqlite"),
            ("mysql", "aiomysql"),
            ("pgsql", "asyncpg"),
            ("oracle", "oracledb"),
        ):
            self.assertIn(package, str(missing_dependency_error(driver, cause)))

    def testMissingDependencyErrorForSyncDriver(self) -> None:
        """
        Report the synchronous package name for a missing sync driver.

        Validates the sync-specific installation hint used by the
        APScheduler jobstore builder.
        """
        cause = ModuleNotFoundError("No module named 'psycopg2'")
        error = missing_dependency_error("pgsql", cause, sync=True)
        self.assertIn("psycopg2", str(error))

    # ── Synchronous engine (APScheduler jobstore) ────────────────────────────

    def testBuildEngineUrlSyncUsesBlockingDialects(self) -> None:
        """
        Select the blocking DBAPI dialect when sync is requested.

        Validates every first-party driver against its synchronous
        SQLAlchemy dialect, used by the APScheduler jobstore.
        """
        expectations = {
            "sqlite": "sqlite",
            "mysql": "mysql+pymysql",
            "pgsql": "postgresql+psycopg2",
            "oracle": "oracle+oracledb",
            "sqlserver": "mssql+pyodbc",
        }
        for driver, drivername in expectations.items():
            config = {
                "driver": driver,
                "host": "localhost",
                "database": "orionis",
                "username": "user",
                "password": "secret",
            }
            url = build_engine_url(config, sync=True)
            self.assertEqual(url.drivername, drivername)

    def testPgsqlSyncOmitsAsyncConnectArgs(self) -> None:
        """
        Skip the asyncpg-only connect args when building a sync engine.

        Validates the documented limitation: sslmode, search_path, and
        charset only translate for the async PostgreSQL driver.
        """
        options = engine_options(
            {"driver": "pgsql", "sslmode": "require", "charset": "UTF8"},
            sync=True,
        )
        self.assertNotIn("connect_args", options)
