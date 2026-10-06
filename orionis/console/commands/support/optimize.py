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
    """Validate application Python sources without writing bytecode."""

    # ruff: noqa: TC001

    timestamps: bool = True
    signature: str = "optimize"
    description: str = "Validate application Python files without writing bytecode."

    def handle(self, app: IApplication, console: Console) -> int: # NOSONAR
        """
        Validate Python modules below the application root in memory.

        Parameters
        ----------
        app : IApplication
            Application providing the project root.
        console : Console
            Console used to report validation results.

        Returns
        -------
        int
            Zero when every source validates; one when validation or traversal fails.
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
                    compile(
                        source_file.read_bytes(),
                        str(source_file),
                        "exec",
                        optimize=2,
                    )
                except (OSError, RuntimeError, SyntaxError, ValueError) as error:
                    errors.append(f"{source_file}: {error}")

        if errors:
            console.error(
                f"Application source validation failed for {len(errors)} item(s).",
                timestamp=False,
            )
            for error in errors:
                console.error(error, timestamp=False)
            return 1

        console.success(
            f"Validated {source_count} Python file(s) without writing bytecode.",
            timestamp=False,
        )
        return 0
