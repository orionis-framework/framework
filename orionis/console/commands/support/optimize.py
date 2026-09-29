import os
import sys
import compileall
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path
from orionis.console.base.command import BaseCommand

# Frozen set of well-known virtual environment directory names to exclude
_VENV_DIR_NAMES: frozenset[str] = frozenset(
    {".venv", "venv", "env", ".env", "virtualenv"},
)

# Active virtual environment directory base name; empty string when not inside a venv
_ACTIVE_VENV_BASENAME: str = (
    Path(sys.prefix).name if sys.prefix != sys.base_prefix else ""
)

# Complete set of directory names to exclude during the project tree walk
_SKIP_DIRS: frozenset[str] = (
    _VENV_DIR_NAMES | frozenset({_ACTIVE_VENV_BASENAME})
    if _ACTIVE_VENV_BASENAME
    else _VENV_DIR_NAMES
)

# Preconfigured callable for bytecode compilation with fixed parameters
_COMPILE_FILE = partial(compileall.compile_file, force=True, optimize=2, quiet=1)

class OptimizeCommand(BaseCommand):

    # Indicates whether timestamps will be shown in the command output
    timestamps: bool = True

    # Command signature and description
    signature: str = "optimize"

    # Command description
    description: str = (
        "Compiles Python files to optimized bytecode and removes "
        "configuration, route, and command caches."
    )

    def handle(self) -> None:
        """Compile project Python files into optimized bytecode.

        Returns
        -------
        None
            Return ``None`` after reporting success or failure to the console.
        """
        try:

            # Local reference to the OS path join function
            path_join = os.path.join

            # Traverse the project tree and collect all Python source file paths,
            # skipping virtual environment directories
            py_files: list[str] = []
            for root, dirs, files in os.walk(".", topdown=True):
                dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
                py_files.extend(
                    path_join(root, f) for f in files if f.endswith(".py")
                )

            # Compile all collected files in parallel across all available CPU cores
            with ProcessPoolExecutor() as executor:
                list(executor.map(_COMPILE_FILE, py_files, chunksize=4))

            # Log the results of the optimization process to the console
            self.success(
                "Application optimized successfully.",
                timestamp=False,
            )

        except (OSError, ValueError, RuntimeError) as e:

            # Log any errors that occur during the optimization process to the console
            self.error(
                f"An error occurred during optimization: {e}",
                timestamp=False,
            )
