from pathlib import Path
from orionis.console.commands.make._base import MakeStubCommand
from orionis.foundation.contracts.application import IApplication  # noqa: TC001

class MakeTest(MakeStubCommand):
    """Generate an application test case."""

    timestamps: bool = False
    signature: str = "make:test"
    description: str = "Creates a new application test case."
    template_name: str = "test"
    path_key: str = "tests"
    success_label: str = "Test"

    def createFiles(
        self,
        app: IApplication,
        name: str,
    ) -> tuple[tuple[str, str], ...]:
        """
        Create a test module with a discoverable filename.

        Parameters
        ----------
        app : IApplication
            Application that resolves the tests directory.
        name : str
            Test name and optional nested directory path.

        Returns
        -------
        tuple[tuple[str, str], ...]
            Label and generated path relative to the application root.

        Raises
        ------
        ValueError
            If the final path component does not contain a test name.
        """
        normalized = name.replace("\\", "/")
        parent, separator, filename = normalized.rpartition("/")
        stem = filename.removesuffix(Path(filename).suffix)
        if stem in {"", ".", ".."}:
            error_msg = f"Invalid filename '{name}' format."
            raise ValueError(error_msg)

        if not stem.lower().startswith("test_"):
            filename = f"test_{filename}"
        target_name = f"{parent}{separator}{filename}"
        return ((self.success_label, self.createFile(app, target_name)),)
