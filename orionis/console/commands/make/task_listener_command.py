import re
from pathlib import Path
from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.foundation.contracts.application import IApplication

# Pattern to validate that names consist of lowercase letters, digits and underscores
_NAME_RE: re.Pattern[str] = re.compile(r"^[a-z][a-z0-9_]*$")

# Absolute path to the task listener stub template file
_STUB_PATH: Path = (
    Path(__file__).parent.parent.parent / "stubs" / "task_listener.stub"
)

class MakeTaskListener(BaseCommand):

    # ruff: noqa: TC001, ASYNC240

    # Indicates whether timestamps will be shown in the command output
    timestamps: bool = False

    # Command signature and description
    signature: str = "make:task:listener"

    # Command description
    description: str = "Creates a new task listener class."

    # Command arguments definition
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="name",
            type_=str,
            required=True,
            help=(
                "The filename and class name for the new task listener "
                "(e.g., 'send_email_listener')."
            ),
        ),
    ]

    async def handle(self, app: IApplication) -> None:
        """
        Create a new task listener class file.

        Parameters
        ----------
        app : IApplication
            The application instance providing configuration and paths.

        Returns
        -------
        None
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

            # Validate the file name format
            if not _NAME_RE.match(name):
                error_msg = "Invalid 'name' format."
                raise ValueError(error_msg)

            # Load the stub template content
            stub = _STUB_PATH.read_text(encoding="utf-8") # NOSONAR

            # Build the PascalCase class name from the underscore-separated file name
            class_name = "".join([w.capitalize() for w in name.split("_")])
            if not class_name.endswith("Listener"):
                # Append the required 'Listener' suffix if not already present
                class_name += "Listener"

            # Replace placeholders in the stub with the actual class name
            stub = stub.replace("{{class_name}}", class_name)

            # Resolve the target directory and normalise the file name
            listeners_dir: Path = app.path("app_console_listeners")

            if not name.lower().endswith("listener"):
                name = name.rstrip("_") + "_listener"

            file_path = listeners_dir / (name + ".py")

            # Check if the file already exists to prevent overwriting
            if file_path.exists():
                file_path_rel = file_path.relative_to(app.basePath)
                error_msg = (
                    f"The file [{file_path_rel}] already exists. "
                    "Please choose another name."
                )
                raise OSError(error_msg)

            listeners_dir.mkdir(parents=True, exist_ok=True)
            file_path.write_text(stub, encoding="utf-8") # NOSONAR
            file_path_rel = file_path.relative_to(app.basePath)
            self.success(
                f"Task listener [{file_path_rel}] created successfully.",
            )

        except (ValueError, OSError) as e:
            # Handle validation and file I/O errors
            self.error(f"Failed to create task listener: {e}")

        finally:
            # Insert a blank line after the command output for readability
            self.newLine()
