from __future__ import annotations
import asyncio
import os
import time
from typing import TYPE_CHECKING
from orionis.support.facades.datetime import DateTime
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

if TYPE_CHECKING:
    from collections.abc import Generator
    from orionis.foundation.contracts.application import IApplication

# Shared terminal output interface reused across all startup display functions
_console = Console()

# Pre-built static splash panel displayed before server initialization begins
_BEFORE_STARTUP_PANEL: Panel = Panel(
    Text("⚡ Starting the Orionis server...", style="bold green"),
    title="Orionis Startup",
    border_style="green",
    padding=(1, 1),
)

# Mapping of GRANIAN_INTERFACE values to their human-readable display labels
_INTERFACE_LABELS: dict[str, str] = {
    "rsgi": "🦀 RSGI: Rust Network Protocol Servers",
    "asgi": "⚡ ASGI: Asynchronous Server Gateway Interface",
    "default": "🔧 Auto-detected",
}

def before_startup_orionis_generator() -> None:
    """
    Render a brief startup panel before the server begins accepting requests.

    Returns
    -------
    None
        Displays the panel for 0.5 s using a fullscreen context, then returns.
    """
    # Display the pre-built splash panel for 0.5 s in fullscreen mode
    with _console.screen():
        _console.print(_BEFORE_STARTUP_PANEL)
        time.sleep(0.5)

def after_startup_orionis_generator(host: str, port: int) -> None:
    """
    Render the server status panel after a successful startup.

    Parameters
    ----------
    host : str
        Hostname used to bind the server.
    port : int
        Port number used to bind the server.

    Returns
    -------
    None
        Prints the status panel to stdout and returns nothing.
    """
    # ruff: noqa: S104

    # Clear the terminal and print a blank line for spacing
    _console.clear()
    _console.line()
    dt_now = DateTime.now()
    now: str = dt_now.strftime("%Y-%m-%d %H:%M:%S")
    tz = dt_now.tzname()
    pid: int = os.getpid()

    # Environment variables take precedence over config values
    host: str = os.environ.get("GRANIAN_HOST", host)
    port: int = os.environ.get("GRANIAN_PORT", port)

    # Normalize loopback addresses to a human-readable label
    if host in ("127.0.0.1", "0.0.0.0"):
        host = "localhost"

    # Resolve the active event loop name and server interface label
    loop = asyncio.get_running_loop()
    _cls = type(loop)
    loop_name = f"{_cls.__module__.title()}.{_cls.__name__.title()}"
    interface = _INTERFACE_LABELS.get(os.environ.get("GRANIAN_INTERFACE", "default"))

    # Assemble the rich panel content
    panel_content: Text = Text.assemble(
        (" 🚀 Orionis HTTP Server \n", "bold white on green"),
        ("\n", ""),
        ("✅ The HTTP server has started successfully.\n", "bold green"),
        ("🔗 Service running at: ", "white"),
        (f"http://{host}:{port}\n", "bold cyan"), # NOSONAR
        (f"🕒 Started at: {tz} - {now}   ", "dim"),
        (f"🆔 PID: {pid}\n", "dim"),
        ("⚡ Orionis Loop: ", "cyan"),
        (f"{loop_name}\n", "bold magenta"),
        ("🌐 Server Interface: ", "cyan"),
        (f"{interface}\n", "bold magenta"),
        ("\n", ""),
        ("🛑 To stop the server, press ", "white"),
        ("Ctrl+C", "bold yellow"),
    )

    _console.print(
        Panel(
            panel_content,
            border_style="green",
            padding=(1, 2),
        ),
    )
    _console.line()

def startup_orionis_generator(app: IApplication) -> Generator[None]:
    """
    Yield control between the pre- and post-startup display steps.

    Parameters
    ----------
    app : IApplication
        Application instance used to read config values and mode flags.

    Returns
    -------
    Generator[None, None, None]
        Yields once; pre-startup runs before the yield, post-startup after.
    """
    # Only show panels in debug mode outside of production
    print_panel: bool = app.isDebug() and not app.isProduction()

    if print_panel:
        before_startup_orionis_generator()

    yield

    if print_panel:
        after_startup_orionis_generator(
            host="127.0.0.1",
            port=8000,
        )
