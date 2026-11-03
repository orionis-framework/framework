"""Recover missing official configuration files from the master branch."""

from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.commands.bootstrap._base import BootstrapCommand
from orionis.console.commands.bootstrap._config import ConfigBootstrapper
from orionis.foundation.contracts.application import IApplication  # noqa: TC001

class BootstrapConfigCommand(BootstrapCommand):
    """Recover missing official configuration files from the master branch."""

    signature = "bootstrap:config"
    """Signature identifier: ``bootstrap:config``."""
    description = "Restore missing configuration files from the official master branch."
    """
    Description identifier: ``Restore missing configuration files from the official
    master branch.``.
    """
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="file",
            type_=str,
            nargs="?",
            default=None,
            help=(
                "Configuration name without .py (for example, app or database). "
                "Omit to restore all missing files; options are read from master."
            ),
        ),
    ]
    """Command-line argument declarations accepted by this command."""

    def bootstrap(self, app: IApplication) -> list[tuple[str, str]]:
        """
        Recover missing configuration without replacing existing files.

        Parameters
        ----------
        app : orionis.IApplication
            Application providing the effective config path.

        Returns
        -------
        list[tuple[str, str]]
            Completed resource actions.
        """
        # Recover the requested file, or all missing official configuration.
        return ConfigBootstrapper(app).bootstrap(self.getArgument("file"))
