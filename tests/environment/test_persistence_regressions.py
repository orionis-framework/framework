# ruff: noqa: PT009, PT027, S603
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Run only the fixed local reentrancy probe with the current Python interpreter.
"""Keep dotenv snapshots and process updates consistent on real temporary files."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import get_type_hints
from unittest.mock import patch
from orionis.environment.contracts.env import IEnv
from orionis.environment.core.dot_env import DotEnv
from orionis.environment.facade import Env
from orionis.support.patterns.singleton.meta import _MISSING
from orionis.test import TestCase


class TestDotEnvPersistence(TestCase):
    """Isolate every file, singleton, and process variable touched by the tests."""

    def setUp(self) -> None:
        """Install isolated process state before creating a temporary dotenv file."""
        super().setUp()
        self.enterContext(patch.dict(os.environ))
        os.environ.pop("PYTHON_DOTENV_DISABLED", None)
        previous = vars(DotEnv)["_singleton_instance"]
        self.addCleanup(type.__setattr__, DotEnv, "_singleton_instance", previous)
        type.__setattr__(DotEnv, "_singleton_instance", _MISSING)
        directory = self.enterContext(TemporaryDirectory())
        self.path = Path(directory) / ".env"

    def testInterpolationIsSharedByTheProcessAndFileSnapshot(self) -> None:
        """Resolve forward references once during initialization and reload."""
        earlier, later = "ORIONIS_ENV_EARLIER", "ORIONIS_ENV_LATER"
        self.enterContext(patch.dict(os.environ, {later: "process-before"}))
        self.path.write_text(
            f"{earlier}=${{{later}}}\n{later}=file-after\n",
            encoding="utf-8",
        )
        service = DotEnv(str(self.path))
        with self.subTest(operation="initialize"):
            self.assertEqual(service.get(earlier), "process-before")
            self.assertEqual(service.all()[earlier], service.get(earlier))
        self.enterContext(patch.dict(os.environ, {later: "process-reloaded"}))
        service.reload()
        with self.subTest(operation="reload"):
            self.assertEqual(service.get(earlier), "process-reloaded")
            self.assertEqual(service.all()[earlier], service.get(earlier))

    def testInvalidProcessValueCannotModifyTheFileOrCache(self) -> None:
        """Reject a null byte before persisting an unusable environment value."""
        service = DotEnv(str(self.path))
        key = "ORIONIS_ENV_ATOMIC_VALUE"
        service.set(key, "previous")
        previous = self.path.read_bytes()
        with self.assertRaises(ValueError):
            service.set(key, "invalid\x00value")
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertEqual(service.get(key), "previous")
        self.assertEqual(service.all()[key], "previous")

    def testInvalidReloadCannotPublishEarlierEntries(self) -> None:
        """Validate the whole parsed file before updating process variables."""
        first, second = "ORIONIS_ENV_FIRST", "ORIONIS_ENV_SECOND"
        self.path.write_text(f"{first}=old\n{second}=old\n", encoding="utf-8")
        service = DotEnv(str(self.path))
        self.path.write_text(
            f"{first}=new\n{second}=invalid\x00value\n",
            encoding="utf-8",
        )
        with self.assertRaises(RuntimeError):
            service.reload()
        self.assertEqual(service.get(first), "old")
        self.assertEqual(service.all()[first], "old")

    def testDisabledLoadingPreservesProcessValues(self) -> None:
        """Preserve python-dotenv's loading switch while retaining the file cache."""
        key = "ORIONIS_ENV_DISABLED_SAMPLE"
        self.enterContext(
            patch.dict(os.environ, {"PYTHON_DOTENV_DISABLED": "true", key: "process"}),
        )
        self.path.write_text(f"{key}=file\n", encoding="utf-8")
        service = DotEnv(str(self.path))
        self.assertEqual(service.get(key), "process")
        self.assertEqual(service.all()[key], "file")

    def testDirectoryCannotMasqueradeAsAnEmptyDotenvFile(self) -> None:
        """Reject a directory passed where an existing dotenv file is required."""
        with self.assertRaises(OSError):
            DotEnv(str(self.path.parent))

    def testPublicTypeHintAnnotationsResolveAtRuntime(self) -> None:
        """Resolve the enum referenced by the environment facade and contract."""
        for target in (IEnv.set, Env.set):
            with self.subTest(target=target.__qualname__):
                self.assertIn("type_hint", get_type_hints(target))

    def testTypedPrefixesUseTheCasterNormalization(self) -> None:
        """Recognize typed prefixes with the same case and spacing as the caster."""
        service = DotEnv(str(self.path))
        for encoded, expected in (("INT:42", 42), (" BOOL :yes", True)):
            with (
                self.subTest(encoded=encoded),
                patch.dict(os.environ, {"ORIONIS_ENV_NORMALIZED": encoded}),
            ):
                self.assertEqual(service.get("ORIONIS_ENV_NORMALIZED"), expected)

    def testCustomSerializationCanReadTheEnvironment(self) -> None:
        """Avoid holding the global lock while invoking a value's text conversion."""
        script = '''
import sys
sys.path.insert(0, sys.argv[2])
from orionis.environment.core.dot_env import DotEnv

values = DotEnv(sys.argv[1])
values.set("ORIONIS_ENV_NESTED_SOURCE", "resolved")

class ReadsEnvironment:
    """Read a process setting while producing the value to persist."""

    def __str__(self) -> str:
        """Return the already loaded environment setting."""
        return values.get("ORIONIS_ENV_NESTED_SOURCE")

values.set("ORIONIS_ENV_NESTED_TARGET", ReadsEnvironment())
assert values.get("ORIONIS_ENV_NESTED_TARGET") == "resolved"
'''
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                script,
                str(self.path),
                str(Path(__file__).resolve().parents[2]),
            ],
            cwd=self.path.parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
