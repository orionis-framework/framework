# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect live module views, class lookup, and valid Python source discovery."""

import sys
import tempfile
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from orionis.introspection.modules.inspector import ModuleInspector
from orionis.introspection.modules.reflection import ReflectionModule
from orionis.test import TestCase


def _function() -> None:
    """Represent a module function which a class may replace."""


class TestModuleRegressions(TestCase):
    """Mutate only synthetic modules and files owned by each test."""

    def setUp(self) -> None:
        """Install an isolated module and temporary source directory."""
        super().setUp()
        self.module = ModuleType("_orionis_module_regression")
        self.enterContext(patch.dict(sys.modules, {self.module.__name__: self.module}))
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def testRefreshesClassCategoriesAfterMutation(self) -> None:
        """Refresh cached class categories after replacement and removal."""
        reflection = ReflectionModule(self.module.__name__)
        for name, getter in (
            ("Public", reflection.getPublicClasses),
            ("_Protected", reflection.getProtectedClasses),
            ("__Private", reflection.getPrivateClasses),
        ):
            with self.subTest(name=name):
                reflection.setClass(name, type("Original", (), {}))
                getter()
                replacement = type("Replacement", (), {})
                reflection.setClass(name, replacement)
                self.assertIs(getter()[name], replacement)
                reflection.removeClass(name)
                self.assertNotIn(name, getter())

    def testRefreshesNonClassViewsAfterReplacingAnAttribute(self) -> None:
        """Remove replaced functions, constants, and imports from cached views."""
        reflection = ReflectionModule(self.module.__name__)
        for name, value, getter in (
            ("function", _function, reflection.getPublicSyncFunctions),
            ("CONSTANT", 7, reflection.getConstants),
            ("imported", ModuleType("synthetic_import"), reflection.getImports),
        ):
            with self.subTest(name=name):
                setattr(self.module, name, value)
                self.assertIn(name, getter())
                reflection.setClass(name, type("Replacement", (), {}))
                self.assertNotIn(name, getter())

    def testLoadsTheCurrentModuleClass(self) -> None:
        """Observe class and module replacements instead of retaining old objects."""
        self.module.Example = type("First", (), {})
        self.assertIs(
            ModuleInspector.loadClass(self.module.__name__, "Example"),
            self.module.Example,
        )
        self.module.Example = type("Second", (), {})
        with self.subTest(operation="replace_class"):
            self.assertIs(
                ModuleInspector.loadClass(self.module.__name__, "Example"),
                self.module.Example,
            )
        replacement = ModuleType(self.module.__name__)
        replacement.Example = type("Third", (), {})
        with patch.dict(sys.modules, {self.module.__name__: replacement}):
            with self.subTest(operation="replace_module"):
                self.assertIs(
                    ModuleInspector.loadClass(self.module.__name__, "Example"),
                    replacement.Example,
                )
            del replacement.Example
            with self.subTest(operation="remove"), self.assertRaises(AttributeError):
                ModuleInspector.loadClass(self.module.__name__, "Example")
            replacement.Example = 7
            with self.subTest(operation="non_class"), self.assertRaises(TypeError):
                ModuleInspector.loadClass(self.module.__name__, "Example")

    def testRecognizesImportsInSupportedPythonSourceEncodings(self) -> None:
        """Read encoding cookies and a UTF-8 BOM as Python itself does."""
        for encoding in ("latin-1", "utf-8-sig"):
            with self.subTest(encoding=encoding):
                cookie = "latin-1" if encoding == "latin-1" else "utf-8"
                source = (
                    f"# coding: {cookie}\n"
                    "from synthetic_routes import Route\n"
                    "value = 'caf\u00e9'\n"
                ).encode(encoding)
                path = self.root / "routes.py"
                path.write_bytes(source)
                compile(source, str(path), "exec")
                with self.subTest(operation="imports"):
                    self.assertTrue(
                        ModuleInspector.fileImportsAny(path, {"synthetic_routes"}),
                    )
                self.module.__file__ = str(path)
                with self.subTest(operation="source"):
                    self.assertEqual(
                        ReflectionModule(self.module.__name__).getSourceCode(),
                        source.decode(encoding),
                    )

    def testReportsTraversalErrorsWithoutRejectingAnAbsentOptionalDirectory(
        self,
    ) -> None:
        """Distinguish missing optional modules from denied directory traversal."""
        self.assertEqual(
            ModuleInspector.discoverModules(self.root, self.root / "absent"),
            set(),
        )
        denied = PermissionError("Synthetic directory traversal denial")
        with (
            patch(
                "orionis.introspection.modules.inspector.os.scandir",
                side_effect=denied,
            ),
            self.assertRaises(PermissionError) as caught,
        ):
            ModuleInspector.discoverModules(self.root, self.root)
        self.assertIs(caught.exception, denied)
