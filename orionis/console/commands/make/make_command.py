import re
from pathlib import Path
from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.console.core.contracts.reactor import IReactor
from orionis.foundation.contracts.application import IApplication

# Pattern to validate that names consist of lowercase letters, digits and underscores
_NAME_RE: re.Pattern[str] = re.compile(r"^[a-z][a-z0-9_]*$")

# Pattern to validate that signatures consist of lowercase letters,
# digits, underscores and colons
_SIGNATURE_RE: re.Pattern[str] = re.compile(r"^[a-z][a-z0-9_:]*$")

# Absolute path to the command stub template file
_STUB_PATH: Path = Path(__file__).parent.parent.parent / "stubs" / "command.stub"

class MakeCommand(BaseCommand):

    # ruff: noqa: TC001, ASYNC240

    # Indicates whether timestamps will be shown in the command output
    timestamps: bool = False

    # Command signature and description
    signature: str = "make:command"

    # Command description
    description: str = "Creates a new custom console command for the Orionis CLI."

    # Command arguments definition
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="name",
            type_=str,
            required=True,
            help=(
                "The filename and class name for the new console command "
                "(e.g., 'send_email_command')."
            ),
        ),
        Argument(
            name_or_flags=["--signature", "-s"],
            type_=str,
            required=True,
            help="The signature for the new command.",
        ),
        Argument(
            name_or_flags=["--description", "-d"],
            type_=str,
            required=False,
            help="The description for the new command.",
        ),
    ]

    async def handle(
        self,
        app: IApplication,
        reactor: IReactor,
    ) -> None:
        """
        Create a new custom console command file.

        Validate arguments, check for signature duplication, load a stub template,
        replace placeholders, and write the code to a new file in the commands
        directory. Ensure the file does not already exist.

        Parameters
        ----------
        app : IApplication
            Application instance for path resolution.
        reactor : IReactor
            Reactor instance for command information.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Insert a blank line before the command output for better readability
        self.newLine()

        try:

            # Retrieve the 'name' from the command arguments
            name: str = self.getArgument("name")

            # Validate that the name argument is provided
            if not name:
                error_msg = "The 'name' argument is required."
                raise ValueError(error_msg)

            # Retrieve the 'signature' from the command arguments
            signature: str = self.getArgument("signature", "custom:command")

            # Validate that the signature argument is provided
            if not signature:
                error_msg = "The 'signature' argument is required."
                raise ValueError(error_msg)

            # Retrieve the 'description' from the command arguments
            description: str = self.getArgument(
                "description", "A custom console command.",
            )

            # Validate the file name format
            if not _NAME_RE.match(name):
                error_msg = "Invalid 'name' format."
                raise ValueError(error_msg)

            # Validate the command signature format
            if not _SIGNATURE_RE.match(signature):
                error_msg = "Invalid 'signature' format."
                raise ValueError(error_msg)

            # Retrieve all registered commands to check for signature conflicts
            commands: list[dict] = await reactor.info()
            if any(cmd.get("signature") == signature for cmd in commands):
                error_msg = (
                    f"A command with the signature '{signature}' already exists. "
                    "Please choose another signature."
                )
                raise ValueError(error_msg)

            # Build the PascalCase class name from the underscore-separated file name
            class_name = "".join([w.capitalize() for w in name.split("_")])
            if not class_name.endswith("Command"):
                # Append the required 'Command' suffix if not already present
                class_name += "Command"

            # Load the stub template and substitute placeholders with actual values
            stub = _STUB_PATH.read_text(encoding="utf-8") # NOSONAR
            stub = stub.replace("{{class_name}}", class_name)
            stub = stub.replace("{{signature}}", signature)
            stub = stub.replace("{{description}}", description)

            # Resolve the target directory and normalise the file name
            commands_dir: Path  = app.path("app_console_commands")

            if not name.lower().endswith("command"):
                name = name.rstrip("_") + "_command"

            file_path = commands_dir / (name + ".py")

            # Check if the file already exists to prevent overwriting
            if file_path.exists():
                error_msg = (
                    f"The file [{file_path.relative_to(app.basePath)}] already exists. "
                    "Please choose another name."
                )
                raise OSError(error_msg)

            commands_dir.mkdir(parents=True, exist_ok=True)
            file_path.write_text(stub, encoding="utf-8") # NOSONAR
            file_path_rel = file_path.relative_to(app.basePath)
            self.success(f"Console command [{file_path_rel}] created successfully.")

        except (ValueError, OSError) as e:

            # Handle validation and file I/O errors
            self.error(f"Failed to create command: {e}")

        finally:

            # Insert a blank line after the command output for better readability
            self.newLine()
