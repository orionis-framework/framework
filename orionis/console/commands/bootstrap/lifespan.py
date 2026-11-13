# ruff: noqa: TC001
# Keep runtime reflection annotations and intentionally deferred imports.
"""Enable native application lifespan callbacks."""

from orionis.console.commands.bootstrap._base import BootstrapCommand
from orionis.console.commands.bootstrap._service import Bootstrapper
from orionis.foundation.contracts.application import IApplication


class BootstrapLifespanCommand(BootstrapCommand):
    """Enable native application lifespan callbacks."""

    signature = "bootstrap:lifespan"
    """Signature identifier: ``bootstrap:lifespan``."""
    description = "Create and register application lifespan callbacks."
    """
    Description identifier: ``Create and register application lifespan callbacks.``.
    """

    def bootstrap(self, app: IApplication) -> list[tuple[str, str]]:
        """
        Enable lifecycle callbacks.

        Parameters
        ----------
        app : orionis.IApplication
            Application providing the effective bootstrap path.

        Returns
        -------
        list[tuple[str, str]]
            Completed resource actions.
        """
        # Reuse the shared service to preserve custom callbacks and bootstrap code.
        return Bootstrapper(app).lifespan()
