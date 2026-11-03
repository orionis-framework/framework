"""Place the application in runtime maintenance mode."""

from orionis.console.commands.support.maintenance import MaintenanceModeCommand

class DownCommand(MaintenanceModeCommand):
    """Place the application in runtime maintenance mode."""

    signature: str = "down"
    """Signature identifier: ``down``."""
    description: str = "Put the application into maintenance mode."
    """Description identifier: ``Put the application into maintenance mode.``."""
    state: str = "down"
    """State identifier: ``down``."""
    status_message: str = "The application is now in maintenance mode."
    """
    Confirmation displayed when the application enters maintenance mode.
    """
