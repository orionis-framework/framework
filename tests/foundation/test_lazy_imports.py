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
    "orionis.console",
    "orionis.console.base",
    "orionis.console.contracts",
    "orionis.support.facades",
    "orionis.cache",
    "orionis.http",
    "orionis.auth",
    "orionis.orm",
    "orionis.database",
    "orionis.test",
    "orionis.failure",
    "orionis.schemas",
    "orionis.queues",
    "orionis.foundation.config.database",
    "orionis.foundation.config.database.enums",
)

def run_import_probe(source: str) -> dict[str, object]:
    """Execute an import assertion in an independent Python interpreter.

    Parameters
    ----------
    source : str
        Python statements printing one JSON object to standard output.

    Returns
    -------
    dict[str, object]
        Structured result from the child process.
    """
    completed = subprocess.run(  # noqa: S603
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
        """Import the built-in command registry without prior application imports.

        Returns
        -------
        None
            Assertions verify the cold import resolves the key command.
        """
        result = run_import_probe(
            "import json\n"
            "from orionis.console.core.commands import CORE_COMMANDS\n"
            "print(json.dumps({'key_command': any(command.signature == "
            "'key:generate' for command in CORE_COMMANDS)}))\n",
        )
        self.assertTrue(result["key_command"])

    def testPackageImportsLeaveImplementationsUnloaded(self) -> None:
        """Keep package inspection independent of implementation imports.

        Returns
        -------
        None
            Assertions verify cold imports and public attribute discovery.
        """
        result = run_import_probe(
            "import importlib, json, sys\n"
            f"packages = {_PACKAGES!r}\n"
            "modules = [importlib.import_module(name) for name in packages]\n"
            "print(json.dumps({\n"
            "    'application': 'orionis.foundation.application' in sys.modules,\n"
            "    'heavy': [name for name in ('sqlalchemy', 'apscheduler',\n"
            "        'jinja2', 'redis', 'rich') if name in sys.modules],\n"
            "    'visible': all(set(module.__all__) <= set(dir(module))\n"
            "        for module in modules),\n"
            "}))\n",
        )
        self.assertFalse(result["application"])
        self.assertEqual(result["heavy"], [])
        self.assertTrue(result["visible"])

    def testApplicationImportExcludesUnusedSubsystems(self) -> None:
        """Import Application without loading optional service implementations.

        Returns
        -------
        None
            Assertions reject eager kernel, provider and backend imports.
        """
        result = run_import_probe(
            "import json, sys\n"
            "from orionis.foundation.application import Application\n"
            "excluded = ('orionis.console.kernel', 'orionis.http.kernel',\n"
            "    'orionis.test.provider', 'orionis.view.provider', 'sqlalchemy',\n"
            "    'apscheduler', 'jinja2', 'redis')\n"
            "print(json.dumps({'loaded': [name for name in excluded\n"
            "    if name in sys.modules]}))\n",
        )
        self.assertEqual(result["loaded"], [])

    def testSqliteImportLeavesOtherDatabaseConfigurationsUnloaded(self) -> None:
        """Import one database entity without evaluating other driver catalogs.

        Returns
        -------
        None
            Direct and public imports share the same selectively loaded class.
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
        """Preserve named exports, repeated access and importlib identities.

        Returns
        -------
        None
            Every declared export remains importable and cached on its package.
        """
        for name in _PACKAGES:
            package = importlib.import_module(name)
            for exported_name in package.__all__:
                with self.subTest(package=name, export=exported_name):
                    value = getattr(package, exported_name)
                    self.assertIs(getattr(package, exported_name), value)
                    self.assertIs(vars(package)[exported_name], value)
            with self.assertRaisesRegex(AttributeError, "has no attribute"):
                _ = package.missing_public_export

    def testWildcardAndDirectImportsKeepExportIdentities(self) -> None:
        """Support wildcard and named imports alongside direct module access.

        Returns
        -------
        None
            Representative exports resolve to the same classes and functions.
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

    def testCoreMetadataMatchesDefiningClasses(self) -> None:
        """Resolve each built-in metadata entry to its original class.

        Returns
        -------
        None
            Kernel, exception handler and scheduler descriptors remain valid.
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
        """Resolve provider descriptors to the existing ordered class tuple.

        Returns
        -------
        None
            The compatibility tuple and explicit loader expose identical classes.
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
        self.assertEqual(len(CORE_PROVIDERS), 18)

    def testConfigurationMappingsHaveIndependentNestedDefaults(self) -> None:
        """Keep configuration edits isolated from subsequent application defaults.

        Returns
        -------
        None
            Fresh mappings and the compatibility export do not share dictionaries.
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
