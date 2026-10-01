import re
from asyncio import to_thread
from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.commands.make._base import MakeStubCommand
from orionis.console.core.contracts.reactor import IReactor  # noqa: TC001
from orionis.foundation.contracts.application import IApplication  # noqa: TC001

_SIGNATURE_RE: re.Pattern[str] = re.compile(
    r"[a-z][a-z0-9]*(?::[a-z][a-z0-9]*(?:-[a-z0-9]+)*)?",
)

class MakeConsoleCommand(MakeStubCommand):
    """Generate a custom command for the Orionis CLI."""

    timestamps: bool = False
    signature: str = "make:console-command"
    description: str = "Creates a new custom console command."
    template_name: str = "console_command"
    path_key: str = "app_console_commands"
    success_label: str = "Console command"
    postfix: str | None = "Command"
    replacement_arguments: ClassVar[dict[str, str]] = {
        "signature": "signature",
        "description": "description",
    }
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="name",
            type_=str,
            required=True,
            help="The file and class name for the new console command.",
        ),
        Argument(
            name_or_flags=["--signature", "-s"],
            type_=str,
            required=True,
            help="The unique signature registered for the command.",
        ),
        Argument(
            name_or_flags=["--description", "-d"],
            type_=str,
            required=False,
            help="A short description shown in command help.",
        ),
    ]

    def getReplacements(self) -> dict[str, str]:
        """
        Return the signature and description placeholders.

        Returns
        -------
        dict[str, str]
            Placeholder values for the console command stub.
        """
        signature = self.getArgument("signature")
        description = self.getArgument("description")
        if description is None:
            description = "A custom console command."
        if not isinstance(signature, str) or not isinstance(description, str):
            error_msg = "Command signature and description must be strings."
            raise TypeError(error_msg)
        return {
            "signature_literal": repr(signature),
            "description_literal": repr(description),
        }

    async def handle(
        self,
        app: IApplication,
        reactor: IReactor,
    ) -> None:
        """
        Validate a command signature and create its file on a worker thread.

        Parameters
        ----------
        app : IApplication
            Application that resolves the destination path.
        reactor : IReactor
            Registered command collection used to reject duplicate signatures.

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

            signature = self.getArgument("signature")
            replacements = self.getReplacements()
            if _SIGNATURE_RE.fullmatch(signature) is None:
                error_msg = "Invalid 'signature' format."
                raise ValueError(error_msg)
            if await reactor.hasCommand(signature):
                error_msg = (
                    f"A command with the signature '{signature}' already exists."
                )
                raise ValueError(error_msg)

            file_path = await to_thread(
                self.createFile,
                app,
                name,
                replacements=replacements,
            )
            self.success(f"Console command [{file_path}] created successfully.")
        except (OSError, TypeError, ValueError) as error:
            self.error(error)
        finally:
            self.newLine()

