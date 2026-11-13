# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from __future__ import annotations
import importlib
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from orionis.introspection.modules.inspector import ModuleInspector
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

_FROZEN_MODULE_SOURCE = """
from dataclasses import dataclass


@dataclass(frozen=True)
class FrozenSample:
    value: int = 1


class InheritedFrozen(FrozenSample):
    pass


@dataclass
class MutableSample:
    value: int = 2


NOT_A_CLASS = 7
"""

_REEXPORT_MODULE_SOURCE = """
from frozen_sample_module import FrozenSample

ALIAS = FrozenSample
"""

_PACKAGE_MODULE_NAMES = ("frozen_sample_module", "reexport_sample_module")

# ---------------------------------------------------------------------------
# discoverModules
# ---------------------------------------------------------------------------


class TestModuleInspectorDiscoverModules(TestCase):
    def testReturnsEmptySetForEmptyDirectory(self) -> None:
        """
        Assert that discoverModules returns an empty set for an empty tree.

        Returns
        -------
        None
            No return value.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            result = ModuleInspector.discoverModules(base, base)
        self.assertEqual(result, set())

    def testFindsModulesInNestedPackages(self) -> None:
        """
        Assert that discoverModules converts nested files to dotted names.

        Returns
        -------
        None
            No return value.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            package = base / "mypkg"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "module_a.py").write_text("", encoding="utf-8")
            result = ModuleInspector.discoverModules(base, base)
        self.assertIsInstance(result, set)
        self.assertIn("mypkg", result)
        self.assertIn("mypkg.module_a", result)

    def testSkipsDirectoriesNamedLikeModules(self) -> None:
        """
        Assert that directories matching the glob are ignored.

        Returns
        -------
        None
            No return value.

        Notes
        -----
        A Python-like suffix does not make a directory an importable file.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            package = base / "pkg"
            package.mkdir()
            (package / "fake.py").mkdir()
            result = ModuleInspector.discoverModules(base, base)
        self.assertEqual(result, set())

    def testFindsFilesLocatedAtTheBasePathRoot(self) -> None:
        """
        Find importable modules located directly under the base directory.

        Returns
        -------
        None
            No return value.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "root_module.py").write_text("", encoding="utf-8")
            result = ModuleInspector.discoverModules(base, base)
        self.assertEqual(result, {"root_module"})

    def testSkipsVirtualEnvironmentDirectories(self) -> None:
        """
        Exclude modules nested inside virtual environments.

        Returns
        -------
        None
            No return value.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            nested = base / "venv" / "Lib" / "site-packages" / "vendor"
            nested.mkdir(parents=True)
            (nested / "thing.py").write_text("", encoding="utf-8")
            result = ModuleInspector.discoverModules(base, base)
        self.assertEqual(result, set())

    def testPreservesPackageNamesContainingEnv(self) -> None:
        """Preserve valid package names containing environment substrings.

        Returns
        -------
        None
            No return value.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            package = base / "environment"
            package.mkdir()
            (package / "service.py").write_text("", encoding="utf-8")
            result = ModuleInspector.discoverModules(base, base)
        self.assertIn("environment.service", result)

    def testPreservesNonVirtualEnvPackage(self) -> None:
        """Discover a package named env when it is not a virtual environment.

        Returns
        -------
        None
            No return value.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            package = base / "env"
            package.mkdir()
            (package / "worker.py").write_text("", encoding="utf-8")
            result = ModuleInspector.discoverModules(base, base)
        self.assertIn("env.worker", result)

    def testSkipsVirtualEnvironmentWithConfig(self) -> None:
        """Skip a virtual environment marked by its configuration file.

        Returns
        -------
        None
            No return value.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            virtualenv = base / "venv"
            virtualenv.mkdir()
            (virtualenv / "pyvenv.cfg").write_text("", encoding="utf-8")
            (virtualenv / "helper.py").write_text("", encoding="utf-8")
            result = ModuleInspector.discoverModules(base, base)
        self.assertNotIn("venv.helper", result)

    def testRejectsTargetOutsideBase(self) -> None:
        """Reject directories whose files cannot form base-relative modules.

        Returns
        -------
        None
            No return value.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base"
            target = Path(tmp) / "other"
            base.mkdir()
            target.mkdir()
            with self.assertRaises(ValueError):
                ModuleInspector.discoverModules(base, target)


# ---------------------------------------------------------------------------
# loadClass
# ---------------------------------------------------------------------------


class TestModuleInspectorLoadClass(TestCase):
    def testResolvesClassFromValidModule(self) -> None:
        """
        Assert that loadClass retrieves a class from a valid module.

        Returns
        -------
        None
            No return value.
        """
        klass = ModuleInspector.loadClass(
            module_path="pathlib",
            class_name="Path",
        )
        self.assertIs(klass, Path)

    def testResolvesClassFromMetadataMapping(self) -> None:
        """
        Assert that loadClass resolves module and class names from metadata.

        Returns
        -------
        None
            No return value.
        """
        klass = ModuleInspector.loadClass(
            metadata={"module": "pathlib", "class": "Path"},
        )
        self.assertIs(klass, Path)

    def testRepeatedLoadsReturnTheDeclaredClass(self) -> None:
        """Retain class identity across repeated imports of an unchanged module."""
        first = ModuleInspector.loadClass("pathlib", "Path")
        second = ModuleInspector.loadClass("pathlib", "Path")
        self.assertIs(first, Path)
        self.assertIs(second, Path)

    def testImportsModulesNotPresentInSysModules(self) -> None:
        """Import a fresh file instead of relying on a stdlib module's state."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            name = "orionis_inspector_fresh_fixture"
            (root / f"{name}.py").write_text("class Sample: pass\n", encoding="utf-8")
            with (
                patch.object(sys, "path", [str(root), *sys.path]),
                patch.dict(sys.modules),
            ):
                sys.modules.pop(name, None)
                importlib.invalidate_caches()
                self.assertNotIn(name, sys.modules)
                klass = ModuleInspector.loadClass(name, "Sample")
                self.assertIs(klass, sys.modules[name].Sample)

    def testRaisesImportErrorForUnknownModule(self) -> None:
        """
        Assert that loadClass raises ImportError for a non-existent module.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(ImportError):
            ModuleInspector.loadClass(
                module_path="non_existent_module_xyz_abc",
                class_name="SomeClass",
            )

    def testRaisesAttributeErrorForUnknownClass(self) -> None:
        """
        Assert that loadClass raises AttributeError for a missing class name.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(AttributeError):
            ModuleInspector.loadClass(
                module_path="pathlib",
                class_name="NonExistentClass",
            )

    def testRaisesTypeErrorWhenAttributeIsNotAClass(self) -> None:
        """
        Assert that loadClass rejects attributes that are not classes.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            ModuleInspector.loadClass(
                module_path="os",
                class_name="sep",
            )


# ---------------------------------------------------------------------------
# fileImportsAny
# ---------------------------------------------------------------------------


class TestModuleInspectorFileImportsAny(TestCase):
    def setUp(self) -> None:
        """Create an owned source directory and register cleanup immediately."""
        self._root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def writeSource(self, name: str, payload: str | bytes) -> Path:
        """
        Write a sample file inside the temporary directory.

        Parameters
        ----------
        name : str
            File name to create inside the temporary directory.
        payload : str or bytes
            Content written to the file.

        Returns
        -------
        Path
            Path of the file that was written.
        """
        path = self._root / name
        if isinstance(payload, bytes):
            path.write_bytes(payload)
        else:
            path.write_text(payload, encoding="utf-8")
        return path

    def testReturnsFalseForMissingFile(self) -> None:
        """
        Assert that fileImportsAny returns False when the file is absent.

        Returns
        -------
        None
            No return value.
        """
        result = ModuleInspector.fileImportsAny(
            file_path=self._root / "missing.py",
            target_modules={"os"},
        )
        self.assertFalse(result)

    def testReturnsTrueForImportFromStatements(self) -> None:
        """
        Assert that ``from x import y`` matches the target module set.

        Returns
        -------
        None
            No return value.
        """
        path = self.writeSource("from_import.py", "from pathlib import Path\n")
        result = ModuleInspector.fileImportsAny(
            file_path=path,
            target_modules={"pathlib"},
        )
        self.assertTrue(result)

    def testReturnsTrueForPlainImportStatements(self) -> None:
        """
        Assert that ``import x`` matches the target module set.

        Returns
        -------
        None
            No return value.
        """
        path = self.writeSource("plain_import.py", "import json\nimport os\n")
        result = ModuleInspector.fileImportsAny(
            file_path=path,
            target_modules={"os"},
        )
        self.assertTrue(result)

    def testReturnsFalseWhenNoTargetIsImported(self) -> None:
        """
        Assert that unrelated imports do not match the target module set.

        Returns
        -------
        None
            No return value.
        """
        path = self.writeSource("unrelated.py", "import json\nx = 1\n")
        result = ModuleInspector.fileImportsAny(
            file_path=path,
            target_modules={"os", "sys"},
        )
        self.assertFalse(result)

    def testReturnsFalseForSyntaxErrors(self) -> None:
        """
        Assert that unparsable sources are reported as non-importing.

        Returns
        -------
        None
            No return value.
        """
        path = self.writeSource("broken.py", "def (:\n")
        result = ModuleInspector.fileImportsAny(
            file_path=path,
            target_modules={"os"},
        )
        self.assertFalse(result)

    def testReturnsFalseForNonUtf8Sources(self) -> None:
        """
        Assert that sources that cannot be decoded are handled gracefully.

        Returns
        -------
        None
            No return value.
        """
        path = self.writeSource("latin.py", b"# \xff\xfe import os\n")
        result = ModuleInspector.fileImportsAny(
            file_path=path,
            target_modules={"os"},
        )
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# discoverFrozenDataclasses
# ---------------------------------------------------------------------------


class TestModuleInspectorFrozenDataclasses(TestCase):
    def setUp(self) -> None:
        """Scope generated modules, the import path and their source directory."""
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / "frozen_sample_module.py").write_text(
            _FROZEN_MODULE_SOURCE,
            encoding="utf-8",
        )
        (root / "reexport_sample_module.py").write_text(
            _REEXPORT_MODULE_SOURCE,
            encoding="utf-8",
        )
        self.enterContext(patch.dict(sys.modules))
        for name in _PACKAGE_MODULE_NAMES:
            sys.modules.pop(name, None)
        self.enterContext(patch.object(sys, "path", [str(root), *sys.path]))
        importlib.invalidate_caches()
        self.addCleanup(importlib.invalidate_caches)

    def testReturnsOnlyFrozenDataclassesDeclaredInTheModule(self) -> None:
        """
        Assert that only frozen dataclasses of the module are returned.

        Returns
        -------
        None
            No return value.

        Notes
        -----
        The fixture module also declares a mutable dataclass and a plain
        integer, both of which must be filtered out.
        """
        found = ModuleInspector.discoverFrozenDataclasses({"frozen_sample_module"})
        names = {entry[2] for entry in found}
        self.assertEqual(names, {"FrozenSample"})

    def testReturnsFileStemAndModulePathForEachEntry(self) -> None:
        """
        Assert the shape of every discovered tuple.

        Returns
        -------
        None
            No return value.
        """
        found = ModuleInspector.discoverFrozenDataclasses({"frozen_sample_module"})
        file_name, module_path, class_name, klass = next(iter(found))
        self.assertEqual(file_name, "frozen_sample_module")
        self.assertEqual(module_path, "frozen_sample_module")
        self.assertEqual(class_name, "FrozenSample")
        self.assertTrue(isinstance(klass, type))

    def testIgnoresDataclassesImportedFromOtherModules(self) -> None:
        """
        Assert that re-exported dataclasses are not attributed to the importer.

        Returns
        -------
        None
            No return value.
        """
        found = ModuleInspector.discoverFrozenDataclasses({"reexport_sample_module"})
        self.assertEqual(found, set())

    def testReturnsEmptySetForEmptyInput(self) -> None:
        """
        Assert that no modules produce no discovered dataclasses.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(ModuleInspector.discoverFrozenDataclasses(set()), set())

    def testRaisesRuntimeErrorWhenAModuleCannotBeImported(self) -> None:
        """
        Assert that import failures are surfaced as RuntimeError.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(RuntimeError):
            ModuleInspector.discoverFrozenDataclasses(
                {"non_existent_module_xyz_abc"},
            )
