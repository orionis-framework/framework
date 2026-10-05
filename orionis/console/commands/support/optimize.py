import compileall
import sys
from pathlib import Path
from orionis.console.base.command import BaseCommand
from orionis.console.output.console import Console
from orionis.foundation.contracts.application import IApplication

_VENV_DIR_NAMES: frozenset[str] = frozenset(
    {".venv", "venv", "env", ".env", "virtualenv"},
)
_ACTIVE_VENV_BASENAME: str = (
    Path(sys.prefix).name if sys.prefix != sys.base_prefix else ""
)
_SKIP_DIRS: frozenset[str] = _VENV_DIR_NAMES | frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    },
)
if _ACTIVE_VENV_BASENAME:
    _SKIP_DIRS |= frozenset({_ACTIVE_VENV_BASENAME})

class OptimizeCommand(BaseCommand):
    """Compile application Python source files into optimized bytecode."""

    # ruff: noqa: TC001

    timestamps: bool = True
    signature: str = "optimize"
    description: str = "Compile application Python files to optimized bytecode."

    def handle(self, app: IApplication, console: Console) -> int: # NOSONAR
        """
        Compile Python modules below the application root.

        Parameters
        ----------
        app : IApplication
            Application providing the project root.
        console : Console
            Console used to report compilation results.

        Returns
        -------
        int
            Zero when every source compiles; one when compilation or traversal fails.
        """
        source_count = 0
        errors: list[str] = []
        for root, directories, filenames in app.basePath.walk(
            top_down=True,
            on_error=lambda error: errors.append(str(error)),
        ):
            directories[:] = [
                name
                for name in directories
                if name not in _SKIP_DIRS and not name.endswith(".egg-info")
            ]
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                source_count += 1
                source_file = root / filename
                try:
                    compiled = compileall.compile_file(
                        str(source_file),
                        force=True,
                        optimize=2,
                        quiet=1,
                    )
                except (OSError, RuntimeError, ValueError) as error:
                    errors.append(f"{source_file}: {error}")
                else:
                    if not compiled:
                        errors.append(f"Could not compile {source_file}.")

        if errors:
            console.error(
                f"Application optimization failed for {len(errors)} item(s).",
                timestamp=False,
            )
            for error in errors:
                console.error(error, timestamp=False)
            return 1

        console.success(
            f"Optimized {source_count} Python file(s).",
            timestamp=False,
        )
        return 0
