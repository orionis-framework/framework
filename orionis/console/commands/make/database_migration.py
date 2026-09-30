import re
from pathlib import Path
from orionis.console.commands.make._base import MakeStubCommand
from orionis.foundation.contracts.application import IApplication  # noqa: TC001
from orionis.support.facades.datetime import DateTime

class MakeDatabaseMigration(MakeStubCommand):
    """Generate a migration named for its creation date and time."""

    timestamps: bool = False
    signature: str = "make:database-migration"
    description: str = "Creates a timestamped database migration."
    template_name: str = "database_migration"
    path_key: str = "database_migrations"
    success_label: str = "Database migration"

    def createFiles(
        self,
        app: IApplication,
        name: str,
    ) -> tuple[tuple[str, str], ...]:
        """
        Create a migration with a timestamp from the application timezone.

        Parameters
        ----------
        app : IApplication
            Application that resolves the migrations directory.
        name : str
            Migration name and optional nested directory path.

        Returns
        -------
        tuple[tuple[str, str], ...]
            Label and application-relative path of the new migration.

        Raises
        ------
        ValueError
            If the migration name cannot form a Python module name.
        """
        normalized = name.replace("\\", "/")
        parts = normalized.split("/")
        source_name = Path(parts[-1]).stem
        if re.fullmatch(r"[a-z][a-z0-9_]*", source_name.lower()) is None:
            error_msg = f"Invalid filename '{name}' format."
            raise ValueError(error_msg)

        class_name = "".join(word.capitalize() for word in source_name.split("_"))
        timestamp = DateTime.now().strftime("%Y%m%d%H%M%S")
        parts[-1] = f"m{timestamp}_{source_name}"
        file_path = self.createFile(
            app,
            "/".join(parts),
            replacements={"migration_class_name": class_name},
        )
        return ((self.success_label, file_path),)
