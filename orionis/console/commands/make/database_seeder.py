from orionis.console.commands.make._base import MakeStubCommand

class MakeDatabaseSeeder(MakeStubCommand):
    """Generate an application database seeder."""

    timestamps: bool = False
    signature: str = "make:database-seeder"
    description: str = "Creates a database seeder."
    template_name: str = "database_seeder"
    path_key: str = "database_seeders"
    success_label: str = "Database seeder"
    postfix: str | None = "Seeder"
