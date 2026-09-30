from orionis.console.commands.support.maintenance import MaintenanceModeCommand

class UpCommand(MaintenanceModeCommand):
    """Restore normal application traffic after maintenance."""

    signature: str = "up"
    description: str = "Bring the application out of maintenance mode."
    state: str = "up"
    status_message: str = "The application is now available."
