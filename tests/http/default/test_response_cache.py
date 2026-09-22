from __future__ import annotations
import asyncio
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
