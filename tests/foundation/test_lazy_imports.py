# ruff: noqa: S603

from __future__ import annotations
import importlib
import json
import subprocess
import sys
from pathlib import Path
from orionis.test import TestCase

_ROOT = Path(__file__).resolve().parents[2]
_PACKAGES = (
    "orionis",
    "orionis.aio",
    "orionis.auth",
    "orionis.auth.context",
    "orionis.auth.guards",
    "orionis.auth.identity",
    "orionis.auth.middleware",
    "orionis.auth.tokens",
    "orionis.background",
    "orionis.cache",
    "orionis.console",
    "orionis.console.base",
    "orionis.console.contracts",
    "orionis.console.fluent",
    "orionis.database",
    "orionis.database.migrations",
    "orionis.database.schema",
    "orionis.database.seeders",
    "orionis.encrypter",
    "orionis.environment",
    "orionis.failure",
    "orionis.failure.base",
    "orionis.foundation.config.app",
    "orionis.foundation.config.auth",
    "orionis.foundation.config.cache",
    "orionis.foundation.config.database",
    "orionis.foundation.config.database.enums",
    "orionis.foundation.config.filesystems",
    "orionis.foundation.config.hashing",
    "orionis.foundation.config.http",
    "orionis.foundation.config.logging",
    "orionis.foundation.config.mail",
    "orionis.foundation.config.queue",
    "orionis.foundation.config.realtime",
    "orionis.foundation.config.scheduler",
    "orionis.foundation.config.session",
    "orionis.foundation.config.testing",
    "orionis.foundation.config.view",
    "orionis.hashing",
    "orionis.hashing.hashers",
    "orionis.http",
    "orionis.introspection",
    "orionis.localization",
    "orionis.logging",
    "orionis.mail",
    "orionis.mail.entities",
    "orionis.mail.transports",
    "orionis.mcp",
    "orionis.orm",
    "orionis.orm.collections",
    "orionis.orm.factories",
    "orionis.orm.query",
    "orionis.orm.relations",
    "orionis.orm.schema",
    "orionis.orm.schema.column",
    "orionis.orm.schema.constraints",
    "orionis.orm.schema.types",
    "orionis.queues",
    "orionis.realtime",
    "orionis.schemas",
    "orionis.schemas.rules",
    "orionis.storage",
    "orionis.storage.drivers",
    "orionis.support.facades",
    "orionis.support.inspirational",
    "orionis.support.types",
    "orionis.test",
    "orionis.view.filters",
    "orionis.view.globals",
)

def run_import_probe(source: str) -> dict[str, object]:
    """
    Run an import probe in a fresh Python interpreter.

    Parameters
    ----------
    source : str
        Python statements that print a single JSON object to standard output.

    Returns
    -------
    dict[str, object]
        JSON object decoded from the child interpreter's standard output.

    Raises
    ------
    subprocess.CalledProcessError
        If the child interpreter exits with a nonzero status.
    subprocess.TimeoutExpired
        If the probe runs for more than 60 seconds.
    json.JSONDecodeError
        If standard output is not valid JSON.
    """
    completed = subprocess.run(
        [sys.executable, "-B", "-c", source],
        cwd=_ROOT,
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    return json.loads(completed.stdout)

class TestLazyImports(TestCase):
    """Exercise public exports without requiring eager subsystem imports."""

    def testCoreCommandsImportInColdInterpreter(self) -> None:
        """
        Verify that core commands load in a fresh interpreter.

        Returns
        -------
        None
            This test does not return a value.
        """
        result = run_import_probe(
            "import json\n"
            "from orionis.console.core.commands import CORE_COMMANDS\n"
            "print(json.dumps({'key_command': any(command.signature == "
            "'key:generate' for command in CORE_COMMANDS)}))\n",
        )
        self.assertTrue(result["key_command"])

    def testPackageImportsLeaveImplementationsUnloaded(self) -> None:
        """
        Verify that package imports leave implementations unloaded.

        Returns
        -------
        None
            This test does not return a value.
        """
        result = run_import_probe(
            "import importlib, json, sys\n"
            f"packages = {_PACKAGES!r}\n"
            "modules = [importlib.import_module(name) for name in packages]\n"
            "print(json.dumps({\n"
            "    'application': 'orionis.foundation.application' in sys.modules,\n"
            "    'heavy': [name for name in ('sqlalchemy', 'apscheduler',\n"
            "        'jinja2', 'redis', 'rich', 'cryptography', 'pwdlib',\n"
            "        'faker', 'markdown', 'boto3', 'azure', 'google.cloud.storage')\n"
            "        if name in sys.modules],\n"
            "    'implementations': sorted({target for module in modules\n"
            "        for target, _ in module._EXPORTS.values()\n"
            "        if target not in packages and target in sys.modules}),\n"
            "    'visible': all(set(module.__all__) <= set(dir(module))\n"
            "        for module in modules),\n"
            "}))\n",
        )
        self.assertFalse(result["application"])
        self.assertEqual(result["heavy"], [])
        self.assertEqual(result["implementations"], [])
        self.assertTrue(result["visible"])

    def testDebugFacadeImportLeavesTheImplementationUnloaded(self) -> None:
        """
        Verify that the debug facade imports without loading its service.

        Returns
        -------
        None
            This test does not return a value.
        """
        result = run_import_probe(
            "import json, sys\n"
            "from orionis.support.facades import Debug\n"
            "print(json.dumps({\n"
            "    'accessor': Debug.getFacadeAccessor(),\n"
            "    'service': 'orionis.console.debug.dumper' in sys.modules,\n"
            "    'application': 'orionis.foundation.application' in sys.modules,\n"
            "    'rich': 'rich' in sys.modules,\n"
            "}))\n",
        )
        self.assertEqual(result["accessor"], "x-orionis-IDumper")
        self.assertFalse(result["service"])
        self.assertFalse(result["application"])
        self.assertFalse(result["rich"])

    def testConcreteDumperStillWorksBeforeApplicationBoot(self) -> None:
        """
        Verify that the console dumper works before application boot.

        Returns
        -------
        None
            This test does not return a value.
        """
        result = run_import_probe(
            "import json, sys\n"
            "from contextlib import redirect_stdout\n"
            "from io import StringIO\n"
            "from orionis.console import Dumper\n"
            "output = StringIO()\n"
            "with redirect_stdout(output):\n"
            "    result = Dumper.dump('before-boot')\n"
            "print(json.dumps({\n"
            "    'output': output.getvalue(),\n"
            "    'returned_none': result is None,\n"
            "    'application': 'orionis.foundation.application' in sys.modules,\n"
            "}))\n",
        )
        self.assertIn("before-boot", result["output"])
        self.assertTrue(result["returned_none"])
        self.assertFalse(result["application"])

    def testLeafImportsDoNotLoadSiblingFeatures(self) -> None:
        """
        Verify that leaf imports leave sibling implementations unloaded.

        Returns
        -------
        None
            This test does not return a value.
        """
        probes = (
            (
                "orionis.orm.query.expressions",
                ("orionis.orm.query.builder", "orionis.orm.resolver"),
            ),
            (
                "orionis.orm.schema.types.integer",
                ("orionis.orm.schema.types.strict_json", "orionis.orm.schema.table"),
            ),
            (
                "orionis.orm.factories.sequence",
                ("orionis.orm.factories.factory", "faker"),
            ),
            (
                "orionis.database.migrations.events",
                ("orionis.database.migrations.migrator", "orionis.orm.resolver"),
            ),
            (
                "orionis.mail.entities.address",
                ("orionis.mail.pending", "orionis.mail.message"),
            ),
            ("orionis.encrypter.contracts", ("cryptography",)),
            ("orionis.hashing.contracts", ("pwdlib",)),
            (
                "orionis.auth.tokens.functions",
                ("orionis.auth.tokens.repository", "orionis.orm.model"),
            ),
            ("orionis.console.fluent.command", ("apscheduler",)),
            ("orionis.view.filters.json", ("markdown",)),
            (
                "orionis.mcp.protocol.constants",
                ("orionis.mcp.server.primitives", "cryptography"),
            ),
            (
                "orionis.foundation.config.scheduler.entities.memory",
                ("orionis.foundation.config.scheduler.entities.scheduler",),
            ),
        )
        for module, excluded in probes:
            with self.subTest(module=module):
                result = run_import_probe(
                    "import importlib, json, sys\n"
                    f"importlib.import_module({module!r})\n"
                    f"excluded = {excluded!r}\n"
                    "print(json.dumps({'loaded': [name for name in excluded\n"
                    "    if name in sys.modules]}))\n",
                )
                self.assertEqual(result["loaded"], [])

    def testColdImportsResolveFormerCircularDependencies(self) -> None:
        """
        Verify that formerly circular imports succeed in fresh interpreters.

        Returns
        -------
        None
            This test does not return a value.
        """
        for module in (
            "orionis.session.manager",
            "orionis.orm.resolver",
            "orionis.orm.query.builder",
            "orionis.database.migrations.migrator",
            "orionis.http.kernel",
        ):
            with self.subTest(module=module):
                result = run_import_probe(
                    "import importlib, json\n"
                    f"module = importlib.import_module({module!r})\n"
                    "print(json.dumps({'name': module.__name__}))\n",
                )
                self.assertEqual(result["name"], module)

    def testApplicationImportExcludesUnusedSubsystems(self) -> None:
        """
        Verify that ``Application`` imports without unused subsystems.

        Returns
        -------
        None
            This test does not return a value.
        """
        result = run_import_probe(
            "import json, sys\n"
            "from orionis.foundation.application import Application\n"
            "excluded = ('orionis.console.kernel', 'orionis.http.kernel',\n"
            "    'orionis.test.provider', 'orionis.view.provider', 'sqlalchemy',\n"
            "    'apscheduler', 'jinja2', 'redis', 'pendulum')\n"
            "print(json.dumps({'loaded': [name for name in excluded\n"
            "    if name in sys.modules]}))\n",
        )
        self.assertEqual(result["loaded"], [])

    def testSqliteImportLeavesOtherDatabaseConfigurationsUnloaded(self) -> None:
        """
        Verify that SQLite imports leave other driver configurations unloaded.

        Returns
        -------
        None
            This test does not return a value.
        """
        result = run_import_probe(
            "import json, sys\n"
            "from orionis.foundation.config.database.entities.sqlite import SQLite\n"
            "from orionis.foundation.config.database import SQLite as Exported\n"
            "prefix = 'orionis.foundation.config.database.'\n"
            "excluded = ('entities.mysql', 'entities.oracle', 'entities.pgsql',\n"
            "    'entities.sqlserver', 'entities.connections',\n"
            "    'enums.mysql_collations', 'enums.pgsql_charsets')\n"
            "print(json.dumps({'same': SQLite is Exported,\n"
            "    'loaded': [name for name in excluded\n"
            "        if prefix + name in sys.modules]}))\n",
        )
        self.assertTrue(result["same"])
        self.assertEqual(result["loaded"], [])

    def testPublicExportsResolveAndCacheTheirOriginalObjects(self) -> None:
        """
        Verify that public exports resolve to cached original objects.

        Returns
        -------
        None
            This test does not return a value.
        """
        for name in _PACKAGES:
            package = importlib.import_module(name)
            self.assertEqual(set(package.__all__), set(package._EXPORTS))
            for exported_name in package.__all__:
                with self.subTest(package=name, export=exported_name):
                    value = getattr(package, exported_name)
                    self.assertIs(getattr(package, exported_name), value)
                    self.assertIs(vars(package)[exported_name], value)
                    module, attribute = package._EXPORTS[exported_name]
                    self.assertIs(
                        value, getattr(importlib.import_module(module), attribute),
                    )
            with self.assertRaisesRegex(AttributeError, "has no attribute"):
                _ = package.missing_public_export

    def testWildcardAndDirectImportsKeepExportIdentities(self) -> None:
        """
        Verify that wildcard and direct imports share export identities.

        Returns
        -------
        None
            This test does not return a value.
        """
        result = run_import_probe(
            "import json\n"
            "from orionis import Application\n"
            "from orionis.foundation.application import Application as DirectApp\n"
            "from orionis.http import *\n"
            "from orionis.http.responses import Response as DirectResponse\n"
            "from orionis.http.factory import response as direct_response\n"
            "from orionis.console.base import BaseScheduler\n"
            "from orionis.console.base.scheduler import BaseScheduler as Direct\n"
            "print(json.dumps({'same': Application is DirectApp\n"
            "    and Response is DirectResponse and response is direct_response\n"
            "    and BaseScheduler is Direct}))\n",
        )
        self.assertTrue(result["same"])

    def testSubmoduleImportsDoNotShadowPublicExports(self) -> None:
        """
        Verify that submodule imports do not shadow public exports.

        Returns
        -------
        None
            This test does not return a value.
        """
        result = run_import_probe(
            "import importlib, json\n"
            f"packages = {_PACKAGES!r}\n"
            "errors = []\n"
            "for name in packages:\n"
            "    package = importlib.import_module(name)\n"
            "    for exported, (origin, attribute) in package._EXPORTS.items():\n"
            "        direct = getattr(importlib.import_module(origin), attribute)\n"
            "        namespace = {}\n"
            "        exec('from ' + name + ' import ' + exported, namespace)\n"
            "        if (getattr(package, exported) is not direct\n"
            "                or namespace[exported] is not direct):\n"
            "            errors.append(name + '.' + exported)\n"
            "print(json.dumps({'errors': errors}))\n",
        )
        self.assertEqual(result["errors"], [])

    def testCoreMetadataMatchesDefiningClasses(self) -> None:
        """
        Verify that core metadata resolves to the defining classes.

        Returns
        -------
        None
            This test does not return a value.
        """
        from orionis.foundation.core_exception_handler import CORE_EXCEPTION_HANDLER
        from orionis.foundation.core_kernels import CORE_KERNELS
        from orionis.foundation.core_scheduler import CORE_SCHEDULER

        for metadata in (
            *CORE_KERNELS.values(), CORE_SCHEDULER, CORE_EXCEPTION_HANDLER,
        ):
            implementation = getattr(
                importlib.import_module(metadata["module"]), metadata["class"],
            )
            self.assertEqual(implementation.__module__, metadata["module"])
            self.assertEqual(implementation.__name__, metadata["class"])

    def testCoreProvidersPreserveRegistrationOrder(self) -> None:
        """
        Verify that core provider descriptors preserve registration order.

        Returns
        -------
        None
            This test does not return a value.
        """
        from orionis.foundation.core_providers import (
            CORE_PROVIDER_METADATA,
            CORE_PROVIDERS,
            get_core_providers_mapping,
        )

        self.assertIsInstance(CORE_PROVIDERS, tuple)
        self.assertEqual(CORE_PROVIDERS, get_core_providers_mapping())
        self.assertEqual(
            [(provider.__module__, provider.__name__) for provider in CORE_PROVIDERS],
            list(CORE_PROVIDER_METADATA),
        )
        self.assertEqual(len(CORE_PROVIDERS), 21)

    def testConfigurationMappingsHaveIndependentNestedDefaults(self) -> None:
        """
        Verify that configuration mappings isolate nested defaults.

        Returns
        -------
        None
            This test does not return a value.
        """
        from orionis.foundation.core_config import CORE_CONFIG, get_core_config_mapping

        first = get_core_config_mapping()
        second = get_core_config_mapping()
        first["app"]["name"] = "Changed independently"
        self.assertNotEqual(first["app"]["name"], second["app"]["name"])
        self.assertIsNot(first["app"], CORE_CONFIG["app"])
        self.assertIsNot(first["http"]["cors"], second["http"]["cors"])
        with self.assertRaises(TypeError):
            first["new"] = {}
