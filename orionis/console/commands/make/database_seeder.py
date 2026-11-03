"""Generate an application database seeder."""

from orionis.console.commands.make._base import MakeStubCommand

class MakeDatabaseSeeder(MakeStubCommand):
    """Generate an application database seeder."""

    timestamps: bool = False
    """Timestamps flag used by ``MakeDatabaseSeeder``."""
    signature: str = "make:database-seeder"
    """Signature identifier: ``make:database-seeder``."""
    description: str = "Creates a database seeder."
    """Description identifier: ``Creates a database seeder.``."""
    template_name: str = "database_seeder"
    """Template name identifier: ``database_seeder``."""
    path_key: str = "database_seeders"
    """Path key identifier: ``database_seeders``."""
    success_label: str = "Database seeder"
    """Success label identifier: ``Database seeder``."""
    postfix: str | None = "Seeder"
    """Postfix identifier: ``Seeder``."""
