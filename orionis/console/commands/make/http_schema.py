"""Generate an HTTP validation schema class."""

from orionis.console.commands.make._base import MakeStubCommand


class MakeHttpSchema(MakeStubCommand):
    """Generate an HTTP validation schema class."""

    timestamps: bool = False
    """Timestamps flag used by ``MakeHttpSchema``."""
    signature: str = "make:http-schema"
    """Signature identifier: ``make:http-schema``."""
    description: str = "Creates a custom HTTP validation schema."
    """Description identifier: ``Creates a custom HTTP validation schema.``."""
    template_name: str = "http_schema"
    """Template name identifier: ``http_schema``."""
    path_key: str = "app_http_schemas"
    """Path key identifier: ``app_http_schemas``."""
    success_label: str = "HTTP schema"
    """Success label identifier: ``HTTP schema``."""
    postfix: str | None = "Schema"
    """Postfix identifier: ``Schema``."""
