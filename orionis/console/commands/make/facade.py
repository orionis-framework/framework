from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.commands.make._base import MakeStubCommand
from orionis.foundation.contracts.application import IApplication  # noqa: TC001

class MakeFacade(MakeStubCommand):
    """Generate a facade and its typing interface."""

    timestamps: bool = False
    signature: str = "make:facade"
    description: str = "Creates a new facade class and interface."
    template_name: str = "facade"
    path_key: str = "app_facades"
    success_label: str = "Facade"
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
        app : IApplication
            Application that resolves the destination path.
        name : str
            File name and optional nested directory path.

        Returns
        -------
        tuple[tuple[str, str], ...]
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

