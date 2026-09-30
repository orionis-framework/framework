from orionis.console.commands.make._base import MakeStubCommand

class MakeModel(MakeStubCommand):
    """Generate an ORM model class."""

    timestamps: bool = False
    signature: str = "make:model"
    description: str = "Creates a new ORM model class."
    template_name: str = "model"
    path_key: str = "app_models"
    success_label: str = "Model"

