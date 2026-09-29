from rich.console import Console
from rich.panel import Panel
from orionis.console.base.command import BaseCommand
from orionis.metadata import framework
from orionis.support.facades.datetime import DateTime

# Panel title — built once at import time from static framework constants
_PANEL_TITLE: str = (
    f"[bold green]{framework.NAME.capitalize()} Framework | v{framework.VERSION}[/]"
)

# Panel body — assembled once at import time; all constituent values are static
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

    # Indicates whether timestamps will be shown in the command output
    timestamps: bool = False

    # Command signature and description
    signature: str = "about"

    # Command description
    description: str = "Displays the Orionis framework version and metadata."

    def handle(
        self,
        console: Console,
    ) -> None:
        """
        Display Orionis framework version and metadata.

        Retrieves the version and metadata from the framework module and prints it in a
        formatted panel to the console. If the '--without-console' flag is set, returns
        only the version string.

        Parameters
        ----------
        console : Console
            Rich console instance for output.

        Returns
        -------
        None
            This method does not return a value. Output is sent to the console.
        """
        # Retrieve the current timestamp for the panel subtitle
        dt_strftime = DateTime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Assemble the panel with the precomputed static content and dynamic subtitle
        panel = Panel(
            _PANEL_BODY,
            title=_PANEL_TITLE,
            border_style="bright_blue",
            padding=(1, 2),
            expand=False,
            subtitle=f"[grey50]{dt_strftime}[/grey50]",
            subtitle_align="right",
        )

        # Print a blank line, the panel, and another blank line for spacing
        console.line()
        console.print(panel)
        console.line()
