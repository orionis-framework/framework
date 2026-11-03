"""Generate an application contract class."""

from orionis.console.commands.make._base import MakeStubCommand

class MakeContract(MakeStubCommand):
    """Generate an application contract class."""

    timestamps: bool = False
    """Timestamps flag used by ``MakeContract``."""
    signature: str = "make:contract"
    """Signature identifier: ``make:contract``."""
    description: str = "Creates a new contract class."
    """Description identifier: ``Creates a new contract class.``."""
    template_name: str = "contract"
    """Template name identifier: ``contract``."""
    path_key: str = "app_contracts"
    """Path key identifier: ``app_contracts``."""
    success_label: str = "Contract"
    """Success label identifier: ``Contract``."""
    prefix: str | None = "I"
    """Prefix identifier: ``I``."""

