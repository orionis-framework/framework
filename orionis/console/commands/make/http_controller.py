from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.commands.make._base import MakeStubCommand

_RESOURCE_ACTIONS: tuple[tuple[str, str], ...] = (
    ("index", "Display a listing of the resource"),
    ("create", "Show the form for creating a resource"),
    ("store", "Store a newly created resource"),
    ("show", "Display the specified resource"),
    ("edit", "Show the form for editing the resource"),
    ("update", "Update the specified resource"),
    ("destroy", "Remove the specified resource"),
)

class MakeHttpController(MakeStubCommand):
    """Generate an invokable or resource HTTP controller."""

    timestamps: bool = False
    signature: str = "make:http-controller"
    description: str = "Creates an invokable or resource HTTP controller."
    template_name: str = "http_controller"
    path_key: str = "app_http_controllers"
    success_label: str = "HTTP controller"
    postfix: str | None = "Controller"
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="name",
            type_=str,
            required=True,
            help="The file and class name for the new controller.",
        ),
        Argument(
            name_or_flags="--invoke",
            default=False,
            help="Generate a single invokable __call__ action.",
            action="store_true",
        ),
        Argument(
            name_or_flags="--api",
            default=False,
            help="Annotate generated actions with JSONResponse.",
            action="store_true",
        ),
    ]

    def getControllerMethods(self) -> str:
        """
        Build documented asynchronous controller action declarations.

        Returns
        -------
        str
            Resource actions or a single invokable action with the selected
            response type.
        """
        api = self.getArgument("api", default=False)
        response_type = "JSONResponse" if api else "HttpResponse"
        if self.getArgument("invoke", default=False):
            return "\n".join([
                f"    async def __call__(self) -> {response_type}:",
                '        """Handle the request for this controller.',
                "",
                "        Returns",
                "        -------",
                f"        {response_type}",
                "            Response produced when this action is implemented.",
                '        """',
            ])

        declarations: list[str] = []
        for action, description in _RESOURCE_ACTIONS:
            declarations.append("\n".join([
                f"    async def {action}(self) -> {response_type}:",
                f'        """{description}.',
                "",
                "        Returns",
                "        -------",
                f"        {response_type}",
                "            Response produced when this action is implemented.",
                '        """',
            ]))
        return "\n\n".join(declarations)

    def getReplacements(self) -> dict[str, str]:
        """
        Return the imports and action declarations for the controller.

        Returns
        -------
        dict[str, str]
            Template placeholders for response types and controller actions.
        """
        if self.getArgument("api", default=False):
            response_import = (
                "from orionis.http import JSONResponse"
            )
        else:
            response_import = "from orionis.http import HttpResponse"
        return {
            "response_import": response_import,
            "methods": self.getControllerMethods(),
        }

