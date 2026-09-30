from orionis.console.commands.make._base import MakeStubCommand

class MakeHttpMiddleware(MakeStubCommand):
    """Generate an HTTP middleware class."""

    timestamps: bool = False
    signature: str = "make:http-middleware"
    description: str = "Creates a new HTTP middleware class."
    template_name: str = "http_middleware"
    path_key: str = "app_http_middleware"
    success_label: str = "HTTP middleware"
    postfix: str | None = "Middleware"

