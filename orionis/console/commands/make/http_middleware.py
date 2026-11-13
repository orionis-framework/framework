"""Generate an HTTP middleware class."""

from orionis.console.commands.make._base import MakeStubCommand


class MakeHttpMiddleware(MakeStubCommand):
    """Generate an HTTP middleware class."""

    timestamps: bool = False
    """Timestamps flag used by ``MakeHttpMiddleware``."""
    signature: str = "make:http-middleware"
    """Signature identifier: ``make:http-middleware``."""
    description: str = "Creates a new HTTP middleware class."
    """Description identifier: ``Creates a new HTTP middleware class.``."""
    template_name: str = "http_middleware"
    """Template name identifier: ``http_middleware``."""
    path_key: str = "app_http_middleware"
    """Path key identifier: ``app_http_middleware``."""
    success_label: str = "HTTP middleware"
    """Success label identifier: ``HTTP middleware``."""
    postfix: str | None = "Middleware"
    """Postfix identifier: ``Middleware``."""
