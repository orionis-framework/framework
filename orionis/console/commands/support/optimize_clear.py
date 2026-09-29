import shutil
import sys
from pathlib import Path
from orionis.console.base.command import BaseCommand
from orionis.console.output.console import Console
from orionis.foundation.contracts.application import IApplication

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

# Build artifact directory names to remove during cleanup
_ARTIFACT_DIRS: tuple[str, ...] = ("build", "dist", "orionis.egg-info")

class OptimizeClearCommand(BaseCommand):

    # ruff: noqa: TC001

    # Indicates whether timestamps will be shown in the command output
    timestamps: bool = True

    # Command signature and description
    signature: str = "optimize:clear"

    # Command description
    description: str = (
        "Removes configuration, route, and command caches, "
        "Python bytecode, and build artifacts."
    )

    def handle(
        self,
        app: IApplication,
        console: Console,
    ) -> None:
        """
        Clear Python bytecode, cache directories, and build artifacts.

        Parameters
        ----------
        app : IApplication
            Application instance for path resolution.
        console : Console
            Console instance for output.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Cache the base path to avoid repeated property dispatch
        base_path = app.basePath

        # Traverse the project tree and remove all __pycache__ directories,
        # skipping virtual environment directories
        for root, dirs, _ in base_path.walk(top_down=True):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            if "__pycache__" in dirs:
                shutil.rmtree(root / "__pycache__", ignore_errors=True)
                dirs.remove("__pycache__")

        # Log the results of clearing bytecode and caches
        console.info("Python bytecode cleared!", timestamp=False)

        # Remove build artifact directories if they exist
        for artifact_dir in _ARTIFACT_DIRS:
            artifact_path = base_path / artifact_dir
            if artifact_path.is_dir():
                shutil.rmtree(artifact_path, ignore_errors=True)

        # Log the results of clearing build artifacts
        console.info("Build artifacts cleared!", timestamp=False)

        # Remove the framework cache directory if it exists
        cache_path: Path = app.path("storage_framework")
        if cache_path.exists():
            shutil.rmtree(cache_path)

        # Log the results of clearing framework cache
        console.info("Commands cache cleared!", timestamp=False)
        console.info("Route cache cleared!", timestamp=False)
        console.info("Configuration cache cleared!", timestamp=False)

        # Recreate the framework cache directory
        cache_path.mkdir(parents=True, exist_ok=True)

        # Log the results of recreating the framework cache directory
        console.info("Framework cache directory has been recreated.", timestamp=False)
