from orionis.console.commands.make._base import MakeStubCommand

class MakeDatabaseSchema(MakeStubCommand):
    """Generate a reusable database table definition holder."""

    timestamps: bool = False
    signature: str = "make:database-schema"
    description: str = "Creates a reusable database table schema."
    template_name: str = "database_schema"
    path_key: str = "database_schemas"
    success_label: str = "Database schema"
    postfix: str | None = "Schema"
