from pathlib import Path
from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.console.templates.stub import Stub
from orionis.foundation.contracts.application import IApplication  # noqa: TC001

class MakeStubCommand(BaseCommand):
    """Create application files from packaged stubs."""

    template_name: ClassVar[str]
    path_key: ClassVar[str]
    success_label: ClassVar[str]
    prefix: ClassVar[str | None] = None
    postfix: ClassVar[str | None] = None
    replacement_arguments: ClassVar[dict[str, str]] = {}
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="name",
            type_=str,
            required=True,
            help="The file and class name for the generated file.",
        ),
    ]

    def getTemplateName(self) -> str:
        """
        Return the selected template name.

        Returns
        -------
        str
            Stub template name without its ``.stub`` suffix.
        """
        return self.template_name

    def getReplacements(self) -> dict[str, str]:
        """
        Read string replacements from the parsed command arguments.

        Returns
        -------
        dict[str, str]
            Template placeholders mapped to their argument values.

        Raises
        ------
        TypeError
            If an argument mapped to a placeholder is not a string.
        """
        replacements: dict[str, str] = {}
        for placeholder, argument in self.replacement_arguments.items():
            value = self.getArgument(argument)
            if not isinstance(value, str):
                error_msg = f"The '{argument}' argument must be a string."
                raise TypeError(error_msg)
            replacements[placeholder] = value
        return replacements

    def createFile(
        self,
        app: IApplication,
        name: str,
        *,
        template_name: str | None = None,
        extension: str = "py",
        replacements: dict[str, str] | None = None,
    ) -> str:
        """
        Render one stub into its configured application directory.

        Parameters
        ----------
        app : IApplication
            Application that resolves the destination path.
        name : str
            File name and optional nested directory path.
        template_name : str | None, optional
            Stub override; the command's template is used when omitted.
        extension : str, optional
            Generated source extension. Defaults to ``"py"``.
        replacements : dict[str, str] | None, optional
            Placeholder values; command replacements are used when omitted.

        Returns
        -------
        str
            Generated path relative to the application base directory.

        Raises
        ------
        OSError
            If the generated file cannot be created.
        TypeError
            If the application path or replacement values are invalid.
        ValueError
            If the name or extension is invalid.
        """
        directory = app.path(self.path_key)
        if not isinstance(directory, Path):
            error_msg = f"Application path '{self.path_key}' is not configured."
            raise TypeError(error_msg)

        stub = Stub(
            template_name=template_name or self.getTemplateName(),
            class_name=name,
            prefix=self.prefix,
            postfix=self.postfix,
            replacements=(
                self.getReplacements() if replacements is None else replacements
            ),
        )
        return stub.create(
            directory=directory,
            relative_to=app.basePath,
            extension=extension,
        )

    def createFiles(
        self,
        app: IApplication,
        name: str,
    ) -> tuple[tuple[str, str], ...]:
        """
        Create the files produced by this command.

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
        return ((self.success_label, self.createFile(app, name)),)

    async def handle(self, app: IApplication) -> None:
        """
        Create files declared by the command's stub configuration.

        Parameters
        ----------
        app : IApplication
            Application that provides destination paths.

        Returns
        -------
        None
            Write success or error details to the command output.
        """
        self.newLine()
        try:
            name = self.getArgument("name")
            if not name:
                error_msg = "The 'name' argument is required."
                raise ValueError(error_msg)

            for label, file_path in self.createFiles(app, name):
                self.success(f"{label} [{file_path}] created successfully.")
        except (OSError, TypeError, ValueError) as error:
            self.error(error)
        finally:
            self.newLine()

