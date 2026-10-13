from __future__ import annotations
import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
from orionis.console.base.command import BaseCommand
from orionis.console.core.loader import Loader

_ROOT = Path(__file__).resolve().parents[3]

class StartupCommand(BaseCommand):
    """Provide an importable command for cached resolution checks."""

    signature = "startup:cached"
    description = "Exercise cached command resolution."
    timestamps = False

    def handle(self) -> None:
        """
        Execute the command without side effects.

        Returns
        -------
        None
            Leave application state and output unchanged.
        """

def command_metadata(command: type[BaseCommand]) -> dict:
    """
    Build cache metadata for an importable command fixture.

    Parameters
    ----------
    command : type[BaseCommand]
        Command class whose identity and settings populate the cache entry.

    Returns
    -------
    dict
        Serializable command metadata with no declared arguments.
    """
    return {
        "module_path": command.__module__,
        "class": command.__name__,
        "method": "handle",
        "signature": command.signature,
        "description": command.description,
        "timestamps": command.timestamps,
        "arguments": [],
    }

class TestLoaderStartup(unittest.IsolatedAsyncioTestCase):
    """Verify command cache usage without booting unrelated services."""

    def make_loader(self, metadata: dict | None) -> tuple[Loader, Mock]:
        """
        Create a loader with a controlled command-cache result.

        Parameters
        ----------
        metadata : dict | None
            Cached signature-to-metadata mapping, or ``None`` for a cache miss.

        Returns
        -------
        tuple[Loader, Mock]
            Isolated loader and persistence mock used to inspect cache access.
        """
        app = Mock()
        app.compiled = False
        loader = Loader(app)
        persistence = Mock()
        persistence.get.return_value = metadata
        loader._Loader__use_cache = True
        loader._Loader__persistence = persistence
        return loader, persistence

    def testColdLoaderImportDefersCoreCommandRegistry(self) -> None:
        """
        Verify that importing the loader defers built-in commands.

        Returns
        -------
        None
            Assert that the core registry and command modules remain unloaded.
        """
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                (
                    "import json, sys\n"
                    "from orionis.console.core.loader import Loader\n"
                    "print(json.dumps({'registry': "
                    "'orionis.console.core.commands' in sys.modules, "
                    "'commands': [name for name in sys.modules "
                    "if name.startswith('orionis.console.commands.')]}))\n"
                ),
            ],
            cwd=_ROOT,
            capture_output=True,
            check=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        result = json.loads(completed.stdout)
        self.assertFalse(result["registry"])
        self.assertEqual(result["commands"], [])

    async def testCacheHitImportsOnlyRequestedCommandOnce(self) -> None:
        """
        Verify that a cache hit materializes only the requested command once.

        Returns
        -------
        None
            Assert command reuse, one cache read, and no discovery or writes.
        """
        selected = command_metadata(StartupCommand)
        unrelated = dict(selected, module_path="startup.unused", signature="unused")
        loader, persistence = self.make_loader({
            StartupCommand.signature: selected,
            "unused": unrelated,
        })

        with (
            patch.object(
                loader, "_Loader__loadCoreCommands", new_callable=AsyncMock,
            ) as core,
            patch.object(
                loader, "_Loader__loadCustomCommands", new_callable=AsyncMock,
            ) as custom,
            patch.object(loader, "_Loader__loadFluentCommands") as fluent,
            patch(
                "orionis.console.core.loader.importlib.import_module",
                wraps=importlib.import_module,
            ) as import_module,
        ):
            command = await loader.get(StartupCommand.signature)
            repeated = await loader.get(StartupCommand.signature)
            missing = await loader.get("missing:command")

        self.assertIs(command.obj, StartupCommand)
        self.assertIs(repeated, command)
        self.assertIsNone(missing)
        self.assertEqual(command.args.parse_args([]).__dict__, {})
        import_module.assert_called_once_with(StartupCommand.__module__)
        persistence.get.assert_called_once_with()
        persistence.save.assert_not_called()
        core.assert_not_called()
        custom.assert_not_called()
        fluent.assert_not_called()

    async def testCacheMissPreservesDiscoveryOrderAndWritesMetadata(self) -> None:
        """
        Verify discovery order and cache persistence after a miss.

        Returns
        -------
        None
            Assert core, custom, and fluent discovery order and one cache write.
        """
        loader, persistence = self.make_loader(None)
        selected = command_metadata(StartupCommand)
        calls = []

        async def core_commands() -> None:
            """
            Register core metadata and record its discovery order.

            Returns
            -------
            None
                Append the core stage and store the selected command fixture.
            """
            calls.append("core")
            loader._Loader__metadata[StartupCommand.signature] = selected

        async def custom_commands() -> None:
            """
            Override the description during custom command discovery.

            Returns
            -------
            None
                Append the custom stage and update the shared metadata.
            """
            calls.append("custom")
            loader._Loader__metadata[StartupCommand.signature]["description"] = "custom"

        def fluent_commands() -> None:
            """
            Apply the final description during fluent command discovery.

            Returns
            -------
            None
                Append the fluent stage and replace the preceding description.
            """
            calls.append("fluent")
            loader._Loader__metadata[StartupCommand.signature]["description"] = "fluent"

        with (
            patch.object(
                loader, "_Loader__loadCoreCommands", side_effect=core_commands,
            ),
            patch.object(
                loader, "_Loader__loadCustomCommands", side_effect=custom_commands,
            ),
            patch.object(
                loader, "_Loader__loadFluentCommands", side_effect=fluent_commands,
            ),
        ):
            command = await loader.get(StartupCommand.signature)
            await loader.get(StartupCommand.signature)

        self.assertEqual(calls, ["core", "custom", "fluent"])
        self.assertEqual(command.description, "fluent")
        persistence.get.assert_called_once_with()
        persistence.save.assert_called_once_with({StartupCommand.signature: selected})

    async def testCoreDiscoveryKeepsPublicRegistryClasses(self) -> None:
        """
        Verify that core discovery preserves public command identities.

        Returns
        -------
        None
            Assert registry signatures, module paths, and class names match.
        """
        from orionis.console.core.commands import CORE_COMMANDS

        loader, _ = self.make_loader(None)
        await loader._Loader__loadCoreCommands()

        self.assertIsInstance(CORE_COMMANDS, tuple)
        self.assertEqual(
            set(loader._Loader__metadata),
            {command.signature for command in CORE_COMMANDS},
        )
        for command in CORE_COMMANDS:
            metadata = loader._Loader__metadata[command.signature]
            self.assertEqual(metadata["module_path"], command.__module__)
            self.assertEqual(metadata["class"], command.__name__)

    async def testSourceChangeInvalidatesCommandMetadata(self) -> None:
        """
        Verify that source changes invalidate cached command metadata.

        Returns
        -------
        None
            Assert that discovery refreshes and persists metadata after an edit.
        """
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "commands.py"
            source.write_text("version = 1\n", encoding="utf-8")
            app = Mock()
            app.compiled = True
            app.compiledPath = Path(temporary) / "compiled"
            app.compiledInvalidationPathsDirs = []
            app.compiledInvalidationPathsFiles = [source]
            original = command_metadata(StartupCommand)
            loader = Loader(app)
            loader._Loader__persistence.save({StartupCommand.signature: original})
            cached = await Loader(app).get(StartupCommand.signature)
            self.assertEqual(cached.description, StartupCommand.description)

            source.write_text("version = 100\n", encoding="utf-8")
            invalidated = Loader(app)
            self.assertIsNone(invalidated._Loader__persistence.get())
            updated = dict(original, description="Source was changed.")

            async def core_commands() -> None:
                """
                Publish refreshed command metadata during core discovery.

                Returns
                -------
                None
                    Store the updated fixture in the invalidated loader.
                """
                invalidated._Loader__metadata[StartupCommand.signature] = updated

            with (
                patch.object(
                    invalidated, "_Loader__loadCoreCommands", side_effect=core_commands,
                ),
                patch.object(
                    invalidated, "_Loader__loadCustomCommands", new_callable=AsyncMock,
                ),
                patch.object(invalidated, "_Loader__loadFluentCommands"),
            ):
                command = await invalidated.get(StartupCommand.signature)

            self.assertEqual(command.description, updated["description"])
            self.assertEqual(
                Loader(app)._Loader__persistence.get(),
                {StartupCommand.signature: updated},
            )

if __name__ == "__main__":
    unittest.main()
