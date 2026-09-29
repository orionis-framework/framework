from rich.console import Console
from rich.panel import Panel
from orionis.console.base.command import BaseCommand
from orionis.console.core.contracts.reactor import IReactor

# Static header portion of the help text, built once at import time
_USAGE_HEADER: str = (
    "[bold cyan]Usage:[/]\n  python reactor <command> <params/flags>\n\n"
    "[bold cyan]Example:[/]\n  python reactor app:command --flag\n\n"
    "[bold cyan]Available Commands:[/]\n"
)

# Static footer portion of the help text, built once at import time
_USAGE_FOOTER: str = (
    "\n[bold cyan]Options:[/]\n"
    "  -h, --help    Show this help message and exit"
)

class HelpCommand(BaseCommand):

    # ruff: noqa: TC001, TC002

    # Indicates whether timestamps will be shown in the command output
    timestamps: bool = False

    # Command signature and description
    signature: str = "list"

    # Command description
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
        # Retrieve the list of available commands from the reactor
        commands = await reactor.info()

        # Extract signature/description pairs and compute the max signature
        # length in a single pass to avoid iterating over commands twice
        pairs: list[tuple[str, str]] = []
        max_sig_len: int = 0
        for cmd in commands:
            sig: str = cmd["signature"]
            desc: str = cmd["description"]
            pairs.append((sig, desc))
            sig_len = len(sig)
            max_sig_len = max(max_sig_len, sig_len)

        # Build each command row as a list element and join once to avoid
        # O(N²) string allocations from repeated += concatenation
        rows: list[str] = [
            f"  [bold yellow]{sig:<{max_sig_len}}[/]  {desc}\n"
            for sig, desc in pairs
        ]
        usage = _USAGE_HEADER + "".join(rows) + _USAGE_FOOTER

        # Assemble the panel with the full help text
        panel = Panel(
            usage,
            title="[bold green]Orionis Framework | Reactor CLI[/]",
            expand=False,
            border_style="bright_blue",
            padding=(1, 2),
        )

        # Print the panel to the console
        console.print()
        console.print(panel)
        console.print()
