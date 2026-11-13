"""Generate an application service class."""

from orionis.console.commands.make._base import MakeStubCommand


class MakeService(MakeStubCommand):
    """Generate an application service class."""

    timestamps: bool = False
    """Timestamps flag used by ``MakeService``."""
    signature: str = "make:service"
    """Signature identifier: ``make:service``."""
    description: str = "Creates a new service class."
    """Description identifier: ``Creates a new service class.``."""
    template_name: str = "service"
    """Template name identifier: ``service``."""
    path_key: str = "app_services"
    """Path key identifier: ``app_services``."""
    success_label: str = "Service"
    """Success label identifier: ``Service``."""
