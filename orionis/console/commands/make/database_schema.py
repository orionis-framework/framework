"""Generate a reusable database table definition module."""

from orionis.console.commands.make._base import MakeStubCommand


class MakeDatabaseSchema(MakeStubCommand):
    """Generate a reusable database table definition module."""

    timestamps: bool = False
    """Timestamps flag used by ``MakeDatabaseSchema``."""
    signature: str = "make:database-schema"
    """Signature identifier: ``make:database-schema``."""
    description: str = "Creates a reusable database table schema."
    """Description identifier: ``Creates a reusable database table schema.``."""
    template_name: str = "database_schema"
    """Template name identifier: ``database_schema``."""
    path_key: str = "database_schemas"
    """Path key identifier: ``database_schemas``."""
    success_label: str = "Database schema"
    """Success label identifier: ``Database schema``."""
    postfix: str | None = "Schema"
    """Postfix identifier: ``Schema``."""
