import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, Mock, patch
from orionis.console.commands.serve.serve import ServerCommand
from orionis.foundation.enums.runtimes import Runtime
from orionis.support.types.sentinel import MISSING
from orionis.test import TestCase

# ruff: noqa: S104

class _Application:
    """Expose server settings from an isolated application root."""

    __slots__ = (
        "basePath",
        "compiled",
        "compiledInvalidationPathsDirs",
        "entryPoint",
        "production",
        "startAt",
    )

    def __init__(self, base_path: Path, *, production: bool = False) -> None:
        """Store paths and metadata used to build the server command.

        Parameters
        ----------
        base_path : Path
            Existing project directory.
        production : bool, optional
            Whether the server runs in production mode.
        """
        self.basePath = base_path
        self.compiled = False
        self.compiledInvalidationPathsDirs: list[Path] = []
        self.entryPoint = "bootstrap.app:app"
        self.production = production
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
        """Report the selected environment for command construction.

        Returns
        -------
        bool
            Whether the test application is in production mode.
        """
        return self.production

class TestServerCommand(TestCase):
    """Verify server launch state and interface lifecycle behavior."""

    async def testAlwaysDisablesBytecodeInEveryEnvironment(self) -> None:
        """Disable bytecode in the parent and server for every environment.

        Returns
        -------
        None
            Assertions verify that inherited settings cannot enable pyc writes.
        """
        for production in (False, True):
            with (
                self.subTest(production=production),
                TemporaryDirectory() as temporary,
                patch.object(sys, "dont_write_bytecode", False),
                patch.dict(os.environ, {"PYTHONDONTWRITEBYTECODE": "0"}),
            ):
                app = _Application(Path(temporary), production=production)
                command = ServerCommand()

                with (
                    patch.object(command, "_ServerCommand__unixServe"),
                    patch.object(command, "_ServerCommand__windowsServe"),
                    patch.object(
                        command, "_ServerCommand__isDebugMode", return_value=False,
                    ),
                ):
                    await command.handle(app)

                self.assertTrue(sys.dont_write_bytecode)
                self.assertEqual(os.environ["PYTHONDONTWRITEBYTECODE"], "1")
                self.assertEqual(
                    command._ServerCommand__env["PYTHONDONTWRITEBYTECODE"], "1",
                )
                self.assertEqual(command._ServerCommand__cmd[1], "-B")

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

    def testHostFlagIsOptionalAndParsesAddresses(self) -> None:
        """Parse host addresses without requiring the flag.

        Returns
        -------
        None
            The parser accepts IPv4, IPv6 and hostnames.
        """
        command = ServerCommand()
        parser = ArgumentParser()
        for argument in command.arguments:
            argument.addToParser(parser)

        self.assertIs(parser.parse_args([]).host, MISSING)

        for host in ("127.0.0.2", "0.0.0.0", "::1", "localhost"):
            with self.subTest(host=host):
                command.setArguments(vars(parser.parse_args(["--host", host])))
                self.assertEqual(command.getArgument("host"), host)

    def testHostSelectionPreservesEnvironmentDefaults(self) -> None:
        """Override the bind address only when the host flag is provided.

        Returns
        -------
        None
            Command arguments and environment use the same resolved address.
        """
        with TemporaryDirectory() as temporary:
            for production in (False, True):
                for host in (None, "0.0.0.0", "127.0.0.2", "::1"):
                    with self.subTest(production=production, host=host):
                        app = _Application(Path(temporary), production=production)
                        command = ServerCommand()
                        command.setArguments({"host": host})
                        command._ServerCommand__appendHostAndPortToCommand(app)

                        default = "0.0.0.0" if production else "127.0.0.1"
                        expected = host if host is not None else default
                        self.assertEqual(
                            command._ServerCommand__cmd,
                            ["-m", "granian", "--host", expected, "--port", "8000"],
                        )
                        self.assertEqual(
                            command._ServerCommand__env["GRANIAN_HOST"], expected,
                        )

    async def testRepeatedExportsRebuildTheCommand(self) -> None:
        """Rebuild the launch command for each invocation of one instance.

        Returns
        -------
        None
            Each export contains one host and port flag with current values.
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
                for host, port in (("0.0.0.0", 9001), ("::1", 9002)):
                    command.setArguments({
                        "host": host, "port": port, "export": True,
                    })
                    with self.assertRaises(SystemExit):
                        await command.handle(app)
                    exported.append(output.call_args.args[0])

            self.assertEqual(
                [line.count("--port") for line in exported],
                [1, 1],
            )
            self.assertEqual(
                [line.count("--host") for line in exported],
                [1, 1],
            )
            self.assertIn("--host 0.0.0.0", exported[0])
            self.assertIn("--host ::1", exported[1])
            self.assertNotIn("--host 0.0.0.0", exported[1])
            self.assertIn("--port 9001", exported[0])
            self.assertIn("--port 9002", exported[1])
            self.assertNotIn("--port 9001", exported[1])

    async def testEmbeddedHostFlagOverridesConfiguration(self) -> None:
        """Resolve the debugger bind address for both server interfaces.

        Returns
        -------
        None
            The host flag takes precedence while existing fallbacks remain.
        """
        cases = (
            (None, None, "127.0.0.1"),
            (None, "127.0.0.2", "127.0.0.2"),
            ("0.0.0.0", "127.0.0.2", "0.0.0.0"),
            ("::1", "127.0.0.2", "::1"),
        )
        for interface in ("asgi", "rsgi"):
            for host, configured_host, expected in cases:
                with (
                    self.subTest(
                        interface=interface, host=host, config=configured_host,
                    ),
                    TemporaryDirectory() as temporary,
                ):
                    app = Mock()
                    app.basePath = Path(temporary)
                    app.config.side_effect = {
                        "app.host": configured_host,
                        "filesystems": {"disks": {"public": {}}},
                    }.get
                    app.isProduction.return_value = False
                    app._Application__onStartup = AsyncMock()
                    app._Application__onShutdown = AsyncMock()
                    server = Mock()
                    server.serve = AsyncMock()
                    command = ServerCommand()
                    command.setArguments({"host": host, "interface": interface})

                    with patch(
                        "granian.server.embed.Server",
                        return_value=server,
                    ) as server_type:
                        await command._ServerCommand__embeddedServe(app)

                    self.assertEqual(server_type.call_args.kwargs["address"], expected)
                    server.serve.assert_awaited_once()

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
