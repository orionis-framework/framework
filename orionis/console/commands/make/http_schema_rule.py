from orionis.console.commands.make._base import MakeStubCommand

class MakeHttpSchemaRule(MakeStubCommand):
    """Generate a custom HTTP validation rule class."""

    timestamps: bool = False
    signature: str = "make:http-schema-rule"
    description: str = "Creates a custom validation rule."
    template_name: str = "http_schema_rule"
    path_key: str = "app_http_schemas_rules"
    success_label: str = "HTTP schema rule"
    postfix: str | None = "Rule"

