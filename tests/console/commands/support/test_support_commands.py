from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, Mock, patch
from aiomcache.exceptions import ClientException
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from orionis.cache.exceptions import CacheStoreException
from orionis.console.commands.support.clear_cache import ClearCacheCommand
from orionis.console.commands.support.clear_testing import ClearTestingCommand
from orionis.console.commands.support.clear_views import ClearViewsCommand
from orionis.console.commands.support.down import DownCommand
from orionis.console.commands.support.environment import EnvironmentCommand
from orionis.console.commands.support.key_generate import KeyGenerateCommand
from orionis.console.commands.support.optimize import OptimizeCommand
from orionis.console.commands.support.up import UpCommand
from orionis.console.core.commands import CORE_COMMANDS
from orionis.database.exceptions import QueryException
from orionis.test import TestCase

class _Application:
    """Provide configuration and paths required by support commands."""

    __slots__ = ("basePath", "configuration")

    def __init__(
        self,
        base_path: Path,
        configuration: dict[str, object] | None = None,
    ) -> None:
        """Store the test application's root and configuration values.

        Parameters
        ----------
        base_path : Path
            Temporary root directory for the application.
        configuration : dict[str, object] | None, optional
            Dot-notated configuration values used by the commands.

        Returns
        -------
        None
            Initialize the application test double.
        """
        self.basePath = base_path
        self.configuration = configuration or {}

    def config(self, key: str) -> object:
        """Return a configured value by its dot-notated key.

        Parameters
        ----------
        key : str
            Configuration key requested by a command.

        Returns
        -------
        object
            Configured value, or ``None`` when the key is absent.
        """
        return self.configuration.get(key)

    def path(self, key: str) -> Path:
        """Resolve a framework path below the temporary application root.

        Parameters
        ----------
        key : str
            Application path key requested by a command.

        Returns
        -------
        Path
            Resolved path for the supported framework storage key.
        """
        if key != "storage_framework":
            raise KeyError(key)
        return self.basePath / "storage" / "framework"

class _CacheManager:
    """Record clearing of the configured application cache store."""

    __slots__ = ("clear_calls", "result")

    def __init__(self, *, result: bool = True) -> None:
        """Set the cache clear outcome returned to the command.

        Parameters
        ----------
        result : bool, optional
            Result returned by the cache manager's clear operation.

        Returns
        -------
        None
            Initialize call tracking and the configured result.
        """
        self.result = result
        self.clear_calls = 0

    async def clear(self) -> bool:
        """Record the clear request and return its configured result.

        Returns
        -------
        bool
            Configured cache clear result.
        """
        self.clear_calls += 1
        return self.result

class TestSupportCommands(TestCase):
    """Verify support command registration and cache operations."""

    def testRegistersSupportCommands(self) -> None:
        """Expose maintenance, environment, key, and clear commands to the CLI.

        Returns
        -------
        None
            Assertions verify each expected command signature is registered.
        """
        signatures = {command.signature for command in CORE_COMMANDS}

        for signature in (
            "key:generate",
            "env",
            "down",
            "up",
            "clear:views",
            "clear:cache",
            "clear:logs",
            "clear:testing",
        ):
            self.assertIn(signature, signatures)

    def testDisplaysTheConfiguredEnvironment(self) -> None:
        """Show the current environment value from the application config.

        Returns
        -------
        None
            Assertions verify the console receives the configured name.
        """
        console = Mock()
        app = _Application(Path(), {"app.env": "testing"})

        EnvironmentCommand().handle(app, console)

        console.info.assert_called_once_with(
            "Current application environment: testing",
            timestamp=False,
        )

    def testPreservesAnExistingKeyUnlessForceIsProvided(self) -> None:
        """Leave a configured key unchanged unless the force flag is set.

        Returns
        -------
        None
            Assertions verify both the protected and forced paths.
        """
        app = _Application(Path(), {"app.cipher": "AES-256-CBC"})
        console = Mock()
        command = KeyGenerateCommand()
        with (
            patch(
                "orionis.console.commands.support.key_generate.Env.get",
                return_value="base64:old-key",
            ),
            patch(
                "orionis.console.commands.support.key_generate.Env.set",
                return_value=True,
            ) as save_key,
            patch(
                "orionis.console.commands.support.key_generate.SecureKeyGenerator.generate",
                return_value="base64:new-key",
            ) as generate_key,
        ):
            self.assertEqual(command.handle(app, console), 0)
            save_key.assert_not_called()
            generate_key.assert_not_called()

            command.setArguments({"force": True})
            self.assertEqual(command.handle(app, console), 0)

        generate_key.assert_called_once_with("AES-256-CBC")
        save_key.assert_called_once_with("APP_KEY", "base64:new-key")

    def testGeneratesAndSavesAKeyWhenNoKeyExists(self) -> None:
        """Persist a newly generated key when the environment has no key.

        Returns
        -------
        None
            Assertions verify cipher selection and environment persistence.
        """
        app = _Application(Path(), {"app.cipher": "AES-128-GCM"})
        console = Mock()
        with (
            patch(
                "orionis.console.commands.support.key_generate.Env.get",
                return_value=None,
            ),
            patch(
                "orionis.console.commands.support.key_generate.Env.set",
                return_value=True,
            ) as save_key,
            patch(
                "orionis.console.commands.support.key_generate.SecureKeyGenerator.generate",
                return_value="base64:generated-key",
            ) as generate_key,
        ):
            result = KeyGenerateCommand().handle(app, console)

        self.assertEqual(result, 0)
        generate_key.assert_called_once_with("AES-128-GCM")
        save_key.assert_called_once_with("APP_KEY", "base64:generated-key")
        console.success.assert_called_once()

    def testDownAndUpWriteRuntimeMaintenanceStates(self) -> None:
        """Write state files read by running HTTP workers.

        Returns
        -------
        None
            Assertions verify down and up commands update the shared state file.
        """
        with TemporaryDirectory() as temporary:
            app = _Application(Path(temporary))
            marker = app.path("storage_framework") / "maintenance"
            console = Mock()

            self.assertEqual(DownCommand().handle(app, console), 0)
            self.assertEqual(marker.read_text(encoding="utf-8"), "down")
            self.assertEqual(UpCommand().handle(app, console), 0)
            self.assertEqual(marker.read_text(encoding="utf-8"), "up")

    def testConcurrentMaintenanceWritesUseIndependentTemporaryFiles(self) -> None:
        """Complete concurrent updates without sharing a temporary file.

        Returns
        -------
        None
            Every write succeeds and leaves only the published state file.
        """
        with TemporaryDirectory() as temporary:
            app = _Application(Path(temporary))
            console = Mock()
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [
                    executor.submit(DownCommand().handle, app, console)
                    for _ in range(32)
                ]
                results = [future.result() for future in futures]

            self.assertEqual(results, [0] * len(results))
            framework_path = app.path("storage_framework")
            self.assertEqual(
                (framework_path / "maintenance").read_text(encoding="utf-8"),
                "down",
            )
            self.assertEqual(list(framework_path.glob(".maintenance.*.tmp")), [])

    def testMaintenanceWriteRetriesTransientReplacementFailures(self) -> None:
        """Publish the state after a transient replacement failure.

        Returns
        -------
        None
            The command retries the replacement and leaves no temporary file.
        """
        with TemporaryDirectory() as temporary:
            app = _Application(Path(temporary))
            console = Mock()
            state_file = app.path("storage_framework") / "maintenance"
            self.assertEqual(UpCommand().handle(app, console), 0)
            original_replace = Path.replace
            replacements: list[Path] = []

            def replace_after_reader_closes(source: Path, target: Path) -> Path:
                """Replace the marker after two simulated sharing failures.

                Parameters
                ----------
                source : Path
                    Temporary state file.
                target : Path
                    Published maintenance marker.

                Returns
                -------
                Path
                    Path of the published state file.
                """
                replacements.append(source)
                if len(replacements) < 3:
                    raise PermissionError(5, "State file is open")
                return original_replace(source, target)

            with patch.object(Path, "replace", new=replace_after_reader_closes):
                self.assertEqual(DownCommand().handle(app, console), 0)

            self.assertEqual(len(replacements), 3)
            self.assertEqual(state_file.read_text(encoding="utf-8"), "down")
            self.assertEqual(
                list(state_file.parent.glob(".maintenance.*.tmp")),
                [],
            )

    def testClearsOnlyTemplateBytecodeFiles(self) -> None:
        """Remove view bytecode while preserving other configured cache files.

        Returns
        -------
        None
            Assertions verify targeted cleanup and directory preservation.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            cache_path = Path("storage/framework/views")
            cache_dir = root / cache_path
            cache_dir.mkdir(parents=True)
            bytecode = cache_dir / "page.cache"
            metadata = cache_dir / "metadata.json"
            bytecode.write_text("bytecode", encoding="utf-8")
            metadata.write_text("metadata", encoding="utf-8")
            console = Mock()
            app = _Application(
                root,
                {"view.cache_path": str(cache_path)},
            )

            result = ClearViewsCommand().handle(app, console)

            self.assertEqual(result, 0)
            self.assertFalse(bytecode.exists())
            self.assertTrue(metadata.is_file())
            self.assertTrue(cache_dir.is_dir())

    async def testClearsTheDefaultApplicationCacheStore(self) -> None:
        """Delegate cache deletion to the configured cache manager.

        Returns
        -------
        None
            Assertions verify the store is cleared once and success is reported.
        """
        cache = _CacheManager()
        console = Mock()

        result = await ClearCacheCommand().handle(cache, console)

        self.assertEqual(result, 0)
        self.assertEqual(cache.clear_calls, 1)
        console.success.assert_called_once_with(
            "Application cache cleared.",
            timestamp=False,
        )

    async def testReportsCacheBackendFailuresWithoutAFalseSuccess(self) -> None:
        """Return failure when a configured cache backend cannot clear entries.

        Returns
        -------
        None
            Backend failures receive a concise message and a nonzero exit code.
        """
        failures = (
            ConnectionRefusedError(1225, "Connection refused"),
            QueryException("Database query failed"),
            CacheStoreException("Store is not configured"),
            RedisError("Redis is unavailable"),
            ClientException("Memcached is unavailable"),
            SQLAlchemyError("Database connection failed"),
        )
        for error in failures:
            with self.subTest(error=type(error).__name__):
                cache = Mock(clear=AsyncMock(side_effect=error))
                console = Mock()

                result = await ClearCacheCommand().handle(cache, console)

                self.assertEqual(result, 1)
                cache.clear.assert_awaited_once_with()
                self.assertIn(type(error).__name__, console.error.call_args.args[0])
                console.success.assert_not_called()

    async def testReportsCacheClearFalseAsFailure(self) -> None:
        """Return failure when a backend reports that clearing did not succeed.

        Returns
        -------
        None
            The command reports failure without displaying a success message.
        """
        cache = _CacheManager(result=False)
        console = Mock()

        result = await ClearCacheCommand().handle(cache, console)

        self.assertEqual(result, 1)
        self.assertEqual(cache.clear_calls, 1)
        console.error.assert_called_once_with(
            "The application cache could not be cleared.",
            timestamp=False,
        )
        console.success.assert_not_called()

    async def testPropagatesUnexpectedCacheImplementationErrors(self) -> None:
        """Leave programming errors available to the command error handler.

        Returns
        -------
        None
            Unexpected exceptions propagate to the reactor for diagnosis.
        """
        cache = Mock(clear=AsyncMock(side_effect=RuntimeError("Invalid state")))

        with self.assertRaisesRegex(RuntimeError, "Invalid state"):
            await ClearCacheCommand().handle(cache, Mock())

    def testClearsOnlyCachedTestResultFiles(self) -> None:
        """Delete JSON test results without removing adjacent framework data.

        Returns
        -------
        None
            Assertions verify result files are removed selectively.
        """
        with TemporaryDirectory() as temporary:
            app = _Application(Path(temporary))
            directory = app.path("storage_framework") / "cache" / "testing"
            directory.mkdir(parents=True)
            result_file = directory / "12345.json"
            metadata = directory / "metadata.txt"
            result_file.write_text("[]", encoding="utf-8")
            metadata.write_text("preserve", encoding="utf-8")
            console = Mock()

            result = ClearTestingCommand().handle(app, console)

            self.assertEqual(result, 0)
            self.assertFalse(result_file.exists())
            self.assertTrue(metadata.is_file())

    def testOptimizesFilesBelowTheApplicationRootOnly(self) -> None:
        """Compile project sources while skipping virtualenv and build folders.

        Returns
        -------
        None
            Assertions verify the source root and excluded directories.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "app" / "module.py"
            excluded_files = (
                root / ".venv" / "lib" / "module.py",
                root / ".git" / "hooks" / "helper.py",
                root / ".ruff_cache" / "module.py",
                root / "__pycache__" / "module.py",
                root / "build" / "module.py",
            )
            source.parent.mkdir(parents=True)
            source.write_text("value = 1", encoding="utf-8")
            for filename in excluded_files:
                filename.parent.mkdir(parents=True)
                filename.write_text("value = 1", encoding="utf-8")
            console = Mock()

            with patch(
                "orionis.console.commands.support.optimize.compileall.compile_file",
                return_value=True,
            ) as compile_file:
                result = OptimizeCommand().handle(_Application(root), console)

            self.assertEqual(result, 0)
            self.assertEqual(compile_file.call_count, 1)
            self.assertEqual(Path(compile_file.call_args.args[0]), source)
