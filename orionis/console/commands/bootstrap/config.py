from orionis.console.commands.bootstrap._base import BootstrapCommand
from orionis.console.commands.bootstrap._config import ConfigBootstrapper
from orionis.foundation.contracts.application import IApplication  # noqa: TC001

class BootstrapConfigCommand(BootstrapCommand):
    """Recover missing official configuration files from the master branch."""

    signature = "bootstrap:config"
    description = "Restore missing configuration files from the official master branch."

    def bootstrap(self, app: IApplication) -> list[tuple[str, str]]:
        """
        Recover missing configuration without replacing existing files.

        Parameters
        ----------
        app : IApplication
            Application providing the effective config path.

        Returns
        -------
        list[tuple[str, str]]
            Completed resource actions.
        """
        # Recover only missing official files through the validated downloader.
        return ConfigBootstrapper(app).bootstrap()
