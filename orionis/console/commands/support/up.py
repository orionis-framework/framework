"""Restore normal application traffic after maintenance."""

from orionis.console.commands.support.maintenance import MaintenanceModeCommand


class UpCommand(MaintenanceModeCommand):
    """Restore normal application traffic after maintenance."""

    signature: str = "up"
    """Signature identifier: ``up``."""
    description: str = "Bring the application out of maintenance mode."
    """Description identifier: ``Bring the application out of maintenance mode.``."""
    state: str = "up"
    """State identifier: ``up``."""
    status_message: str = "The application is now available."
    """Confirmation displayed when the application leaves maintenance mode."""
