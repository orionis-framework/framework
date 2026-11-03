"""Display available commands and their usage information."""

from rich.console import Console
from rich.panel import Panel
from orionis.console.base.command import BaseCommand
from orionis.console.core.contracts.reactor import IReactor

# Show usage, an example, and the available command list heading.
_USAGE_HEADER: str = (
    "[bold cyan]Usage:[/]\n  python reactor <command> <params/flags>\n\n"
    "[bold cyan]Example:[/]\n  python reactor app:command --flag\n\n"
    "[bold cyan]Available Commands:[/]\n"
)
"""Show usage, an example, and the available command list heading."""

# Show the help option after the registered commands.
_USAGE_FOOTER: str = (
    "\n[bold cyan]Options:[/]\n"
    "  -h, --help    Show this help message and exit"
)
"""Show the help option after the registered commands."""

class HelpCommand(BaseCommand):

    # ruff: noqa: TC001, TC002

    # Control whether this command includes timestamps in its output.
    """Display available commands and their usage information."""

    timestamps: bool = False
    """Control whether this command includes timestamps in its output."""

    # Identify the command in the CLI registry.
    signature: str = "list"
    """Identify the command in the CLI registry."""

    # Describe the information displayed by this command.
    description: str = "Show available commands and usage."
    """Describe the information displayed by this command."""

    async def handle(
        self,
        reactor: IReactor,
        console: Console,
    ) -> None:
        """
        Display usage information and available commands for the Orionis CLI.

        Parameters
        ----------
        reactor : orionis.console.core.contracts.reactor.IReactor
            Reactor instance providing command metadata via ``info()`` method.
        console : orionis.console.Console
            Rich console instance for output.

        Returns
        -------
        None
            This method outputs help information to the console and returns None.
        """
        # Get the commands registered with the reactor.
        commands = await reactor.info()

        # Collect command labels and determine the width used to align them.
        pairs: list[tuple[str, str]] = []
        max_sig_len: int = 0
        for cmd in commands:
            sig: str = cmd["signature"]
            desc: str = cmd["description"]
            pairs.append((sig, desc))
            sig_len = len(sig)
            max_sig_len = max(max_sig_len, sig_len)

        # Format one aligned help row for each registered command.
        rows: list[str] = [
            f"  [bold yellow]{sig:<{max_sig_len}}[/]  {desc}\n"
            for sig, desc in pairs
        ]
        usage = _USAGE_HEADER + "".join(rows) + _USAGE_FOOTER

        # Build the panel containing usage information and command rows.
        panel = Panel(
            usage,
            title="[bold green]Orionis Framework | Reactor CLI[/]",
            expand=False,
            border_style="bright_blue",
            padding=(1, 2),
        )

        # Display the help panel between blank lines.
        console.print()
        console.print(panel)
        console.print()
