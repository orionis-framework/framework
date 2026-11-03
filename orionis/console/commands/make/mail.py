"""Generate a reusable Mailable class."""

from orionis.console.commands.make._base import MakeStubCommand

class MakeMail(MakeStubCommand):
    """Generate a reusable Mailable class."""

    timestamps: bool = False
    """Timestamps flag used by ``MakeMail``."""
    signature: str = "make:mail"
    """Signature identifier: ``make:mail``."""
    description: str = "Creates a reusable mail notification class."
    """Description identifier: ``Creates a reusable mail notification class.``."""
    template_name: str = "mail"
    """Template name identifier: ``mail``."""
    path_key: str = "app_notifications"
    """Path key identifier: ``app_notifications``."""
    success_label: str = "Mail"
    """Success label identifier: ``Mail``."""
    postfix: str | None = "Mail"
    """Postfix identifier: ``Mail``."""

