# ruff: noqa: TC001
# Keep runtime reflection annotations and intentionally deferred imports.
"""Generate a facade and its typing interface."""

from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.commands.make._base import MakeStubCommand
from orionis.foundation.contracts.application import IApplication


class MakeFacade(MakeStubCommand):
    """Generate a facade and its typing interface."""

    timestamps: bool = False
    """Timestamps flag used by ``MakeFacade``."""
    signature: str = "make:facade"
    """Signature identifier: ``make:facade``."""
    description: str = "Creates a new facade class and interface."
    """Description identifier: ``Creates a new facade class and interface.``."""
    template_name: str = "facade"
    """Template name identifier: ``facade``."""
    path_key: str = "app_facades"
    """Path key identifier: ``app_facades``."""
    success_label: str = "Facade"
    """Success label identifier: ``Facade``."""
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="name",
            type_=str,
            required=True,
            help="The file and class name for the new facade.",
        ),
        Argument(
            name_or_flags=["--accessor", "-a"],
            type_=str,
            required=True,
            help="The service identifier in the application container.",
        ),
    ]
    """Command-line argument declarations accepted by this command."""

    def getReplacements(self) -> dict[str, str]:
        """
        Return a Python string literal for the configured accessor.

        Returns
        -------
        dict[str, str]
            Accessor literal inserted into the generated facade.

        Raises
        ------
        TypeError
            If the accessor argument is not a string.
        """
        accessor = self.getArgument("accessor")
        if not isinstance(accessor, str):
            error_msg = "The 'accessor' argument must be a string."
            raise TypeError(error_msg)
        return {"accessor_literal": repr(accessor)}

    def createFiles(
        self,
        app: IApplication,
        name: str,
    ) -> tuple[tuple[str, str], ...]:
        """
        Create a facade implementation and its ``.pyi`` interface.

        Parameters
        ----------
        app : orionis.IApplication
            Application that resolves the destination path.
        name : str
            File name and optional nested directory path.

        Returns
        -------
        tuple[tuple[str, str], ``...``]
            Success labels and generated application-relative paths.
        """
        implementation = self.createFile(app, name)
        interface = self.createFile(
            app,
            name,
            template_name="facade_interface",
            extension="pyi",
            replacements={},
        )
        return (
            ("Facade", implementation),
            ("Facade interface", interface),
        )
