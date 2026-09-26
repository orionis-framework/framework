import base64
import tempfile
from dataclasses import asdict
from pathlib import Path

from config.http import BootstrapHTTP
from config.view import BootstrapView
from orionis.database.dialect import build_engine_url, engine_options
from orionis.foundation.config.app import App, Cipher, Environments
from orionis.foundation.config.cache import File as CacheFile
from orionis.foundation.config.database import (
    PGSQL,
    Database,
    MySQL,
    Oracle,
    PGSQLCharset,
    PGSQLSSLMode,
    SQLite,
    SQLiteForeignKey,
    SQLiteJournalMode,
    SQLiteSynchronous,
    SQLServer,
)
from orionis.foundation.config.filesystems import S3, Disks, Local, Public
from orionis.foundation.config.hashing import Argon2, Bcrypt
from orionis.foundation.config.http import Cors, HTTPCsrf, HTTPProxies, HTTPRateLimit
from orionis.foundation.config.logging import Chunked, Daily, Hourly, Monthly, Weekly
from orionis.foundation.config.mail import Mail, Smtp
from orionis.foundation.config.queue.entities.database import Database as QueueDatabase
from orionis.foundation.config.scheduler import Redis, Scheduler, Stores
from orionis.foundation.config.session import Session
from orionis.foundation.config.testing import Testing
from orionis.foundation.config.view import View
from orionis.mail.entities.smtp_settings import SmtpSettings
from tests.foundation.config.support import ConfigurationTestCase


class TestConfigurationRegressions(ConfigurationTestCase):
    def testAppNormalizesEnumNamesValuesAndBinaryKeys(self) -> None:
        """Produce the raw key and canonical cipher required by encryption."""
        for cipher in Cipher:
            length = 16 if "128" in cipher.value else 32
            raw = bytes(range(length))
            encoded = "base64:" + base64.b64encode(raw).decode("ascii")
            for value in (cipher, cipher.name.lower(), cipher.value.lower()):
                with self.subTest(cipher=value):
                    config = App(key=encoded, cipher=value, env=" production ")
                    self.assertEqual(config.cipher, cipher.value)
                    self.assertEqual(config.key, raw)
                    self.assertEqual(config.env, Environments.PRODUCTION.value)

    def testGeneratedKeysMatchEveryCipher(self) -> None:
        """Make absent keys immediately usable by encryption consumers."""
        for cipher in Cipher:
            with self.subTest(cipher=cipher):
                config = App(key=None, cipher=cipher)
                self.assertEqual(len(config.key), 16 if "128" in cipher.value else 32)
        self.assertEqual(len(self.environment.writes), len(Cipher))

    def testInvalidKeysFailBeforeAnyWrite(self) -> None:
        """Reject empty, malformed and wrong-length encryption keys."""
        for value in (b"", "", "base64:???", b"x" * 15, 42):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                App(key=value)
        self.assertEqual(self.environment.writes, [])

    def testNumericOptionsRejectBooleans(self) -> None:
        """Prevent booleans from passing integer range checks across sections."""
        cases = (
            (MySQL, "port"),
            (PGSQL, "port"),
            (Oracle, "port"),
            (SQLServer, "port"),
            (SQLite, "busy_timeout"),
            (Cors, "max_age"),
            (Session, "lifetime"),
            (Testing, "verbosity"),
            (View, "cache_size"),
            (Argon2, "time"),
            (Bcrypt, "rounds"),
            (Chunked, "mb_size"),
            (Chunked, "files"),
            (Daily, "retention_days"),
            (Hourly, "retention_hours"),
            (Weekly, "retention_weeks"),
            (Monthly, "retention_months"),
            (QueueDatabase, "visibility_timeout"),
            (QueueDatabase, "retry_delay"),
            (QueueDatabase, "max_attempts"),
            (Scheduler, "jitter"),
            (HTTPRateLimit, "rate_limit_requests"),
            (Smtp, "port"),
            (Smtp, "timeout"),
        )
        for cls, field in cases:
            for value in (False, True):
                with (
                    self.subTest(entity=cls.__name__, field=field, value=value),
                    self.assertRaises((TypeError, ValueError)),
                ):
                    cls(**{field: value})

    def testExplicitZeroFalseAndEmptyAllowedValuesSurvive(self) -> None:
        """Preserve disabled caches, zero waits and unauthenticated credentials."""
        self.assertEqual(SQLite(busy_timeout=0, prefix="").busy_timeout, 0)
        self.assertEqual(Cors(max_age=0).max_age, 0)
        self.assertEqual(Scheduler(jitter=0, coalesce=False).jitter, 0)
        self.assertFalse(View(cache_size=0, autoescape=False).autoescape)
        self.assertEqual(MySQL(password="", prefix="").password, "")
        self.assertFalse(Testing(fail_fast=False, cache_results=False).cache_results)

    def testSqlitePathsAndForeignKeyOptionsReachTheDialect(self) -> None:
        """Accept memory and arbitrary SQLite filenames with coherent URLs."""
        for database in (":memory:", "database/app.db", "database/no_extension"):
            for value, expected in (
                (True, "ON"),
                (False, "OFF"),
                ("off", "OFF"),
                (SQLiteForeignKey.ON, "ON"),
            ):
                with self.subTest(database=database, value=value):
                    config = SQLite(database=database, foreign_key_constraints=value)
                    self.assertEqual(config.url, "sqlite:///" + database)
                    self.assertEqual(config.foreign_key_constraints, expected)
                    self.assertEqual(
                        build_engine_url(asdict(config)).database,
                        database,
                    )
                    engine_options(asdict(config))

    def testDatabaseEnumWireValuesRoundTrip(self) -> None:
        """Accept hyphenated PostgreSQL SSL modes and all SQLite enum values."""
        for mode in PGSQLSSLMode:
            self.assertEqual(PGSQL(sslmode=mode.value).sslmode, mode.value)
        for charset in PGSQLCharset:
            self.assertEqual(PGSQL(charset=charset.value).charset, charset.value)
        for mode in SQLiteJournalMode:
            self.assertEqual(SQLite(journal_mode=mode.value).journal_mode, mode.value)
        for mode in SQLiteSynchronous:
            self.assertEqual(SQLite(synchronous=mode.value).synchronous, mode.value)

    def testDatabaseRejectsInvalidEnumsWithoutAttributeErrors(self) -> None:
        """Report clear configuration exceptions for invalid enum inputs."""
        for cls, field in (
            (PGSQL, "charset"),
            (PGSQL, "sslmode"),
            (SQLite, "journal_mode"),
            (SQLite, "synchronous"),
            (SQLite, "foreign_key_constraints"),
        ):
            for value in (None, 7, "invalid"):
                with (
                    self.subTest(field=field, value=value),
                    self.assertRaises((TypeError, ValueError)),
                ):
                    cls(**{field: value})

    def testPostgresPortRangeAndNumericStrings(self) -> None:
        """Keep numeric string ports but enforce real TCP port bounds."""
        self.assertEqual(PGSQL(port="5432").port, "5432")
        for value in (0, 65536, "0", "65536", "²", 1.5):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                PGSQL(port=value)

    def testSqlServerValidatesAllOptions(self) -> None:
        """Reject unvalidated SQL Server flags and unsupported encrypt modes."""
        for values in (
            {"charset": " "},
            {"prefix_indexes": 1},
            {"trust_server_certificate": "true"},
            {"encrypt": "sometimes"},
            {"odbc_driver": " "},
        ):
            with (
                self.subTest(values=values),
                self.assertRaises((TypeError, ValueError)),
            ):
                SQLServer(**values)
        for value in (False, True, "yes", "no", "on", "off", "1", "0"):
            config = SQLServer(encrypt=value)
            self.assertEqual(config.encrypt, value)
            expected = "yes" if value in (True, "yes", "on", "1") else "no"
            self.assertEqual(
                build_engine_url(asdict(config)).query["Encrypt"],
                expected,
            )

    def testOracleAlternativeEndpointsAndNullableOptions(self) -> None:
        """Accept DSN or TNS without requiring a SID or service name."""
        for values in ({"dsn": "host/service"}, {"tns_name": "REPORTS"}, {"sid": "XE"}):
            self.assertEqual(Oracle(service_name=None, **values).driver, "oracle")
        with self.assertRaises(ValueError):
            Oracle(service_name=None, sid=None, dsn=None, tns_name=None)
        self.assertIsNone(SQLite(busy_timeout=None).busy_timeout)
        self.assertEqual(Database(connections={}).default, "sqlite")

    def testMutableListsAreOwnedByEachConfiguration(self) -> None:
        """Separate instance state from caller-owned and environment-owned lists."""
        for cls, name, values in (
            (Cors, "allow_origins", ["https://example.com"]),
            (HTTPProxies, "trusted_proxies", ["127.0.0.1"]),
            (View, "paths", ["templates"]),
        ):
            with self.subTest(entity=cls.__name__):
                first = cls(**{name: values})
                second = cls(**{name: values})
                getattr(first, name).append("another")
                self.assertEqual(getattr(second, name), values)
                self.assertIsNot(getattr(second, name), values)
        first = Disks()
        second = Disks()
        self.assertIsNot(first.local, second.local)

    def testListElementsAndCorsAgeAreValidated(self) -> None:
        """Reject malformed headers, origins, proxies and template paths early."""
        for cls, name in (
            (Cors, "allow_origins"),
            (Cors, "allow_headers"),
            (Cors, "expose_headers"),
            (View, "paths"),
            (HTTPProxies, "trusted_proxies"),
        ):
            for value in ([3], [None], [""]):
                with (
                    self.subTest(entity=cls.__name__, field=name),
                    self.assertRaises((TypeError, ValueError)),
                ):
                    cls(**{name: value})
        self.assertEqual(Cors(allow_methods=["HEAD"]).allow_methods, ["HEAD"])
        self.assertIsNone(Cors(max_age=None).max_age)
        with self.assertRaises(ValueError):
            Cors(max_age=-1)
        with self.assertRaises(ValueError):
            Cors(allow_origin_regex="[")

    def testInheritedValidationRejectsInvalidEnvironmentTypes(self) -> None:
        """Prevent template factories from coercing invalid values silently."""
        self.environment.values.update(VIEW_AUTOESCAPE="false", RATE_LIMIT_REQUESTS=1.5)
        for cls in (View, BootstrapView, HTTPRateLimit, BootstrapHTTP):
            with self.subTest(entity=cls.__name__), self.assertRaises(TypeError):
                cls()

    def testPreviouslyUnvalidatedBooleanFieldsAreChecked(self) -> None:
        """Run inherited post-init validation for testing and CSRF options."""
        with self.assertRaises(TypeError):
            HTTPCsrf(cookie_secure="false")
        with self.assertRaises(TypeError):
            Testing(cache_results=1)

    def testConfigurationDoesNotCreateStorageDirectories(self) -> None:
        """Leave directory creation to runtime drivers after validation succeeds."""
        with tempfile.TemporaryDirectory() as directory:
            for cls in (Local, Public, CacheFile):
                path = Path(directory) / cls.__module__.replace(".", "_")
                cls(path=str(path))
                self.assertFalse(path.exists())
        self.assertIn(S3().driver, {"aws", "s3"})

    def testHashingMemoryDependsOnParallelism(self) -> None:
        """Enforce the minimum Argon2 memory needed for every thread."""
        self.assertEqual(Argon2(memory=32, threads=4, time=1).memory, 32)
        with self.assertRaises(ValueError):
            Argon2(memory=31, threads=4)

    def testSchedulerUsesSupportedGracePeriodsAndStoreDependencies(self) -> None:
        """Match APScheduler's positive-or-unlimited grace period contract."""
        self.assertIsNone(Scheduler(misfire_grace_time=None).misfire_grace_time)
        with self.assertRaises(ValueError):
            Scheduler(misfire_grace_time=0)
        with self.assertRaises(ValueError):
            Scheduler(store="redis", stores=Stores(redis=None))
        with self.assertRaises(TypeError):
            Redis(password=1)
        with self.assertRaises(ValueError):
            Redis(key="same", run_times_key="same")

    def testMailCopiesNestedMappingsAndKeepsCustomDrivers(self) -> None:
        """Preserve named mailers and isolate mutable driver settings."""
        settings = {"archive": {"driver": "custom", "options": ["a"]}}
        sender = {"address": "from@example.com"}
        first = Mail(default="archive", mailers=settings, from_address=sender)
        second = Mail(default="archive", mailers=settings, from_address=sender)
        first.mailers["archive"]["options"].append("b")
        first.from_address["address"] = "changed@example.com"
        self.assertEqual(second.mailers, settings)
        self.assertEqual(second.from_address, sender)
        with self.assertRaises(TypeError):
            Mail(from_address={"address": None})
        with self.assertRaises(TypeError):
            Mail(mailers={"smtp": {"port": "587"}})
        with self.assertRaises(ValueError):
            Mail(default="absent")

    def testSmtpUrlOverridesInactiveOperationalOptions(self) -> None:
        """Keep the transport's documented precedence and lazy validation."""
        options = Smtp(url="smtps://smtp.example.com", port=-1, timeout=None)
        self.assertEqual(SmtpSettings.fromConfig(asdict(options)).port, 465)

    def testViewCacheSupportsDisabledAndUnlimitedModes(self) -> None:
        """Expose Jinja's zero and minus-one cache modes without coercion."""
        self.assertEqual(View(cache_size=-1, cache_path=None).cache_size, -1)
        with self.assertRaises(ValueError):
            View(cache_size=-2)
        with self.assertRaises(ValueError):
            View(cache_path=" ")
