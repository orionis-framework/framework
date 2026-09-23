from __future__ import annotations
import asyncio
import json
import mimetypes
import re
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from orionis.http.default.responses import DefaultResponses
from orionis.http.responses import FileResponse, Response
from orionis.support.formatter.exceptions.parser import ExceptionParser
from orionis.test import TestCase
from orionis.view.engine import Jinja2Engine
from orionis.view.environment import ViewEnvironment
from tests.http._support import replace_attribute
from tests.http.default.test_response_cache import (
    _DefaultFixture, _RecordingEngine, _Request,
)

if TYPE_CHECKING:
    import os


class _Page(HTMLParser):
    """Expose actual browser contexts in rendered pages for security checks."""

    def __init__(self, content: bytes) -> None:
        """Parse the rendered document into text and real HTML attributes."""
        super().__init__(convert_charrefs=True)
        self.elements: list[tuple[str, dict[str, str | None]]] = []
        self.text: list[str] = []
        self.script_content: list[str] = []
        self._in_script = False
        self.feed(content.decode("utf-8"))
        self.close()

    def handleStartTag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        """Record parsed attributes so escaping cannot hide injected handlers."""
        self.elements.append((tag, dict(attrs)))
        if tag == "script":
            self._in_script = True

    def handleEndTag(self, tag: str) -> None:
        """Stop collecting script contents at the real closing element."""
        if tag == "script":
            self._in_script = False

    def handleData(self, data: str) -> None:
        """Collect decoded text and executable script content separately."""
        self.text.append(data)
        if self._in_script:
            self.script_content.append(data)

    handle_starttag = handleStartTag
    handle_endtag = handleEndTag
    handle_data = handleData


class _SuspendedEngine:
    """Pause the first render while another request changes shared configuration."""

    __slots__ = ("calls", "engine", "release", "started")

    def __init__(self, engine: Jinja2Engine) -> None:
        """Allocate per-test synchronization without sleeps or shared globals."""
        self.engine = engine
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.calls = 0

    async def render(self, template: str, context: dict[str, object]) -> str:
        """Hold the first context until a later render has had time to finish."""
        self.calls += 1
        if self.calls == 1:
            self.started.set()
            await self.release.wait()
        return await self.engine.render(template, context)


def local_defaults(
    fixture: _DefaultFixture, engine: object, assets: Path,
) -> DefaultResponses:
    """Create a slot-safe response fixture with an isolated asset directory."""
    class LocalDefaults(DefaultResponses):
        __slots__ = ()
        _ASSETS_DIR = assets

    return LocalDefaults(fixture, fixture, engine)


class TestDefaultTemplates(TestCase):
    """Exercise default pages through the public framework rendering engine."""

    def setUp(self) -> None:
        """Build a service with real Jinja templates and isolated application views."""
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.fixture = _DefaultFixture(self.directory)
        self.engine = Jinja2Engine(ViewEnvironment(self.fixture))
        self.defaults = DefaultResponses(self.fixture, self.fixture, self.engine)

    async def testHealthStatusAndJsonRemainConsistentWithMaintenance(self) -> None:
        """Reflect maintenance transitions independently for HTML and JSON requests."""
        for maintenance, status, label in (
            (False, 200, "Online Application"),
            (True, 503, "Application in Maintenance"),
            (False, 200, "Online Application"),
        ):
            self.fixture.settings["app.maintenance"] = maintenance
            for wants_json in (False, True):
                with self.subTest(maintenance=maintenance, wants_json=wants_json):
                    response = await self.defaults.health(
                        _Request(wants_json=wants_json),
                    )
                    self.assertEqual(response.getStatusCode(), status)
                    self.assertEqual(
                        response.getHeader("cache-control"),
                        ["no-cache, no-store, must-revalidate"],
                    )
                    if wants_json:
                        self.assertEqual(
                            json.loads(response.getBody()), {"message": label},
                        )

    async def testRetainedHealthServiceRefreshesLabelsAndLocale(self) -> None:
        """Invalidate cached health markup after live app configuration changes."""
        for name, locale, maintenance in (
            ("Original application", "en", False),
            ("Updated <application>", "es", False),
            ("Updated <application>", "es", True),
            ("Updated <application>", "pt-BR", True),
            ("Updated <application>", "pt-BR", False),
        ):
            self.fixture.settings.update({
                "app.name": name, "app.locale": locale,
                "app.maintenance": maintenance,
            })
            response = await self.defaults.health(_Request(wants_json=False))
            page = _Page(response.getBody())
            self.assertIn(name, "".join(page.text))
            html = next(attrs for tag, attrs in page.elements if tag == "html")
            self.assertEqual(html["lang"], locale)
            self.assertEqual(response.getStatusCode(), 503 if maintenance else 200)
            self.assertNotIn(b"<application>", response.getBody())

    async def testSlowHealthRenderCannotReplaceNewConfigurationCache(self) -> None:
        """Keep newer cached markup when an earlier asynchronous render finishes."""
        engine = _SuspendedEngine(self.engine)
        defaults = DefaultResponses(self.fixture, self.fixture, engine)
        pending = asyncio.create_task(defaults.health(_Request(wants_json=False)))
        await asyncio.wait_for(engine.started.wait(), 2)
        try:
            self.fixture.settings.update({"app.name": "New name", "app.locale": "es"})
            newer = await defaults.health(_Request(wants_json=False))
        finally:
            engine.release.set()
        older = await asyncio.wait_for(pending, 2)
        cached = await defaults.health(_Request(wants_json=False))
        self.assertIn(b"Example", older.getBody())
        self.assertNotIn(b"New name", older.getBody())
        self.assertIn(b"New name", newer.getBody())
        self.assertIn(b'<html lang="es">', cached.getBody())
        self.assertEqual(cached.getBody(), newer.getBody())
        self.assertEqual(engine.calls, 2)

    async def testEveryHtmlPageUsesInjectedViewEngine(self) -> None:
        """Delegate health, maintenance, error and exception markup to IViewEngine."""
        engine = _RecordingEngine()
        defaults = DefaultResponses(self.fixture, self.fixture, engine)
        await defaults.health(_Request(wants_json=False))
        self.fixture.settings["app.maintenance"] = True
        await defaults.health(_Request(wants_json=False))
        await defaults.error(404, "Missing", expects_json=False)
        response = await defaults.exception("/missing", "GET", ValueError("Broken"))
        self.assertEqual(response.getBody(), b"<main>Injected engine</main>")
        self.assertEqual(
            [template for template, _context in engine.calls],
            [
                "__orionis__/default/up.html",
                "__orionis__/default/down.html",
                "__orionis__/default/error.html",
                "__orionis__/default/exception.html",
            ],
        )

    async def testFrameworkNamespaceCannotBeShadowedByApplicationViews(self) -> None:
        """Keep built-in pages available without trusting matching app filenames."""
        shadow = self.directory / "__orionis__" / "default"
        shadow.mkdir(parents=True)
        for filename in ("base.html", "up.html", "error.html"):
            (shadow / filename).write_text("SHADOWED TEMPLATE", encoding="utf-8")
        response = await self.defaults.health(_Request(wants_json=False))
        self.assertNotIn(b"SHADOWED TEMPLATE", response.getBody())
        self.assertIn(b"<!DOCTYPE html>", response.getBody())

    async def testBuiltinEscapingSurvivesDisabledApplicationAutoescape(self) -> None:
        """Escape app labels and attributes even when application views opt out."""
        payload = '"><script>probe()</script><img src=x onerror="probe()"> & Español'
        self.fixture.settings["app.name"] = payload
        self.fixture.settings["app.locale"] = payload
        self.fixture.settings["view"]["autoescape"] = False
        (self.directory / "app.html").write_text("{{ value }}", encoding="utf-8")
        engine = Jinja2Engine(ViewEnvironment(self.fixture))
        defaults = DefaultResponses(self.fixture, self.fixture, engine)
        for response in (
            await defaults.health(_Request(wants_json=False)),
            await defaults.error(500, payload, expects_json=False),
        ):
            page = _Page(response.getBody())
            self.assertIn(payload, "".join(page.text))
            html_attrs = next(attrs for tag, attrs in page.elements if tag == "html")
            self.assertEqual(html_attrs["lang"], payload)
            self._assertLocalResources(page)
            self.assertNotIn(b"<script>probe()", response.getBody())
        self.assertEqual(await engine.render("app", {"value": payload}), payload)

    async def testExceptionDetailsAndSourceRenderAsText(self) -> None:
        """Keep request data, exception messages and source snippets out of scripts."""
        payload = '</script><script>probe()</script><img src=x onerror="probe()">'
        source_payload = f"source = {payload!r}"
        traceback_data = {
            "error_type": f"Error{payload}",
            "error_message": f"Message{payload}",
            "error_code": None,
            "stack_trace": [
                {
                    "id": 1,
                    "filename": f"source{payload}.py",
                    "lineno": 7,
                    "name": f"function{payload}",
                    "line_code": source_payload,
                    "code": [source_payload],
                    "lines": [7],
                    "code_with_lines": [f"7:{source_payload}"],
                },
            ],
        }
        self.fixture.settings["view"]["autoescape"] = False
        self.defaults = DefaultResponses(
            self.fixture,
            self.fixture,
            Jinja2Engine(ViewEnvironment(self.fixture)),
        )
        def parse_data(_parser: ExceptionParser) -> dict[str, object]:
            """Supply hostile source and exception data to the actual renderer."""
            return traceback_data

        with replace_attribute(ExceptionParser, "toDict", parse_data):
            response = await self.defaults.exception(
                f"/request{payload}", f"GET{payload}", ValueError(payload),
            )
        page = _Page(response.getBody())
        text = "".join(page.text)
        for value in (
            f"/request{payload}",
            f"GET{payload}",
            f"Message{payload}",
            f"source{payload}.py",
            source_payload,
        ):
            self.assertIn(value, text)
        self.assertIn(payload, text)
        self.assertEqual(response.getStatusCode(), 500)
        self.assertNotIn(b"<script>probe()", response.getBody())
        self.assertNotIn("img", [tag for tag, _ in page.elements])
        self._assertLocalResources(page)

    async def testConcurrentErrorRendersKeepDescriptionsAndHeadersSeparate(
        self,
    ) -> None:
        """Reuse compiled templates without leaking per-request values or headers."""
        descriptions = [f"request-{index:02d}-<tag>" for index in range(12)]
        responses = await asyncio.gather(
            *[
                self.defaults.error(
                    500, value, expects_json=False, headers={"x-request": str(index)},
                )
                for index, value in enumerate(descriptions)
            ],
        )
        for index, response in enumerate(responses):
            text = "".join(_Page(response.getBody()).text)
            self.assertIn(descriptions[index], text)
            self.assertEqual(response.getHeader("x-request"), [str(index)])
            for other in descriptions:
                if other != descriptions[index]:
                    self.assertNotIn(other, text)

    async def testSuspendedErrorsAndExceptionsKeepTheirOwnContext(self) -> None:
        """Preserve each in-flight render's app labels and request-specific details."""
        for page in ("error", "exception"):
            with self.subTest(page=page):
                self.fixture.settings.update({
                    "app.name": "First application", "app.locale": "en",
                })
                engine = _SuspendedEngine(self.engine)
                defaults = DefaultResponses(self.fixture, self.fixture, engine)

                async def render_response(
                    message: str,
                    service: DefaultResponses = defaults,
                    template_page: str = page,
                ) -> Response:
                    """Render either error path through the same retained service."""
                    if template_page == "error":
                        return await service.error(404, message, expects_json=False)
                    return await service.exception(
                        f"/{message}", "POST", ValueError(message),
                    )

                pending = asyncio.create_task(render_response("first-details"))
                await asyncio.wait_for(engine.started.wait(), 2)
                try:
                    self.fixture.settings.update({
                        "app.name": "Second application", "app.locale": "es",
                    })
                    second = await render_response("second-details")
                finally:
                    engine.release.set()
                first = await asyncio.wait_for(pending, 2)
                for response, name, locale, own, other in (
                    (
                        first, b"First application", b"en",
                        b"first-details", b"second-details",
                    ),
                    (
                        second, b"Second application", b"es",
                        b"second-details", b"first-details",
                    ),
                ):
                    body = response.getBody()
                    self.assertIn(name, body)
                    self.assertIn(b'<html lang="' + locale + b'">', body)
                    self.assertIn(own, body)
                    self.assertNotIn(other, body)

    async def testAllPagesReferenceOneLocalStylesheetAndScript(self) -> None:
        """Render every page with the shared local bundle and no inline code."""
        responses = [await self.defaults.health(_Request(wants_json=False))]
        self.fixture.settings["app.maintenance"] = True
        responses.append(await self.defaults.health(_Request(wants_json=False)))
        responses.append(await self.defaults.error(404, "Missing", expects_json=False))
        responses.append(
            await self.defaults.exception("/test", "GET", ValueError("Example")),
        )
        for response in responses:
            self._assertLocalResources(_Page(response.getBody()))

    def _assertLocalResources(self, page: _Page) -> None:
        """Check rendered dependency URLs and executable browser attributes."""
        stylesheets = []
        scripts = []
        for tag, attrs in page.elements:
            self.assertNotEqual(tag, "style")
            self.assertNotIn("style", attrs)
            self.assertFalse(any(name.startswith("on") for name in attrs))
            if tag == "script":
                scripts.append(attrs.get("src"))
            if tag == "link" and attrs.get("rel") == "stylesheet":
                stylesheets.append(attrs.get("href"))
            if tag in {"script", "link", "img", "iframe", "source"}:
                for attr in ("src", "href"):
                    if attrs.get(attr):
                        value = attrs[attr]
                        self.assertFalse(urlsplit(value).netloc, value)
                        self.assertFalse(urlsplit(value).scheme, value)
                        self.assertTrue(
                            value.startswith(DefaultResponses.ASSET_PREFIX), value,
                        )
        self.assertEqual(stylesheets, [f"{DefaultResponses.ASSET_PREFIX}default.css"])
        self.assertEqual(scripts, [f"{DefaultResponses.ASSET_PREFIX}default.js"])
        self.assertFalse("".join(page.script_content).strip())

    async def testPackagedAssetsServeContentTypesAndIndependentStreams(self) -> None:
        """Make each locally referenced bundle or font available to browsers."""
        for name, content_type in (
            ("default.css", "text/css"),
            ("default.js", "text/javascript"),
            ("fonts/orbitron.ttf", "font/ttf"),
            ("fonts/share-tech-mono.ttf", "font/ttf"),
            ("fonts/fira-code.ttf", "font/ttf"),
            ("favicon.ico", "image/x-icon"),
        ):
            with self.subTest(asset=name):
                first = self.defaults.asset(name)
                second = self.defaults.asset(name)
                self.assertIsInstance(first, FileResponse)
                self.assertIsNot(first, second)
                self.assertEqual(first.getStatusCode(), 200)
                self.assertTrue(
                    first.getHeader("content-type")[0].startswith(content_type),
                )
                self.assertEqual(first.getHeader("x-content-type-options"), ["nosniff"])
                self.assertEqual(
                    first.getHeader("cache-control"), ["public, max-age=3600"],
                )
                first.setHeader("x-private", "first")
                self.assertFalse(second.hasHeader("x-private"))
                contents = await asyncio.gather(
                    self._consume(first), self._consume(second),
                )
                self.assertTrue(contents[0])
                self.assertEqual(contents[0], contents[1])

    async def testMissingPublicFilesAwaitTheirErrorPage(self) -> None:
        """Render all three missing-file fallbacks rather than returning coroutines."""
        engine = _RecordingEngine("<main>Missing asset</main>")
        defaults = local_defaults(self.fixture, engine, self.directory / "absent")
        for method in (defaults.favicon, defaults.robotsTxt, defaults.sitemapXml):
            response = await method()
            self.assertEqual(response.getStatusCode(), 404)
            self.assertEqual(response.getBody(), b"<main>Missing asset</main>")
        self.assertEqual(len(engine.calls), 3)
        for template, _context in engine.calls:
            self.assertEqual(template, "__orionis__/default/error.html")

    async def testAssetCacheRechecksCreatedChangedAndRemovedFiles(self) -> None:
        """Cache asset locations while observing filesystem changes on every request."""
        assets = self.directory / "assets"
        assets.mkdir()
        defaults = local_defaults(self.fixture, self.engine, assets)
        path = assets / "default.css"
        self.assertEqual(defaults.asset("default.css").getStatusCode(), 404)
        path.write_bytes(b"initial")
        first = defaults.asset("default.css")
        self.assertEqual(await self._consume(first), b"initial")
        first.setHeader("x-private", "first")
        path.write_bytes(b"updated stylesheet")
        second = defaults.asset("default.css")
        self.assertIsNot(first, second)
        self.assertFalse(second.hasHeader("x-private"))
        self.assertEqual(second.getHeader("content-length"), ["18"])
        self.assertEqual(await self._consume(second), b"updated stylesheet")
        path.unlink()
        self.assertEqual(defaults.asset("default.css").getStatusCode(), 404)
        path.mkdir()
        self.assertEqual(defaults.asset("default.css").getStatusCode(), 404)
        path.rmdir()
        path.write_bytes(b"restored")
        restored = defaults.asset("default.css")
        self.assertEqual(await self._consume(restored), b"restored")

    def testKnownAssetTypeAvoidsMimeGuessingAndDuplicateStat(self) -> None:
        """Validate each packaged asset once and use its already-known MIME type."""
        original_stat = Path.stat
        inspected: list[Path] = []

        def record_stat(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
            """Record filesystem validation while preserving actual file metadata."""
            inspected.append(path)
            return original_stat(path, follow_symlinks=follow_symlinks)

        def reject_guess(_path: object, *, strict: bool = True) -> tuple[str, None]:
            """Fail if a response guesses metadata already known to the asset map."""
            self.fail(f"Unexpected MIME lookup with strict={strict}")

        with (
            replace_attribute(Path, "stat", record_stat),
            replace_attribute(mimetypes, "guess_file_type", reject_guess),
        ):
            for name in ("default.css", "default.js", "fonts/orbitron.ttf"):
                for _request in range(2):
                    inspected.clear()
                    response = self.defaults.asset(name)
                    self.assertIsInstance(response, FileResponse)
                    self.assertEqual(inspected, [response.getPath()])

    async def testCachedPublicFilesRecoverAfterTheirRemoval(self) -> None:
        """Replace stale public paths with packaged fallbacks or a rendered 404."""
        assets = self.directory / "fallbacks"
        assets.mkdir()
        (assets / "favicon.ico").write_bytes(b"fallback icon")
        (assets / "robots.txt").write_bytes(b"fallback robots")
        defaults = local_defaults(self.fixture, self.engine, assets)
        for filename, method, fallback in (
            ("favicon.ico", defaults.favicon, b"fallback icon"),
            ("robots.txt", defaults.robotsTxt, b"fallback robots"),
            ("sitemap.xml", defaults.sitemapXml, None),
        ):
            with self.subTest(filename=filename):
                public = self.directory / filename
                public.write_bytes(b"public version")
                initial = await method()
                self.assertEqual(await self._consume(initial), b"public version")
                public.unlink()
                recovered = await method()
                if fallback is None:
                    self.assertEqual(recovered.getStatusCode(), 404)
                else:
                    self.assertEqual(await self._consume(recovered), fallback)
                    (assets / filename).unlink()
                    missing = await method()
                    self.assertEqual(missing.getStatusCode(), 404)
                public.write_bytes(b"restored public")
                restored = await method()
                self.assertEqual(await self._consume(restored), b"restored public")

    def testAssetAllowlistRejectsTraversalAndUnrelatedFiles(self) -> None:
        """Refuse paths that could expose package source or arbitrary local files."""
        for name in (
            "../responses.py",
            "../../view/engine.py",
            "../pages/base.html",
            "fonts/../../responses.py",
            "fonts\\..\\..\\responses.py",
            "%2e%2e/responses.py",
            "/default.css",
            "C:\\Windows\\win.ini",
            "default.css/",
            "default.css?anything",
            "fonts/OFL.txt",
            "robots.txt",
        ):
            with self.subTest(asset=name):
                response = self.defaults.asset(name)
                self.assertEqual(response.getStatusCode(), 404)
                self.assertNotIsInstance(response, FileResponse)

    async def testCssFontUrlsResolveToPackagedAssets(self) -> None:
        """Ensure fonts load locally without network imports or missing files."""
        css = (await self._consume(self.defaults.asset("default.css"))).decode("utf-8")
        self.assertNotIn("@import", css)
        urls = [
            next(value for value in groups if value)
            for groups in re.findall(
                r"""url\(\s*(?:"([^"]*)"|'([^']*)'|([^)]*))\s*\)""", css,
            )
        ]
        self.assertTrue(urls)
        for url in urls:
            if url.startswith("data:image/svg+xml,"):
                continue
            self.assertFalse(urlsplit(url).netloc, url)
            self.assertFalse(urlsplit(url).scheme, url)
            name = url.removeprefix(DefaultResponses.ASSET_PREFIX)
            self.assertIsInstance(self.defaults.asset(name), FileResponse)

    @staticmethod
    async def _consume(response: FileResponse) -> bytes:
        """Collect a file response through its asynchronous public stream API."""
        return b"".join([chunk async for chunk in response.getStream()])
