from orionis.console.commands.make._base import MakeStubCommand

class MakeConsoleListener(MakeStubCommand):
    """Generate a console task listener class."""

    timestamps: bool = False
    signature: str = "make:console-listener"
    description: str = "Creates a new console task listener class."
    template_name: str = "console_listener"
    path_key: str = "app_console_listeners"
    success_label: str = "Console task listener"
    postfix: str | None = "Listener"

