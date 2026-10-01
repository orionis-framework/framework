from orionis.console.commands.seed.seed import SeedCommand

class DbSeedCommand(SeedCommand):
    """Run pending seeders through the ``db:seed`` command."""

    signature: str = "db:seed"
    description: str = "Runs all pending database seeders."
