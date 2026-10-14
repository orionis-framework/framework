from orionis.console.commands.bootstrap._base import BootstrapCommand
from orionis.console.commands.bootstrap._service import Bootstrapper
from orionis.foundation.contracts.application import IApplication  # noqa: TC001

class BootstrapLifespanCommand(BootstrapCommand):
    """Enable native application lifespan callbacks."""

    signature = "bootstrap:lifespan"
    description = "Create and register application lifespan callbacks."

    def bootstrap(self, app: IApplication) -> list[tuple[str, str]]:
        """
        Enable lifecycle callbacks.

        Parameters
        ----------
        app : IApplication
            Application providing the effective bootstrap path.

        Returns
        -------
        list[tuple[str, str]]
            Completed resource actions.
        """
        # Reuse the shared service to preserve custom callbacks and bootstrap code.
        return Bootstrapper(app).lifespan()
