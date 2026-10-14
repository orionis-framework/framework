import re
from contextlib import redirect_stdout
from io import StringIO
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock, patch
from orionis.console.commands.bootstrap.config import BootstrapConfigCommand
from orionis.console.commands.bootstrap.lifespan import BootstrapLifespanCommand
from orionis.console.commands.bootstrap.routes import (
    BootstrapAiCommand,
    BootstrapApiCommand,
    BootstrapConsoleCommand,
    BootstrapWebCommand,
    BootstrapWebsocketCommand,
)
from orionis.console.enums.styles import ANSIColors
from orionis.foundation.contracts.application import IApplication

# Exercise each public command through its inherited Reactor handler.
_COMMANDS = (
    BootstrapAiCommand,
    BootstrapApiCommand,
    BootstrapConsoleCommand,
    BootstrapWebCommand,
    BootstrapWebsocketCommand,
    BootstrapConfigCommand,
    BootstrapLifespanCommand,
)
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")

class TestBootstrapOutput(IsolatedAsyncioTestCase):
    """Verify aligned action rows without duplicate console severity badges."""

    async def test_all_commands_render_aligned_status_only_colors(self) -> None:
        """
        Render uniform action rows through every public bootstrap handler.

        Returns
        -------
        None
            Assert aligned resources, status colors, and consistent spacing.
        """
        # Isolate generation so the assertions cover only user-visible output.
        actions = [
            ("CREATED", "routes/api.py"),
            ("EXISTS", "app/http/controllers"),
            ("UPDATED", "bootstrap/app.py"),
            ("SKIPPED", "Routing already registered"),
        ]
        app = Mock(spec=IApplication)
        reset = ANSIColors.DEFAULT.value
        expected = (
            "\n"
            f"  {ANSIColors.TEXT_BOLD_SUCCESS.value}CREATED{reset}  routes/api.py\n"
            f"  {ANSIColors.TEXT_MUTED.value}EXISTS {reset}  app/http/controllers\n"
            f"  {ANSIColors.TEXT_BOLD_INFO.value}UPDATED{reset}  bootstrap/app.py\n"
            f"  {ANSIColors.TEXT_MUTED.value}SKIPPED{reset}  "
            "Routing already registered\n\n"
        )
        visible = (
            "\n"
            "  CREATED  routes/api.py\n"
            "  EXISTS   app/http/controllers\n"
            "  UPDATED  bootstrap/app.py\n"
            "  SKIPPED  Routing already registered\n\n"
        )
        for command_type in _COMMANDS:
            with self.subTest(command=command_type.signature):
                command = command_type()
                output = StringIO()
                with (
                    patch.object(command, "_execute", return_value=actions) as execute,
                    redirect_stdout(output),
                ):
                    result = await command.handle(app)

                # Compare terminal and redirected forms, including blank lines.
                text = output.getvalue()
                self.assertEqual(result, 0)
                execute.assert_called_once_with(app)
                self.assertEqual(text, expected)
                self.assertEqual(_ANSI_ESCAPE.sub("", text), visible)
                self.assertNotIn("SUCCESS", text)
                self.assertNotIn("INFO", text)

    async def test_resource_text_remains_literal(self) -> None:
        """
        Preserve path text and markup-like characters in action resources.

        Returns
        -------
        None
            Assert resources retain their literal characters and spacing.
        """
        # Include characters that styled renderers might interpret as markup.
        resources = (
            "routes/[bold]api.py[/bold]",
            r"D:\My Project\app\controllers",
        )
        command = BootstrapApiCommand()
        output = StringIO()
        with (
            patch.object(
                command, "_execute",
                return_value=[("EXISTS", resource) for resource in resources],
            ),
            redirect_stdout(output),
        ):
            result = await command.handle(Mock(spec=IApplication))

        # Preserve the resource verbatim after the fixed-width status column.
        self.assertEqual(result, 0)
        self.assertEqual(
            _ANSI_ESCAPE.sub("", output.getvalue()),
            "\n" + "".join(f"  EXISTS   {resource}\n" for resource in resources)
            + "\n",
        )

    async def test_failures_keep_native_error_reporting(self) -> None:
        """
        Report failed generation without emitting successful resource rows.

        Returns
        -------
        None
            Assert failure exit codes and native Reactor error reporting.
        """
        # Retain the standard error badge and resource-specific failure details.
        app = Mock(spec=IApplication)
        error_msg = "Cannot write routes/api.py: read-only filesystem"
        for command_type in _COMMANDS:
            with self.subTest(command=command_type.signature):
                command = command_type()
                output = StringIO()
                with (
                    patch.object(command, "_execute", side_effect=OSError(error_msg)),
                    patch.object(command, "error", wraps=command.error) as report,
                    redirect_stdout(output),
                ):
                    result = await command.handle(app)

                # Check the native failure path independently of action styling.
                text = _ANSI_ESCAPE.sub("", output.getvalue())
                self.assertEqual(result, 1)
                report.assert_called_once_with(
                    f"{command.signature}: {error_msg}", timestamp=False,
                )
                self.assertIn("ERROR", text)
                self.assertIn(error_msg, text)
                self.assertNotIn("CREATED", text)
                self.assertTrue(text.startswith("\n"))
                self.assertTrue(text.endswith("\n\n"))
