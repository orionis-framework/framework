from rich.console import Console
from rich.panel import Panel
from orionis.console.base.command import BaseCommand
from orionis.metadata import framework
from orionis.support.facades.datetime import DateTime

# Show the framework name and version in the panel title.
_PANEL_TITLE: str = (
    f"[bold green]{framework.NAME.capitalize()} Framework | v{framework.VERSION}[/]"
)

# Show framework details, author contact information, and project links.
_PANEL_BODY: str = (
    f"📝 [italic]{framework.DESCRIPTION}[/italic]\n\n"
    f"[bold]Author:[/bold] {framework.AUTHOR}  |  "
    f"[bold]Email:[/bold] {framework.AUTHOR_EMAIL}\n"
    f"🐍 [bold]Python Requires:[/bold] >= "
    f"{framework.PYTHON_REQUIRES[0]}.{framework.PYTHON_REQUIRES[1]}\n"
    f"📖 [bold]Docs:[/bold]"
    f"[underline blue]{framework.DOCS}[/underline blue]\n"
    f"💻 [bold]Repo:[/bold]"
    f"[underline blue]{framework.FRAMEWORK}[/underline blue]\n"
)

class VersionCommand(BaseCommand):

    # ruff: noqa: TC002

    # Control whether this command includes timestamps in its output.
    timestamps: bool = False

    # Identify the command in the CLI registry.
    signature: str = "about"

    # Describe the information displayed by this command.
    description: str = "Displays the Orionis framework version and metadata."

    def handle(
        self,
        console: Console,
    ) -> None:
        """
        Display Orionis framework version and metadata.

        Build a panel from framework metadata and print it to the console.

        Parameters
        ----------
        console : Console
            Rich console instance for output.

        Returns
        -------
        None
            This method does not return a value. Output is sent to the console.
        """
        # Get the current timestamp for the panel subtitle.
        dt_strftime = DateTime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build the panel with framework details and the current timestamp.
        panel = Panel(
            _PANEL_BODY,
            title=_PANEL_TITLE,
            border_style="bright_blue",
            padding=(1, 2),
            expand=False,
            subtitle=f"[grey50]{dt_strftime}[/grey50]",
            subtitle_align="right",
        )

        # Separate the panel from other console output.
        console.line()
        console.print(panel)
        console.line()
