import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from orionis.console.bootstrap import (
    bootstrap_recovery,
    bootstrap_recovery_active,
    recovering_route,
)
from orionis.console.startup import startup_feedback
from orionis.foundation.application import Application

_ROOT = Path(__file__).resolve().parents[4]
_CONTEXTS = ("api", "ai", "console", "web", "websocket")

class TestBootstrapRecovery(unittest.TestCase):
    """Keep recovery limited to one explicitly selected native routing context."""

    def _project(
        self,
        root: Path,
        context: str | None,
        *,
        compile_app: bool = False,
    ) -> Path:
        """Write a real application with a registered yet missing routing file.

        Parameters
        ----------
        root : Path
            Root directory of the disposable application.
        context : str | None
            Route context to register, or no route registration.
        compile_app : bool
            Whether to enable compiled application state.

        Returns
        -------
        Path
            Path to the generated application bootstrap file.
        """
        # Write a minimal application that exposes startup recovery behavior.
        bootstrap = root / "bootstrap" / "app.py"
        bootstrap.parent.mkdir()
        bootstrap.write_text(
            "from pathlib import Path\n"
            "from orionis import Application\n"
            "app = Application(base_path=Path(__file__).parent.parent)\n"
            + ("app.compile()\n" if compile_app else "")
            + (
                f"app.withRouting({context}='endpoints/{context}.py', "
                "health='/ready')\n"
                if context else ""
            )
            + "app.create()\n",
            encoding="utf-8",
        )
        (root / "reactor").write_bytes((_ROOT / "reactor").read_bytes())
        return bootstrap

    def _run(
        self,
        root: Path,
        *arguments: str,
    ) -> subprocess.CompletedProcess[str]:
        """Invoke the unmodified Reactor executable in a clean subprocess.

        Parameters
        ----------
        root : Path
            Root directory containing the disposable Reactor executable.
        *arguments : str
            CLI arguments forwarded unchanged to Reactor.

        Returns
        -------
        subprocess.CompletedProcess[str]
            Completed CLI process with captured text output.
        """
        # Keep the application subprocess independent of local imports and caches.
        return subprocess.run(  # noqa: S603
            [sys.executable, "-B", str(root / "reactor"), *arguments],
            cwd=root,
            env={
                **os.environ,
                "PYTHONPATH": str(_ROOT),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUTF8": "1",
                "NO_COLOR": "1",
            },
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=45,
            check=False,
        )

    def test_registered_missing_routes_can_be_recovered_for_every_context(self) -> None:
        """Reach each native command before its absent route prevents app import.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Check failed startup, successful recovery, and repeated invocation.
        for context in _CONTEXTS:
            with self.subTest(context=context), TemporaryDirectory() as temporary:
                root = Path(temporary)
                bootstrap = self._project(root, context)
                original = bootstrap.read_bytes()
                failed = self._run(root, "list")
                self.assertNotEqual(failed.returncode, 0)
                self.assertIn("Routing file does not exist", failed.stderr)

                restored = self._run(root, f"bootstrap:{context}")

                self.assertEqual(
                    restored.returncode, 0, restored.stdout + restored.stderr,
                )
                self.assertTrue((root / "endpoints" / f"{context}.py").is_file())
                self.assertEqual(bootstrap.read_bytes(), original)
                healthy = self._run(root, "list")
                self.assertEqual(healthy.returncode, 0, healthy.stdout + healthy.stderr)
                before = {
                    path: (path.read_bytes(), path.stat().st_mtime_ns)
                    for path in root.rglob("*.py")
                }
                repeated = self._run(root, f"bootstrap:{context}")
                self.assertEqual(repeated.returncode, 0, repeated.stderr)
                self.assertEqual(before, {
                    path: (path.read_bytes(), path.stat().st_mtime_ns)
                    for path in root.rglob("*.py")
                })

    def test_unrelated_missing_context_remains_strict(self) -> None:
        """Preserve missing API validation during console recovery.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Keep unrelated missing routes fatal before resource creation.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap = self._project(root, "api")
            original = bootstrap.read_bytes()

            result = self._run(root, "bootstrap:console")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Routing file does not exist", result.stderr)
            self.assertEqual(bootstrap.read_bytes(), original)
            self.assertFalse((root / "endpoints").exists())
            self.assertFalse((root / "app").exists())

    def test_help_does_not_relax_validation_or_create_resources(self) -> None:
        """Keep help invocations free of recovery effects for incomplete apps.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exclude help requests from startup recovery behavior.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap = self._project(root, "console")
            original = bootstrap.read_bytes()
            for flag in ("--help", "-h"):
                with self.subTest(flag=flag):
                    result = self._run(root, "bootstrap:console", flag)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("Routing file does not exist", result.stderr)
                    self.assertEqual(bootstrap.read_bytes(), original)
                    self.assertFalse((root / "endpoints").exists())
                    self.assertFalse((root / "app").exists())

    def test_compiled_recovery_does_not_create_transient_caches(self) -> None:
        """Ignore compiled state while repairing a registered missing console file.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Repair compiled projects without persisting transient application state.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._project(root, "console", compile_app=True)

            result = self._run(root, "bootstrap:console")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((root / "endpoints" / "console.py").is_file())
            cache_path = root / "storage" / "framework" / "cache"
            self.assertEqual(list(cache_path.iterdir()), [])

    def test_compiled_state_is_neither_read_nor_written_in_recovery(self) -> None:
        """Expose a resolved cache path without reading or writing compiled state.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Observe cache calls while compiled recovery is active.
        with TemporaryDirectory() as temporary:
            app = object.__new__(Application)
            Application.__init__(app, Path(temporary))
            cache = Mock()
            with (
                bootstrap_recovery(["reactor", "bootstrap:api"]),
                patch("orionis.foundation.application.FileBasedCache", cache),
            ):
                app.compile()
                self.assertTrue(app.compiled)
                self.assertEqual(
                    app.compiledPath,
                    (Path(temporary) / "storage" / "framework" / "cache").resolve(),
                )
                cache.assert_called_once()
                cache.return_value.get.assert_not_called()
                app._Application__compiled_state_store = cache
                app._Application__persistCompiledState()
                cache.save.assert_not_called()

    def test_warm_compiled_application_uses_generated_registration_next_start(
        self,
    ) -> None:
        """Invalidate stale routing caches without configured monitored paths.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Warm the cache before recovery and inspect routing on the next startup.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._project(root, None, compile_app=True)
            warmed = self._run(root, "list")
            self.assertEqual(warmed.returncode, 0, warmed.stdout + warmed.stderr)
            cache_path = root / "storage" / "framework" / "cache"
            self.assertTrue((cache_path / "config").is_file())

            recovered = self._run(root, "bootstrap:api")

            self.assertEqual(
                recovered.returncode, 0, recovered.stdout + recovered.stderr,
            )
            inspected = subprocess.run(
                [
                    sys.executable, "-B", "-c",
                    (
                        "from bootstrap.app import app; "
                        "print([path.name for path in app.routingPaths('api')])"
                    ),
                ],
                cwd=root,
                env={
                    **os.environ,
                    "PYTHONPATH": str(_ROOT),
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONUTF8": "1",
                },
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=45,
                check=False,
            )
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            self.assertIn("['api.py']", inspected.stdout)
            warmed_again = self._run(root, "list")
            self.assertEqual(warmed_again.returncode, 0, warmed_again.stderr)
            cached = {
                path.name: (path.read_bytes(), path.stat().st_mtime_ns)
                for path in cache_path.iterdir() if path.is_file()
            }

            repeated = self._run(root, "bootstrap:api")

            self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
            self.assertEqual(cached, {
                path.name: (path.read_bytes(), path.stat().st_mtime_ns)
                for path in cache_path.iterdir() if path.is_file()
            })

    def test_only_exact_commands_activate_recovery(self) -> None:
        """Parse optional executable prefixes and exclude help or unknown commands.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Accept only exact native command names and supported executable prefixes.
        for arguments in (
            None, [], ["list"],
            ["bootstrap:unknown"], ["bootstrap:api:extra"],
            ["reactor", "bootstrap:api", "--help"], ["bootstrap:api", "-h"],
        ):
            with self.subTest(arguments=arguments), bootstrap_recovery(arguments):
                self.assertFalse(bootstrap_recovery_active())
                self.assertFalse(any(
                    recovering_route(context) for context in _CONTEXTS
                ))
        for arguments in (
            ["bootstrap:api"], ["reactor", "bootstrap:api"],
            ["C:\\project\\reactor.py", "bootstrap:api"],
        ):
            with self.subTest(arguments=arguments), bootstrap_recovery(arguments):
                self.assertTrue(bootstrap_recovery_active())
                self.assertTrue(recovering_route("api"))
                self.assertFalse(recovering_route("console"))
        self.assertFalse(bootstrap_recovery_active())
        for context in ("config", "lifespan"):
            with bootstrap_recovery(["reactor", f"bootstrap:{context}"]):
                self.assertTrue(bootstrap_recovery_active())
                self.assertFalse(any(
                    recovering_route(route) for route in _CONTEXTS
                ))

    def test_context_resets_after_errors_and_nested_startup(self) -> None:
        """Keep scoped recovery active for CLI startup and restore it afterward.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Nest recovery contexts and raise an error to verify state restoration.
        with ( # NOSONAR
            self.assertRaisesRegex(RuntimeError, "interrupted"),
            startup_feedback(["reactor", "bootstrap:api"]),
        ):
            self.assertTrue(recovering_route("api"))
            with startup_feedback(["reactor", "bootstrap:console"]):
                self.assertTrue(recovering_route("console"))
                self.assertFalse(recovering_route("api"))
            self.assertTrue(recovering_route("api"))
            error_msg = "interrupted"
            raise RuntimeError(error_msg)
        self.assertFalse(bootstrap_recovery_active())

if __name__ == "__main__":
    # Run this module directly with the standard unittest runner.
    unittest.main()
