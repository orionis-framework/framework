from __future__ import annotations
import importlib
import sys
import tempfile
from pathlib import Path
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
            Raises AssertionError on failure.
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
            Raises AssertionError on failure.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            package = base / "mypkg"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "module_a.py").write_text("", encoding="utf-8")
            result = ModuleInspector.discoverModules(base, base)
        self.assertIsInstance(result, set)
        self.assertIn("mypkg.module_a", result)

    def testSkipsDirectoriesNamedLikeModules(self) -> None:
        """
        Assert that directories matching the glob are ignored.

        Returns
        -------
        None
            Raises AssertionError on failure.

        Notes
        -----
        ``rglob('*.py')`` also matches directories, so the ``is_file`` guard
        must discard them.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            package = base / "pkg"
            package.mkdir()
            (package / "fake.py").mkdir()
            result = ModuleInspector.discoverModules(base, base)
        self.assertEqual(result, set())

    def testSkipsFilesLocatedAtTheBasePathRoot(self) -> None:
        """
        Assert that files whose package path collapses to empty are skipped.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "root_module.py").write_text("", encoding="utf-8")
            result = ModuleInspector.discoverModules(base, base)
        self.assertEqual(result, set())

    def testStripsVirtualEnvironmentSegments(self) -> None:
        """
        Assert that virtualenv and site-packages segments are removed.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            nested = base / "venv" / "Lib" / "site-packages" / "vendor"
            nested.mkdir(parents=True)
            (nested / "thing.py").write_text("", encoding="utf-8")
            result = ModuleInspector.discoverModules(base, base)
        self.assertEqual(result, {"vendor.thing"})

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
            Raises AssertionError on failure.
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
            Raises AssertionError on failure.
        """
        klass = ModuleInspector.loadClass(
            metadata={"module": "pathlib", "class": "Path"},
        )
        self.assertIs(klass, Path)

    def testCachesResolvedClasses(self) -> None:
        """
        Assert that repeated lookups return the very same class object.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        first = ModuleInspector.loadClass(
            module_path="pathlib",
            class_name="Path",
        )
        second = ModuleInspector.loadClass(
            module_path="pathlib",
            class_name="Path",
        )
        self.assertIs(first, second)

    def testImportsModulesNotPresentInSysModules(self) -> None:
        """
        Assert that loadClass imports a module absent from ``sys.modules``.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        klass = ModuleInspector.loadClass(
            module_path="xml.dom.minidom",
            class_name="Document",
        )
        self.assertTrue(isinstance(klass, type))

    def testRaisesImportErrorForUnknownModule(self) -> None:
        """
        Assert that loadClass raises ImportError for a non-existent module.

        Returns
        -------
        None
            Raises AssertionError on failure.
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
            Raises AssertionError on failure.
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
            Raises AssertionError on failure.
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
        """
        Create an isolated temporary directory for the sample files.

        Returns
        -------
        None
            This method does not return a value.
        """
        self._tmp = tempfile.TemporaryDirectory()
        self._root = Path(self._tmp.name)

    def tearDown(self) -> None:
        """
        Remove the temporary directory created for the sample files.

        Returns
        -------
        None
            This method does not return a value.
        """
        self._tmp.cleanup()

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
            Raises AssertionError on failure.
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
            Raises AssertionError on failure.
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
            Raises AssertionError on failure.
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
            Raises AssertionError on failure.
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
            Raises AssertionError on failure.
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
            Raises AssertionError on failure.
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
        """
        Publish two throwaway modules on ``sys.path`` for the discovery tests.

        Returns
        -------
        None
            This method does not return a value.
        """
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        (root / "frozen_sample_module.py").write_text(
            _FROZEN_MODULE_SOURCE,
            encoding="utf-8",
        )
        (root / "reexport_sample_module.py").write_text(
            _REEXPORT_MODULE_SOURCE,
            encoding="utf-8",
        )
        sys.path.insert(0, str(root))
        importlib.invalidate_caches()

    def tearDown(self) -> None:
        """
        Remove the throwaway modules from ``sys.path`` and ``sys.modules``.

        Returns
        -------
        None
            This method does not return a value.
        """
        sys.path.remove(str(Path(self._tmp.name)))
        for name in _PACKAGE_MODULE_NAMES:
            sys.modules.pop(name, None)
        self._tmp.cleanup()

    def testReturnsOnlyFrozenDataclassesDeclaredInTheModule(self) -> None:
        """
        Assert that only frozen dataclasses of the module are returned.

        Returns
        -------
        None
            Raises AssertionError on failure.

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
            Raises AssertionError on failure.
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
            Raises AssertionError on failure.
        """
        found = ModuleInspector.discoverFrozenDataclasses({"reexport_sample_module"})
        self.assertEqual(found, set())

    def testReturnsEmptySetForEmptyInput(self) -> None:
        """
        Assert that no modules produce no discovered dataclasses.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertEqual(ModuleInspector.discoverFrozenDataclasses(set()), set())

    def testRaisesRuntimeErrorWhenAModuleCannotBeImported(self) -> None:
        """
        Assert that import failures are surfaced as RuntimeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(RuntimeError):
            ModuleInspector.discoverFrozenDataclasses(
                {"non_existent_module_xyz_abc"},
            )
