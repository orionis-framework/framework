from __future__ import annotations
import asyncio
import json
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from orionis.http.default.responses import DefaultResponses
from orionis.test import TestCase

if TYPE_CHECKING:
    from orionis.http.responses import FileResponse

class _DefaultFixture:

    def __init__(self, directory: Path) -> None:
        """
        Store the public directory and application configuration.

        Parameters
        ----------
        directory : Path
            Public directory containing the test assets.

        Returns
        -------
        None
            No return value.
        """
        self.directory = directory
        self.settings = {
            "app.name": "Example", "app.locale": "en", "app.maintenance": False,
        }

    def config(self, key: str) -> str | bool:
        """
        Return the requested configuration value.

        Parameters
        ----------
        key : str
            Configuration key to retrieve.

        Returns
        -------
        str | bool
            Stored configuration value.
        """
        return self.settings[key]

    def storagePublic(self) -> Path:
        """
        Return the public asset directory.

        Returns
        -------
        Path
            Configured public directory.
        """
        return self.directory

class _Request:

    def __init__(self, *, wants_json: bool) -> None:
        """
        Store the requested response format.

        Parameters
        ----------
        wants_json : bool
            Whether the request prefers a JSON response.

        Returns
        -------
        None
            No return value.
        """
        self.wants_json = wants_json

    def wantsJson(self) -> bool:
        """
        Return whether the request prefers JSON.

        Returns
        -------
        bool
            Whether JSON is requested.
        """
        return self.wants_json


class _ErrorPage(HTMLParser):
    """Collect markup, description text and scripts from an error page."""

    def __init__(self, content: bytes) -> None:
        """Parse the rendered UTF-8 page into observable browser contexts."""
        super().__init__(convert_charrefs=True)
        self.tags: list[str] = []
        self.description: list[str] = []
        self.scripts: list[str] = []
        self._in_description = False
        self._in_script = False
        self.feed(content.decode("utf-8"))
        self.close()

    def handleStartTag(
        self, tag: str, attrs: list[tuple[str, str | None]],
    ) -> None:
        """Record element structure and the active text context."""
        self.tags.append(tag)
        if ("class", "error-description") in attrs:
            self._in_description = True
        if tag == "script":
            self._in_script = True

    def handleEndTag(self, tag: str) -> None:
        """Leave the description or script context at its closing tag."""
        if tag == "div":
            self._in_description = False
        if tag == "script":
            self._in_script = False

    def handleData(self, data: str) -> None:
        """Collect text independently from HTML elements and script source."""
        if self._in_description:
            self.description.append(data)
        if self._in_script:
            self.scripts.append(data)

    # Bind the standard-library callbacks to the project's camelCase methods.
    handle_starttag = handleStartTag
    handle_endtag = handleEndTag
    handle_data = handleData


def _defaults(directory: Path) -> DefaultResponses:
    """
    Build the default response service with deterministic configuration.

    Parameters
    ----------
    directory : Path
        Public directory containing the test assets.

    Returns
    -------
    DefaultResponses
        Service configured for the test assets.
    """
    fixture = _DefaultFixture(directory)
    return DefaultResponses(fixture, fixture)


class TestDefaultResponseCache(TestCase):

    def testHealthResponsesDoNotShareMutableState(self) -> None:
        """Keep headers and flash data private to each health request."""
        with TemporaryDirectory() as directory:
            defaults = _defaults(Path(directory))
            for wants_json in (True, False):
                request = _Request(wants_json=wants_json)
                first = defaults.health(request)
                first.setHeader("x-private", "first")
                first.withFlash("message", "private")
                second = defaults.health(request)
                self.assertIsNot(first, second)
                self.assertEqual(first.getBody(), second.getBody())
                self.assertFalse(second.hasHeader("x-private"))
                self.assertIsNone(second.getFlashData())
                if not wants_json:
                    self.assertIs(first.getBody(), second.getBody())

    def testErrorDoesNotSerializeUnusedDetails(self) -> None:
        """Render an explicit message without serializing other fields."""
        with TemporaryDirectory() as directory:
            defaults = _defaults(Path(directory))
            result = defaults.error(
                500, {"message": "Readable", "opaque": object()}, expects_json=False,
            )
            self.assertIn(b"Readable", result.getBody())

    def testErrorRendersUntrustedDescriptionsAsText(self) -> None:
        """Keep payloads out of markup and scripts across cached renders."""
        payload = (
            '</script><script>probe()</script><img src=x onerror="probe()">'
            " 'quoted' & \"double\" \\ newline\nEspañol \u2028 \u2029"
        )
        with TemporaryDirectory() as directory:
            defaults = _defaults(Path(directory))
            baseline = _ErrorPage(
                defaults.error(500, "Safe", expects_json=False).getBody(),
            )
            for content, expected in (
                (payload, payload),
                ({"message": payload, "opaque": object()}, payload),
                ({"detail": payload}, json.dumps({"detail": payload})),
                ("&lt;unchanged&gt;", "&lt;unchanged&gt;"),
                ("Next response", "Next response"),
            ):
                with self.subTest(content=content):
                    parsed = _ErrorPage(
                        defaults.error(500, content, expects_json=False).getBody(),
                    )
                    self.assertEqual("".join(parsed.description), expected)
                    self.assertEqual(parsed.tags, baseline.tags)
                    self.assertEqual(parsed.scripts, baseline.scripts)

    def testErrorJsonPreservesDescriptionValues(self) -> None:
        """Keep JSON strings and structured fields independent of HTML escaping."""
        payload = '<em title="quoted">A&B</em>\nEspañol'
        with TemporaryDirectory() as directory:
            defaults = _defaults(Path(directory))
            for content, expected in (
                (payload, {"message": payload}),
                ({"message": payload, "code": 42}, {"message": payload, "code": 42}),
                ({"detail": payload}, {"detail": payload}),
            ):
                with self.subTest(content=content):
                    result = defaults.error(500, content, expects_json=True)
                    self.assertEqual(json.loads(result.getBody()), expected)

    def testErrorAcceptsKnownAndUnlistedStatusCodesInBothFormats(self) -> None:
        """Preserve custom status codes and existing labels on repeated renders."""
        with TemporaryDirectory() as directory:
            defaults = _defaults(Path(directory))
            for status, label in (
                (100, "Continue"), (404, "Not Found"), (419, "Page Expired"),
                (499, "HTTP 499"), (599, "HTTP 599"),
            ):
                with self.subTest(status=status):
                    for expects_json in (True, False, False):
                        result = defaults.error(
                            status, "Example", expects_json=expects_json,
                        )
                        self.assertEqual(result.getStatusCode(), status)
                        if not expects_json:
                            title = f'<div class="error-title">{label}</div>'
                            self.assertIn(title.encode(), result.getBody())

    def testErrorRejectsInvalidStatusesBeforeRendering(self) -> None:
        """Validate type and range before reading templates or converting content."""
        with TemporaryDirectory() as directory:
            defaults = _defaults(Path(directory))
            # A missing template directory exposes validation performed too late.
            defaults._PAGES_DIR = Path(directory) / "missing"
            for value, exception in (
                ("400", TypeError), (400.0, TypeError), (None, TypeError),
                (-1, ValueError), (99, ValueError), (600, ValueError),
                (True, ValueError), (False, ValueError),
            ):
                for expects_json in (True, False):
                    with (
                        self.subTest(value=value, expects_json=expects_json),
                        self.assertRaises(exception),
                    ):
                        defaults.error(
                            value, {"opaque": object()}, expects_json=expects_json,
                        )

    def testErrorPreservesCallerHeaders(self) -> None:
        """Apply cache defaults without mutating the supplied mapping."""
        with TemporaryDirectory() as directory:
            defaults = _defaults(Path(directory))
            headers = {"x-test": "value"}
            result = defaults.error(500, "Error", expects_json=True, headers=headers)
            self.assertEqual(headers, {"x-test": "value"})
            self.assertTrue(result.hasHeader("cache-control"))
            result = defaults.error(
                500, "Error", expects_json=True, headers={"Cache-Control": "custom"},
            )
            self.assertEqual(result.getHeader("cache-control"), ["custom"])

    async def testCachedAssetsRemainIndependentAcrossConcurrentRequests(self) -> None:
        """Serve each cached asset through a fresh stream and header mapping."""
        with TemporaryDirectory() as directory:
            public = Path(directory)
            defaults = _defaults(public)
            for filename, method in (
                ("favicon.ico", defaults.favicon),
                ("robots.txt", defaults.robotsTxt),
                ("sitemap.xml", defaults.sitemapXml),
            ):
                content = filename.encode("ascii")
                (public / filename).write_bytes(content)
                first = method()
                first.setHeader("x-private", "first")
                second = method()
                self.assertIsNot(first, second)
                self.assertFalse(second.hasHeader("x-private"))

                async def consume(response: FileResponse) -> bytes:
                    """
                    Collect the response body from its asynchronous stream.

                    Parameters
                    ----------
                    response : FileResponse
                        Response whose stream is consumed.

                    Returns
                    -------
                    bytes
                        Byte content read from the stream.
                    """
                    return b"".join([part async for part in response.getStream()])

                self.assertEqual(
                    await asyncio.gather(consume(first), consume(second)),
                    [content, content],
                )
