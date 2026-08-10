from jinja2 import Environment
from markupsafe import Markup
from orionis.test import TestCase
from orionis.view.exceptions import ViewRenderException
from orionis.view.extensions import CsrfExtension

_FIELD = Markup('<input type="hidden" name="_csrf" value="tok-123">')

def _makeEnvironment(csrf_field: object = None) -> Environment:
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
    env = Environment(  # noqa: S701
        enable_async=True,
        extensions=[CsrfExtension],
    )

    if csrf_field is not None:
        env.globals["csrf_field"] = csrf_field

    return env

class TestCsrfExtension(TestCase):

    def testDeclaresTheCsrfTag(self) -> None:
        """
        Verify the extension registers the ``csrf`` statement tag.

        Validates that Jinja2 recognises ``{% csrf %}`` as a statement
        handled by this extension.
        """
        self.assertIn("csrf", CsrfExtension.tags)

    async def testRendersFieldFromAsyncGlobal(self) -> None:
        """
        Render the hidden input produced by an async ``csrf_field``.

        Validates that the coroutine returned by the template global is
        awaited before its markup is written to the output.
        """
        async def csrf_field() -> Markup:
            return _FIELD

        env = _makeEnvironment(csrf_field)
        result = await env.from_string("{% csrf %}").render_async()
        self.assertEqual(result, str(_FIELD))

    async def testRendersFieldFromSyncGlobal(self) -> None:
        """
        Render the hidden input produced by a sync ``csrf_field``.

        Validates that a plain callable is supported as well, without
        requiring the global to be a coroutine function.
        """
        env = _makeEnvironment(lambda: _FIELD)
        result = await env.from_string("{% csrf %}").render_async()
        self.assertEqual(result, str(_FIELD))

    async def testMarkupIsNotDoubleEscaped(self) -> None:
        """
        Confirm the rendered markup keeps its raw HTML characters.

        Validates that the safe :class:`Markup` value is written as-is
        instead of being escaped into entities.
        """
        env = _makeEnvironment(lambda: _FIELD)
        result = await env.from_string("{% csrf %}").render_async()
        self.assertNotIn("&lt;", result)
        self.assertIn('name="_csrf"', result)

    async def testUnsafeValueIsEscaped(self) -> None:
        """
        Escape a plain string returned by the ``csrf_field`` global.

        Validates that a value not marked as safe cannot inject markup
        into the rendered template.
        """
        env = _makeEnvironment(lambda: "<script>alert(1)</script>")
        result = await env.from_string("{% csrf %}").render_async()
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)

    async def testRendersInsideSurroundingMarkup(self) -> None:
        """
        Render the tag as part of a larger form template.

        Validates that the tag can be placed anywhere in a template and
        composes with the surrounding static markup.
        """
        env = _makeEnvironment(lambda: _FIELD)
        template = env.from_string("<form>{% csrf %}</form>")
        result = await template.render_async()
        self.assertEqual(result, f"<form>{_FIELD}</form>")

    async def testRendersMultipleOccurrences(self) -> None:
        """
        Render several ``{% csrf %}`` tags within one template.

        Validates that each occurrence resolves the global independently
        and produces its own hidden input.
        """
        env = _makeEnvironment(lambda: _FIELD)
        template = env.from_string("{% csrf %}{% csrf %}")
        result = await template.render_async()
        self.assertEqual(result.count('name="_csrf"'), 2)

    async def testRaisesWhenGlobalIsMissing(self) -> None:
        """
        Fail loudly when the ``csrf_field`` global is not registered.

        Validates that a misconfigured environment reports a view error
        instead of rendering an empty field silently.
        """
        env = _makeEnvironment()
        with self.assertRaises(ViewRenderException):
            await env.from_string("{% csrf %}").render_async()
