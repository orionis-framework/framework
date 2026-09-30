from pathlib import Path
from orionis.console.base.command import BaseCommand
from orionis.console.commands.support._clear import clear_files
from orionis.console.output.console import Console
from orionis.foundation.contracts.application import IApplication

class ClearViewsCommand(BaseCommand):
    """Remove compiled template bytecode from the configured view cache."""

    # ruff: noqa: TC001

    timestamps: bool = False
    signature: str = "clear:views"
    description: str = "Clear compiled view templates."

    def handle(self, app: IApplication, console: Console) -> int:
        """
        Remove Jinja bytecode cache files while preserving the cache directory.

        Parameters
        ----------
        app : IApplication
            Application providing view cache configuration and base path.
        console : Console
            Console used to report the cleanup result.

        Returns
        -------
        int
            Zero when every cache file is removed; one when removal fails.
        """
        cache_path = app.config("view.cache_path")
        if cache_path is None:
            console.info("View bytecode caching is disabled.", timestamp=False)
            return 0
        if not isinstance(cache_path, str):
            console.error("The configured view cache path is invalid.", timestamp=False)
            return 1

        directory = Path(cache_path)
        if not directory.is_absolute():
            directory = app.basePath / directory
        removed_count, errors = clear_files(directory, ".cache")
        console.info(
            f"View cache cleared ({removed_count} file(s)).",
            timestamp=False,
        )
        for error in errors:
            console.error(error, timestamp=False)
        return int(bool(errors))
