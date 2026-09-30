from orionis.console.commands.make._base import MakeStubCommand

class MakeService(MakeStubCommand):
    """Generate an application service class."""

    timestamps: bool = False
    signature: str = "make:service"
    description: str = "Creates a new service class."
    template_name: str = "service"
    path_key: str = "app_services"
    success_label: str = "Service"

