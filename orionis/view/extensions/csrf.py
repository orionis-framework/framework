# ruff: noqa: TC002
# Keep the Jinja parser type available for runtime annotation resolution.

"""Provide the ``{% csrf %}`` statement tag."""

from __future__ import annotations
import inspect
from typing import ClassVar
from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.parser import Parser
from markupsafe import Markup, escape
from orionis.view.exceptions import ViewRenderException

# Template global the tag delegates to; registered by ViewServiceProvider.
_CSRF_FIELD_GLOBAL = "csrf_field"
"""Template global the tag delegates to; registered by ViewServiceProvider."""


class CsrfExtension(Extension):
    """
    Provide the ``{% csrf %}`` statement tag.

    The tag is a zero-argument shortcut for ``{{ csrf_field() }}``: it
    renders the hidden input holding the current CSRF token, so forms
    need no explicit call to the template global.
    """

    tags: ClassVar[set[str]] = {"csrf"}
    """Template tag names recognized by this Jinja extension."""

    def parse(self, parser: Parser) -> nodes.Output:
        """
        Compile the ``{% csrf %}`` tag into an output node.

        Parameters
        ----------
        parser : ``jinja2.parser.Parser``
            Jinja2 parser positioned on the tag name token.

        Returns
        -------
        ``jinja2.nodes.Output``
            Node emitting the hidden CSRF input at render time.
        """
        # Consume the tag name token and keep its line for tracebacks
        lineno: int = next(parser.stream).lineno

        return nodes.Output(
            [self.call_method("_renderField", lineno=lineno)],
            lineno=lineno,
        )

    async def _renderField(self) -> Markup:
        """
        Render the hidden CSRF input through the ``csrf_field`` global.

        Returns
        -------
        ``markupsafe.Markup``
            Safe HTML markup with the hidden input.

        Raises
        ------
        orionis.view.exceptions.ViewRenderException
            When the ``csrf_field`` template global is not registered.
        """
        builder = self.environment.globals.get(_CSRF_FIELD_GLOBAL)
        if builder is None:
            error_msg = (
                f"The '{_CSRF_FIELD_GLOBAL}' template global is not "
                f"registered; '{{% csrf %}}' cannot be rendered."
            )
            raise ViewRenderException(error_msg)

        field = builder()
        if inspect.isawaitable(field):
            field = await field

        # ``escape`` returns Markup untouched and secures any other value
        return escape(field)
