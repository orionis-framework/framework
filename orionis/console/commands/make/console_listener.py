"""Generate a console task listener class."""

from orionis.console.commands.make._base import MakeStubCommand

class MakeConsoleListener(MakeStubCommand):
    """Generate a console task listener class."""

    timestamps: bool = False
    """Timestamps flag used by ``MakeConsoleListener``."""
    signature: str = "make:console-listener"
    """Signature identifier: ``make:console-listener``."""
    description: str = "Creates a new console task listener class."
    """Description identifier: ``Creates a new console task listener class.``."""
    template_name: str = "console_listener"
    """Template name identifier: ``console_listener``."""
    path_key: str = "app_console_listeners"
    """Path key identifier: ``app_console_listeners``."""
    success_label: str = "Console task listener"
    """Success label identifier: ``Console task listener``."""
    postfix: str | None = "Listener"
    """Postfix identifier: ``Listener``."""

