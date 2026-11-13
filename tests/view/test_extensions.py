# ruff: noqa: PT009, PT027, S701
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Disable Jinja escaping to verify that the CSRF tag escapes raw values itself.

"""Verify the Jinja CSRF tag and its parser annotations."""

from typing import get_type_hints
from unittest.mock import Mock
from jinja2 import Environment
from jinja2.parser import Parser
from markupsafe import Markup
from orionis.test import TestCase
from orionis.view.exceptions import ViewRenderException
from orionis.view.extensions import CsrfExtension

_FIELD = Markup('<input type="hidden" name="_csrf" value="tok-123">')


def _make_environment(csrf_field: object = None) -> Environment:
    """
    Build an async Jinja2 environment with the CSRF extension loaded.

    Parameters
    ----------
    csrf_field : object, optional
        Callable registered as the ``csrf_field`` global.  When omitted
        the global is not registered at all.

    Returns
    -------
    Environment
        Async-enabled environment with :class:`CsrfExtension` installed.
    """
    env = Environment(
        autoescape=False,
        enable_async=True,
        extensions=[CsrfExtension],
    )

    if csrf_field is not None:
        env.globals["csrf_field"] = csrf_field

    return env


class TestCsrfExtension(TestCase):
    """Check parsing, async dispatch, and the tag's own escaping."""

    def testDeclaresTheCsrfTag(self) -> None:
        """
        Verify the extension registers the ``csrf`` statement tag.

        Validates that Jinja2 recognises ``{% csrf %}`` as a statement
        handled by this extension.

        Returns
        -------
        None
            No return value.
        """
        self.assertIn("csrf", CsrfExtension.tags)

    async def testRendersFieldFromAsyncGlobal(self) -> None:
        """
        Render the hidden input produced by an async ``csrf_field``.

        Validates that the coroutine returned by the template global is
        awaited before its markup is written to the output.

        Returns
        -------
        None
            No return value.
        """

        async def csrf_field() -> Markup:
            """Return the hidden CSRF field used by the template.

            Returns
            -------
            Markup
                Markup rendered for the CSRF field.
            """
            return _FIELD

        env = _make_environment(csrf_field)
        result = await env.from_string("{% csrf %}").render_async()
        self.assertEqual(result, str(_FIELD))

    async def testRendersFieldFromSyncGlobal(self) -> None:
        """
        Render the hidden input produced by a sync ``csrf_field``.

        Validates that a plain callable is supported as well, without
        requiring the global to be a coroutine function.

        Returns
        -------
        None
            No return value.
        """
        env = _make_environment(lambda: _FIELD)
        result = await env.from_string("{% csrf %}").render_async()
        self.assertEqual(result, str(_FIELD))
        self.assertNotIn("&lt;", result)
        self.assertIn('name="_csrf"', result)

    async def testUnsafeValueIsEscaped(self) -> None:
        """
        Escape a plain string returned by the ``csrf_field`` global.

        Validates that a value not marked as safe cannot inject markup
        into the rendered template.

        Returns
        -------
        None
            No return value.
        """
        env = _make_environment(lambda: "<script>alert(1)</script>")
        result = await env.from_string("{% csrf %}").render_async()
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)

    async def testRendersInsideSurroundingMarkup(self) -> None:
        """
        Render the tag as part of a larger form template.

        Validates that the tag can be placed anywhere in a template and
        composes with the surrounding static markup.

        Returns
        -------
        None
            No return value.
        """
        env = _make_environment(lambda: _FIELD)
        template = env.from_string("<form>{% csrf %}</form>")
        result = await template.render_async()
        self.assertEqual(result, f"<form>{_FIELD}</form>")

    async def testRendersMultipleOccurrences(self) -> None:
        """
        Render several ``{% csrf %}`` tags within one template.

        Validates that each occurrence resolves the global independently
        and produces its own hidden input.

        Returns
        -------
        None
            No return value.
        """
        builder = Mock(return_value=_FIELD)
        env = _make_environment(builder)
        template = env.from_string("{% csrf %}{% csrf %}")
        result = await template.render_async()
        self.assertEqual(result.count('name="_csrf"'), 2)
        self.assertEqual(builder.call_count, 2)

    async def testRaisesWhenGlobalIsMissing(self) -> None:
        """
        Fail loudly when the ``csrf_field`` global is not registered.

        Validates that a misconfigured environment reports a view error
        instead of rendering an empty field silently.

        Returns
        -------
        None
            No return value.
        """
        env = _make_environment()
        with self.assertRaises(ViewRenderException):
            await env.from_string("{% csrf %}").render_async()

    def testParserAnnotationsResolveAtRuntime(self) -> None:
        """Resolve the actual Jinja parser type exposed by the extension.

        Returns
        -------
        None
            No return value.
        """
        self.assertIs(get_type_hints(CsrfExtension.parse)["parser"], Parser)
