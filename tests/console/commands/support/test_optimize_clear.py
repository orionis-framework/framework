import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from orionis.console.commands.support import optimize_clear
from orionis.console.commands.support.optimize_clear import OptimizeClearCommand
from orionis.test import TestCase

class _Application:
    """Expose project and framework cache paths to the command."""

    __slots__ = ("basePath", "compiledPath")

    def __init__(self, base_path: Path, compiled_path: Path | None = None) -> None:
        """Store the root and optional compiled cache directory.

        Parameters
        ----------
        base_path : Path
            Root directory of the temporary application.
        compiled_path : Path | None, optional
            Explicit compiled cache directory, if configured.

        Returns
        -------
        None
            Store the application paths used by the test double.
        """
        self.basePath = base_path
        self.compiledPath = compiled_path

    def path(self, key: str) -> Path:
        """Resolve the framework storage directory for the application.

        Parameters
        ----------
        key : str
            Application path key requested by the command.

        Returns
        -------
        Path
            Framework storage directory under the application root.
        """
        if key != "storage_framework":
            raise KeyError(key)
        return self.basePath / "storage" / "framework"

class TestOptimizeClearCommand(TestCase):
    """Verify that optimize:clear removes only generated artifacts."""

    def testClearsOptimizationArtifactsAndPreservesRuntimeStorage(self) -> None:
        """Remove bytecode, build outputs, and compiled caches selectively.

        Returns
        -------
        None
            Assertions verify generated files are removed and runtime data stays.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            framework = root / "storage" / "framework"
            cache = framework / "cache"
            generated_paths = (
                root / "app" / "module" / "__pycache__",
                root / "build" / "lib",
                root / "dist" / "package.whl",
                root / "sample.egg-info" / "PKG-INFO",
            )
            for path in generated_paths:
                path.mkdir(parents=True, exist_ok=True)
                (path / "generated.pyc").write_text("bytecode", encoding="utf-8")

            cache.mkdir(parents=True, exist_ok=True)
            for name in ("config", "commands", "routes"):
                (cache / name).write_text("compiled state", encoding="utf-8")

            preserved_files = (
                cache / "data" / "runtime.cache",
                framework / "sessions" / "session-id",
                framework / "views" / "template.cache",
                root / ".venv" / "lib" / "__pycache__" / "module.pyc",
                root / ".git" / "hooks" / "__pycache__" / "module.pyc",
                root / "node_modules" / "tool" / "__pycache__" / "module.pyc",
                root / "legacy.pyc",
            )
            for path in preserved_files:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("runtime data", encoding="utf-8")

            console = Mock()
            OptimizeClearCommand().handle(_Application(root), console)

            self.assertFalse((root / "app" / "module" / "__pycache__").exists())
            self.assertFalse((root / "legacy.pyc").exists())
            self.assertFalse((root / "build").exists())
            self.assertFalse((root / "dist").exists())
            self.assertFalse((root / "sample.egg-info").exists())
            for name in ("config", "commands", "routes"):
                self.assertFalse((cache / name).exists())
            for path in preserved_files[:-1]:
                self.assertTrue(path.is_file())
            self.assertTrue(framework.is_dir())
            console.error.assert_not_called()

    def testUsesConfiguredCompiledCachePath(self) -> None:
        """Clear compiled files from the configured cache directory.

        Returns
        -------
        None
            Assertions verify the configured cache is cleared selectively.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            compiled_path = root / "var" / "compiled"
            compiled_path.mkdir(parents=True)
            for name in ("config", "commands", "routes", "other.cache"):
                (compiled_path / name).write_text("state", encoding="utf-8")

            console = Mock()
            OptimizeClearCommand().handle(
                _Application(root, compiled_path),
                console,
            )

            for name in ("config", "commands", "routes"):
                self.assertFalse((compiled_path / name).exists())
            self.assertTrue((compiled_path / "other.cache").is_file())
            console.error.assert_not_called()

    def testReportsRemovalErrorsAndContinuesCleaning(self) -> None:
        """Report a failed removal while continuing other cleanup work.

        Returns
        -------
        None
            Assertions verify the failure is reported and other paths are cleared.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            build_path = root / "build"
            build_path.mkdir()
            (build_path / "artifact.whl").write_text("build", encoding="utf-8")
            dist_path = root / "dist"
            dist_path.mkdir()
            (dist_path / "artifact.whl").write_text("build", encoding="utf-8")
            console = Mock()
            remove_path = shutil.rmtree

            def failForBuild(path: str | Path, *args: object, **kwargs: object) -> None:
                """Raise a permission error for the build directory only.

                Parameters
                ----------
                path : str | Path
                    Directory passed to ``shutil.rmtree``.
                *args : object
                    Positional options passed through to ``shutil.rmtree``.
                **kwargs : object
                    Keyword options passed through to ``shutil.rmtree``.

                Returns
                -------
                None
                    Remove the requested path unless it is the simulated failure.

                Raises
                ------
                PermissionError
                    When the path is the build directory.
                """
                if Path(path) == build_path:
                    message = "permission denied"
                    raise PermissionError(message)
                remove_path(path, *args, **kwargs)

            with patch.object(optimize_clear.shutil, "rmtree", failForBuild):
                OptimizeClearCommand().handle(_Application(root), console)

            self.assertTrue(build_path.exists())
            self.assertFalse(dist_path.exists())
            reported_errors = [call.args[0] for call in console.error.call_args_list]
            self.assertTrue(
                any("permission denied" in error for error in reported_errors),
            )
