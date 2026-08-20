from typing import Any
from orionis.http.response import HTMLResponse
from orionis.test import TestCase
from orionis.view.exceptions import ViewRenderException, ViewTemplateNotFoundException
from orionis.view.factory import ViewFactory
from orionis.view.pending import PendingView

# Failure messages hoisted out of the raise statements (EM101).
_MISSING_TEMPLATE: str = "template not found"
_RENDER_FAILURE: str = "render failed"

class _StubEngine:
    """View engine double recording calls and returning canned output."""

    __slots__ = ("calls", "error", "html")

    def __init__(
        self,
        html: str = "<html></html>",
        error: Exception | None = None,
    ) -> None:
        self.html: str = html
        self.error: Exception | None = error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def render(self, template: str, context: dict[str, Any]) -> str:
        """Return the canned HTML or raise the configured error."""
        self.calls.append((template, context))
        if self.error is not None:
            raise self.error
        return self.html

class TestViewFactory(TestCase):

    def _buildEngine(
        self,
        html: str = "<html></html>",
        error: Exception | None = None,
    ) -> _StubEngine:
        """
        Build a stub engine returning the given html or raising an error.

        Parameters
        ----------
        html : str
            HTML string the stub engine's render method will return.
        error : Exception or None
            Error raised instead of returning the HTML.

        Returns
        -------
        _StubEngine
            A stub engine recording every render call it receives.
        """
        return _StubEngine(html=html, error=error)

    def testMakeReturnsPendingView(self) -> None:
        """
        Return a PendingView from make instead of a rendered response.

        Validates that response mutators can be chained on the value
        returned by the factory.
        """
        factory = ViewFactory(self._buildEngine())
        self.assertIsInstance(factory.make("users.index"), PendingView)

    def testMakeDefersRendering(self) -> None:
        """
        Skip every engine call until the pending view is awaited.

        Validates that building a view is free of I/O so it can be
        chained safely inside controllers.
        """
        engine = self._buildEngine()
        ViewFactory(engine).make("users.index")
        self.assertEqual(engine.calls, [])

    async def testMakeReturnsHtmlResponse(self) -> None:
        """
        Verify make returns an HTMLResponse instance.

        Validates that the factory wraps the engine's output in an
        HTMLResponse rather than returning a plain string.
        """
        engine = self._buildEngine(html="<p>Hello</p>")
        factory = ViewFactory(engine)
        response = await factory.make("users.index")
        self.assertIsInstance(response, HTMLResponse)

    async def testMakeBodyContainsRenderedHtml(self) -> None:
        """
        Verify the response body contains the rendered HTML string.

        Validates that the engine's output is correctly stored in the
        response body and is accessible as bytes.
        """
        engine = self._buildEngine(html="<p>Rendered</p>")
        factory = ViewFactory(engine)
        response = await factory.make("users.index")
        self.assertEqual(response.getBody(), b"<p>Rendered</p>")

    async def testMakePassesTemplateNameToEngine(self) -> None:
        """
        Forward the template name to the underlying engine.

        Validates that the factory calls engine.render with the exact
        template string supplied by the caller.
        """
        engine = self._buildEngine()
        factory = ViewFactory(engine)
        await factory.make("users.index")
        self.assertEqual(engine.calls, [("users.index", {})])

    async def testMakePassesContextToEngine(self) -> None:
        """
        Forward keyword context arguments to the engine as a dict.

        Validates that **context kwargs are collected into a dict and
        forwarded as the second positional argument to engine.render.
        """
        engine = self._buildEngine()
        factory = ViewFactory(engine)
        await factory.make("users.index", name="World", count=5)
        self.assertEqual(
            engine.calls,
            [("users.index", {"name": "World", "count": 5})],
        )

    async def testMakeSetsOrionisRenderHeader(self) -> None:
        """
        Set the X-Orionis-Render header on the response.

        Validates that the factory marks SSR responses with the
        X-Orionis-Render header so clients can identify server rendering.
        """
        factory = ViewFactory(self._buildEngine())
        response = await factory.make("users.index")
        self.assertTrue(response.hasHeader("x-orionis-render"))

    async def testMakeOrionisRenderHeaderValueIsSsr(self) -> None:
        """
        Set the X-Orionis-Render header value to 'SSR'.

        Validates that the header carries the expected SSR marker value
        identifying server-side rendering.
        """
        factory = ViewFactory(self._buildEngine())
        response = await factory.make("users.index")
        self.assertEqual(response.getHeader("x-orionis-render"), ["SSR"])

    async def testMakeSupportsChainedResponseMutators(self) -> None:
        """
        Apply response mutators chained on the pending view.

        Validates the fluent contract documented for the factory, where
        mutators are replayed on the rendered response.
        """
        factory = ViewFactory(self._buildEngine())
        response = await factory.make("users.index").addHeader("X-Demo", "1")
        self.assertEqual(response.getHeader("x-demo"), ["1"])

    async def testMakePropagatesToViewTemplateNotFoundException(self) -> None:
        """
        Propagate ViewTemplateNotFoundException from the engine.

        Validates that the factory does not swallow template-not-found
        errors raised by the rendering engine.
        """
        engine = self._buildEngine(
            error=ViewTemplateNotFoundException(_MISSING_TEMPLATE),
        )
        factory = ViewFactory(engine)
        with self.assertRaises(ViewTemplateNotFoundException):
            await factory.make("missing.template")

    async def testMakePropagatesViewRenderException(self) -> None:
        """
        Propagate ViewRenderException from the engine.

        Validates that the factory does not swallow render errors raised
        by the underlying Jinja2 engine.
        """
        engine = self._buildEngine(error=ViewRenderException(_RENDER_FAILURE))
        factory = ViewFactory(engine)
        with self.assertRaises(ViewRenderException):
            await factory.make("broken.template")

    async def testMakeWithEmptyContextSucceeds(self) -> None:
        """
        Render a template successfully when no context kwargs are given.

        Validates that an empty context is forwarded correctly without
        causing errors in the engine call.
        """
        factory = ViewFactory(self._buildEngine(html="<p>static</p>"))
        response = await factory.make("static.page")
        self.assertEqual(response.getBody(), b"<p>static</p>")
