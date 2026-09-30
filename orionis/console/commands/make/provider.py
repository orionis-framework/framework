from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.commands.make._base import MakeStubCommand

class MakeProvider(MakeStubCommand):
    """Generate an eager or deferred application provider."""

    timestamps: bool = False
    signature: str = "make:provider"
    description: str = "Creates a new provider class file."
    template_name: str = "provider_eager"
    path_key: str = "app_providers"
    success_label: str = "Provider"
    postfix: str | None = "Provider"
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="name",
            type_=str,
            required=True,
            help="The file and class name for the new provider.",
        ),
        Argument(
            name_or_flags="--deferred",
            default=False,
            help="Load the provider only when one of its services is needed.",
            action="store_true",
        ),
    ]

    def getTemplateName(self) -> str:
        """
        Select the provider template from the deferred option.

        Returns
        -------
        str
            Eager or deferred provider template name.
        """
        return (
            "provider_deferred"
            if self.getArgument("deferred", default=False)
            else "provider_eager"
        )

