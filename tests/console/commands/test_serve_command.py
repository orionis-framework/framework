from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, Mock, patch
from orionis.console.commands.serve.serve import ServerCommand
from orionis.foundation.enums.runtimes import Runtime
from orionis.test import TestCase

class _Application:
    """Expose server settings from an isolated application root."""

    __slots__ = (
        "basePath",
        "compiled",
        "compiledInvalidationPathsDirs",
        "entryPoint",
        "startAt",
    )

    def __init__(self, base_path: Path) -> None:
        """Store paths and metadata used to build the server command.

        Parameters
        ----------
        base_path : Path
            Existing project directory.
        """
        self.basePath = base_path
        self.compiled = False
        self.compiledInvalidationPathsDirs: list[Path] = []
        self.entryPoint = "bootstrap.app:app"
        self.startAt = 123

    def config(self, key: str) -> object:
        """Return the configuration requested by the server command.

        Parameters
        ----------
        key : str
            Dot-notated configuration key.

        Returns
        -------
        object
            Configured value or ``None``.
        """
        return {
            "app.name": "Demo App",
            "filesystems": {"disks": {"public": {}}},
        }.get(key)

    def isProduction(self) -> bool:
        """Report a development environment for command construction.

        Returns
        -------
        bool
            Always false for this test application.
        """
        return False

class TestServerCommand(TestCase):
    """Verify server launch state and interface lifecycle behavior."""

    def testInstancesHaveIndependentArgumentState(self) -> None:
        """Keep arguments private to each server command instance.

        Returns
        -------
        None
            A second instance has fresh command argument storage.
        """
        first = ServerCommand()
        first.setArguments({"port": 9001})
        second = ServerCommand()

        self.assertIsNot(first, second)
        self.assertEqual(second.getArguments(), {})

    async def testRepeatedExportsRebuildTheCommand(self) -> None:
        """Rebuild the launch command for each invocation of one instance.

        Returns
        -------
        None
            Each export contains one port flag and the current value.
        """
        with TemporaryDirectory() as temporary:
            app = _Application(Path(temporary))
            command = ServerCommand()
            exported: list[str] = []

            with (
                patch.object(command, "exitSuccess", side_effect=SystemExit(0)),
                patch.object(command, "newLine"),
                patch.object(command, "textInfoBold"),
                patch.object(command, "textInfo"),
                patch.object(command, "textMuted") as output,
            ):
                for port in (9001, 9002):
                    command.setArguments({"port": port, "export": True})
                    with self.assertRaises(SystemExit):
                        await command.handle(app)
                    exported.append(output.call_args.args[0])

            self.assertEqual(
                [line.count("--port") for line in exported],
                [1, 1],
            )
            self.assertIn("--port 9001", exported[0])
            self.assertIn("--port 9002", exported[1])
            self.assertNotIn("--port 9001", exported[1])

    async def testEmbeddedAsgiUsesApplicationLifespan(self) -> None:
        """Let the ASGI server drive startup and shutdown through lifespan.

        Returns
        -------
        None
            The application is the ASGI target without manual lifecycle calls.
        """
        with TemporaryDirectory() as temporary:
            app = Mock()
            app.basePath = Path(temporary)
            app.config.side_effect = {
                "app.host": "127.0.0.1",
                "filesystems": {"disks": {"public": {}}},
            }.get
            app.isProduction.return_value = False
            app._Application__onStartup = AsyncMock()
            app._Application__onShutdown = AsyncMock()
            server = Mock()
            server.serve = AsyncMock()
            command = ServerCommand()
            command.setArguments({"interface": "asgi"})

            with patch(
                "granian.server.embed.Server",
                return_value=server,
            ) as server_type:
                await command._ServerCommand__embeddedServe(app)

            self.assertIs(server_type.call_args.kwargs["target"], app)
            server.serve.assert_awaited_once()
            app._Application__onStartup.assert_not_awaited()
            app._Application__onShutdown.assert_not_awaited()

    async def testEmbeddedRsgiShutsDownAfterServerFailure(self) -> None:
        """Run RSGI lifecycle hooks around the embedded server.

        Returns
        -------
        None
            Shutdown executes even if the embedded server raises an error.
        """
        with TemporaryDirectory() as temporary:
            app = Mock()
            app.basePath = Path(temporary)
            app.config.side_effect = {
                "app.host": "127.0.0.1",
                "filesystems": {"disks": {"public": {}}},
            }.get
            app.isProduction.return_value = False
            app._Application__onStartup = AsyncMock()
            app._Application__onShutdown = AsyncMock()
            server = Mock()
            server.serve = AsyncMock(side_effect=RuntimeError("server failure"))
            command = ServerCommand()

            with (
                patch(
                    "granian.server.embed.Server",
                    return_value=server,
                ) as server_type,
                self.assertRaisesRegex(RuntimeError, "server failure"),
            ):
                await command._ServerCommand__embeddedServe(app)

            self.assertIsNot(server_type.call_args.kwargs["target"], app)
            app._Application__onStartup.assert_awaited_once_with(
                runtime=Runtime.HTTP,
                http_interface="rsgi",
            )
            app._Application__onShutdown.assert_awaited_once_with(
                runtime=Runtime.HTTP,
            )
