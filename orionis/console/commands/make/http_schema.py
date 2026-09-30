from orionis.console.commands.make._base import MakeStubCommand

class MakeHttpSchema(MakeStubCommand):
    """Generate an HTTP validation schema class."""

    timestamps: bool = False
    signature: str = "make:http-schema"
    description: str = "Creates a custom HTTP validation schema."
    template_name: str = "http_schema"
    path_key: str = "app_http_schemas"
    success_label: str = "HTTP schema"
    postfix: str | None = "Schema"

