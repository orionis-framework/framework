from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock
from orionis.console.commands.support.optimize import OptimizeCommand
from orionis.test import TestCase

class TestOptimizeCommand(TestCase):
    """Verify source validation never persists or executes compiled code."""

    def testNeverWritesBytecode(self) -> None:
        """Validate Python files without executing them or writing pyc caches.

        Returns
        -------
        None
            Assertions verify successful validation and no bytecode artifacts.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "app.py").write_text(
                "raise RuntimeError('source must not execute')\n",
                encoding="utf-8",
            )
            console = Mock()

            result = OptimizeCommand().handle(Mock(basePath=root), console)

            self.assertEqual(result, 0)
            self.assertEqual(list(root.rglob("*.pyc")), [])
            self.assertEqual(list(root.rglob("__pycache__")), [])
            console.error.assert_not_called()
            console.success.assert_called_once_with(
                "Validated 1 Python file(s) without writing bytecode.",
                timestamp=False,
            )

    def testReportsInvalidPythonSources(self) -> None:
        """Report syntax failures without persisting any bytecode.

        Returns
        -------
        None
            Assertions verify failure status, source context, and no pyc files.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_file = root / "broken.py"
            source_file.write_text("return 1\n", encoding="utf-8")
            console = Mock()

            result = OptimizeCommand().handle(Mock(basePath=root), console)

            self.assertEqual(result, 1)
            console.success.assert_not_called()
            self.assertEqual(console.error.call_count, 2)
            self.assertIn(str(source_file), console.error.call_args.args[0])
            self.assertEqual(list(root.rglob("*.pyc")), [])
            self.assertEqual(list(root.rglob("__pycache__")), [])

    def testSkipsDependencyAndBuildDirectories(self) -> None:
        """Keep dependencies and generated directories outside validation.

        Returns
        -------
        None
            Assertions verify that only application source files are checked.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
            for name in (
                ".venv", ".git", "build", "dist", "node_modules",
                "sample.egg-info",
            ):
                directory = root / name
                directory.mkdir()
                (directory / "broken.py").write_text(
                    "return 1\n", encoding="utf-8",
                )
            console = Mock()

            result = OptimizeCommand().handle(Mock(basePath=root), console)

            self.assertEqual(result, 0)
            console.error.assert_not_called()
            console.success.assert_called_once_with(
                "Validated 1 Python file(s) without writing bytecode.",
                timestamp=False,
            )
            self.assertEqual(list(root.rglob("*.pyc")), [])
