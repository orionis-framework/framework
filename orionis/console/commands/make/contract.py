from orionis.console.commands.make._base import MakeStubCommand

class MakeContract(MakeStubCommand):
    """Generate an application contract class."""

    timestamps: bool = False
    signature: str = "make:contract"
    description: str = "Creates a new contract class."
    template_name: str = "contract"
    path_key: str = "app_contracts"
    success_label: str = "Contract"
    prefix: str | None = "I"

