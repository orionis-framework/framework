from orionis.console.commands.make._base import MakeStubCommand

class MakeMail(MakeStubCommand):
    """Generate a reusable Mailable class."""

    timestamps: bool = False
    signature: str = "make:mail"
    description: str = "Creates a reusable mail notification class."
    template_name: str = "mail"
    path_key: str = "app_notifications"
    success_label: str = "Mail"
    postfix: str | None = "Mail"

