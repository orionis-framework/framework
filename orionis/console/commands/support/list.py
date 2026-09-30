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

# Show the help option after the registered commands.
_USAGE_FOOTER: str = (
    "\n[bold cyan]Options:[/]\n"
    "  -h, --help    Show this help message and exit"
)

class HelpCommand(BaseCommand):

    # ruff: noqa: TC001, TC002

    # Control whether this command includes timestamps in its output.
    timestamps: bool = False

    # Identify the command in the CLI registry.
    signature: str = "list"

    # Describe the information displayed by this command.
    description: str = "Show available commands and usage."

    async def handle(
        self,
        reactor: IReactor,
        console: Console,
    ) -> None:
        """
        Display usage information and available commands for the Orionis CLI.

        Parameters
        ----------
        reactor : IReactor
            Reactor instance providing command metadata via `info()` method.
        console : Console
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
