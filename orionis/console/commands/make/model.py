"""Generate an ORM model class."""

from orionis.console.commands.make._base import MakeStubCommand


class MakeModel(MakeStubCommand):
    """Generate an ORM model class."""

    timestamps: bool = False
    """Timestamps flag used by ``MakeModel``."""
    signature: str = "make:model"
    """Signature identifier: ``make:model``."""
    description: str = "Creates a new ORM model class."
    """Description identifier: ``Creates a new ORM model class.``."""
    template_name: str = "model"
    """Template name identifier: ``model``."""
    path_key: str = "app_models"
    """Path key identifier: ``app_models``."""
    success_label: str = "Model"
    """Success label identifier: ``Model``."""
