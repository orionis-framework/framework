import ast
import logging
import os
import subprocess
import sys
from dataclasses import MISSING, fields, is_dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from dotenv.parser import parse_stream
from config.database import BootstrapDatabase
from config.http import BootstrapHTTP
from config.logging import BootstrapLogging
from config.session import BootstrapSession
from tests.foundation.config.test_environment import (
    ConfigurationTestCase,
    configuration_classes,
)

class TestConfigurationTemplates(ConfigurationTestCase):
    def testExampleEnvironmentDeclaresEachVariableOnce(self) -> None:
        """Reject duplicated environment keys that silently replace earlier defaults.

        Returns
        -------
        None
            Every parsed example key has one unambiguous declaration.
        """
        example = Path(__file__).resolve().parents[3] / ".env.example"
        with example.open(encoding="utf-8") as stream:
            keys = [binding.key for binding in parse_stream(stream) if binding.key]
        self.assertEqual(len(keys), len(set(keys)))

    def testExampleEnvironmentBuildsEveryApplicationConfiguration(self) -> None:
        """Construct real configuration defaults in an isolated child process.

        Returns
        -------
        None
            The shipped example can initialize every editable configuration module.
        """
        root = Path(__file__).resolve().parents[3]
        script = """
import importlib
import json
import os
from pathlib import Path
from dataclasses import is_dataclass
from dotenv import dotenv_values
for key in dotenv_values('.env'):
    os.environ.pop(key, None)
errors = []
count = 0
for path in sorted((Path(os.environ['ORIONIS_AUDIT_ROOT']) / 'config').glob('*.py')):
    module = importlib.import_module('config.' + path.stem)
    for value in vars(module).values():
        if not isinstance(value, type) or not is_dataclass(value):
            continue
        if value.__module__ != module.__name__:
            continue
        count += 1
        try:
            value()
        except Exception as error:
            errors.append([module.__name__, type(error).__name__, str(error)])
print(json.dumps({'configurations': count, 'errors': errors}))
raise SystemExit(bool(errors) or count == 0)
"""
        with TemporaryDirectory() as directory:
            (Path(directory) / ".env").write_bytes((root / ".env.example").read_bytes())
            result = subprocess.run(  # noqa: S603
                [sys.executable, "-B", "-c", script],
                cwd=directory,
                env={
                    **os.environ, "PYTHONPATH": str(root),
                    "ORIONIS_AUDIT_ROOT": str(root),
                },
                capture_output=True, text=True, encoding="utf-8",
                timeout=30, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def testEveryApplicationOptionIsDeclaredInItsTemplate(self) -> None:
        """Keep every framework option visible in the editable application layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for cls in configuration_classes(self.modules):
            if not cls.__module__.startswith("config."):
                continue
            with self.subTest(template=cls.__module__):
                self.assertEqual(
                    set(cls.__annotations__),
                    {item.name for item in fields(cls) if item.init},
                )

    def testNestedTemplatesExposeAllConstructorOptions(self) -> None:
        """Reject hidden entity factories and incomplete nested configuration trees.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for module in self.modules:
            if not module.__name__.startswith("config."):
                continue
            tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                with self.subTest(
                    template=module.__name__,
                    line=getattr(node, "lineno", 0),
                ):
                    if (
                        isinstance(node, ast.keyword)
                        and node.arg == "default_factory"
                        and isinstance(node.value, ast.Name)
                    ):
                        self.assertFalse(
                            is_dataclass(vars(module).get(node.value.id)),
                            "Expand the entity factory in config/.",
                        )
                    if not isinstance(node, ast.Call) or not isinstance(
                        node.func,
                        ast.Name,
                    ):
                        continue
                    entity = vars(module).get(node.func.id)
                    if isinstance(entity, type) and is_dataclass(entity):
                        declared = {option.arg for option in node.keywords}
                        options = {item.name for item in fields(entity) if item.init}
                        self.assertLessEqual(declared, options)
                        self.assertLessEqual(
                            options - declared,
                            {"driver"},
                            f"Declare configurable {entity.__name__} "
                            "options in config/.",
                        )
                        if "driver" in options - declared:
                            driver = next(
                                item for item in fields(entity) if item.name == "driver"
                            )
                            self.assertTrue(
                                driver.default is not MISSING
                                or driver.default_factory is not MISSING,
                            )

    def testRecentHttpAndSessionOptionsReadEnvironment(self) -> None:
        """Expose HTTP and session options through the application templates.

        Returns
        -------
        None
            Assertions verify the selected environment values.
        """
        self.environment.values.update(
            HTTP_MONITOR_DISCONNECTS=True,
            SESSION_TRACK_PREVIOUS_URL=False,
            SESSION_RENEWAL_INTERVAL=60,
        )
        self.assertTrue(BootstrapHTTP().monitor_disconnects)
        session = BootstrapSession()
        self.assertFalse(session.track_previous_url)
        self.assertEqual(session.renewal_interval, 60)

    def testDatabaseTemplateReadsNestedEnvironmentOptions(self) -> None:
        """Apply application choices across all five explicitly configured drivers.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.environment.values.update(
            DB_HOST="database.example.com",
            DB_PREFIX="tenant_",
            DB_FOREIGN_KEYS=True,
            DB_BUSY_TIMEOUT=None,
            DB_STRICT=False,
            DB_SEARCH_PATH="tenant,public",
            DB_SERVICE_NAME="TENANT",
            DB_TRUST_SERVER_CERTIFICATE=False,
        )
        connections = BootstrapDatabase().connections
        for name in ("mysql", "pgsql", "oracle", "sqlserver"):
            with self.subTest(connection=name):
                self.assertEqual(
                    getattr(connections, name).host,
                    "database.example.com",
                )
        self.assertEqual(connections.sqlite.prefix, "tenant_")
        self.assertEqual(connections.sqlite.foreign_key_constraints, "ON")
        self.assertIsNone(connections.sqlite.busy_timeout)
        self.assertFalse(connections.mysql.strict)
        self.assertEqual(connections.pgsql.search_path, "tenant,public")
        self.assertEqual(connections.oracle.service_name, "TENANT")
        self.assertFalse(connections.sqlserver.trust_server_certificate)

    def testLoggingTemplateReadsEachChannelOptions(self) -> None:
        """Apply paths and retention independently to each logging channel.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        retentions = {
            "hourly": "retention_hours",
            "daily": "retention_days",
            "weekly": "retention_weeks",
            "monthly": "retention_months",
        }
        for name in ("stack", "hourly", "daily", "weekly", "monthly", "chunked"):
            path = (
                "storage/tenant.log"
                if name == "stack"
                else "storage/tenant_{suffix}.log"
            )
            self.environment.values.update(
                LOG_CHANNEL=name,
                LOG_PATH=path,
                LOG_LEVEL="DEBUG",
                LOG_RETENTION=2,
                LOG_ROTATION_TIME="03:30",
                LOG_MB_SIZE=20,
                LOG_FILES=3,
            )
            with self.subTest(channel=name):
                config = BootstrapLogging()
                channel = getattr(config.channels, name)
                self.assertEqual(channel.path, path)
                if name in retentions:
                    self.assertEqual(getattr(channel, retentions[name]), 2)
                for other in fields(config.channels):
                    self.assertEqual(
                        getattr(config.channels, other.name).level,
                        logging.DEBUG,
                    )
                    if other.name != name:
                        self.assertNotEqual(
                            getattr(config.channels, other.name).path,
                            path,
                        )
                self.assertEqual(config.channels.daily.at.hour, 3)
                self.assertEqual(config.channels.daily.at.minute, 30)
                self.assertEqual(config.channels.chunked.mb_size, 20)
                self.assertEqual(config.channels.chunked.files, 3)
