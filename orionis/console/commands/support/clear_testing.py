from orionis.console.base.command import BaseCommand
from orionis.console.commands.support._clear import clear_files
from orionis.console.output.console import Console
from orionis.foundation.contracts.application import IApplication

class ClearTestingCommand(BaseCommand):
    """Remove saved test-run result files."""

    # ruff: noqa: TC001

    timestamps: bool = False
    signature: str = "clear:testing"
    description: str = "Clear cached test-run results."

    def handle(self, app: IApplication, console: Console) -> int:
        """
        Remove JSON test results from the framework test cache.

        Parameters
        ----------
        app : IApplication
            Application providing the framework storage path.
        console : Console
            Console used to report the cleanup result.

        Returns
        -------
        int
            Zero when every result file is removed; one when removal fails.
        """
        directory = app.path("storage_framework") / "cache" / "testing"
        removed_count, errors = clear_files(directory, ".json")
        console.info(
            f"Test result cache cleared ({removed_count} file(s)).",
            timestamp=False,
        )
        for error in errors:
            console.error(error, timestamp=False)
        return int(bool(errors))
