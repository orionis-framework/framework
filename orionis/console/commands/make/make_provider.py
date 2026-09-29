import re
from pathlib import Path
from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.foundation.contracts.application import IApplication

# Pattern to validate that names consist of lowercase letters, digits and underscores
_NAME_RE: re.Pattern[str] = re.compile(r"^[a-z][a-z0-9_]*$")

# Absolute paths to the eager and deferred provider stub template files
_EAGER_STUB_PATH: Path = (
    Path(__file__).parent.parent.parent / "stubs" / "eager_provider.stub"
)
_DEFERRED_STUB_PATH: Path = (
    Path(__file__).parent.parent.parent / "stubs" / "deferred_provider.stub"
)

class MakeProvider(BaseCommand):

    # ruff: noqa: TC001, ASYNC240

    # Indicates whether timestamps will be shown in the command output
    timestamps: bool = False

    # Command signature and description
    signature: str = "make:provider"

    # Command description
    description: str = (
        "Creates a new provider class file in the providers directory."
    )

    # Command arguments definition
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="name",
            type_=str,
            required=True,
            help=(
                "The filename and class name for the new provider class"
            ),
        ),
        Argument(
            name_or_flags=["--deferred"],
            default=False,
            help=(
                "If set, the provider will be deferred and only loaded "
                "when needed."
            ),
            action="store_true",
        ),
    ]

    async def handle(self, app: IApplication) -> None:
        """
        Create a new provider class file in the providers directory.

        Parameters
        ----------
        app : IApplication
            The application instance used to access paths and configuration.

        Returns
        -------
        None
            Outputs success or error messages to the console.
        """
        # Insert a blank line before the command output for readability
        self.newLine()

        try:

            # Retrieve the 'name' argument from command arguments
            name: str = self.getArgument("name")

            # Validate that the name argument is provided
            if not name:
                error_msg = "The 'name' argument is required."
                raise ValueError(error_msg)

            # Validate the file name format
            if not _NAME_RE.match(name):
                error_msg = "Invalid 'name' format."
                raise ValueError(error_msg)

            # Retrieve the 'deferred' flag from command arguments
            deferred: bool = self.getArgument("deferred")

            # Select the stub template based on whether the provider is deferred
            stub_path = _DEFERRED_STUB_PATH if deferred else _EAGER_STUB_PATH

            # Load the stub template content
            stub: str = stub_path.read_text(encoding="utf-8") # NOSONAR

            # Build the PascalCase class name from the underscore-separated file name
            class_name: str = "".join([w.capitalize() for w in name.split("_")])
            if not class_name.endswith("Provider"):
                # Append the required 'Provider' suffix if not already present
                class_name += "Provider"

            # Substitute the class name placeholder in the stub template
            stub = stub.replace("{{class_name}}", class_name)

            # Resolve the target directory and normalise the file name
            providers_dir: Path = app.path("app_providers")

            if not name.lower().endswith("provider"):
                name = name.rstrip("_") + "_provider"

            file_path: Path = providers_dir / (name + ".py")

            # Check if the file already exists to prevent overwriting
            if file_path.exists():
                file_path_rel: Path = file_path.relative_to(app.basePath)
                error_msg = (
                    f"The file [{file_path_rel}] already exists. "
                    "Please choose another name."
                )
                raise OSError(error_msg)

            providers_dir.mkdir(parents=True, exist_ok=True)
            file_path.write_text(stub, encoding="utf-8") # NOSONAR
            file_path_rel = file_path.relative_to(app.basePath)
            self.success(f"Provider [{file_path_rel}] created successfully.")

        except (ValueError, OSError) as e:

            # Handle validation and file I/O errors
            self.error(f"Failed to create provider: {e}")

        finally:

            # Insert a blank line after the command output for readability
            self.newLine()
