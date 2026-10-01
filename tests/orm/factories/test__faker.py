import json
import subprocess
import sys
from pathlib import Path
from orionis.test import TestCase

_ROOT = Path(__file__).resolve().parents[3]

_PROBE_SOURCE = """
import importlib
import importlib.abc
import importlib.util
import json
import sys
from typing import Any

mode = sys.argv[1]
dependency_name = "orionis_factory_probe_missing_dependency"


class BrokenFakerLoader(importlib.abc.Loader):
    def create_module(self, spec):
        return None

    def exec_module(self, module):
        importlib.import_module(dependency_name)


class MissingFaker(importlib.abc.MetaPathFinder):
    def __init__(self):
        self.attempts = []

    def find_spec(self, fullname, path, target=None):
        if fullname == "faker" or fullname.startswith("faker."):
            self.attempts.append(fullname)
            if mode == "transitive":
                return importlib.util.spec_from_loader(
                    fullname, BrokenFakerLoader(),
                )
            raise ModuleNotFoundError("Faker unavailable in probe", name=fullname)
        if fullname == dependency_name:
            raise ModuleNotFoundError("Dependency unavailable", name=fullname)
        return None


blocker = MissingFaker()
sys.meta_path.insert(0, blocker)

from orionis.orm import Integer, Model
from orionis.orm.factories import Factory, Sequence, FactoryDependencyException


class ProbeUser(Model):
    id = Integer().primary()


class ProbeFactory(Factory[ProbeUser]):
    model = ProbeUser

    def definition(self) -> dict[str, Any]:
        return {}


result = {
    "factory": Factory.__name__,
    "sequence": Sequence.__name__,
    "faker_loaded": "faker" in sys.modules,
    "import_attempts": list(blocker.attempts),
}
if mode != "import":
    try:
        ProbeFactory()
    except (FactoryDependencyException, ModuleNotFoundError) as error:
        result.update({
            "error_type": type(error).__name__,
            "error_message": str(error),
            "error_name": getattr(error, "name", None),
            "cause_name": getattr(error.__cause__, "name", None),
        })
    else:
        result["error_type"] = None
    result["construction_attempts"] = blocker.attempts
print(json.dumps(result))
"""

def _run_dependency_probe(mode: str) -> dict[str, object]:
    """Run an optional dependency scenario in a fresh interpreter.

    Parameters
    ----------
    mode : str
        Import-only, absent Faker, or missing transitive dependency scenario.

    Returns
    -------
    dict[str, object]
        Structured import and construction results from the child process.
    """
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-B", "-c", _PROBE_SOURCE, mode],
        cwd=_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    return json.loads(result.stdout)

class TestFactoryDependency(TestCase):
    """Verify the optional Faker dependency without changing installed packages."""

    def testPublicPackageImportsWithoutFaker(self) -> None:
        """Import and subclass the public API without loading optional Faker.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        result = _run_dependency_probe("import")
        self.assertEqual(result["factory"], "Factory")
        self.assertEqual(result["sequence"], "Sequence")
        self.assertFalse(result["faker_loaded"])
        self.assertEqual(result["import_attempts"], [])

    def testConstructingFactoryReportsMissingExtra(self) -> None:
        """Fail only on construction and provide the actionable uv installation.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        result = _run_dependency_probe("missing")
        self.assertEqual(result["import_attempts"], [])
        self.assertEqual(result["construction_attempts"], ["faker"])
        self.assertEqual(result["error_type"], "FactoryDependencyException")
        self.assertIn("uv add 'orionis[factories]'", result["error_message"])
        self.assertEqual(result["cause_name"], "faker")

    def testTransitiveImportFailureRetainsOriginalException(self) -> None:
        """Preserve a broken provider's missing dependency for accurate diagnosis.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        result = _run_dependency_probe("transitive")
        self.assertEqual(result["import_attempts"], [])
        self.assertEqual(result["construction_attempts"], ["faker"])
        self.assertEqual(result["error_type"], "ModuleNotFoundError")
        self.assertEqual(
            result["error_name"],
            "orionis_factory_probe_missing_dependency",
        )
        self.assertNotIn("orionis[factories]", result["error_message"])
