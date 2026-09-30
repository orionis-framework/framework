from orionis.console.commands.support.maintenance import MaintenanceModeCommand

class DownCommand(MaintenanceModeCommand):
    """Place the application in runtime maintenance mode."""

    signature: str = "down"
    description: str = "Put the application into maintenance mode."
    state: str = "down"
    status_message: str = "The application is now in maintenance mode."
