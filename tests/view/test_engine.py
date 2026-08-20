import jinja2
from orionis.test import TestCase
from orionis.view import engine as engine_module
from orionis.view.engine import Jinja2Engine
from orionis.view.exceptions import ViewRenderException, ViewTemplateNotFoundException

class _StubTemplate:
    """Template double recording the context passed to render_async."""

    __slots__ = ("calls", "error", "html")

    def __init__(
        self,
        html: str = "",
        error: Exception | None = None,
    ) -> None:
        self.html: str = html
        self.error: Exception | None = error
        self.calls: list[dict[str, object]] = []

    async def render_async(self, **context: object) -> str:
        """Return the canned HTML or raise the configured error."""
        self.calls.append(context)
        if self.error is not None:
            raise self.error
        return self.html

class _StubJinjaEnvironment:
    """Jinja2 environment double resolving a single stubbed template."""

    __slots__ = ("error", "requested", "template")

    def __init__(
        self,
        template: _StubTemplate | None = None,
        error: Exception | None = None,
    ) -> None:
        self.template: _StubTemplate | None = template
        self.error: Exception | None = error
        self.requested: list[str] = []

    def get_template(self, path: str) -> _StubTemplate | None:
        """Return the stubbed template or raise the configured error."""
        self.requested.append(path)
        if self.error is not None:
            raise self.error
        return self.template

class _StubViewEnvironment:
    """View environment double exposing a stubbed Jinja2 environment."""

    __slots__ = ("calls", "jinja")

    def __init__(self, jinja: _StubJinjaEnvironment) -> None:
        self.jinja: _StubJinjaEnvironment = jinja
        self.calls: int = 0

    def getJinjaEnvironment(self) -> _StubJinjaEnvironment:
        """Return the stubbed Jinja2 environment."""
        self.calls += 1
        return self.jinja

class TestJinja2EngineNormalisePath(TestCase):

    def setUp(self) -> None:
        """
        Clear the module-level path cache before each test.

        Keeps every case deterministic regardless of the order in which
        templates were normalised by previous tests.
        """
        engine_module._PATH_CACHE.clear()

    def tearDown(self) -> None:
        """
        Clear the module-level path cache after each test.

        Prevents memoised entries from leaking into unrelated test
        modules sharing the same process.
        """
        engine_module._PATH_CACHE.clear()

    def testDotNotationConvertsToSlashPath(self) -> None:
        """
        Convert dot-notation template names to slash-delimited paths.

        Validates that dots are replaced with forward slashes and the
        .html extension is appended when absent.
        """
        result = Jinja2Engine._normalisePath("users.index")
        self.assertEqual(result, "users/index.html")

    def testDirectPathWithExtensionIsUnchanged(self) -> None:
        """
        Return a direct path with extension unchanged.

        Validates that a path containing a forward slash and an existing
        extension is not modified by the normalisation step.
        """
        result = Jinja2Engine._normalisePath("users/index.html")
        self.assertEqual(result, "users/index.html")

    def testDirectPathWithoutExtensionGetsHtmlSuffix(self) -> None:
        """
        Append .html to a direct path that has no extension.

        Validates that when a slash is present but no extension exists
        in the last segment, the default .html suffix is added.
        """
        result = Jinja2Engine._normalisePath("users/index")
        self.assertEqual(result, "users/index.html")

    def testSingleWordGetsHtmlSuffix(self) -> None:
        """
        Append .html to a single-word template identifier.

        Validates that a bare word without slash or dot produces a
        .html filename in the normalised output.
        """
        result = Jinja2Engine._normalisePath("nav")
        self.assertEqual(result, "nav.html")

    def testDeepDotNotationConvertsToNestedPath(self) -> None:
        """
        Convert multi-level dot notation to a nested slash path.

        Validates that three or more dot-separated segments are all
        converted to slash separators with .html appended.
        """
        result = Jinja2Engine._normalisePath("admin.users.index")
        self.assertEqual(result, "admin/users/index.html")

    def testNestedDirectPathWithExtensionIsUnchanged(self) -> None:
        """
        Return a deeply nested direct path with extension unchanged.

        Validates that the presence of a slash signals direct-path mode
        for arbitrarily deep template paths.
        """
        result = Jinja2Engine._normalisePath("partials/nav.html")
        self.assertEqual(result, "partials/nav.html")

    def testTwoDotSegmentsConvertsCorrectly(self) -> None:
        """
        Convert a two-segment dot-notation name to a slash path.

        Validates the basic two-segment case: module.template becomes
        module/template.html.
        """
        result = Jinja2Engine._normalisePath("layout.base")
        self.assertEqual(result, "layout/base.html")

    def testDirectPathWithNonHtmlExtensionIsUnchanged(self) -> None:
        """
        Return a direct path with a non-HTML extension unchanged.

        Validates that any existing dot in the last path segment prevents
        a double extension from being appended.
        """
        result = Jinja2Engine._normalisePath("emails/welcome.txt")
        self.assertEqual(result, "emails/welcome.txt")

    def testNormalisePathMemoisesTheResult(self) -> None:
        """
        Memoise the normalised path for later lookups.

        Validates that the identifier to path translation is computed
        only once per template name.
        """
        Jinja2Engine._normalisePath("users.index")
        self.assertEqual(
            engine_module._PATH_CACHE["users.index"],
            "users/index.html",
        )

class TestJinja2EngineRender(TestCase):

    def setUp(self) -> None:
        """
        Clear the module-level path cache before each test.

        Guarantees that cache-hit assertions observe only the entries
        produced by the test itself.
        """
        engine_module._PATH_CACHE.clear()

    def tearDown(self) -> None:
        """
        Clear the module-level path cache after each test.

        Prevents memoised entries from leaking into unrelated test
        modules sharing the same process.
        """
        engine_module._PATH_CACHE.clear()

    def _buildEngine(
        self,
        html: str = "",
        error: Exception | None = None,
        lookup_error: Exception | None = None,
    ) -> tuple[Jinja2Engine, _StubJinjaEnvironment, _StubTemplate]:
        """
        Build an engine wired to stubbed Jinja2 collaborators.

        Parameters
        ----------
        html : str
            HTML returned by the stubbed template.
        error : Exception or None
            Error raised while rendering the stubbed template.
        lookup_error : Exception or None
            Error raised while looking the template up.

        Returns
        -------
        tuple[Jinja2Engine, _StubJinjaEnvironment, _StubTemplate]
            The engine under test and both stubbed collaborators.
        """
        template = _StubTemplate(html=html, error=error)
        jinja = _StubJinjaEnvironment(template=template, error=lookup_error)
        engine = Jinja2Engine(_StubViewEnvironment(jinja))
        return engine, jinja, template

    def testEngineResolvesJinjaEnvironmentOnce(self) -> None:
        """
        Resolve the Jinja2 environment a single time on construction.

        Validates that the environment reference is cached instead of
        being fetched on every render.
        """
        view_env = _StubViewEnvironment(_StubJinjaEnvironment())
        Jinja2Engine(view_env)
        self.assertEqual(view_env.calls, 1)

    async def testRenderReturnsRenderedHtml(self) -> None:
        """
        Return the rendered HTML string from a successful render call.

        Validates that the engine delegates to the Jinja2 template's
        render_async and returns the resulting HTML unchanged.
        """
        engine, _, _ = self._buildEngine(html="<h1>Hello</h1>")
        result = await engine.render("users.index", {"name": "World"})
        self.assertEqual(result, "<h1>Hello</h1>")

    async def testRenderNormalisesTemplateNameToPath(self) -> None:
        """
        Normalise the template name before requesting it from the loader.

        Validates that the engine translates dot notation to a file path
        before calling get_template on the Jinja2 environment.
        """
        engine, jinja, _ = self._buildEngine()
        await engine.render("users.index", {})
        self.assertEqual(jinja.requested, ["users/index.html"])

    async def testRenderReusesTheMemoisedPath(self) -> None:
        """
        Reuse the memoised path instead of normalising it again.

        Validates that the module-level cache short-circuits the
        identifier translation on subsequent renders.
        """
        engine, jinja, _ = self._buildEngine()
        engine_module._PATH_CACHE["users.index"] = "cached/path.html"
        await engine.render("users.index", {})
        self.assertEqual(jinja.requested, ["cached/path.html"])

    async def testRenderForwardsContextAsKeywordArgs(self) -> None:
        """
        Forward the context dict as keyword arguments to render_async.

        Validates that all variables in the context mapping are passed
        through to the Jinja2 template during rendering.
        """
        engine, _, template = self._buildEngine(html="<p>ok</p>")
        await engine.render("page.index", {"title": "Home", "count": 3})
        self.assertEqual(template.calls, [{"title": "Home", "count": 3}])

    async def testRenderRaisesViewTemplateNotFoundOnMissingTemplate(self) -> None:
        """
        Raise ViewTemplateNotFoundException when the template is missing.

        Validates that a Jinja2 TemplateNotFound error is wrapped and
        re-raised as the framework's ViewTemplateNotFoundException.
        """
        engine, _, _ = self._buildEngine(
            lookup_error=jinja2.TemplateNotFound("users/index.html"),
        )
        with self.assertRaises(ViewTemplateNotFoundException):
            await engine.render("users.index", {})

    async def testRenderRaisesViewRenderExceptionOnTemplateError(self) -> None:
        """
        Raise ViewRenderException when Jinja2 fails during rendering.

        Validates that a Jinja2 TemplateError raised by render_async is
        wrapped and re-raised as the framework's ViewRenderException.
        """
        engine, _, _ = self._buildEngine(
            error=jinja2.TemplateError("syntax error"),
        )
        with self.assertRaises(ViewRenderException):
            await engine.render("users.index", {})

    async def testViewTemplateNotFoundPreservesChainedCause(self) -> None:
        """
        Preserve the original Jinja2 exception as __cause__.

        Validates that the ViewTemplateNotFoundException chains the
        original TemplateNotFound exception via the from clause.
        """
        original = jinja2.TemplateNotFound("missing.html")
        engine, _, _ = self._buildEngine(lookup_error=original)
        with self.assertRaises(ViewTemplateNotFoundException) as ctx:
            await engine.render("missing", {})
        self.assertIs(ctx.exception.__cause__, original)

    async def testViewRenderExceptionPreservesChainedCause(self) -> None:
        """
        Preserve the original Jinja2 TemplateError as __cause__.

        Validates that the ViewRenderException chains the original
        TemplateError exception via the from clause.
        """
        original = jinja2.TemplateError("bad syntax")
        engine, _, _ = self._buildEngine(error=original)
        with self.assertRaises(ViewRenderException) as ctx:
            await engine.render("broken.template", {})
        self.assertIs(ctx.exception.__cause__, original)

    async def testRenderWithEmptyContextSucceeds(self) -> None:
        """
        Render a template successfully when an empty context is supplied.

        Validates that passing an empty dict does not cause errors and
        the engine returns the expected HTML string.
        """
        engine, _, _ = self._buildEngine(html="<p>static</p>")
        result = await engine.render("static.page", {})
        self.assertEqual(result, "<p>static</p>")
