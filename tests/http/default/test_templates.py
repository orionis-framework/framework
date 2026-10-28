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
from orionis.console.output.var_dumper import VarDumper
from orionis.http.default.responses import DefaultResponses
from orionis.http.responses import FileResponse, Response
from orionis.support.formatter.exceptions.parser import ExceptionParser
from orionis.test import TestCase
from orionis.view.engine import Jinja2Engine
from orionis.view.environment import ViewEnvironment
from tests.http.default.test_response_cache import (
    _DefaultFixture,
    _RecordingEngine,
    _Request,
)
from tests.http.test_support import replace_attribute

if TYPE_CHECKING:
    import os

class _Page(HTMLParser):
    """Expose actual browser contexts in rendered pages for security checks."""

    def __init__(self, content: bytes) -> None:
        """
        Parse rendered HTML into attributes, text, and script contents.

        Parameters
        ----------
        content : bytes
            UTF-8 encoded HTML document to inspect.

        Returns
        -------
        None
            Populate the parsed element, text, and script collections.
        """
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
        """
        Record start-tag attributes and begin collecting script content.

        Parameters
        ----------
        tag : str
            Parsed HTML element name.
        attrs : list[tuple[str, str | None]]
            Parsed attribute names and decoded values.

        Returns
        -------
        None
            Append the element and track whether it opens a script.
        """
        self.elements.append((tag, dict(attrs)))
        if tag == "script":
            self._in_script = True

    def handleEndTag(self, tag: str) -> None:
        """
        Stop collecting script content when a script element closes.

        Parameters
        ----------
        tag : str
            Parsed closing element name.

        Returns
        -------
        None
            Clear the script-content flag for closing script tags.
        """
        if tag == "script":
            self._in_script = False

    def handleData(self, data: str) -> None:
        """
        Collect decoded text and any active script content.

        Parameters
        ----------
        data : str
            Decoded text node supplied by the HTML parser.

        Returns
        -------
        None
            Append text to the page and, when applicable, script collections.
        """
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
        """
        Initialize render coordination around the supplied view engine.

        Parameters
        ----------
        engine : Jinja2Engine
            Rendering engine used after the first call is released.

        Returns
        -------
        None
            Create start and release events with a zeroed call counter.
        """
        self.engine = engine
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.calls = 0

    async def render(self, template: str, context: dict[str, object]) -> str:
        """
        Pause the first render until its release event is set.

        Parameters
        ----------
        template : str
            Template name forwarded to the wrapped engine.
        context : dict[str, object]
            Values forwarded unchanged to the wrapped engine.

        Returns
        -------
        str
            Markup returned by the wrapped rendering engine.
        """
        self.calls += 1
        if self.calls == 1:
            self.started.set()
            await self.release.wait()
        return await self.engine.render(template, context)

def local_defaults(
    fixture: _DefaultFixture, engine: object, assets: Path,
) -> DefaultResponses:
    """
    Create default responses with an isolated asset directory.

    Parameters
    ----------
    fixture : _DefaultFixture
        Application fixture providing paths and settings.
    engine : object
        Rendering engine injected into the response service.
    assets : Path
        Asset root assigned only to the local response subclass.

    Returns
    -------
    DefaultResponses
        Response service using the fixture, engine, and isolated asset root.
    """

    class LocalDefaults(DefaultResponses):
        __slots__ = ()
        _ASSETS_DIR = assets

    return LocalDefaults(fixture, fixture, engine)

class TestDefaultTemplates(TestCase):
    """Exercise default pages through the public framework rendering engine."""

    def setUp(self) -> None:
        """
        Initialize real templates and isolated application views.

        Returns
        -------
        None
            Store a temporary fixture, view engine, and response service.
        """
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.fixture = _DefaultFixture(self.directory)
        self.engine = Jinja2Engine(ViewEnvironment(self.fixture))
        self.defaults = DefaultResponses(self.fixture, self.fixture, self.engine)

    async def testHealthStatusAndJsonRemainConsistentWithMaintenance(self) -> None:
        """
        Verify health status and JSON labels across maintenance changes.

        Returns
        -------
        None
            This test does not return a value.
        """
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
        """
        Verify that retained health services refresh labels and locale.

        Returns
        -------
        None
            This test does not return a value.
        """
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
        """
        Verify that stale health renders cannot replace newer cached markup.

        Returns
        -------
        None
            This test does not return a value.
        """
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
        """
        Verify that every built-in HTML page uses the injected view engine.

        Returns
        -------
        None
            This test does not return a value.
        """
        engine = _RecordingEngine()
        defaults = DefaultResponses(self.fixture, self.fixture, engine)
        await defaults.health(_Request(wants_json=False))
        self.fixture.settings["app.maintenance"] = True
        await defaults.health(_Request(wants_json=False))
        await defaults.error(404, "Missing", expects_json=False)
        await defaults.exception("/missing", "GET", ValueError("Broken"))
        response = await defaults.dump("<pre>value</pre>")
        self.assertEqual(response.getBody(), b"<main>Injected engine</main>")
        self.assertEqual(
            [template for template, _context in engine.calls],
            [
                "__orionis__/default/up.html",
                "__orionis__/default/down.html",
                "__orionis__/default/error.html",
                "__orionis__/default/exception.html",
                "__orionis__/default/dump.html",
            ],
        )

    async def testDumpUsesDiagnosticLayoutWithoutDoubleEscaping(self) -> None:
        """
        Verify that dump pages share branding without double escaping.

        Returns
        -------
        None
            This test does not return a value.
        """
        fragment = VarDumper().values({"message": "Hola"}).toHtml()
        response = await self.defaults.dump(fragment)
        body = response.getBody()

        self.assertEqual(response.getStatusCode(), 200)
        self.assertEqual(
            response.getHeader("content-type"), ["text/html; charset=utf-8"],
        )
        self.assertEqual(response.getHeader("cache-control"), ["no-store"])
        self.assertTrue(body.startswith(b"<!DOCTYPE html>"))
        self.assertIn(b'<body class="page-dump">', body)
        self.assertIn(b'class="orionis-header"', body)
        self.assertIn(b"<title>Variable Dump | Example</title>", body)
        self.assertIn(b"Debug dump", body)
        self.assertEqual(body.count(fragment.encode()), 1)
        self.assertIn(b"Hola", body)

    async def testDumpEscapesValuesAndLabelsWithAutoescapeDisabled(self) -> None:
        """
        Verify dump escaping when application autoescape is disabled.

        Returns
        -------
        None
            This test does not return a value.
        """
        payload = '"><script>probe()</script><img src=x onerror="probe()">'
        self.fixture.settings["app.name"] = payload
        self.fixture.settings["view"]["autoescape"] = False
        engine = Jinja2Engine(ViewEnvironment(self.fixture))
        defaults = DefaultResponses(self.fixture, self.fixture, engine)
        fragment = VarDumper().values(payload).toHtml()
        response = await defaults.dump(fragment)
        page = _Page(response.getBody())

        self.assertIn(payload, "".join(page.text))
        self.assertFalse("".join(page.script_content).strip())
        self.assertNotIn(b"<script>probe()", response.getBody())
        for tag, attrs in page.elements:
            self.assertFalse(any(name.startswith("on") for name in attrs))
            if tag == "img":
                self.assertEqual(
                    attrs.get("src"),
                    f"{DefaultResponses.ASSET_PREFIX}orionis-mark.png",
                )

    async def testDumpProvidesCopyActionTemplate(self) -> None:
        """
        Verify the accessible copy action and shared local script.

        Returns
        -------
        None
            This test does not return a value.
        """
        response = await self.defaults.dump("<pre>copy-value</pre>")
        page = _Page(response.getBody())
        templates = [
            attrs for tag, attrs in page.elements
            if tag == "template" and attrs.get("id") == "dump-copy-action"
        ]
        buttons = [
            attrs for tag, attrs in page.elements
            if tag == "button" and "data-copy-dump" in attrs
        ]
        statuses = [
            attrs for tag, attrs in page.elements
            if "data-dump-copy-status" in attrs
        ]

        self.assertEqual(len(templates), 1)
        self.assertEqual(len(buttons), 1)
        self.assertEqual(buttons[0].get("type"), "button")
        self.assertEqual(buttons[0].get("aria-label"), "Copy dump content")
        self.assertEqual(buttons[0].get("title"), "Copy dump content")
        self.assertEqual(len(statuses), 1)
        self.assertEqual(statuses[0].get("role"), "status")
        self._assertLocalResources(page)

    async def testFrameworkNamespaceCannotBeShadowedByApplicationViews(self) -> None:
        """
        Verify that application views cannot shadow built-in templates.

        Returns
        -------
        None
            This test does not return a value.
        """
        shadow = self.directory / "__orionis__" / "default"
        shadow.mkdir(parents=True)
        for filename in ("base.html", "up.html", "error.html"):
            (shadow / filename).write_text("SHADOWED TEMPLATE", encoding="utf-8")
        response = await self.defaults.health(_Request(wants_json=False))
        self.assertNotIn(b"SHADOWED TEMPLATE", response.getBody())
        self.assertIn(b"<!DOCTYPE html>", response.getBody())

    async def testBuiltinEscapingSurvivesDisabledApplicationAutoescape(self) -> None:
        """
        Verify that built-in pages escape labels despite disabled autoescape.

        Returns
        -------
        None
            This test does not return a value.
        """
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
        """
        Verify that exception details and source snippets render as text.

        Returns
        -------
        None
            This test does not return a value.
        """
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
            """
            Supply hostile traceback data to the real exception renderer.

            Parameters
            ----------
            _parser : ExceptionParser
                Unused parser instance bound by the patched instance method.

            Returns
            -------
            dict[str, object]
                Prepared traceback data with hostile source and exception text.
            """
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
        self.assertEqual(
            [attrs.get("src") for tag, attrs in page.elements if tag == "img"],
            [f"{DefaultResponses.ASSET_PREFIX}orionis-mark.png"],
        )
        self._assertLocalResources(page)

    async def testConcurrentErrorRendersKeepDescriptionsAndHeadersSeparate(
        self,
    ) -> None:
        """
        Verify that concurrent errors keep descriptions and headers separate.

        Returns
        -------
        None
            This test does not return a value.
        """
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
        """
        Verify that suspended error pages retain their request context.

        Returns
        -------
        None
            This test does not return a value.
        """
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
                    """
                    Render an error or exception through the retained service.

                    Parameters
                    ----------
                    message : str
                        Error description or exception detail for this request.
                    service : DefaultResponses, optional
                        Response service retained for the current subtest.
                    template_page : str, optional
                        Select an error for ``'error'``, otherwise an exception.

                    Returns
                    -------
                    Response
                        Rendered HTML error or exception response.
                    """
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
        """
        Verify that every page uses one local stylesheet and script.

        Returns
        -------
        None
            This test does not return a value.
        """
        responses = [await self.defaults.health(_Request(wants_json=False))]
        self.fixture.settings["app.maintenance"] = True
        responses.append(await self.defaults.health(_Request(wants_json=False)))
        responses.append(await self.defaults.error(404, "Missing", expects_json=False))
        responses.append(
            await self.defaults.exception("/test", "GET", ValueError("Example")),
        )
        responses.append(await self.defaults.dump("<pre>value</pre>"))
        for response in responses:
            self._assertLocalResources(_Page(response.getBody()))

    def _assertLocalResources(self, page: _Page) -> None:
        """
        Verify local asset URLs and the absence of inline executable code.

        Parameters
        ----------
        page : _Page
            Parsed page whose resources and attributes must be checked.

        Returns
        -------
        None
            Complete the shared-bundle, URL, and executable-content assertions.
        """
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
        """
        Verify asset content types, cache headers, and independent streams.

        Returns
        -------
        None
            This test does not return a value.
        """
        for name, content_type in (
            ("default.css", "text/css"),
            ("default.js", "text/javascript"),
            ("fonts/orbitron.ttf", "font/ttf"),
            ("fonts/share-tech-mono.ttf", "font/ttf"),
            ("fonts/fira-code.ttf", "font/ttf"),
            ("fonts/titillium-web-400-latin.woff2", "font/woff2"),
            ("fonts/titillium-web-400-latin-ext.woff2", "font/woff2"),
            ("fonts/titillium-web-600-latin.woff2", "font/woff2"),
            ("fonts/titillium-web-600-latin-ext.woff2", "font/woff2"),
            ("fonts/titillium-web-700-latin.woff2", "font/woff2"),
            ("fonts/titillium-web-700-latin-ext.woff2", "font/woff2"),
            ("orionis-mark.png", "image/png"),
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
        """
        Verify that missing public files yield awaited error responses.

        Returns
        -------
        None
            This test does not return a value.
        """
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
        """
        Verify that cached assets follow filesystem changes.

        Returns
        -------
        None
            This test does not return a value.
        """
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
        """
        Verify that known assets avoid MIME guesses and duplicate stat calls.

        Returns
        -------
        None
            This test does not return a value.
        """
        original_stat = Path.stat
        inspected: list[Path] = []

        def record_stat(path: Path, *, follow_symlinks: bool = True) -> os.stat_result:
            """
            Record each stat lookup while preserving the original result.

            Parameters
            ----------
            path : Path
                Asset path whose metadata is requested.
            follow_symlinks : bool, optional
                Whether to follow symbolic links; defaults to ``True``.

            Returns
            -------
            os.stat_result
                Metadata returned by the original ``Path.stat`` implementation.
            """
            inspected.append(path)
            return original_stat(path, follow_symlinks=follow_symlinks)

        def reject_guess(_path: object, *, strict: bool = True) -> tuple[str, None]:
            """
            Fail the test if a known asset triggers MIME guessing.

            Parameters
            ----------
            _path : object
                Unused path supplied by the MIME-guessing call.
            strict : bool, optional
                Flag included in the failure message; defaults to ``True``.

            Returns
            -------
            tuple[str, None]
                Never returned because any MIME lookup fails the test.

            Raises
            ------
            AssertionError
                Always raised to reject an unexpected MIME lookup.
            """
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
        """
        Verify that removed public files recover through fallbacks or 404s.

        Returns
        -------
        None
            This test does not return a value.
        """
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
        """
        Verify that the asset allowlist rejects traversal and unrelated files.

        Returns
        -------
        None
            This test does not return a value.
        """
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
        """
        Verify that stylesheet fonts resolve to local packaged assets.

        Returns
        -------
        None
            This test does not return a value.
        """
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
        """
        Collect a file response's asynchronous stream into bytes.

        Parameters
        ----------
        response : FileResponse
            File response whose stream should be consumed.

        Returns
        -------
        bytes
            All stream chunks concatenated in their original order.
        """
        return b"".join([chunk async for chunk in response.getStream()])
