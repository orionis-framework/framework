"""Display the active application environment."""

from orionis.console.base.command import BaseCommand
from orionis.console.output.console import Console
from orionis.foundation.contracts.application import IApplication

class EnvironmentCommand(BaseCommand):
    """Display the active application environment."""

    # ruff: noqa: TC001

    timestamps: bool = False
    """Timestamps flag used by ``EnvironmentCommand``."""
    signature: str = "env"
    """Signature identifier: ``env``."""
    description: str = "Display the current application environment."
    """Description identifier: ``Display the current application environment.``."""

    def handle(self, app: IApplication, console: Console) -> None:
        """
        Print the environment configured for the running application.

        Parameters
        ----------
        app : orionis.IApplication
            Application providing the active environment value.
        console : orionis.console.Console
            Console used to display the environment.

        Returns
        -------
        None
            Write the environment name to the console.
        """
        environment = app.config("app.env")
        console.info(f"Current application environment: {environment}", timestamp=False)
